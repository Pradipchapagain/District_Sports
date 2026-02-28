import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import json
import time
import os
import base64

# ==========================================
# 🖼️ ०. Image Caching System
# ==========================================
@st.cache_data
def get_cached_base64_image(filename):
    filepath = os.path.join("assets", filename)
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# ==========================================
# 🛠️ १. DB र Helper Functions
# ==========================================
def fetch_team_players(event_code, team_name):
    conn = db.get_connection()
    c = conn.cursor()
    # 💡 PostgreSQL Logic: Safe String Matching
    c.execute("SELECT municipality_id FROM teams WHERE event_code=%s AND name ILIKE %s", (event_code, f"%{team_name.strip()}%"))
    team_info = c.fetchone()
    
    if team_info and team_info[0]:
        muni_id = team_info[0]
        c.execute("""
            SELECT p.name FROM registrations r 
            JOIN players p ON r.player_id = p.id 
            WHERE r.event_code = %s AND p.municipality_id = %s
        """, (event_code, muni_id))
        players = c.fetchall()
        c.close()
        conn.close()
        if players: return [p[0] for p in players]
        
    c.close()
    conn.close()
    return [f"Player {i}" for i in range(1, 13)]

def load_kabaddi_scores(event_code, match_id, p1, p2):
    state_key = f"kabaddi_{event_code}_{match_id}"
    
    if state_key not in st.session_state:
        conn = db.get_connection()
        c = conn.cursor()
        # 💡 PostgreSQL Syntax
        c.execute("SELECT live_state, status FROM matches WHERE match_no=%s AND event_code=%s", (match_id, event_code))
        row = c.fetchone()
        c.close()
        conn.close()
        
        saved_state = None
        if row and row[0] and row[1] != 'Completed':
            try: 
                saved_state = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except: pass
            
        if saved_state:
            if 'out_players' not in saved_state: saved_state['out_players'] = {p1: [], p2: []}
            if 'empty_raids' not in saved_state: saved_state['empty_raids'] = {p1: 0, p2: 0}
            if 'cards' not in saved_state: saved_state['cards'] = {p1: {}, p2: {}}
            if 'yc_timers' not in saved_state: saved_state['yc_timers'] = {p1: {}, p2: {}} 
            if 'raider_team' not in saved_state: saved_state['raider_team'] = None
            if 'raider_num' not in saved_state: saved_state['raider_num'] = None
            if 'selected_targets' not in saved_state: saved_state['selected_targets'] = []
            if 'swap_sides' not in saved_state: saved_state['swap_sides'] = False
            if 'lona_transition' not in saved_state: saved_state['lona_transition'] = None
            if 'raid_pos' not in saved_state: saved_state['raid_pos'] = 0 
            if 'baulk_crossed' not in saved_state: saved_state['baulk_crossed'] = False
            if 'bonus_crossed' not in saved_state: saved_state['bonus_crossed'] = False
            if 'match_started' not in saved_state: saved_state['match_started'] = False 
            if 'timer_running' not in saved_state: saved_state['timer_running'] = False 
            if 'timeout_active' not in saved_state: saved_state['timeout_active'] = False 
            if 'next_raider_team' not in saved_state: saved_state['next_raider_team'] = None
            if 'first_half_starter' not in saved_state: saved_state['first_half_starter'] = None 
            if 'last_event_msg' not in saved_state: saved_state['last_event_msg'] = "" 
            if 'last_event_icon' not in saved_state: saved_state['last_event_icon'] = "" 
            
            st.session_state[state_key] = saved_state
            st.session_state[state_key]['timeouts'] = {int(k): v for k, v in saved_state.get('timeouts', {1: {p1: 0, p2: 0}, 2: {p1: 0, p2: 0}}).items()}
        else:
            st.session_state[state_key] = {
                'setup_complete': False, 'match_started': False, 'timer_running': False, 'timeout_active': False,
                'score_a': 0, 'score_b': 0, 'half': 1, 'status': 'Playing',
                'timeouts': {1: {p1: 0, p2: 0}, 2: {p1: 0, p2: 0}}, 
                'subs': {p1: 0, p2: 0}, 'roster': {p1: {}, p2: {}}, 
                'lineup': { p1: {"court": [], "bench": [], "captain": None}, p2: {"court": [], "bench": [], "captain": None} },
                'out_players': {p1: [], p2: []}, 'empty_raids': {p1: 0, p2: 0},   
                'cards': {p1: {}, p2: {}}, 'yc_timers': {p1: {}, p2: {}},       
                'raider_team': None, 'raider_num': None, 'selected_targets': [],
                'swap_sides': False, 'lona_transition': None, 'raid_pos': 0, 'baulk_crossed': False, 'bonus_crossed': False,
                'next_raider_team': None, 'first_half_starter': None, 'last_event_msg': "", 'last_event_icon': ""
            }
        
        st.session_state[f"{state_key}_show_subs_{p1}"] = False; st.session_state[f"{state_key}_show_subs_{p2}"] = False
        st.session_state[f"{state_key}_show_cards_{p1}"] = False; st.session_state[f"{state_key}_show_cards_{p2}"] = False
        
    return state_key

def save_kabaddi_scores(event_code, match_id, state):
    conn = db.get_connection()
    c = conn.cursor()
    # 💡 PostgreSQL JSONB save logic
    c.execute("UPDATE matches SET live_state=%s WHERE match_no=%s AND event_code=%s", (json.dumps(state), match_id, event_code))
    conn.commit()
    c.close()
    conn.close()

def update_live_tv(event_name, state, p1, p2):
    c_half = state.get('half', 1)
    t_1 = state.get('timeouts', {}).get(c_half, {}).get(p1, 0)
    t_2 = state.get('timeouts', {}).get(c_half, {}).get(p2, 0)
    status_text = f"Half {c_half} | T/O: {p1}({t_1}), {p2}({t_2})"
    ls.update_live_match(event_name, p1, p2, str(state['score_a']), str(state['score_b']), status=status_text)

