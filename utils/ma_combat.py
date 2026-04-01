import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import utils.ma_bracket as ma_bracket # 💡 Bracket मा नतिजा पठाउन
from datetime import datetime
import time
import re
import psycopg2.extras
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components # 💡 साउन्डको लागि

# ==========================================
# 🎨 स्कोरबोर्डको लागि विशेष CSS
# ==========================================
st.markdown("""
<style>
    .score-card { padding: 20px; border-radius: 16px; text-align: center; box-shadow: 0 10px 20px rgba(0,0,0,0.15); color: white; }
    .score-blue { background: linear-gradient(145deg, #1e3a8a, #2563eb); border: 4px solid #1d4ed8; }
    .score-red { background: linear-gradient(145deg, #7f1d1d, #dc2626); border: 4px solid #b91c1c; }
    .score-number { font-size: 80px !important; font-weight: 900; margin: 0; line-height: 1; text-shadow: 2px 2px 4px rgba(0,0,0,0.4); }
    .player-title { font-size: 20px; font-weight: 600; margin-top: 10px; opacity: 0.9; }
    .penalty-box { background: #334155; color: #fbbf24; padding: 5px 10px; border-radius: 6px; font-size: 14px; font-weight: bold; margin-top: 10px; }
    .stButton button { font-weight: bold; border-radius: 8px; }
    .timer-box { background:#1e293b; color:#fbbf24; font-size:45px; font-weight:bold; text-align:center; border:3px solid #fbbf24; border-radius:10px; padding:0px 5px; font-family:monospace; margin-bottom:10px; }
</style>
""", unsafe_allow_html=True)

