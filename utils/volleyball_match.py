import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import json
import psycopg2.extras # 💡 Dictionary Access को लागि

# ==========================================
# 🏐 १. DB र खेलाडी तान्ने फङ्सनहरू
# ==========================================
def ensure_columns_exist():
    """PostgreSQL मा Column छ कि छैन भनेर चेक गर्ने सही तरिका"""
    conn = db.get_connection()
    c = conn.cursor()
    try:
        # Information Schema बाट column चेक गर्ने
        c.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name='matches'
        """)
        existing_columns = [row[0] for row in c.fetchall()]
        
        if 'score_summary' not in existing_columns: c.execute("ALTER TABLE matches ADD COLUMN score_summary TEXT")
        if 'winner_id' not in existing_columns: c.execute("ALTER TABLE matches ADD COLUMN winner_id TEXT")
        conn.commit()
    except Exception as e:
        print(f"Error checking columns: {e}")
        conn.rollback()
    finally:
        c.close()
        conn.close()

def fetch_team_players(event_code, team_name):
    """डाटाबेसबाट खेलाडी तान्ने सबैभन्दा सटिक तरिका"""
    conn = db.get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    clean_team = str(team_name).strip()
    
    # टिमको नामबाट पालिकाको ID पत्ता लगाउने (%s प्रयोग गरिएको)
    c.execute("SELECT municipality_id FROM teams WHERE event_code=%s AND name LIKE %s", (event_code, f"%{clean_team}%"))
    team_info = c.fetchone()
    
    if team_info and team_info['municipality_id']:
        muni_id = team_info['municipality_id']
        query = """SELECT p.name FROM registrations r JOIN players p ON r.player_id = p.id WHERE r.event_code = %s AND p.municipality_id = %s"""
        c.execute(query, (event_code, muni_id))
        players = c.fetchall()
        c.close(); conn.close()
        
        if players:
            return [p['name'] for p in players]
            
    c.close(); conn.close()
    return [f"Player {i}" for i in range(1, 13)]

def load_match_state(m_id, p1, p2):
    s_key = f"vb_state_{m_id}"
    if s_key not in st.session_state:
        st.session_state[s_key] = {
            "setup_complete": False, "p1_name": p1, "p2_name": p2,
            "current_set": 1, "sets_won": {p1: 0, p2: 0},
            "scores": {i: {p1: 0, p2: 0} for i in range(1, 6)},
            "timeouts": {i: {p1: 0, p2: 0} for i in range(1, 6)},
            "serving": p1, "status": "In Progress",
            "settings": {"points_per_set": 25, "best_of": 3},
            "roster": {p1: {}, p2: {}}, 
            "lineup": { p1: {"court": [], "bench": [], "captain": None, "libero": []}, p2: {"court": [], "bench": [], "captain": None, "libero": []} },
            "cards": {p1: {}, p2: {}} 
        }
    return s_key

def save_match_scores(event_code, match_id, state):
    ensure_columns_exist()
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE matches SET score_summary=%s WHERE match_no=%s AND event_code=%s", (json.dumps(state), match_id, event_code))
    conn.commit(); c.close(); conn.close()

def update_match_winner_in_db(event_code, match_id, winner_name, winner_id, final_score_str):
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE matches SET winner_team_id=%s, score_summary=%s, status='Completed' WHERE match_no=%s AND event_code=%s", (winner_id, final_score_str, match_id, event_code))
    conn.commit(); c.close(); conn.close()

def update_live_tv(event_name, state):
    c_set, p1, p2 = state['current_set'], state['p1_name'], state['p2_name']
    score_a, score_b = state['scores'][c_set][p1], state['scores'][c_set][p2]
    sets_a, sets_b = state['sets_won'][p1], state['sets_won'][p2]
    to_a, to_b = state['timeouts'][c_set][p1], state['timeouts'][c_set][p2]
    serving_team = 'A' if state['serving'] == p1 else 'B'
    
    conn = db.get_connection()
    c = conn.cursor()
    
    # PostgreSQL मा SERIAL प्रयोग हुन्छ
    c.execute('''CREATE TABLE IF NOT EXISTS vb_live_match (id SERIAL PRIMARY KEY, match_title TEXT, team_a TEXT, team_b TEXT, score_a INTEGER, score_b INTEGER, sets_a INTEGER, sets_b INTEGER, timeout_a INTEGER, timeout_b INTEGER, serving TEXT, state_json TEXT)''')
    
    # Information Schema बाट column चेक गर्ने
    c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='vb_live_match'")
    cols = [row[0] for row in c.fetchall()]
    if 'state_json' not in cols:
        c.execute("ALTER TABLE vb_live_match ADD COLUMN state_json TEXT")
        
    c.execute("DELETE FROM vb_live_match") # सबै पुरानो डाटा हटाउने (ID 1 मात्र नभई)
    c.execute("INSERT INTO vb_live_match (match_title, team_a, team_b, score_a, score_b, sets_a, sets_b, timeout_a, timeout_b, serving, state_json) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                 (event_name, p1, p2, score_a, score_b, sets_a, sets_b, to_a, to_b, serving_team, json.dumps(state)))
    conn.commit(); c.close(); conn.close()

    prev_scores = [f"S{s}({state['scores'][s][p1]}-{state['scores'][s][p2]})" for s in range(1, c_set)]
    history_str = f" | History: {' | '.join(prev_scores)}" if prev_scores else ""
    ls.update_live_match(event_name, p1, p2, str(score_a), str(score_b), status=f"Set {c_set} | Sets Won: {sets_a} - {sets_b}{history_str}", is_kumite=False)

# ==========================================
# 🏐 २. अपरेटर कोर्ट UI (Horizontal)
# ==========================================
def render_operator_court(state, p1, p2):
    """अपरेटर प्यानलको लागि ठिक्कको (Horizontal) कोर्ट (Swap फिचरसहित)"""
    left_team = p2 if state.get('ui_swapped', False) else p1
    right_team = p1 if state.get('ui_swapped', False) else p2
    
    st.markdown("""
    <style>
        .arena { display: flex; justify-content: center; align-items: center; width: 100%; gap: 15px; margin: 10px 0; }
        .bench { display: flex; flex-direction: column; gap: 5px; background: #334155; padding: 10px; border-radius: 10px; min-width: 50px; align-items: center; }
        .bench-title { color: white; font-size: 10px; font-weight: bold; margin-bottom: 5px; }
        .vb-court-op { display: flex; width: 100%; max-width: 650px; aspect-ratio: 2/1; background-color: #f17b37; border: 3px solid white; position: relative; box-shadow: 0 5px 10px rgba(0,0,0,0.2); }
        .net-line-op { position: absolute; top: -5px; bottom: -5px; left: 50%; width: 8px; background-color: #1e3a8a; transform: translateX(-50%); z-index: 10; border-left: 2px solid white; border-right: 2px solid white; }
        .half-op { width: 50%; height: 100%; position: relative; }
        .attack-left { position: absolute; top: 0; bottom: 0; right: 33.33%; border-right: 3px dashed white; }
        .attack-right { position: absolute; top: 0; bottom: 0; left: 33.33%; border-left: 3px dashed white; }
        .p-dot { position: absolute; width: 35px; height: 35px; border-radius: 50%; background: white; color: black; font-weight: bold; font-size: 14px; display: flex; justify-content: center; align-items: center; transform: translate(-50%, -50%); border: 2px solid #334155; z-index: 5; box-shadow: 1px 1px 3px rgba(0,0,0,0.5);}
        .p-dot-bench { position: relative; width: 30px; height: 30px; transform: none; font-size: 12px; }
        .libero { background-color: #fbbf24 !important; color: #78350f !important; }
        .captain { border-style: double !important; border-width: 4px !important; border-color: #1e293b !important; }
        .serving-dot { border-color: #fbbf24 !important; box-shadow: 0 0 8px 3px #fbbf24 !important; }
        .card-badge { position: absolute; top: -4px; right: -4px; width: 12px; height: 16px; border-radius: 2px; border: 1px solid black; z-index: 15; }
        .card-Yellow { background-color: #fde047; }
        .card-Red { background-color: #ef4444; }
        .card-Expulsion { background: linear-gradient(135deg, #ef4444 50%, #fde047 50%); }
        .card-Disqualified { background: black; border: 1px solid white; }
    </style>
    """, unsafe_allow_html=True)
    
    pos_a = {0:("20%","80%"), 1:("80%","80%"), 2:("80%","50%"), 3:("80%","20%"), 4:("20%","20%"), 5:("40%","50%")}
    pos_b = {0:("80%","20%"), 1:("20%","20%"), 2:("20%","50%"), 3:("20%","80%"), 4:("80%","80%"), 5:("60%","50%")}

    def make_dot(team, num, is_court=True, idx=-1, is_left_side=True):
        cls = ["p-dot" if is_court else "p-dot p-dot-bench"]
        if num in state['lineup'][team]['libero']: cls.append("libero")
        if num == state['lineup'][team]['captain']: cls.append("captain")
        if is_court and state['serving'] == team and idx == 0: cls.append("serving-dot")
        
        pos_map = pos_a if is_left_side else pos_b
        style = f"left:{pos_map[idx][0]}; top:{pos_map[idx][1]};" if is_court else ""
        
        card = state['cards'][team].get(num)
        card_html = f'<div class="card-badge card-{card}" title="{card} Card"></div>' if card else ""
        name = state['roster'][team].get(num, num)
        return f'<div class="{" ".join(cls)}" style="{style}" title="{name}">{num}{card_html}</div>'

    html = '<div class="arena">'
    # बायाँ (Left) टिम
    html += f'<div class="bench"><div class="bench-title">BENCH</div>{"".join([make_dot(left_team, n, False) for n in state["lineup"][left_team]["bench"]])}</div>'
    html += '<div class="vb-court-op"><div class="net-line-op"></div>'
    html += '<div class="half-op"><div class="attack-left"></div>' + "".join([make_dot(left_team, n, True, i, is_left_side=True) for i, n in enumerate(state['lineup'][left_team]['court'])]) + '</div>'
    
    # दायाँ (Right) टिम
    html += '<div class="half-op"><div class="attack-right"></div>' + "".join([make_dot(right_team, n, True, i, is_left_side=False) for i, n in enumerate(state['lineup'][right_team]['court'])]) + '</div>'
    html += '</div>'
    html += f'<div class="bench"><div class="bench-title">BENCH</div>{"".join([make_dot(right_team, n, False) for n in state["lineup"][right_team]["bench"]])}</div></div>'
    
    st.markdown(html, unsafe_allow_html=True)

# ==========================================
# 🏐 ३. मुख्य रेन्डर फङ्सन
# ==========================================
def render_match(event_code, match):
    m_id, p1, p2 = match['id'], match['p1'], match['p2']
    
    conn = db.get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT name, gender FROM events WHERE code=%s", (event_code,))
    evt_info = c.fetchone()
    c.close(); conn.close()
    
    match_title = f"{evt_info['name']} ({evt_info['gender']}) - Match #{m_id}" if evt_info else f"Volleyball Match #{m_id}"

    s_key = load_match_state(m_id, p1, p2)
    state = st.session_state[s_key]

    # --- Match Rules Setup ---
    if state['status'] != "Completed":
        can_edit = (state['current_set'] == 1 and state['scores'][1][p1] == 0 and state['scores'][1][p2] == 0)
        with st.expander("⚙️ म्याच नियम (Rules)", expanded=can_edit):
            cr1, cr2 = st.columns(2)
            n_pts = cr1.selectbox("Points per Set:", [25, 15], index=0 if state['settings']['points_per_set']==25 else 1)
            n_bst = cr2.selectbox("Match Format:", [3, 5], index=0 if state['settings']['best_of']==3 else 1, format_func=lambda x: f"Best of {x}")
            if st.button("💾 अपडेट नियम"):
                state['settings']['points_per_set'] = n_pts
                state['settings']['best_of'] = n_bst
                save_match_scores(event_code, m_id, state); st.rerun()

    if state['status'] == "Completed":
        st.success(f"✅ यो म्याच सम्पन्न भइसकेको छ। विजेता: {match.get('winner')}")
        return

    # -------------------------------------------------------------
    # PHASE 1: LINE-UP MANAGER (Smart Table UI)
    # -------------------------------------------------------------
    if not state["setup_complete"]:
        st.info("📋 **खेलाडीको लाइन-अप (Line-up) तयार गर्नुहोस्। तलको टेबलमै जर्सी नम्बर भर्न र पोजिसन छान््न मिल्छ।**")
        c_t1, c_t2 = st.columns(2)
        
        def setup_team(team_name, col):
            with col:
                st.markdown(f"### 🏐 {team_name}")
                players = fetch_team_players(event_code, team_name)
                
                df_key = f"df_setup_{m_id}_{team_name}"
                if df_key not in st.session_state:
                    st.session_state[df_key] = pd.DataFrame({
                        "Player Name": players,
                        "Jersey": ["" for _ in players], 
                        "Position": ["Bench"] * len(players),
                        "Captain": [False] * len(players)
                    })

                config = {
                    "Player Name": st.column_config.TextColumn("खेलाडीको नाम", required=True),
                    "Jersey": st.column_config.TextColumn("जर्सी नं.", required=True, max_chars=3),
                    "Position": st.column_config.SelectboxColumn(
                        "पोजिसन (Position)",
                        options=["Bench", "Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5", "Zone 6", "Libero"],
                        required=True
                    ),
                    "Captain": st.column_config.CheckboxColumn("क्याप्टेन (C)", default=False)
                }

                st.caption("💡 *नयाँ खेलाडी थप्न परेमा टेबलको पुछारमा क्लिक गरेर सिधै टाइप गर्नुहोस्।*")
                edited_df = st.data_editor(
                    st.session_state[df_key],
                    column_config=config,
                    num_rows="dynamic",
                    key=f"editor_{m_id}_{team_name}",
                    use_container_width=True,
                    hide_index=True
                )

                valid = True
                error_msg = ""
                
                active_mask = edited_df['Position'] != "Bench"
                if edited_df[active_mask]['Jersey'].str.strip().eq("").any() or edited_df[active_mask]['Jersey'].isna().any():
                    valid = False
                    error_msg = "कोर्टमा जाने र लिबेरोको जर्सी नम्बर खाली छोड्न मिल्दैन।"
                else:
                    pos_counts = edited_df['Position'].value_counts()
                    for z in ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5", "Zone 6"]:
                        if pos_counts.get(z, 0) != 1:
                            valid = False
                            error_msg = f"सबै Zone (1 देखि 6) मा ठीक १-१ जना खेलाडी हुनुपर्छ। (अहिले '{z}' मिलेको छैन)"
                            break
                    
                    if valid and pos_counts.get("Libero", 0) > 2:
                        valid = False
                        error_msg = "बढीमा २ जना मात्र लिबेरो राख्न मिल्छ।"
                        
                    if valid and edited_df['Captain'].sum() != 1:
                        valid = False
                        error_msg = "टिममा ठ्याक्कै १ जना मात्र क्याप्टेन (Captain) हुनुपर्छ।"
                        
                    if valid:
                        active_jerseys = edited_df[active_mask]['Jersey'].astype(str).str.strip().tolist()
                        if len(active_jerseys) != len(set(active_jerseys)):
                            valid = False
                            error_msg = "एउटै जर्सी नम्बर दुई जना खेलाडीलाई दिन मिल्दैन।"

                if valid:
                    st.success("✅ लाइन-अप ठीक छ।")
                    clean_df = edited_df[edited_df['Player Name'].str.strip() != ""]
                    roster = {str(row['Jersey']).strip(): row['Player Name'] for _, row in clean_df.iterrows() if str(row['Jersey']).strip() != ""}
                    
                    starters = []
                    for z in ["Zone 1", "Zone 2", "Zone 3", "Zone 4", "Zone 5", "Zone 6"]:
                        z_j = clean_df[clean_df['Position'] == z]['Jersey'].iloc[0]
                        starters.append(str(z_j).strip())
                        
                    bench = clean_df[clean_df['Position'] == "Bench"]['Jersey'].astype(str).str.strip().tolist()
                    bench = [b for b in bench if b != ""]
                    liberos = clean_df[clean_df['Position'] == "Libero"]['Jersey'].astype(str).str.strip().tolist()
                    
                    cap_row = clean_df[clean_df['Captain'] == True]
                    captain_jersey = str(cap_row['Jersey'].iloc[0]).strip() if not cap_row.empty else None
                    
                    return roster, starters, bench, captain_jersey, liberos
                else:
                    st.error(f"⚠️ {error_msg}")
                    return None, [], [], None, []

        ta_rost, ta_start, ta_bench, ta_cap, ta_lib = setup_team(p1, c_t1)
        tb_rost, tb_start, tb_bench, tb_cap, tb_lib = setup_team(p2, c_t2)

        st.divider()
        if len(ta_start) == 6 and len(tb_start) == 6:
            if st.button("🚀 म्याच सुरु गर्नुहोस् (Start Match)", type="primary", use_container_width=True):
                state['roster'][p1], state['roster'][p2] = ta_rost, tb_rost
                state['lineup'][p1] = {"court": ta_start, "bench": ta_bench, "captain": ta_cap, "libero": ta_lib}
                state['lineup'][p2] = {"court": tb_start, "bench": tb_bench, "captain": tb_cap, "libero": tb_lib}
                state["setup_complete"] = True
                save_match_scores(event_code, m_id, state)
                try: update_live_tv(match_title, state) 
                except: pass
                st.rerun()
        return

    # -------------------------------------------------------------
    # PHASE 2: LIVE MATCH CONTROL
    # -------------------------------------------------------------
    c_set = state['current_set']
    st.markdown(f"### 🏐 Set {c_set} | 🔴 {p1} vs 🔵 {p2} (Best of {state['settings']['best_of']})")
    
    render_operator_court(state, p1, p2)
    st.divider()
    
    col1, col_vs, col2 = st.columns([2, 1, 2])
    
    def handle_point(scorer, loser):
        state['scores'][c_set][scorer] += 1
        if state['serving'] != scorer:
            state['serving'] = scorer
            c = state['lineup'][scorer]['court']
            state['lineup'][scorer]['court'] = [c[1], c[2], c[3], c[4], c[5], c[0]]
            
    left_team = p2 if state.get('ui_swapped', False) else p1
    right_team = p1 if state.get('ui_swapped', False) else p2

    def render_team_controls(team_name, col_obj, color_hex, is_p1):
        with col_obj:
            team_emoji = "🔴" if is_p1 else "🔵"
            st.markdown(f"<h3 style='color:{color_hex}; text-align:center;'>{team_emoji} {team_name}</h3><h1 style='font-size:50px; text-align:center;'>{state['scores'][c_set][team_name]}</h1>", unsafe_allow_html=True)
            if st.button(f"➕ Point ({team_name[:5]})", key=f"pt_{team_name}", type="primary", use_container_width=True): 
                handle_point(team_name, p2 if is_p1 else p1)
                save_match_scores(event_code, m_id, state); update_live_tv(match_title, state); st.rerun()
            if st.button(f"🔙 Undo ({team_name[:5]})", key=f"un_{team_name}", use_container_width=True): 
                state['scores'][c_set][team_name] = max(0, state['scores'][c_set][team_name]-1)
                save_match_scores(event_code, m_id, state); update_live_tv(match_title, state); st.rerun()

    render_team_controls(left_team, col1, "#dc2626" if left_team==p1 else "#2563eb", left_team==p1)
    render_team_controls(right_team, col2, "#dc2626" if right_team==p1 else "#2563eb", right_team==p1)

    with col_vs:
        st.markdown(f"<h4 style='text-align:center;'>Sets: <br>{state['sets_won'][left_team]} - {state['sets_won'][right_team]}</h4>", unsafe_allow_html=True)
        if st.button("↔️ Swap L/R", type="secondary", use_container_width=True):
            state['ui_swapped'] = not state.get('ui_swapped', False)
            save_match_scores(event_code, m_id, state)
            st.rerun()
            
        st.markdown("<p style='text-align:center; font-size:12px; margin-top:10px;'>Manual Rotate</p>", unsafe_allow_html=True)
        cr1, cr2 = st.columns(2)
        if cr1.button("L 🔄", use_container_width=True, key="rot_l"): 
            c=state['lineup'][left_team]['court']; state['lineup'][left_team]['court'] = [c[1],c[2],c[3],c[4],c[5],c[0]]; save_match_scores(event_code, m_id, state); st.rerun()
        if cr2.button("R 🔄", use_container_width=True, key="rot_r"): 
            c=state['lineup'][right_team]['court']; state['lineup'][right_team]['court'] = [c[1],c[2],c[3],c[4],c[5],c[0]]; save_match_scores(event_code, m_id, state); st.rerun()

    st.divider()
    
    # -------------------------------------------------------------
    # ⏱️ MATCH TIMER & BEEPER
    # -------------------------------------------------------------
    with st.expander("⏱️ म्याच टाइमर र अटो-बीप (Timeouts / Breaks)", expanded=False):
        tc1, tc2, tc3 = st.columns(3)
        
        if tc1.button("⏳ ३० सेकेन्ड (Time-Out)", use_container_width=True):
            st.session_state[f"timer_{m_id}"] = 30
            st.rerun()
        if tc2.button("⏱️ ६० सेकेन्ड (Set Break)", use_container_width=True):
            st.session_state[f"timer_{m_id}"] = 60
            st.rerun()
        if tc3.button("🛑 टाइमर बन्द गर्नुहोस्", use_container_width=True):
            st.session_state[f"timer_{m_id}"] = 0
            st.rerun()

        timer_val = st.session_state.get(f"timer_{m_id}", 0)
        
        if timer_val > 0:
            st.warning("⚠️ टाइमर चलिरहेको छ... (कृपया अन्य बटन नथिच्नुहोला)")
            st.markdown(f"""
            <div id="matchTimer" style="font-size:60px; font-weight:bold; color:#dc2626; text-align:center; padding:15px; background:#f1f5f9; border-radius:15px; border:3px solid #cbd5e1; margin-top:10px;">
                {timer_val}
            </div>
            
            <script>
                var t = {timer_val};
                var elem = document.getElementById('matchTimer');
                
                function playBuzzer() {{
                    var ctx = new (window.AudioContext || window.webkitAudioContext)();
                    function beep(freq, duration, delay) {{
                        var osc = ctx.createOscillator();
                        osc.type = 'square';
                        osc.frequency.value = freq;
                        osc.connect(ctx.destination);
                        osc.start(ctx.currentTime + delay);
                        osc.stop(ctx.currentTime + delay + duration);
                    }}
                    beep(500, 0.3, 0); 
                    beep(500, 0.6, 0.4);
                }}

                var timerId = setInterval(function() {{
                    t--;
                    if(t > 0) {{
                        elem.innerHTML = t + "<span style='font-size:30px;'>s</span>";
                    }} else {{
                        elem.innerHTML = "TIME UP!";
                        elem.style.backgroundColor = "#fecaca";
                        elem.style.borderColor = "#ef4444";
                        clearInterval(timerId);
                        playBuzzer();
                    }}
                }}, 1000);
            </script>
            """, unsafe_allow_html=True)
            st.stop() 

    # --- Subs & Cards ---
    cs1, cs2 = st.columns(2)
    with cs1:
        with st.expander("🔄 Substitution"):
            ts = st.radio("Team:", [p1, p2], key="st")
            cc1, cb1 = st.columns(2)
            op = cc1.selectbox("Court (Out):", state['lineup'][ts]['court'])
            ip = cb1.selectbox("Bench (In):", state['lineup'][ts]['bench'])
            if st.button("🔄 Swap Player", type="primary", use_container_width=True):
                c_idx, b_idx = state['lineup'][ts]['court'].index(op), state['lineup'][ts]['bench'].index(ip)
                state['lineup'][ts]['court'][c_idx], state['lineup'][ts]['bench'][b_idx] = ip, op
                save_match_scores(event_code, m_id, state); st.rerun()
                
    with cs2:
        with st.expander("⚠️ Disciplinary Cards"):
            tc = st.radio("Team:", [p1, p2], key="ct")
            ps = st.selectbox("Player:", state['lineup'][tc]['court'] + state['lineup'][tc]['bench'])
            cd = st.selectbox("Card:", ["Yellow", "Red", "Expulsion", "Disqualified"])
            if st.button("🚨 Issue Card", type="primary", use_container_width=True):
                state['cards'][tc][ps] = cd
                if cd == "Red":
                    opp = p2 if tc == p1 else p1
                    state['scores'][c_set][opp] += 1
                    state['serving'] = opp
                    update_live_tv(match_title, state)
                save_match_scores(event_code, m_id, state); st.rerun()

    # -------------------------------------------------------------
    # PHASE 3: 8-POINT SWITCH & SET OVER LOGIC
    # -------------------------------------------------------------
    pts_per_set = state['settings']['points_per_set']
    best_of = state['settings']['best_of']
    is_deciding_set = (c_set == best_of)
    p1_score, p2_score = state['scores'][c_set][p1], state['scores'][c_set][p2]
    target = 15 if is_deciding_set else pts_per_set

    if is_deciding_set and (p1_score == 8 or p2_score == 8):
        sw_key = f"switched_{m_id}_{c_set}"
        if not st.session_state.get(sw_key, False):
            st.error("⚠️ **निर्णायक सेटमा ८ अङ्क पुग्यो: कोर्ट परिवर्तन (Court Switch) को समय भयो!**")
            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("✅ कोर्ट परिवर्तन भयो (सुचारु गर्नुहोस्)", type="primary", use_container_width=True):
                    st.session_state[sw_key] = True; st.rerun()
            with cb2:
                if st.button("⏱️ ६० सेकेन्डको ब्रेक दिनुहोस्", use_container_width=True):
                    st.session_state[f"btimer_{m_id}"] = True; st.session_state[sw_key] = True; st.rerun()
            st.stop()

    if st.session_state.get(f"btimer_{m_id}", False):
        st.warning("⏱️ **ब्रेक टाइम चलिरहेको छ... (खेलाडीहरू कोर्ट परिवर्तन गर्दैछन्)**")
        st.markdown("""<div id="bt" style="font-size:50px; font-weight:bold; color:#dc2626; text-align:center; padding:20px; background:#f1f5f9; border-radius:10px;">60</div>
        <script>var t=60, e=document.getElementById('bt'), id=setInterval(()=>{if(t==0){clearTimeout(id);e.innerHTML="Time Up!";}else{e.innerHTML=t;t--;}},1000);</script>""", unsafe_allow_html=True)
        if st.button("▶️ ब्रेक अन्त्य गर्नुहोस्", type="primary", use_container_width=True):
            st.session_state[f"btimer_{m_id}"] = False; st.rerun()
        st.stop()

    if max(p1_score, p2_score) >= target and abs(p1_score - p2_score) >= 2:
        winner_set = p1 if p1_score > p2_score else p2
        st.markdown(f"<div style='background:#dcfce7; padding:20px; border-radius:10px; border:2px solid #22c55e; text-align:center; margin-bottom:20px;'><h2 style='color:#166534; margin:0;'>🛑 SET OVER!</h2><h3 style='color:#15803d; margin:10px 0;'>{winner_set} ले यो सेट जित्यो!</h3></div>", unsafe_allow_html=True)
        
        if st.button(f"✅ Set {c_set} नतिजा पक्का गर्नुहोस्", type="primary", use_container_width=True):
            state['sets_won'][winner_set] += 1
            if state['sets_won'][winner_set] >= (best_of // 2) + 1:
                state['status'] = "Completed"
                w_name = winner_set
                w_id = match['team1_id'] if w_name == p1 else match['team2_id'] # 💡 'p1_id' को सट्टा 'team1_id' (database.py मा team1_id छ)
                score_str = ", ".join([f"{state['scores'][s][p1]}-{state['scores'][s][p2]}" for s in range(1, c_set + 1)])
                
                update_match_winner_in_db(event_code, m_id, w_name, w_id, score_str)
                ls.clear_live_match()
                ls.trigger_match_result(f"Volleyball Match #{m_id}", w_name, p2 if w_name==p1 else p1, score_str)
                st.success(f"🎉 म्याच सम्पन्न! {w_name} विजयी।"); st.balloons()
            else:
                state['current_set'] += 1
            save_match_scores(event_code, m_id, state); update_live_tv(match_title, state); st.rerun()