# ==========================================
# 🤼 २. कबड्डी कोर्ट रेन्डर (Visual Engine) - 🚀 FRAGMENTED
# ==========================================
@st.fragment
def render_kabaddi_court(state, p1, p2):
    # यो ब्लक भित्र भएको UI अपडेट गर्दा पूरै पेज रिफ्रेस हुँदैन! 
    # यसले Flickering ९०% ले घटाउँछ।
    
    left_team = p2 if state.get('swap_sides') else p1
    right_team = p1 if state.get('swap_sides') else p2
    
    l1, l2 = state['lineup'].get(left_team, {}), state['lineup'].get(right_team, {})
    c_left, c_right = l1.get('court', []), l2.get('court', [])
    b_left, b_right = l1.get('bench', []), l2.get('bench', [])
    out_left, out_right = state.get('out_players', {}).get(left_team, []), state.get('out_players', {}).get(right_team, [])

    is_attacking_right = (state.get('raider_team') == left_team)
    r_pos = state.get('raid_pos', 0)
    baulk_c = state.get('baulk_crossed', False)
    bonus_c = state.get('bonus_crossed', False)
    
    c_mid = "#ef4444" if r_pos >= 1 else "white" 
    c_baulk_l = "white"; c_bonus_l = "white"
    if not is_attacking_right:
        if r_pos >= 2: c_baulk_l = "#22c55e"  
        elif baulk_c: c_baulk_l = "#facc15"   
        if r_pos >= 3: c_bonus_l = "#22c55e"
        elif bonus_c: c_bonus_l = "#facc15"   
        
    c_baulk_r = "white"; c_bonus_r = "white"
    if is_attacking_right:
        if r_pos >= 2: c_baulk_r = "#22c55e"
        elif baulk_c: c_baulk_r = "#facc15"
        if r_pos >= 3: c_bonus_r = "#22c55e"
        elif bonus_c: c_bonus_r = "#facc15"

    st.markdown(f"""
    <style>
        .kb-arena {{ display: flex; justify-content: center; align-items: stretch; width: 100%; gap: 10px; margin: 10px 0; height: 340px; }}
        .kb-bench {{ display: flex; flex-direction: column; gap: 5px; background: #1e293b; padding: 5px; border-radius: 5px; min-width: 40px; align-items: center; overflow-y: auto; overflow-x: hidden; border: 2px solid #475569; }}
        .bench-title {{ color: white; font-size: 10px; font-weight: bold; margin-bottom: 2px; writing-mode: vertical-rl; flex-grow: 1; text-align: center; letter-spacing: 2px; }}
        .sitting-block {{ display: flex; flex-direction: column; justify-content: flex-end; gap: 4px; background: #e2e8f0; padding: 5px; border-radius: 5px; width: 50px; border: 2px solid #cbd5e1; }}
        .sit-slot {{ width: 34px; height: 34px; border-radius: 50%; background: white; border: 2px dashed #94a3b8; display: flex; justify-content: center; align-items: center; font-size: 12px; font-weight: bold; color: #475569; position: relative; margin: 0 auto; }}
        .sit-filled {{ background: #cbd5e1; border: 2px solid #475569; color: black; }}
        
        .kb-court {{ display: flex; width: 100%; max-width: 1000px; height: 100%; background-color: #fcd34d; border: 5px solid white; position: relative; box-shadow: 0 5px 15px rgba(0,0,0,0.3); overflow: hidden; border-radius: 8px; }}
        
        .mid-line {{ position: absolute; top: 0; bottom: 0; left: 50%; width: 6px; background-color: {c_mid}; transform: translateX(-50%); z-index: 10; box-shadow: 0 0 10px {c_mid}; transition: 0.3s; }}
        .baulk-line-left {{ position: absolute; top: 0; bottom: 0; left: 25%; width: 4px; background-color: {c_baulk_l}; box-shadow: 0 0 8px {c_baulk_l}; transition: 0.3s; }}
        .bonus-line-left {{ position: absolute; top: 0; bottom: 0; left: 15%; width: 4px; background-color: {c_bonus_l}; box-shadow: 0 0 8px {c_bonus_l}; transition: 0.3s; }}
        .baulk-line-right {{ position: absolute; top: 0; bottom: 0; right: 25%; width: 4px; background-color: {c_baulk_r}; box-shadow: 0 0 8px {c_baulk_r}; transition: 0.3s; }}
        .bonus-line-right {{ position: absolute; top: 0; bottom: 0; right: 15%; width: 4px; background-color: {c_bonus_r}; box-shadow: 0 0 8px {c_bonus_r}; transition: 0.3s; }}
        
        .bg-blue {{ background-color: #2563eb !important; color: white !important; border: 2px solid white !important; }}
        .bg-red {{ background-color: #dc2626 !important; color: white !important; border: 2px solid white !important; }}
        .bg-green {{ background-color: #22c55e !important; color: white !important; border: 2px solid white !important; }}
        .bg-out {{ background-color: #ef4444 !important; color: white !important; border: 2px solid black !important; }}

        .p-dot {{ position: absolute; width: 34px; height: 34px; border-radius: 50%; font-weight: bold; font-size: 15px; display: flex; justify-content: center; align-items: center; transform: translate(-50%, -50%); z-index: 5; transition: all 0.5s cubic-bezier(0.4, 0, 0.2, 1); box-shadow: 1px 1px 5px rgba(0,0,0,0.5); }}
        .p-dot-bench {{ position: relative; width: 28px; height: 28px; transform: none; font-size: 12px; margin-bottom: 3px; box-shadow: none; }}
        .captain-dot {{ border: 4px double white !important; box-shadow: 0 0 8px rgba(0,0,0,0.8); }}

        .raider-dod {{ box-shadow: 0 0 20px #ea580c; transform: translate(-50%, -50%) scale(1.4); z-index: 20; animation: blink 0.8s infinite; }}
        .raider-normal {{ box-shadow: 0 0 15px white; transform: translate(-50%, -50%) scale(1.4); z-index: 20; }}
        .target-active {{ background-color: #fef08a !important; color: black !important; border-color: #eab308 !important; box-shadow: 0 0 15px #eab308; transform: translate(-50%, -50%) scale(1.2); z-index: 15;}}
        @keyframes blink {{ 50% {{ opacity: 0.6; box-shadow: 0 0 8px #ea580c; }} }}
        
        .court-popup {{
            display: flex; align-items: center; justify-content: center; gap: 15px;
            position: absolute; top: 15%; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, #0f172a, #1e293b); color: #f8fafc;
            padding: 12px 25px; border-radius: 10px; border: 3px solid #facc15;
            font-size: 20px; font-weight: bold; z-index: 100;
            box-shadow: 0px 5px 20px rgba(0,0,0,0.6); text-align: center;
            animation: fadeOut 4s forwards;
        }}
        .popup-icon {{
            width: 55px; height: 55px; object-fit: contain;
            background: rgba(255,255,255,0.1); border-radius: 50%; padding: 5px;
            border: 2px solid rgba(255,255,255,0.3);
        }}
        .flip-horizontal {{ transform: scaleX(-1); }}
        
        @keyframes fadeOut {{ 0% {{ opacity: 1; top: 15%; }} 70% {{ opacity: 1; }} 100% {{ opacity: 0; top: 10%; display: none; visibility: hidden; }} }}
    </style>
    """, unsafe_allow_html=True)
    
    pos_a = {0:("15%","20%"), 1:("25%","35%"), 2:("35%","50%"), 3:("25%","65%"), 4:("15%","80%"), 5:("10%","35%"), 6:("10%","65%")}
    pos_b = {0:("85%","20%"), 1:("75%","35%"), 2:("65%","50%"), 3:("75%","65%"), 4:("85%","80%"), 5:("90%","35%"), 6:("90%","65%")}

    def get_sitting_block_html(team, out_list):
        slots_html = ""
        eligible_idx = -1
        for i, p in enumerate(out_list):
            if state['cards'].get(team, {}).get(p) != 'Yellow':
                eligible_idx = i; break
        for i in range(7):
            if i < len(out_list):
                p_num = out_list[i]
                icon = "✨" if i == eligible_idx else ""
                slots_html += f'<div class="sit-slot sit-filled">{p_num}<span class="revive-icon">{icon}</span></div>'
            else:
                slots_html += '<div class="sit-slot"></div>'
        return f'<div class="sitting-block">{slots_html}</div>'

    def make_dot(team, num, is_court=True, idx=-1, is_left=True):
        if is_court and num in state['out_players'].get(team, []): return ""
        if state['cards'].get(team, {}).get(num) == 'Red':
            return f'<div class="p-dot p-dot-bench bg-out">{num}</div>' if not is_court else ""
            
        cls = ["p-dot" if is_court else "p-dot p-dot-bench"]
        bg_class = "bg-blue" if team == p1 else "bg-red"
        is_yc_over = False
        if state['cards'].get(team, {}).get(num) == 'Yellow':
            st_time = state.get('yc_timers', {}).get(team, {}).get(num, 0)
            if time.time() - st_time >= 120: is_yc_over = True
            
        if not is_court and is_yc_over: bg_class = "bg-green"
        cls.append(bg_class)
        
        if num == state['lineup'].get(team, {}).get('captain'): cls.append("captain-dot")

        is_raider = (state.get('raider_num') == num and state.get('raider_team') == team)
        if is_raider:
            is_dod = state['empty_raids'].get(team, 0) >= 2
            cls.append("raider-dod" if is_dod else "raider-normal")
        if num in state.get('selected_targets', []) and team != state.get('raider_team'): 
            cls.append("target-active")
            
        style = ""
        if is_court:
            if is_raider:
                if is_attacking_right:
                    if r_pos == 0: style_pos = "left: 45%; top: 50%;" 
                    elif r_pos == 1: style_pos = "left: 55%; top: 50%;" 
                    elif r_pos == 2: style_pos = "left: 70%; top: 50%;" 
                    else: style_pos = "left: 88%; top: 50%;" 
                else:
                    if r_pos == 0: style_pos = "left: 55%; top: 50%;" 
                    elif r_pos == 1: style_pos = "left: 45%; top: 50%;"
                    elif r_pos == 2: style_pos = "left: 30%; top: 50%;" 
                    else: style_pos = "left: 12%; top: 50%;" 
            else:
                pos = pos_a if is_left else pos_b
                style_pos = f"left:{pos[idx][0]}; top:{pos[idx][1]};"
            style = style_pos
            
        return f'<div class="{" ".join(cls)}" style="{style}">{num}</div>'

    yc_html = "<div style='display:flex; justify-content:space-between; width:100%; max-width:1000px; margin: 0 auto; padding: 0 10px;'>"
    def get_yc_box(team):
        box_html = "<div style='display:flex; gap:10px;'>"
        for yp, st_time in state.get('yc_timers', {}).get(team, {}).items():
            if state['cards'].get(team, {}).get(yp) != 'Yellow': continue
            elapsed = time.time() - st_time
            rem = max(0, 120 - int(elapsed))
            m, s = divmod(rem, 60)
            color = "#fde047" if rem > 0 else "#22c55e" 
            txt = f"{m:02d}:{s:02d}" if rem > 0 else "भित्र पठाउनुहोस्"
            box_html += f"<div style='background:{color}; color:black; padding:4px 10px; border-radius:5px; font-weight:bold; border:2px solid #334155; font-size:14px; box-shadow:0 2px 5px rgba(0,0,0,0.3);'>🟨 जर्सी {yp} ⏳ {txt}</div>"
        return box_html + "</div>"

    yc_html += get_yc_box(left_team) + get_yc_box(right_team) + "</div>"
    
    html = yc_html + '<div class="kb-arena">'
    html += f'<div class="kb-bench">{"".join([make_dot(left_team, n, False) for n in b_left])}<div class="bench-title">BENCH</div></div>'
    html += get_sitting_block_html(left_team, out_left)
    
    html += '<div class="kb-court">'
    
    if state.get('last_event_msg'):
        icon_tag = ""
        if state.get('last_event_icon'):
            b64_str = get_cached_base64_image(state['last_event_icon'])
            if b64_str:
                icon_cls = "popup-icon"
                dir_icons = ["KB_start_raid.png", "kB_raider_out.png", "KB_line_cut.png", "KB_substitution.png"]
                active_r_team = state.get('raider_team') or state.get('next_raider_team') or left_team
                if state['last_event_icon'] in dir_icons and (active_r_team == right_team):
                    icon_cls += " flip-horizontal"
                icon_tag = f"<img class='{icon_cls}' src='data:image/png;base64,{b64_str}'>"
                
        html += f"<div class='court-popup'>{icon_tag}<div>{state['last_event_msg']}</div></div>"
        
        st.components.v1.html("""
            <script>
                const ctx = new (window.AudioContext || window.webkitAudioContext)();
                if(ctx.state === 'suspended') ctx.resume();
                const osc = ctx.createOscillator();
                const gainNode = ctx.createGain();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(800, ctx.currentTime);
                gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
                osc.connect(gainNode); gainNode.connect(ctx.destination);
                osc.start(); setTimeout(() => { osc.stop(); }, 400);
            </script>
        """, height=0)
        
        state['last_event_msg'] = "" 
        state['last_event_icon'] = "" 

    html += f'<div class="mid-line"></div>'
    html += f'<div class="baulk-line-left"></div>'
    html += f'<div class="bonus-line-left"></div>'
    html += f'<div class="baulk-line-right"></div>'
    html += f'<div class="bonus-line-right"></div>'
    
    html += "".join([make_dot(left_team, n, True, i, True) for i, n in enumerate(c_left)])
    html += "".join([make_dot(right_team, n, True, i, False) for i, n in enumerate(c_right)])
    html += '</div>'
    
    html += get_sitting_block_html(right_team, out_right)
    html += f'<div class="kb-bench">{"".join([make_dot(right_team, n, False) for n in b_right])}<div class="bench-title">BENCH</div></div></div>'
    st.markdown(html, unsafe_allow_html=True)