@st.fragment
def render_panel(evt_code, current_event, players_df, bout_info=None):
    grp = current_event.get('event_group', '')
    round_text = bout_info['r_name'] if bout_info else "Exhibition Match"
    bout_id_text = bout_info['id'] if bout_info else "0"
    
    st.header(f"🥊 {grp} Scoreboard - {round_text} {bout_id_text}")
    
    if players_df is None or players_df.empty:
        st.warning("⚠️ यस इभेन्टमा खेलाडी दर्ता भएका छैनन्।")
        return
        
    p_opts = {}
    for _, r in players_df.iterrows():
        p_name = r.get('Player_Name', r.get('name', 'Unknown'))
        m_name = r.get('Municipality', r.get('school_name', ''))
        p_id = r['id']
        m_id = r.get('mun_id', r.get('municipality_id', 0))
        label = f"{p_name} ({m_name})"
        p_opts[label] = {"p_id": p_id, "m_id": m_id, "full_label": f"{label} [ID:{p_id}] [M_ID:{m_id}]"}
    
    # --- State Initialization ---
    prefix = f"combat_{evt_code}_{bout_id_text}"
    MAX_TIME = 180.0 # ३ मिनेटको टाइमर
    
    if f"{prefix}_init" not in st.session_state:
        st.session_state.fight_scores = {
            'senshu': None,
            'r1_a': 0, 'r1_b': 0, 'r2_a': 0, 'r2_b': 0, 'r3_a': 0, 'r3_b': 0,
            'pen_a': 0, 'pen_b': 0  
        }
        st.session_state.fight_logs = []
        st.session_state[f"{prefix}_timer_running"] = False
        st.session_state[f"{prefix}_elapsed_time"] = 0.0
        st.session_state[f"{prefix}_last_start_time"] = None
        st.session_state[f"{prefix}_played_15s"] = False
        st.session_state[f"{prefix}_played_end"] = False
        st.session_state[f"{prefix}_init"] = True

    default_a_index = 0
    default_b_index = 1 if len(p_opts) > 1 else 0
    
    if bout_info:
        def get_clean_name(p_str):
             m = re.search(r"^(.*?)\s*\(", p_str)
             return m.group(1).strip() if m else str(p_str).split(" [ID:")[0]

        p1_name = get_clean_name(bout_info['p1'])
        p2_name = get_clean_name(bout_info['p2'])
        
        for idx, key in enumerate(p_opts.keys()):
            if p1_name.lower() in key.lower(): default_a_index = idx
            if p2_name.lower() in key.lower(): default_b_index = idx

    with st.container(border=True):
        c_a, c_b = st.columns(2)
        with c_a:
            p_a_label = st.selectbox("🔵 Player A (AO/Blue/Chung)", list(p_opts.keys()), index=default_a_index)
            p_a_info = p_opts[p_a_label]
        with c_b:
            p_b_label = st.selectbox("🔴 Player B (AKA/Red/Hong)", list(p_opts.keys()), index=default_b_index)
            p_b_info = p_opts[p_b_label]
            
        if p_a_info['p_id'] == p_b_info['p_id']:
            st.error("❌ कृपया दुई फरक खेलाडी छान्नुहोस्।")
            return
            
    st.divider()

    # ==========================================
    # ⏱️ ADVANCED TIMER & SOUND LOGIC
    # ==========================================
    if st.session_state[f"{prefix}_timer_running"]:
        current_time = time.time()
        added_time = current_time - st.session_state[f"{prefix}_last_start_time"]
        st.session_state[f"{prefix}_elapsed_time"] += added_time
        st.session_state[f"{prefix}_last_start_time"] = current_time
        st_autorefresh(interval=1000, key=f"timer_ref_{bout_id_text}")

    elapsed = st.session_state[f"{prefix}_elapsed_time"]
    remaining = max(0.0, MAX_TIME - elapsed)
    
    r_mins, r_secs = divmod(int(remaining), 60)
    timer_display_down = f"{r_mins:02d}:{r_secs:02d}"

    def play_beeps(type):
        js_code = ""
        if type == "15s": js_code = "playBeep(2, 0.2, 800);"
        elif type == "end": js_code = "playBeep(1, 1.0, 600);"
        components.html(f"""
        <script>
            function playBeep(times, duration, freq) {{
                let ctx = new (window.AudioContext || window.webkitAudioContext)();
                let i = 0;
                let interval = setInterval(() => {{
                    let osc = ctx.createOscillator(); osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime);
                    osc.connect(ctx.destination); osc.start();
                    osc.stop(ctx.currentTime + duration); i++;
                    if(i >= times) clearInterval(interval);
                }}, (duration * 1000) + 50);
            }}
            {js_code}
        </script>
        """, height=0, width=0)

    if int(remaining) == 15 and not st.session_state[f"{prefix}_played_15s"]:
        play_beeps("15s"); st.session_state[f"{prefix}_played_15s"] = True
    if remaining <= 0 and not st.session_state[f"{prefix}_played_end"]:
        st.session_state[f"{prefix}_elapsed_time"] = MAX_TIME
        st.session_state[f"{prefix}_timer_running"] = False
        play_beeps("end"); st.session_state[f"{prefix}_played_end"] = True

    # ==========================================
    # 📡 CLOUD DB SYNC LOGIC (Direct to PostgreSQL)
    # ==========================================
    def sync_to_db():
        tot_a = sum(st.session_state.fight_scores[f'r{i}_a'] for i in [1,2,3])
        tot_b = sum(st.session_state.fight_scores[f'r{i}_b'] for i in [1,2,3])
        conn = db.get_connection()
        c = conn.cursor()
        
        c.execute("SELECT id FROM live_match LIMIT 1")
        if not c.fetchone():
            c.execute("""
                INSERT INTO live_match (event_code, bout_id, event_name, round_name, player1, player2)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (evt_code, bout_id_text, current_event['name'], round_text, p_b_label.split('(')[0], p_a_label.split('(')[0]))
            
        c.execute("""
            UPDATE live_match 
            SET score_a=%s, score_b=%s, pen_a=%s, pen_b=%s, senshu=%s, timer=%s
        """, (tot_b, tot_a, st.session_state.fight_scores['pen_b'], st.session_state.fight_scores['pen_a'], st.session_state.fight_scores['senshu'], timer_display_down))
        conn.commit()
        c.close(); conn.close()

    if st.session_state[f"{prefix}_timer_running"] and int(elapsed) % 2 == 0:
        sync_to_db()

    def get_wkf2026_penalty_name(level):
        if level == 0: return "No Penalty"
        elif level == 1: return "Chui 1"
        elif level == 2: return "Chui 2"
        elif level == 3: return "Chui 3"
        elif level == 4: return "Hansoku-Chui"
        elif level >= 5: return "Hansoku"
        return ""

    def update(target, pts, action_name, rnd=1):
        st.session_state.fight_scores[f"r{rnd}_{target}"] += pts
        if grp == 'Kumite':
            opp = 'b' if target == 'a' else 'a'
            if pts > 0 and st.session_state.fight_scores['senshu'] is None and st.session_state.fight_scores[f'r1_{opp}'] == 0:
                col = 'Blue' if target == 'a' else 'Red'
                st.session_state.fight_scores['senshu'] = col
                st.session_state.fight_logs.insert(0, {"Time": datetime.now().strftime("%H:%M:%S"), "Side": "🌟", "Desc": f"Auto-Senshu ({col})"})

        st.session_state.fight_logs.insert(0, {"Time": datetime.now().strftime("%H:%M:%S"), "Side": "🔵" if target=='a' else "🔴", "Desc": f"{action_name} (+{pts})"})
        sync_to_db(); st.rerun()

    def add_pen(target, grp_type=""):
        st.session_state.fight_scores[f"pen_{target}"] += 1
        level = st.session_state.fight_scores[f"pen_{target}"]
        pen_name = get_wkf2026_penalty_name(level) if grp_type == 'Kumite' else "Foul"
        st.session_state.fight_logs.insert(0, {"Time": datetime.now().strftime("%H:%M:%S"), "Side": "🔵" if target=='a' else "🔴", "Desc": f"⚠️ Penalty ({pen_name})"})
        sync_to_db(); st.rerun()

    # ==========================================
    # 🎛️ TIMER UI RENDER
    # ==========================================
    c_t1, c_t2, c_t3 = st.columns([1, 2, 1])
    with c_t2: st.markdown(f"<div class='timer-box'>{timer_display_down}</div>", unsafe_allow_html=True)
    b_t1, b_t2, b_t3 = st.columns([1, 1, 1])
    with b_t1:
        if st.button("▶️ Start", width="stretch"): 
            st.session_state[f"{prefix}_timer_running"] = True; st.session_state[f"{prefix}_last_start_time"] = time.time(); st.rerun()
    with b_t2:
        if st.button("⏸️ Pause", width="stretch"): 
            st.session_state[f"{prefix}_timer_running"] = False; sync_to_db(); st.rerun()
    with b_t3:
        if st.button("🛑 End", type="primary", width="stretch"): 
            st.session_state[f"{prefix}_timer_running"] = False; sync_to_db(); st.rerun()
    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

    # =========================================================
    # 1. KUMITE (WKF 2026)
    # =========================================================
    if grp == 'Kumite':
        s_a = st.session_state.fight_scores['r1_a']
        s_b = st.session_state.fight_scores['r1_b']
        pen_a = st.session_state.fight_scores['pen_a']
        pen_b = st.session_state.fight_scores['pen_b']
        
        c_sa, c_mid, c_sb = st.columns([2, 1, 2])
        with c_sa:
            st.markdown(f"<div class='score-card score-blue'><h1 class='score-number'>{s_a}</h1><div class='player-title'>{p_a_label.split('(')[0]} (AO)</div></div>", unsafe_allow_html=True)
            if pen_a > 0: st.markdown(f"<div class='penalty-box'>⚠️ {get_wkf2026_penalty_name(pen_a)}</div>", unsafe_allow_html=True)
        with c_mid:
            st.markdown("<h2 style='text-align:center; color:#94a3b8; margin-top:20px;'>VS</h2>", unsafe_allow_html=True)
            senshu = st.session_state.fight_scores['senshu']
            if not senshu:
                c1, c2 = st.columns(2)
                if c1.button("🔵", help="Senshu AO"): st.session_state.fight_scores['senshu'] = 'Blue'; sync_to_db(); st.rerun()
                if c2.button("🔴", help="Senshu AKA"): st.session_state.fight_scores['senshu'] = 'Red'; sync_to_db(); st.rerun()
            else:
                col = "#2563eb" if senshu == 'Blue' else "#dc2626"
                st.markdown(f"<div style='text-align:center; background-color:{col}; color:white; padding:8px; border-radius:8px;'>SENSHU</div>", unsafe_allow_html=True)
                if st.button("❌", help="Remove Senshu"): st.session_state.fight_scores['senshu'] = None; sync_to_db(); st.rerun()
        with c_sb:
            st.markdown(f"<div class='score-card score-red'><h1 class='score-number'>{s_b}</h1><div class='player-title'>{p_b_label.split('(')[0]} (AKA)</div></div>", unsafe_allow_html=True)
            if pen_b > 0: st.markdown(f"<div class='penalty-box'>⚠️ {get_wkf2026_penalty_name(pen_b)}</div>", unsafe_allow_html=True)
            
        st.markdown("<br>", unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca:
            b1, b2, b3 = st.columns(3)
            if b1.button("👊 +1 Yuko", key="k1a"): update('a', 1, "Yuko")
            if b2.button("🦵 +2 Waza", key="k2a"): update('a', 2, "Waza-ari")
            if b3.button("💥 +3 Ippon", key="k3a"): update('a', 3, "Ippon")
            if pen_a < 5 and st.button(f"⚠️ Foul ➔ {get_wkf2026_penalty_name(pen_a+1)}", key="kpa"): add_pen('a', 'Kumite')
        with cb:
            r1, r2, r3 = st.columns(3)
            if r1.button("👊 +1 Yuko", key="k1b"): update('b', 1, "Yuko")
            if r2.button("🦵 +2 Waza", key="k2b"): update('b', 2, "Waza-ari")
            if r3.button("💥 +3 Ippon", key="k3b"): update('b', 3, "Ippon")
            if pen_b < 5 and st.button(f"⚠️ Foul ➔ {get_wkf2026_penalty_name(pen_b+1)}", key="kpb"): add_pen('b', 'Kumite')

    # =========================================================
    # 2. KYORUGI (Taekwondo)
    # =========================================================
    elif grp == 'Kyorugi':
        t1, t2, t3 = st.tabs(["Round 1", "Round 2", "Round 3"])
        def render_kyorugi_round(rn):
            ka, kb = f"r{rn}_a", f"r{rn}_b"
            sa, sb = st.session_state.fight_scores[ka], st.session_state.fight_scores[kb]
            c_a, c_m, c_b = st.columns([2, 1, 2])
            with c_a:
                st.markdown(f"<div class='score-card score-blue'><h1 class='score-number'>{sa}</h1></div>", unsafe_allow_html=True)
                if st.button("👊 Punch (+1)", key=f"tk_1a_{rn}"): update('a', 1, "Punch", rn)
                if st.button("🥋 Body (+2)", key=f"tk_2a_{rn}"): update('a', 2, "Body", rn)
                if st.button("🤕 Head (+3)", key=f"tk_3a_{rn}"): update('a', 3, "Head", rn)
                if st.button("⚠️ Gam-jeom", key=f"tk_ga_{rn}"): update('b', 1, "Gam-jeom", rn)
            with c_m: st.markdown(f"<h3 style='text-align:center;'>Round {rn}</h3>", unsafe_allow_html=True)
            with c_b:
                st.markdown(f"<div class='score-card score-red'><h1 class='score-number'>{sb}</h1></div>", unsafe_allow_html=True)
                if st.button("👊 Punch (+1)", key=f"tk_1b_{rn}"): update('b', 1, "Punch", rn)
                if st.button("🥋 Body (+2)", key=f"tk_2b_{rn}"): update('b', 2, "Body", rn)
                if st.button("🤕 Head (+3)", key=f"tk_3b_{rn}"): update('b', 3, "Head", rn)
                if st.button("⚠️ Gam-jeom", key=f"tk_gb_{rn}"): update('a', 1, "Gam-jeom", rn)
        with t1: render_kyorugi_round(1)
        with t2: render_kyorugi_round(2)
        with t3: render_kyorugi_round(3)

    # =========================================================
    # 3. SANDA (Wushu)
    # =========================================================
    elif grp == 'Sanda':
        t1, t2, t3 = st.tabs(["Round 1", "Round 2", "Round 3"])
        def render_sanda_round(rn):
            ka, kb = f"r{rn}_a", f"r{rn}_b"
            sa, sb = st.session_state.fight_scores[ka], st.session_state.fight_scores[kb]
            c_a, c_m, c_b = st.columns([2, 1, 2])
            with c_a:
                st.markdown(f"<div class='score-card score-blue'><h1 class='score-number'>{sa}</h1></div>", unsafe_allow_html=True)
                if st.button("👊 Hit (+1)", key=f"sd_1a_{rn}"): update('a', 1, "Hit", rn)
                if st.button("🤼 Throw (+2)", key=f"sd_2a_{rn}"): update('a', 2, "Throw", rn)
            with c_m: st.markdown(f"<h3 style='text-align:center;'>Round {rn}</h3>", unsafe_allow_html=True)
            with c_b:
                st.markdown(f"<div class='score-card score-red'><h1 class='score-number'>{sb}</h1></div>", unsafe_allow_html=True)
                if st.button("👊 Hit (+1)", key=f"sd_1b_{rn}"): update('b', 1, "Hit", rn)
                if st.button("🤼 Throw (+2)", key=f"sd_2b_{rn}"): update('b', 2, "Throw", rn)
        with t1: render_sanda_round(1)
        with t2: render_sanda_round(2)
        with t3: render_sanda_round(3)

    # =========================================================
    # 🏁 Match Log & Save Result
    # =========================================================
    st.divider()
    with st.expander("📝 Match Log & Activity History", expanded=False):
        if st.session_state.fight_logs:
            st.dataframe(pd.DataFrame(st.session_state.fight_logs), width="stretch", hide_index=True)
            
    c_res, c_rst = st.columns([3, 1])
    with c_res:
        if st.button("💾 Save Match Result to Bracket", type="primary", width="stretch"):
            win_info = None
            winner_full_name_for_bracket = ""
            
            if grp == 'Kumite':
                s_a = st.session_state.fight_scores['r1_a']
                s_b = st.session_state.fight_scores['r1_b']
                pen_a = st.session_state.fight_scores['pen_a']
                pen_b = st.session_state.fight_scores['pen_b']
                
                if pen_a >= 5: win_info = p_b_info; winner_full_name_for_bracket = bout_info['p2'] if bout_info else p_b_info['full_label']
                elif pen_b >= 5: win_info = p_a_info; winner_full_name_for_bracket = bout_info['p1'] if bout_info else p_a_info['full_label']
                elif s_a > s_b: win_info = p_a_info; winner_full_name_for_bracket = bout_info['p1'] if bout_info else p_a_info['full_label']
                elif s_b > s_a: win_info = p_b_info; winner_full_name_for_bracket = bout_info['p2'] if bout_info else p_b_info['full_label']
                elif s_a == s_b and st.session_state.fight_scores['senshu']:
                    win_info = p_a_info if st.session_state.fight_scores['senshu'] == 'Blue' else p_b_info
                    winner_full_name_for_bracket = bout_info['p1'] if (bout_info and win_info == p_a_info) else (bout_info['p2'] if bout_info else (p_a_info['full_label'] if win_info == p_a_info else p_b_info['full_label']))
            else:
                tot_a = sum(st.session_state.fight_scores[f'r{i}_a'] for i in [1,2,3])
                tot_b = sum(st.session_state.fight_scores[f'r{i}_b'] for i in [1,2,3])
                if tot_a > tot_b: win_info = p_a_info; winner_full_name_for_bracket = bout_info['p1'] if bout_info else p_a_info['full_label']
                elif tot_b > tot_a: win_info = p_b_info; winner_full_name_for_bracket = bout_info['p2'] if bout_info else p_b_info['full_label']

            if win_info:
                lose_info = p_b_info if win_info == p_a_info else p_a_info
                
                if bout_info:
                    st.session_state[f"winner_{evt_code}_{bout_info['id']}"] = winner_full_name_for_bracket
                    st.session_state[f"published_{evt_code}_{bout_info['id']}"] = True
                    st.session_state.active_bout_data = None
                    # Bracket अपडेट गर्ने
                    ma_bracket.sync_progress_to_db(evt_code)
                
                # 💡 Final Medal Tally Save (PostgreSQL)
                if bout_info and bout_info['r_name'] == 'Final':
                    s_str = f"{s_a}-{s_b}" if grp == 'Kumite' else f"{tot_a}-{tot_b}"
                    conn = db.get_connection()
                    c = conn.cursor()
                    
                    c.execute("""
                        INSERT INTO results (event_code, municipality_id, player_id, position, score_details, medal) 
                        VALUES (%s, %s, %s, 1, %s, 'Gold')
                    """, (evt_code, win_info['m_id'], win_info['p_id'], s_str))
                    
                    c.execute("""
                        INSERT INTO results (event_code, municipality_id, player_id, position, score_details, medal) 
                        VALUES (%s, %s, %s, 2, %s, 'Silver')
                    """, (evt_code, lose_info['m_id'], lose_info['p_id'], s_str))
                    
                    conn.commit()
                    c.close(); conn.close()
                    st.toast("🎉 फाइनल म्याच सम्पन्न! नतिजा र पदक सुरक्षित भयो।")
                
                # लाइभ म्याच खाली गर्ने
                conn = db.get_connection()
                conn.cursor().execute("DELETE FROM live_match")
                conn.commit(); conn.close()
                
                st.success(f"✅ Result Saved! Advancing to next round...")
                st.balloons()
                st.rerun()
            else:
                st.warning("⚠️ स्कोर बराबर छ (Tie)। कृपया Hantei वा Golden Point मार्फत विजेता छुट्ट्याउनुहोस्।")
                
    with c_rst:
        if st.button("🔄 Reset Scoreboard", type="secondary", width="stretch"):
            st.session_state.fight_scores = {k: (None if k=='senshu' else 0) for k in st.session_state.fight_scores}
            st.session_state.fight_logs = []
            st.session_state[f"{prefix}_elapsed_time"] = 0.0
            st.session_state[f"{prefix}_timer_running"] = False
            sync_to_db()
            st.rerun()