# ==========================================
# 🎮 ३. Main Render Function
# ==========================================
def render_match(evt_code, sel_m):
    mid = sel_m['id']
    p1, p2 = sel_m['p1'], sel_m['p2']
    
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT name, gender FROM events WHERE code=%s", (evt_code,))
    evt_info = c.fetchone()
    c.close()
    conn.close()
    
    match_title = f"{evt_info[0]} ({evt_info[1]}) - Match #{mid}" if evt_info else f"Kabaddi Match #{mid}"
    is_women = evt_info[1] == 'Girls' if evt_info else False

    state_key = load_kabaddi_scores(evt_code, mid, p1, p2)
    state = st.session_state[state_key]
    
    if state.get('status') == 'Completed':
        st.success("✅ यो म्याच सम्पन्न भइसकेको छ।")
        return

    # --- SETUP PHASE ---
    if not state.get("setup_complete"):
        st.info("📋 **कबड्डी लाइन-अप तयार गर्नुहोस् (७ जना कोर्टमा, ५ जना बेन्चमा)।**")
        c_t1, c_t2 = st.columns(2)
        def setup_team(team_name, col):
            with col:
                st.markdown(f"### 🤼 {team_name}")
                players = fetch_team_players(evt_code, team_name)
                df_key = f"kb_setup_{mid}_{team_name}"
                if df_key not in st.session_state:
                    st.session_state[df_key] = pd.DataFrame({"Player Name": players, "Jersey": ["" for _ in players], "Position": ["Bench"] * len(players), "Captain": [False] * len(players)})
                config = {"Player Name": st.column_config.TextColumn("खेलाडीको नाम", required=True), "Jersey": st.column_config.TextColumn("जर्सी नं.", required=True, max_chars=3), "Position": st.column_config.SelectboxColumn("पोजिसन", options=["Bench", "Starting 7"], required=True), "Captain": st.column_config.CheckboxColumn("क्याप्टेन (C)", default=False)}
                edited_df = st.data_editor(st.session_state[df_key], column_config=config, num_rows="dynamic", key=f"kb_ed_{mid}_{team_name}", use_container_width=True, hide_index=True)
                valid, error_msg = True, ""
                active_mask = edited_df['Position'] == "Starting 7"
                if edited_df[active_mask]['Jersey'].str.strip().eq("").any() or edited_df[active_mask]['Jersey'].isna().any(): valid, error_msg = False, "जर्सी नम्बर खाली छोड्न मिल्दैन।"
                else:
                    if edited_df['Position'].value_counts().get("Starting 7", 0) != 7: valid, error_msg = False, "ठ्याक्कै ७ जना खेलाडी 'Starting 7' मा हुनुपर्छ।"
                    if valid and edited_df['Captain'].sum() != 1: valid, error_msg = False, "१ जना मात्र क्याप्टेन हुनुपर्छ।"
                    if valid:
                        active_j = edited_df[active_mask]['Jersey'].astype(str).str.strip().tolist()
                        if len(active_j) != len(set(active_j)): valid, error_msg = False, "एउटै जर्सी नम्बर दुई जनालाई दिन मिल्दैन।"
                if valid:
                    clean_df = edited_df[edited_df['Player Name'].str.strip() != ""]
                    roster = {str(row['Jersey']).strip(): row['Player Name'] for _, row in clean_df.iterrows() if str(row['Jersey']).strip() != ""}
                    starters = clean_df[clean_df['Position'] == "Starting 7"]['Jersey'].astype(str).str.strip().tolist()
                    bench = [b for b in clean_df[clean_df['Position'] == "Bench"]['Jersey'].astype(str).str.strip().tolist() if b != ""]
                    cap_j = str(clean_df[clean_df['Captain'] == True]['Jersey'].iloc[0]).strip()
                    return roster, starters, bench, cap_j
                else:
                    st.error(f"⚠️ {error_msg}")
                    return None, [], [], None

        ta_rost, ta_start, ta_bench, ta_cap = setup_team(p1, c_t1)
        tb_rost, tb_start, tb_bench, tb_cap = setup_team(p2, c_t2)
        if len(ta_start) == 7 and len(tb_start) == 7:
            if st.button("🚀 लाइन-अप लक गर्नुहोस्", type="primary", width="stretch"):
                state['roster'][p1], state['roster'][p2] = ta_rost, tb_rost
                state['lineup'][p1] = {"court": ta_start, "bench": ta_bench, "captain": ta_cap}
                state['lineup'][p2] = {"court": tb_start, "bench": tb_bench, "captain": tb_cap}
                state["setup_complete"] = True
                save_kabaddi_scores(evt_code, mid, state); st.rerun()
        return

    # -------------------------------------------------------------
    # PHASE 2: LIVE MATCH CONTROL 
    # -------------------------------------------------------------
    c_half = state['half']
    left_team = p2 if state['swap_sides'] else p1
    right_team = p1 if state['swap_sides'] else p2
    
    if state.get('lona_transition'):
        team_out = state['lona_transition']
        opponent = p2 if team_out == p1 else p1
        state['last_event_msg'] = f"🚨 LONA! {opponent} लाई +2 अङ्क!" 
        state['last_event_icon'] = "KB_lona_allout.png" 
        render_kabaddi_court(state, p1, p2) 
        time.sleep(1) 
        safe_out = []
        for p in state['out_players'][team_out]:
            if state['cards'].get(team_out, {}).get(p) in ['Yellow', 'Red']: safe_out.append(p)
        state['out_players'][team_out] = safe_out
        state[f'score_{"a" if opponent==p1 else "b"}'] += 2 
        state['lona_transition'] = None
        state['next_raider_team'] = team_out
        save_kabaddi_scores(evt_code, mid, state); st.rerun()

    def add_score_and_revive(team, points, is_bonus=False):
        if team == p1: state['score_a'] += points
        else: state['score_b'] += points
        if not is_bonus and points > 0:
            for _ in range(points):
                for i, p in enumerate(state['out_players'].get(team, [])):
                    if state['cards'].get(team, {}).get(p) != 'Yellow':
                        state['out_players'][team].pop(i)
                        break 
        save_kabaddi_scores(evt_code, mid, state)
        update_live_tv(match_title, state, p1, p2)

    # 💡 SCOREBOARD
    c_timer, c_score_L, c_score_R, c_half_info = st.columns([1.5, 4, 4, 1.5])
    score_left = state['score_b'] if state['swap_sides'] else state['score_a']
    score_right = state['score_a'] if state['swap_sides'] else state['score_b']
    
    c_L_main = "#2563eb" if left_team == p1 else "#dc2626"
    c_L_text = "#93c5fd" if left_team == p1 else "#fca5a5"
    
    c_R_main = "#2563eb" if right_team == p1 else "#dc2626"
    c_R_text = "#93c5fd" if right_team == p1 else "#fca5a5"
    
    active_r_team = state.get('raider_team') or state.get('next_raider_team') or left_team
    l_role = "🏃 रेडर टिम (Raider)" if active_r_team == left_team else "🛡️ डिफेन्स टिम (Defence)"
    l_role_bg = c_L_main if active_r_team == left_team else "#475569"
    r_role = "🏃 रेडर टिम (Raider)" if active_r_team == right_team else "🛡️ डिफेन्स टिम (Defence)"
    r_role_bg = c_R_main if active_r_team == right_team else "#475569"
    
    with c_timer:
        max_min = 15 if is_women else 20
        st.components.v1.html(f"""
            <div style="font-family:monospace; background:#1e293b; color:white; padding:10px; border-radius:8px; text-align:center;">
                <div style="font-size:26px; font-weight:bold;"><span id="min">{max_min}</span>:<span id="sec">00</span></div>
                <div id="to_box" style="display:{'block' if state.get('timeout_active') else 'none'}; margin-top:5px; font-size:14px; color:#ef4444; font-weight:bold; background:#fee2e2; padding:2px; border-radius:5px;">
                    ⏳ <span id="to_sec">30</span>s
                </div>
            </div>
            <script>
                const actx = new (window.AudioContext || window.webkitAudioContext)();
                function playBeep(type) {{
                    if(actx.state === 'suspended') actx.resume();
                    const osc = actx.createOscillator(); osc.type = 'sine'; 
                    if(type==='long') {{ osc.frequency.value = 300; osc.start(); setTimeout(()=>osc.stop(), 1500); }}
                    else {{ osc.frequency.value = 600; osc.start(); setTimeout(()=>osc.stop(), 800); }}
                    osc.connect(actx.destination);
                }}

                if(!sessionStorage.getItem('m_sec')) sessionStorage.setItem('m_sec', {max_min*60});
                if(!sessionStorage.getItem('to_sec')) sessionStorage.setItem('to_sec', 30);
                
                let s = parseInt(sessionStorage.getItem('m_sec')); 
                let t = parseInt(sessionStorage.getItem('to_sec'));
                let running = { 'true' if state.get('timer_running') else 'false' };
                let is_to = { 'true' if state.get('timeout_active') else 'false' };
                
                function update() {{ 
                    if(running && s>0) {{ s--; sessionStorage.setItem('m_sec', s); if(s===0) playBeep('long'); }}
                    if(is_to && t>0) {{
                        t--; sessionStorage.setItem('to_sec', t);
                        document.getElementById('to_sec').innerText = t<10?'0'+t:t;
                        if(t===0) playBeep('short');
                    }} else if (!is_to) {{ sessionStorage.setItem('to_sec', 30); }}

                    let m = Math.floor(s/60); let sec = s%60;
                    document.getElementById('sec').innerText = sec<10?'0'+sec:sec; 
                    document.getElementById('min').innerText = m<10?'0'+m:m; 
                }}
                window.timer = setInterval(update, 1000);
            </script>
        """, height=110)
        
    with c_score_L:
        st.markdown(f"""
            <div style='background:#1e293b; border-bottom:8px solid {c_L_main}; padding:15px; border-radius:15px; text-align:center; box-shadow: 0 5px 15px rgba(0,0,0,0.5);'>
                <h2 style='color:{c_L_text}; margin:0; font-size:32px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{left_team}</h2>
                <div style='font-size:80px; font-weight:900; color:white; line-height:1.1; text-shadow: 3px 3px 6px rgba(0,0,0,0.6);'>{score_left}</div>
                <div style='background:{l_role_bg}; color:white; font-size:14px; font-weight:bold; padding:4px 15px; border-radius:15px; display:inline-block; margin-top:5px;'>{l_role}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c_score_R:
        st.markdown(f"""
            <div style='background:#1e293b; border-bottom:8px solid {c_R_main}; padding:15px; border-radius:15px; text-align:center; box-shadow: 0 5px 15px rgba(0,0,0,0.5);'>
                <h2 style='color:{c_R_text}; margin:0; font-size:32px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{right_team}</h2>
                <div style='font-size:80px; font-weight:900; color:white; line-height:1.1; text-shadow: 3px 3px 6px rgba(0,0,0,0.6);'>{score_right}</div>
                <div style='background:{r_role_bg}; color:white; font-size:14px; font-weight:bold; padding:4px 15px; border-radius:15px; display:inline-block; margin-top:5px;'>{r_role}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c_half_info:
        prev_h = ""
        if c_half == 2:
            prev_score = state.get('half_1_score', '0-0').split('-')
            ps_l = prev_score[1] if state['swap_sides'] else prev_score[0]
            ps_r = prev_score[0] if state['swap_sides'] else prev_score[1]
            prev_h = f"<div style='font-size:12px; color:gray; margin-top:5px;'>H1: {ps_l}-{ps_r}</div>"
        st.markdown(f"<div style='background:#f1f5f9; padding:10px; border-radius:8px; text-align:center; border:1px solid #cbd5e1;'><div style='font-size:14px; color:gray;'>SET</div><h3 style='margin:0; color:#334155;'>{c_half}</h3>{prev_h}</div>", unsafe_allow_html=True)

    raid_active = "true" if state.get('raider_team') else "false"
    st.components.v1.html(f"""
        <div style="text-align:center; font-family:monospace; margin-bottom:-10px; display:{'block' if state.get('raider_team') else 'none'};">
            <span style="font-size:14px; color:#64748b; font-weight:bold; vertical-align:middle;">RAID </span>
            <span style="font-size:24px; font-weight:bold; color:#ef4444; background:#fee2e2; padding:2px 10px; border-radius:15px; border:2px solid #fca5a5;"><span id="r_sec">30</span>s</span>
        </div>
        <script>
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            function beep() {{
                if(audioCtx.state === 'suspended') audioCtx.resume();
                const osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 800;
                osc.connect(audioCtx.destination); osc.start(); setTimeout(() => osc.stop(), 500);
            }}
            let r = {30 if state.get('raider_team') else 0}; let r_run = {raid_active};
            if(r_run) {{
                window.rtimer = setInterval(() => {{
                    if(r>0) {{ r--; document.getElementById('r_sec').innerText = r<10?'0'+r:r; if(r===0) beep(); }}
                }}, 1000);
            }}
        </script>
    """, height=40)

    render_kabaddi_court(state, p1, p2)
    
    def get_dod_dots(team):
        empties = state.get('empty_raids', {}).get(team, 0)
        return "⚪ ⚪" if empties == 0 else "🔴 ⚪" if empties == 1 else "🔴 🔴 (Do-or-Die)"
    def get_to_icons(team):
        used = state.get('timeouts', {}).get(str(c_half), {}).get(team, 0)
        return " ".join(["⏱️" if i < used else "⚪" for i in range(2)])

    c_ind_l, c_ind_r = st.columns(2)
    c_ind_l.markdown(f"<div style='text-align:center; font-size:14px; color:#64748b;'>Do-or-Die: {get_dod_dots(left_team)} | T/O: {get_to_icons(left_team)}</div>", unsafe_allow_html=True)
    c_ind_r.markdown(f"<div style='text-align:center; font-size:14px; color:#64748b;'>T/O: {get_to_icons(right_team)} | Do-or-Die: {get_dod_dots(right_team)}</div>", unsafe_allow_html=True)

    st.markdown("---")

    def reset_raid(is_cancel=False):
        if not is_cancel:
            state['next_raider_team'] = left_team if state['raider_team'] == right_team else right_team
        state['raider_team'] = None; state['raider_num'] = None; state['selected_targets'] = []
        state['raid_pos'] = 0; state['baulk_crossed'] = False; state['bonus_crossed'] = False

    # ==========================================
    # 🏃 SMART MATCH FLOW & AUTO-SCORING
    # ==========================================
    
    if not state.get('match_started'):
        st.markdown("<div style='text-align:center; padding:20px; background:#f8fafc; border-radius:10px; border:2px dashed #cbd5e1;'>", unsafe_allow_html=True)
        if c_half == 1:
            if not state.get('next_raider_team'):
                st.markdown("<h3 style='color:#334155;'>🪙 टस (Toss) र साइड छनौट</h3>", unsafe_allow_html=True)
                if st.button("🔄 कोर्टको साइड परिवर्तन गर्नुहोस् (Swap Sides)", use_container_width=True):
                    state['swap_sides'] = not state['swap_sides']; save_kabaddi_scores(evt_code, mid, state); st.rerun()
                    
                st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color:#475569;'>पहिलो रेड कुन टिमको?</h4>", unsafe_allow_html=True)
                ct1, ct2 = st.columns(2)
                lbl_color_L = "नीलो" if left_team == p1 else "रातो"
                lbl_color_R = "नीलो" if right_team == p1 else "रातो"
                
                if ct1.button(f"👈 {left_team} ({lbl_color_L})", use_container_width=True):
                    state['next_raider_team'] = left_team; state['first_half_starter'] = left_team; save_kabaddi_scores(evt_code, mid, state); st.rerun()
                if ct2.button(f"{right_team} ({lbl_color_R}) 👉", use_container_width=True):
                    state['next_raider_team'] = right_team; state['first_half_starter'] = right_team; save_kabaddi_scores(evt_code, mid, state); st.rerun()
            else:
                t_color_active = "#2563eb" if state['next_raider_team'] == p1 else "#dc2626"
                st.markdown(f"<h3 style='color:#334155;'>पहिलो रेड: <span style='color:{t_color_active};'>{state['next_raider_team']}</span></h3>", unsafe_allow_html=True)
                if st.button("🔄 टस सच्याउनुहोस् (Reset Toss)"):
                    state['next_raider_team'] = None; state['first_half_starter'] = None; save_kabaddi_scores(evt_code, mid, state); st.rerun()
                
                st.markdown("<br><h4 style='color:#475569;'>रेफ्रीको सिट्ठी कुरेर खेल सुरु गर्नुहोस् 👇</h4>", unsafe_allow_html=True)
                c_btn = st.columns([1,2,1])
                if c_btn[1].button("▶️ खेल सुरु गर्नुहोस् (Start Match)", type="primary", use_container_width=True):
                    state['match_started'] = True; state['timer_running'] = True
                    state['last_event_msg'] = "▶️ म्याच सुरु भयो!"
                    state['last_event_icon'] = "KB_start_raid.png" 
                    save_kabaddi_scores(evt_code, mid, state); st.rerun()
        else:
            st.markdown("<h3 style='color:#334155;'>⏳ दोस्रो हाफ सुरु गर्न तयार हुनुहोस्</h3>", unsafe_allow_html=True)
            t_color_active = "#2563eb" if state.get('next_raider_team') == p1 else "#dc2626"
            st.markdown(f"<p style='font-size:18px;'>नियम अनुसार दोस्रो हाफको पहिलो रेड: <b><span style='color:{t_color_active};'>{state.get('next_raider_team')}</span></b> को हुन्छ।</p>", unsafe_allow_html=True)
            c_btn = st.columns([1,2,1])
            if c_btn[1].button("▶️ दोस्रो हाफ सुरु गर्नुहोस्", type="primary", use_container_width=True):
                state['match_started'] = True; state['timer_running'] = True
                state['last_event_msg'] = "▶️ दोस्रो हाफ सुरु!"
                state['last_event_icon'] = "KB_start_raid.png" 
                save_kabaddi_scores(evt_code, mid, state); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop() 

    st.markdown("<br>", unsafe_allow_html=True)
    c_t_toggle, c_gap = st.columns([2, 6])
    if state.get('timer_running'):
        if c_t_toggle.button("⏸️ टाइमर रोक्नुहोस् (Pause)", use_container_width=True):
            state['timer_running'] = False; save_kabaddi_scores(evt_code, mid, state); st.rerun()
    else:
        if c_t_toggle.button("▶️ टाइमर चलाउनुहोस् (Play)", type="primary", use_container_width=True):
            state['timer_running'] = True; state['timeout_active'] = False; save_kabaddi_scores(evt_code, mid, state); st.rerun()

    # --- RAIDER SELECTION ---
    if not state['raider_team']:
        next_t = state.get('next_raider_team')
        if not next_t: next_t = left_team 
        
        c_r1, c_r2 = st.columns(2)
        
        def set_raider(team, num):
            state['raider_team'] = team; state['raider_num'] = num; state['selected_targets'] = []
            state['raid_pos'] = 0; state['baulk_crossed'] = False; state['bonus_crossed'] = False
            if state.get('empty_raids', {}).get(team, 0) >= 2:
                state['last_event_msg'] = "🔥 डु-अर-डाइ रेड!"
                state['last_event_icon'] = "KB_do_or_die.png" 
            save_kabaddi_scores(evt_code, mid, state); st.rerun()
            
        st.markdown("""<style>.team-btn-blue button[kind="primary"] { background-color: #2563eb !important; border-color: #2563eb !important; color: white !important; } .team-btn-red button[kind="primary"] { background-color: #dc2626 !important; border-color: #dc2626 !important; color: white !important; }</style>""", unsafe_allow_html=True)
        
        active_p = [n for n in state['lineup'].get(next_t, {}).get('court', []) if n not in state.get('out_players', {}).get(next_t, [])]
        btn_class = "team-btn-blue" if next_t == p1 else "team-btn-red"
        
        target_col = c_r1 if next_t == left_team else c_r2
        with target_col:
            st.markdown(f"<div style='text-align:center; font-weight:bold; color:#475569; margin-bottom:5px;'>१. {next_t} को रेडर छान्नुहोस्:</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{btn_class}'>", unsafe_allow_html=True)
            cols = st.columns(7)
            for i, n in enumerate(active_p):
                if cols[i%7].button(str(n), key=f"rs_{next_t}_{n}", type="primary", use_container_width=True): set_raider(next_t, n)
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        raider_t = state['raider_team']
        defender_t = p1 if raider_t == p2 else p2
        r_num = state['raider_num']
        active_defenders = [n for n in state['lineup'].get(defender_t, {}).get('court', []) if n not in state.get('out_players', {}).get(defender_t, [])]
        is_dod = state.get('empty_raids', {}).get(raider_t, 0) >= 2
        is_att_right = (raider_t == left_team)
        r_pos = state['raid_pos']
        
        def handle_line(btn_action):
            if btn_action == "mid_in": state['raid_pos'] = 1
            elif btn_action == "baulk_in": state['raid_pos'] = 2; state['baulk_crossed'] = True
            elif btn_action == "bonus_in": state['raid_pos'] = 3; state['bonus_crossed'] = True
            elif btn_action == "bonus_out": state['raid_pos'] = 2
            elif btn_action == "baulk_out": state['raid_pos'] = 1
            elif btn_action == "safe_home":
                touch_count = len(state['selected_targets'])
                bonus_pts = 1 if (state['bonus_crossed'] and len(active_defenders) >= 6) else 0
                total_pts = touch_count + bonus_pts
                
                if total_pts > 0:
                    state['out_players'][defender_t].extend(state['selected_targets'])
                    add_score_and_revive(raider_t, total_pts)
                    state['empty_raids'][raider_t] = 0 
                    
                    if total_pts >= 3: 
                        state['last_event_msg'] = f"🚀 सुपर रेड! ({touch_count} टच + {bonus_pts} बोनस)"
                        state['last_event_icon'] = "KB_touch_point.png"
                    else: 
                        state['last_event_msg'] = f"✅ रेड सफल! ({touch_count} टच + {bonus_pts} बोनस)"
                        state['last_event_icon'] = "KB_touch_point.png" if touch_count > 0 else "KB_bonus_point.png"
                else:
                    if state['baulk_crossed']:
                        state['empty_raids'][raider_t] += 1
                        if is_dod:
                            state['out_players'][raider_t].append(r_num); add_score_and_revive(defender_t, 1); state['empty_raids'][raider_t] = 0
                            state['last_event_msg'] = "❌ Do-or-Die मा अङ्क नल्याउँदा रेडर आउट!"
                            state['last_event_icon'] = "kB_raider_out.png"
                        else:
                            state['last_event_msg'] = "⏭️ खाली रेड (Empty Raid)"
                            state['last_event_icon'] = "KB_start_raid.png" 
                    else:
                        state['last_event_msg'] = "❌ Baulk line क्रस नभएकोले रेडर आउट!"
                        state['last_event_icon'] = "KB_line_cut.png"
                        state['out_players'][raider_t].append(r_num); add_score_and_revive(defender_t, 1)
                
                reset_raid(); save_kabaddi_scores(evt_code, mid, state); st.rerun(); return
            save_kabaddi_scores(evt_code, mid, state); st.rerun()

        st.markdown(f"""
        <style>
            .def-btn button[kind="primary"] {{ background-color: #facc15 !important; color: black !important; border: 2px solid black !important; box-shadow: 0 0 10px #facc15; }}
            .def-btn button[kind="secondary"] {{ background-color: {'#2563eb' if defender_t==p1 else '#dc2626'} !important; border-color: {'#2563eb' if defender_t==p1 else '#dc2626'} !important; color: white !important; }}
            div.mid-btn button {{ background-color: #ef4444 !important; color: white !important; font-weight: bold; border: 2px solid #991b1b !important; }}
            div.baulk-btn button {{ background-color: #22c55e !important; color: white !important; font-weight: bold; border: 2px solid #14532d !important; }}
            div.bonus-btn button {{ background-color: #22c55e !important; color: white !important; font-weight: bold; border: 2px solid #14532d !important; }}
        </style>
        """, unsafe_allow_html=True)
        
        c_r1, c_r2 = st.columns(2)
        target_col = c_r1 if defender_t == left_team else c_r2
        
        with target_col:
            if r_pos == 0:
                st.markdown("<div style='text-align:center; font-size:16px; font-weight:bold; color:#475569; margin-bottom:5px;'>रेडरलाई भित्र पठाउनुहोस्:</div>", unsafe_allow_html=True)
                c_mid_l1, c_mid_l2, c_mid_l3 = st.columns(3)
                if not is_att_right:
                    with c_mid_l3:
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("◀️ Mid ┃", use_container_width=True): handle_line("mid_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    with c_mid_l1:
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("┃ Mid ▶️", use_container_width=True): handle_line("mid_in")
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:center; font-size:16px; font-weight:bold; color:#475569; margin-bottom:5px;'>डिफेन्डर ({defender_t}): टच भएमा छान्नुहोस्</div>", unsafe_allow_html=True)
                c_l1, c_l2, c_l3 = st.columns(3)
                if not is_att_right: 
                    with c_l1: 
                        st.markdown("<div class='bonus-btn'>", unsafe_allow_html=True)
                        if st.button("Bonus ║", disabled=(r_pos<2), use_container_width=True): handle_line("bonus_out" if r_pos>=3 else "bonus_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l2: 
                        st.markdown("<div class='baulk-btn'>", unsafe_allow_html=True)
                        if st.button("Baulk ┃", disabled=(r_pos<1), use_container_width=True): handle_line("baulk_out" if r_pos>=2 else "baulk_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l3: 
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("◀️ Safe", use_container_width=True): handle_line("safe_home") 
                        st.markdown("</div>", unsafe_allow_html=True)
                else: 
                    with c_l1: 
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("Safe ▶️", use_container_width=True): handle_line("safe_home") 
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l2: 
                        st.markdown("<div class='baulk-btn'>", unsafe_allow_html=True)
                        if st.button("┃ Baulk", disabled=(r_pos<1), use_container_width=True): handle_line("baulk_out" if r_pos>=2 else "baulk_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l3: 
                        st.markdown("<div class='bonus-btn'>", unsafe_allow_html=True)
                        if st.button("║ Bonus", disabled=(r_pos<2), use_container_width=True): handle_line("bonus_out" if r_pos>=3 else "bonus_in")
                        st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                cols = st.columns(7)
                st.markdown("<div class='def-btn'>", unsafe_allow_html=True)
                for i, n in enumerate(active_defenders):
                    is_sel = n in state['selected_targets']
                    if cols[i%7].button(str(n), key=f"def_{n}", type="primary" if is_sel else "secondary", use_container_width=True):
                        if is_sel: state['selected_targets'].remove(n)
                        else: state['selected_targets'].append(n)
                        save_kabaddi_scores(evt_code, mid, state); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><hr style='margin:10px 0;'>", unsafe_allow_html=True)
        c_act1, c_act2, c_act3 = st.columns([1, 2, 1])
        with c_act2:
            cc1, cc2 = st.columns(2)
            if cc1.button("🛡️ ट्याकल/आउट", type="primary", use_container_width=True):
                is_super_tackle = len(active_defenders) <= 3
                tackle_pts = 2 if is_super_tackle else 1
                state['out_players'][raider_t].append(r_num); add_score_and_revive(defender_t, tackle_pts); state['empty_raids'][raider_t] = 0 
                
                state['last_event_msg'] = f"🌟 सुपर ट्याकल! (+2 अङ्क)" if is_super_tackle else f"🛡️ ट्याकल! (+1 अङ्क)"
                state['last_event_icon'] = "kB_raider_out.png"
                reset_raid(); save_kabaddi_scores(evt_code, mid, state); st.rerun()
                
            if cc2.button("🔙 क्यान्सिल", use_container_width=True):
                state['last_event_msg'] = "🔙 रेड रद्द गरियो!" 
                state['last_event_icon'] = "KB_cant_broken.png"
                reset_raid(is_cancel=True); save_kabaddi_scores(evt_code, mid, state); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    c_end1, c_end2, c_end3 = st.columns([1, 2, 1])
    btn_label = "⏸️ पहिलो हाफ समाप्त गर्नुहोस्" if c_half == 1 else "🏁 म्याच समाप्त गर्नुहोस्"
    if c_end2.button(btn_label, use_container_width=True, type="secondary"):
        if c_half == 1:
            state['half'] = 2; state['swap_sides'] = not state['swap_sides']; state['half_1_score'] = f"{state['score_a']}-{state['score_b']}"
            state['match_started'] = False; state['timer_running'] = False; state['next_raider_team'] = p2 if state.get('first_half_starter') == p1 else p1 
            state['last_event_msg'] = "🔄 हाफ परिवर्तन भयो!"
            state['last_event_icon'] = "KB_match_end.png"
            save_kabaddi_scores(evt_code, mid, state); st.rerun()
        else:
            winner = p1 if state['score_a'] > state['score_b'] else p2 if state['score_b'] > state['score_a'] else "Tie"
            # 💡 Team IDs instead of general string ID
            winner_team_id = sel_m['p1_id'] if winner == p1 else sel_m['p2_id'] if winner == p2 else None
            winner_muni_id = sel_m['p1_muni'] if winner == p1 else sel_m['p2_muni'] if winner == p2 else None
            
            conn = db.get_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE matches SET winner_name=%s, winner_team_id=%s, winner_muni_id=%s, live_state=%s, status='Completed' 
                WHERE match_no=%s AND event_code=%s
            """, (winner, winner_team_id, winner_muni_id, json.dumps(state), mid, evt_code))
            conn.commit()
            c.close()
            conn.close()
            
            state['last_event_msg'] = f"🏁 म्याच सम्पन्न! {winner} विजयी!" 
            state['last_event_icon'] = "KB_match_end.png"
            save_kabaddi_scores(evt_code, mid, state); st.balloons(); st.stop()


    # ==========================================
    # ⚙️ SIDE PANELS & HIDDEN SETTINGS
    # ==========================================
    st.divider()
    
    with st.expander("⚙️ म्यानुअल कन्ट्रोल (गल्ती सच्याउन)"):
        c_mc1, c_mc2 = st.columns(2)
        if c_mc1.button("🔄 पालो (Turn) परिवर्तन गर्नुहोस्", use_container_width=True):
            if state.get('next_raider_team'): state['next_raider_team'] = left_team if state['next_raider_team'] == right_team else right_team; st.rerun()
        if c_mc2.button("🔄 कोर्टको साइड स्वाप (Swap Sides)", use_container_width=True):
            state['swap_sides'] = not state['swap_sides']; state['last_event_msg'] = "🔄 म्यानुअल साइड स्वाप!"; state['last_event_icon']="KB_substitution.png"; save_kabaddi_scores(evt_code, mid, state); st.rerun()

    def toggle_state(key):
        st.session_state[key] = not st.session_state.get(key, False); st.rerun()

    def render_side_panel(team, col):
        with col:
            active_p = len([n for n in state['lineup'].get(team, {}).get('court', []) if n not in state.get('out_players', {}).get(team, [])])
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            if c1.button(f"🔄 Subs({5-state.get('subs', {}).get(team, 0)})", key=f"bs_{team}", use_container_width=True): toggle_state(f"{state_key}_show_subs_{team}")
            if c2.button("🃏 Cards", key=f"bc_{team}", use_container_width=True): toggle_state(f"{state_key}_show_cards_{team}")
            if c3.button("⚙️ Tech Pt", key=f"bt_{team}", use_container_width=True): 
                add_score_and_revive(team, 1)
                state['last_event_msg'] = f"⚙️ {team} लाई प्राविधिक अङ्क (+1)"
                state['last_event_icon'] = "KB_touch_point.png"
                save_kabaddi_scores(evt_code, mid, state); st.rerun()
            if c4.button("⏳ Time", key=f"bto_{team}", use_container_width=True): 
                if state.get('timeouts', {}).get(str(c_half), {}).get(team, 0) < 2: 
                    if str(c_half) not in state['timeouts']: state['timeouts'][str(c_half)] = {}
                    state['timeouts'][str(c_half)][team] = state['timeouts'][str(c_half)].get(team, 0) + 1
                    state['timeout_active'] = True; state['timer_running'] = False 
                    state['last_event_msg'] = f"⏳ {team} को टाइमआउट!"
                    state['last_event_icon'] = "KB_time_out.png"
                    save_kabaddi_scores(evt_code, mid, state); st.rerun()
            
            if active_p == 0:
                if st.button("🚨 LONA", type="primary", use_container_width=True, key=f"lona_{team}"): state['lona_transition'] = team; st.rerun()

            if st.session_state.get(f"{state_key}_show_subs_{team}"):
                st.markdown("<div style='background:#f8fafc; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                subs_left = 5 - state.get('subs', {}).get(team, 0)
                if subs_left > 0:
                    co, ci = st.columns(2)
                    co.caption("Out (Court):"); ci.caption("In (Bench):")
                    valid_bench = [b for b in state['lineup'][team]['bench'] if state.get('cards', {}).get(team, {}).get(b) != 'Red']
                    sub_out = state.get(f"sub_out_{team}"); sub_in = state.get(f"sub_in_{team}")
                    
                    bo = co.columns(3)
                    for i, op in enumerate(state['lineup'][team]['court']):
                        if bo[i%3].button(str(op), key=f"so_{team}_{op}", type="primary" if sub_out==op else "secondary"): state[f"sub_out_{team}"] = op; st.rerun()
                    bi = ci.columns(3)
                    for i, ip in enumerate(valid_bench):
                        if bi[i%3].button(str(ip), key=f"si_{team}_{ip}", type="primary" if sub_in==ip else "secondary"): state[f"sub_in_{team}"] = ip; st.rerun()
                            
                    if sub_out and sub_in:
                        if st.button(f"✅ Swap {sub_out} ↔ {sub_in}", key=f"do_sub_{team}", use_container_width=True):
                            c_idx, b_idx = state['lineup'][team]['court'].index(sub_out), state['lineup'][team]['bench'].index(sub_in)
                            state['lineup'][team]['court'][c_idx] = sub_in; state['lineup'][team]['bench'][b_idx] = sub_out
                            state['subs'][team] += 1; state[f"sub_out_{team}"] = None; state[f"sub_in_{team}"] = None
                            
                            state['last_event_msg'] = f"🔄 खेलाडी परिवर्तन: {sub_out} Out ➔ {sub_in} In" 
                            state['last_event_icon'] = "KB_substitution.png"
                            
                            toggle_state(f"{state_key}_show_subs_{team}")
                            save_kabaddi_scores(evt_code, mid, state); st.rerun()
                else: st.error("Subs Limit Reached!")
                st.markdown("</div>", unsafe_allow_html=True)

            if st.session_state.get(f"{state_key}_show_cards_{team}"):
                st.markdown("<div style='background:#fef2f2; padding:10px; border-radius:5px;'>", unsafe_allow_html=True)
                y_cards = [p for p, c in state.get('cards', {}).get(team, {}).items() if c == 'Yellow']
                for yp in y_cards:
                    if st.button(f"⏱️ {yp} लाई भित्र पठाउनुहोस्", key=f"y_clr_{team}_{yp}"):
                        state['cards'][team].pop(yp)
                        if yp in state.get('yc_timers', {}).get(team, {}): state['yc_timers'][team].pop(yp)
                        state['last_event_msg'] = f"🟨 जर्सी {yp} कोर्टमा फर्किए!"
                        state['last_event_icon'] = "KB_substitution.png"
                        save_kabaddi_scores(evt_code, mid, state); st.rerun()

                cd1, cd2, cd3 = st.columns(3)
                sel_card = state.get(f'card_sel_{team}', None)
                if cd1.button("🟩", key=f"cg_{team}", use_container_width=True): state[f'card_sel_{team}'] = "Green"; st.rerun()
                if cd2.button("🟨", key=f"cy_{team}", use_container_width=True): state[f'card_sel_{team}'] = "Yellow"; st.rerun()
                if cd3.button("🟥", key=f"cr_{team}", use_container_width=True): state[f'card_sel_{team}'] = "Red"; st.rerun()
                
                if sel_card:
                    st.caption(f"{sel_card} कार्ड कसलाई?")
                    active_for_card = state['lineup'].get(team, {}).get('court', []) + state['lineup'].get(team, {}).get('bench', [])
                    btn_c = st.columns(7)
                    for i, cp in enumerate(active_for_card):
                        if btn_c[i%7].button(str(cp), key=f"cbtn_{team}_{cp}"):
                            if team not in state['cards']: state['cards'][team] = {}
                            if team not in state['yc_timers']: state['yc_timers'][team] = {}
                            
                            state['cards'][team][cp] = sel_card
                            
                            state['last_event_icon'] = "KB_penalty_card.png"
                            if sel_card == 'Yellow': 
                                state['yc_timers'][team][cp] = time.time()
                                state['last_event_msg'] = f"🟨 जर्सी {cp} लाई पहेँलो कार्ड (२ मिनेट निलम्बन)!"
                            elif sel_card == 'Red':
                                state['last_event_msg'] = f"🟥 जर्सी {cp} लाई रातो कार्ड (निष्कासन)!"
                            else:
                                state['last_event_msg'] = f"🟩 जर्सी {cp} लाई ग्रीन कार्ड (चेतावनी)!"
                                
                            if sel_card in ['Yellow', 'Red'] and cp not in state['out_players'].get(team, []): state['out_players'][team].append(cp) 
                            state[f'card_sel_{team}'] = None
                            toggle_state(f"{state_key}_show_cards_{team}")
                            save_kabaddi_scores(evt_code, mid, state); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

    c_panel_L, c_panel_R = st.columns(2)
    render_side_panel(left_team, c_panel_L)
    render_side_panel(right_team, c_panel_R)