import streamlit as st
import pandas as pd
import database as db
import utils.ma_bracket as ma_bracket
from datetime import datetime
import time
import re
import psycopg2.extras
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components 

def render_panel(evt_code, current_event, players_df, bout_info):
    """WT 2026 Rules Kyorugi (Taekwondo) Operator Panel"""
    
    round_text = bout_info.get('r_name', '')
    bout_id_text = bout_info.get('id', '')
    
    st.markdown(f"<h3 style='text-align:center; color:#1E88E5; margin:0;'>🥋 Kyorugi (WT 2026) - {round_text} {bout_id_text}</h3>", unsafe_allow_html=True)
    
    def get_full_name(p_str):
        return str(p_str).split(" [ID:")[0] if p_str else "Unknown"
        
    p_a_name = get_full_name(bout_info['p1']) # Chung (Blue)
    p_b_name = get_full_name(bout_info['p2']) # Hong (Red)

    # ==========================================
    # ⚙️ STATE INITIALIZATION (Best of 3 & WT 2026)
    # ==========================================
    prefix = f"tkd_{evt_code}_{bout_info['id']}"
    
    if f"{prefix}_init" not in st.session_state:
        st.session_state[f"{prefix}_a"] = 0 
        st.session_state[f"{prefix}_b"] = 0 
        st.session_state[f"{prefix}_gj_a"] = 0 # Gam-jeoms
        st.session_state[f"{prefix}_gj_b"] = 0 
        st.session_state[f"{prefix}_rw_a"] = 0 # Round Wins
        st.session_state[f"{prefix}_rw_b"] = 0 
        st.session_state[f"{prefix}_round"] = 1 # Current Round (1 to 3)
        st.session_state[f"{prefix}_logs"] = []
        
        # Timer States (WT Standard: 2 Mins per round)
        st.session_state[f"{prefix}_timer_running"] = False
        st.session_state[f"{prefix}_elapsed_time"] = 0.0
        st.session_state[f"{prefix}_last_start_time"] = None
        st.session_state[f"{prefix}_game_over"] = False
        st.session_state[f"{prefix}_played_end"] = False 
        st.session_state[f"{prefix}_init"] = True

        # पहिलो पटक प्यानल खुल्दा डाटाबेसमा म्याच सुरु भएको जानकारी पठाउने
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM live_match") # पुरानो म्याच हटाउने
        c.execute("""
            INSERT INTO live_match (event_code, bout_id, event_name, round_name, player1, player2, score_a, score_b, pen_a, pen_b, timer)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0, 0, '02:00')
        """, (evt_code, bout_id_text, current_event['name'], f"Round 1 ({round_text})", p_a_name, p_b_name))
        conn.commit()
        c.close()
        conn.close()

    # ==========================================
    # 🎵 AUDIO BEEP SYSTEM
    # ==========================================
    def play_time_up_beep():
        components.html("""
        <script>
            let ctx = new (window.AudioContext || window.webkitAudioContext)();
            let osc = ctx.createOscillator();
            osc.type = 'sine';
            osc.frequency.setValueAtTime(600, ctx.currentTime);
            osc.connect(ctx.destination);
            osc.start();
            osc.stop(ctx.currentTime + 1.0); // १ सेकेन्डको लामो बीप
        </script>
        """, height=0, width=0)

    # ==========================================
    # ⏱️ TIMER LOGIC
    # ==========================================
    MAX_TIME = 120.0 # 2 Minutes per round
    
    if st.session_state[f"{prefix}_timer_running"]:
        current_time = time.time()
        added_time = current_time - st.session_state[f"{prefix}_last_start_time"]
        st.session_state[f"{prefix}_elapsed_time"] += added_time
        st.session_state[f"{prefix}_last_start_time"] = current_time
        st_autorefresh(interval=1000, key=f"timer_ref_tkd_{bout_info['id']}")

    elapsed = st.session_state[f"{prefix}_elapsed_time"]
    remaining = max(0.0, MAX_TIME - elapsed)
    mins, secs = divmod(int(remaining), 60)
    timer_display = f"{mins:02d}:{secs:02d}"

    if remaining <= 0 and not st.session_state[f"{prefix}_played_end"]:
        st.session_state[f"{prefix}_elapsed_time"] = MAX_TIME
        st.session_state[f"{prefix}_timer_running"] = False
        play_time_up_beep()
        st.session_state[f"{prefix}_played_end"] = True

    is_game_over = st.session_state[f"{prefix}_game_over"]
    cur_round = st.session_state[f"{prefix}_round"]

    # ==========================================
    # 📡 LIVE TV SYNC (PostgreSQL Direct)
    # ==========================================
    def sync_to_db():
        s_a = st.session_state[f"{prefix}_a"]
        s_b = st.session_state[f"{prefix}_b"]
        gj_a = st.session_state[f"{prefix}_gj_a"]
        gj_b = st.session_state[f"{prefix}_gj_b"]
        rw_a = st.session_state[f"{prefix}_rw_a"]
        rw_b = st.session_state[f"{prefix}_rw_b"]
        
        # राउन्ड र जितको जानकारी पठाउने
        display_round = f"Round {cur_round} (W: {rw_a}-{rw_b})" if not is_game_over else f"FINISHED ({rw_a}-{rw_b})"
        
        conn = db.get_connection()
        cur = conn.cursor()
        cur.execute("""
            UPDATE live_match 
            SET score_a=%s, score_b=%s, pen_a=%s, pen_b=%s, round_name=%s, timer=%s
        """, (s_a, s_b, gj_a, gj_b, display_round, timer_display))
        conn.commit()
        cur.close()
        conn.close()

    if st.session_state[f"{prefix}_timer_running"] and int(elapsed) % 2 == 0:
        sync_to_db()

    # ==========================================
    # 🎛️ ROUND & TIMER CONTROLS
    # ==========================================
    c_t1, c_t2, c_t3 = st.columns([1, 2, 1])
    with c_t2:
        st.markdown(f"""
        <div style='background:#1e293b; color:#10b981; font-size:35px; font-weight:bold; text-align:center; 
                    border:3px solid #10b981; border-radius:10px; padding:5px; font-family:monospace; margin-bottom:10px;'>
            R{cur_round} - {timer_display}
        </div>
        """, unsafe_allow_html=True)
    
    b_t1, b_t2, b_t3 = st.columns([1, 1, 1])
    with b_t1:
        if st.button("▶️ Start/Resume", disabled=st.session_state[f"{prefix}_timer_running"] or is_game_over, width="stretch"):
            st.session_state[f"{prefix}_timer_running"] = True
            st.session_state[f"{prefix}_last_start_time"] = time.time()
            st.rerun()
    with b_t2:
        if st.button("⏸️ Pause", disabled=not st.session_state[f"{prefix}_timer_running"], width="stretch"):
            st.session_state[f"{prefix}_timer_running"] = False
            sync_to_db()
            st.rerun()
    with b_t3:
        if st.button("🏁 End Round", disabled=is_game_over, type="primary", width="stretch"):
            st.session_state[f"{prefix}_timer_running"] = False
            
            s_a = st.session_state[f"{prefix}_a"]
            s_b = st.session_state[f"{prefix}_b"]
            gj_a = st.session_state[f"{prefix}_gj_a"]
            gj_b = st.session_state[f"{prefix}_gj_b"]
            
            # Award Round Win
            if gj_a >= 5: st.session_state[f"{prefix}_rw_b"] += 1
            elif gj_b >= 5: st.session_state[f"{prefix}_rw_a"] += 1
            elif s_a > s_b: st.session_state[f"{prefix}_rw_a"] += 1
            elif s_b > s_a: st.session_state[f"{prefix}_rw_b"] += 1
            else:
                st.warning("Round Tied! Resolve via Superiority (Woo-se-girok) before ending.")
            
            # Check Match Winner
            if st.session_state[f"{prefix}_rw_a"] == 2 or st.session_state[f"{prefix}_rw_b"] == 2:
                st.session_state[f"{prefix}_game_over"] = True
            else:
                # Reset for next round
                st.session_state[f"{prefix}_a"] = 0
                st.session_state[f"{prefix}_b"] = 0
                st.session_state[f"{prefix}_gj_a"] = 0
                st.session_state[f"{prefix}_gj_b"] = 0
                st.session_state[f"{prefix}_elapsed_time"] = 0.0
                st.session_state[f"{prefix}_played_end"] = False
                st.session_state[f"{prefix}_round"] += 1
            
            sync_to_db()
            st.rerun()

    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

    # ==========================================
    # 💡 SCORE UPDATE HELPERS
    # ==========================================
    def update_score(target, pts, action_name="Point"):
        st.session_state[f"{prefix}_{target}"] = max(0, st.session_state[f"{prefix}_{target}"] + pts)
        cur_a, cur_b = st.session_state[f"{prefix}_a"], st.session_state[f"{prefix}_b"]
        st.session_state[f"{prefix}_logs"].insert(0, {"Time": datetime.now().strftime("%H:%M:%S"), "Side": "🔵" if target=='a' else "🔴", "Desc": f"{action_name} (+{pts}) [{cur_a}-{cur_b}]"})
        sync_to_db()
        st.rerun()

    def add_gamjeom(target):
        opp = 'b' if target == 'a' else 'a'
        st.session_state[f"{prefix}_gj_{target}"] += 1
        st.session_state[f"{prefix}_{opp}"] += 1 # 1 pt to opponent
        
        st.session_state[f"{prefix}_logs"].insert(0, {"Time": datetime.now().strftime("%H:%M:%S"), "Side": "🔵" if target=='a' else "🔴", "Desc": f"⚠️ Gam-jeom (+1 to Opponent)"})
        if st.session_state[f"{prefix}_gj_{target}"] >= 5:
            st.warning(f"5 Gam-jeoms reached! Click 'End Round' to award round to opponent.")
            
        sync_to_db()
        st.rerun()

    # ==========================================
    # 🟩 UI GENERATORS
    # ==========================================
    def get_gamjeom_ui(count):
        squares = ""
        for i in range(1, 6):
            bg_color = "#facc15" if i <= count else "transparent"
            border = "1px solid #cbd5e1" if i > count else "none"
            squares += f"<div style='width:20px; height:20px; background:{bg_color}; border:{border}; margin:0 3px; display:inline-block; border-radius:4px;'></div>"
        return f"<div style='text-align:center; margin-top:5px;'><span style='font-size:14px; font-weight:bold; color:#64748b;'>Gam-jeoms:</span><br>{squares}</div>"

    def get_round_wins_ui(count, color):
        circles = ""
        for i in range(2):
            bg = color if i < count else "transparent"
            border = f"2px solid {color}"
            circles += f"<div style='width:25px; height:25px; background:{bg}; border:{border}; margin:0 5px; display:inline-block; border-radius:50%; box-shadow:0 0 5px {color};'></div>"
        return f"<div style='text-align:center; margin-bottom:10px;'>{circles}</div>"

    # ==========================================
    # 🎨 OPERATOR SCOREBOARD
    # ==========================================
    s_a, s_b = st.session_state[f"{prefix}_a"], st.session_state[f"{prefix}_b"]
    gj_a, gj_b = st.session_state[f"{prefix}_gj_a"], st.session_state[f"{prefix}_gj_b"]
    rw_a, rw_b = st.session_state[f"{prefix}_rw_a"], st.session_state[f"{prefix}_rw_b"]
    
    c_sa, c_mid, c_sb = st.columns([2, 0.5, 2])
    
    # 🔵 CHUNG (Blue)
    with c_sa:
        st.markdown(f"""
        <div style='border:4px solid #2563eb; border-radius:10px; padding:15px; background-color:#eff6ff;'>
            {get_round_wins_ui(rw_a, '#2563eb')}
            <h1 style='text-align:center; color:#2563eb; font-size:90px; margin:0; line-height:1;'>{s_a}</h1>
            <h4 style='text-align:center; color:#2563eb; margin:5px 0;'>🔵 CHUNG (Blue)</h4>
            <div style='font-size:16px; text-align:center; font-weight:bold; color:#1d4ed8;'>{p_a_name}</div>
            {get_gamjeom_ui(gj_a)}
        </div>
        """, unsafe_allow_html=True)

    with c_mid:
        st.markdown("<h2 style='text-align:center; color:#cbd5e1; margin-top:80px;'>VS</h2>", unsafe_allow_html=True)

    # 🔴 HONG (Red)
    with c_sb:
        st.markdown(f"""
        <div style='border:4px solid #dc2626; border-radius:10px; padding:15px; background-color:#fef2f2;'>
            {get_round_wins_ui(rw_b, '#dc2626')}
            <h1 style='text-align:center; color:#dc2626; font-size:90px; margin:0; line-height:1;'>{s_b}</h1>
            <h4 style='text-align:center; color:#dc2626; margin:5px 0;'>🔴 HONG (Red)</h4>
            <div style='font-size:16px; text-align:center; font-weight:bold; color:#b91c1c;'>{p_b_name}</div>
            {get_gamjeom_ui(gj_b)}
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ==========================================
    # 🎛️ ACTION BUTTONS (WT 2026 Rules)
    # ==========================================
    st.markdown("""
    <style>
        .blue-zone { border-right: 4px solid #2563eb; padding-right: 15px; }
        .red-zone { border-left: 4px solid #dc2626; padding-left: 15px; }
        .stButton button { font-weight: bold; border-radius: 8px; height: 50px; }
    </style>
    """, unsafe_allow_html=True)

    st.info("⚡ **Passive Penalty (Power Play):** यदि कुनै खेलाडीले प्यासिभ पेनाल्टी पायो भने, विपक्षीको लागि १० सेकेन्डसम्म अङ्क दोब्बर (x2) हुन्छ। तलको चेकबक्स अन गर्नुहोस्।")
    pp_c1, pp_c2 = st.columns(2)
    with pp_c1: pp_a = st.checkbox("🔥 Blue Power Play Active (x2 Pts)", key="pp_a")
    with pp_c2: pp_b = st.checkbox("🔥 Red Power Play Active (x2 Pts)", key="pp_b")
    
    mult_a = 2 if pp_a else 1
    mult_b = 2 if pp_b else 1

    ac_a, ac_div, ac_b = st.columns([1, 0.05, 1])

    with ac_a:
        st.markdown('<div class="blue-zone">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        if col1.button(f"👊 Punch (+{1 * mult_a})", key="tk_1a", disabled=is_game_over): update_score('a', 1 * mult_a, "Punch")
        if col2.button(f"🥋 Body Kick (+{2 * mult_a})", key="tk_2a", disabled=is_game_over): update_score('a', 2 * mult_a, "Body Kick")
        if col3.button(f"🤕 Head Kick (+{3 * mult_a})", key="tk_3a", disabled=is_game_over): update_score('a', 3 * mult_a, "Head Kick")
        
        col4, col5 = st.columns(2)
        if col4.button(f"🔄 Turn Body (+{4 * mult_a})", key="tk_4a", disabled=is_game_over): update_score('a', 4 * mult_a, "Turn Body Kick")
        if col5.button(f"🌪️ Turn Head (+{6 * mult_a})", key="tk_6a", disabled=is_game_over): update_score('a', 6 * mult_a, "Turn Head Kick")
        
        f1, f2 = st.columns([2, 1])
        if f1.button("⚠️ Gam-jeom", key="gj_a", disabled=is_game_over or gj_a>=5, type="primary"): add_gamjeom('a')
        if f2.button("➖1", key="m_a", disabled=is_game_over): update_score('a', -1, "Correction")
        st.markdown('</div>', unsafe_allow_html=True)

    with ac_div:
        st.markdown("<div style='border-left: 3px dashed #cbd5e1; height: 180px; margin: 0 auto;'></div>", unsafe_allow_html=True)

    with ac_b:
        st.markdown('<div class="red-zone">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        if col1.button(f"👊 Punch (+{1 * mult_b})", key="tk_1b", disabled=is_game_over): update_score('b', 1 * mult_b, "Punch")
        if col2.button(f"🥋 Body Kick (+{2 * mult_b})", key="tk_2b", disabled=is_game_over): update_score('b', 2 * mult_b, "Body Kick")
        if col3.button(f"🤕 Head Kick (+{3 * mult_b})", key="tk_3b", disabled=is_game_over): update_score('b', 3 * mult_b, "Head Kick")
        
        col4, col5 = st.columns(2)
        if col4.button(f"🔄 Turn Body (+{4 * mult_b})", key="tk_4b", disabled=is_game_over): update_score('b', 4 * mult_b, "Turn Body Kick")
        if col5.button(f"🌪️ Turn Head (+{6 * mult_b})", key="tk_6b", disabled=is_game_over): update_score('b', 6 * mult_b, "Turn Head Kick")
        
        f1, f2 = st.columns([2, 1])
        if f1.button("⚠️ Gam-jeom", key="gj_b", disabled=is_game_over or gj_b>=5, type="primary"): add_gamjeom('b')
        if f2.button("➖1", key="m_b", disabled=is_game_over): update_score('b', -1, "Correction")
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # 🏁 SAVE RESULT
    # ==========================================
    st.divider()
    if is_game_over: st.success("🏆 MATCH COMPLETED. Please Save Result.")
    
    with st.expander("📝 Match Log", expanded=False):
        logs = st.session_state[f"{prefix}_logs"]
        if logs: st.dataframe(pd.DataFrame(logs), width="stretch", hide_index=True)
    
    c_res, c_rst = st.columns([3, 1])
    with c_res:
        if st.button("💾 Save Final Result & Confirm", type="primary" if is_game_over else "secondary", width="stretch"):
            win_id = None
            
            # Winner Logic (First to 2 Round Wins)
            if rw_a == 2: win_id = bout_info['p1']
            elif rw_b == 2: win_id = bout_info['p2']
            else:
                st.warning("⚠️ Best of 3 अझै सकिएको छैन। कुनै एक खेलाडीले २ राउन्ड जित्नुपर्छ।")
                return

            if win_id:
                winner_name = get_full_name(win_id)
                loser_id = bout_info['p2'] if win_id == bout_info['p1'] else bout_info['p1']
                
                # 💡 Bracket Update
                st.session_state[f"winner_{evt_code}_{bout_info['id']}"] = win_id
                st.session_state[f"published_{evt_code}_{bout_info['id']}"] = True
                
                # 💡 Final Medal Save (PostgreSQL)
                if round_text == "Final":
                    def ext_ids(s_val):
                        p_match = re.search(r"\[ID:\s*(\d+)\]", s_val)
                        m_match = re.search(r"\[M_ID:\s*(\d+)\]", s_val)
                        return (int(p_match.group(1)) if p_match else None), (int(m_match.group(1)) if m_match else None)
                    
                    win_pid, win_mid = ext_ids(win_id)
                    lose_pid, lose_mid = ext_ids(loser_id)
                    final_score = f"{rw_a} - {rw_b}"
                    
                    conn = db.get_connection()
                    c = conn.cursor()
                    if win_pid and win_mid:
                        c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 1, 'Gold', %s)", (evt_code, win_mid, win_pid, f'{{"score": "{final_score}"}}'))
                    if lose_pid and lose_mid:
                        c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 2, 'Silver', %s)", (evt_code, lose_mid, lose_pid, f'{{"score": "{final_score}"}}'))
                    conn.commit(); c.close(); conn.close()
                    st.toast("🎉 स्वर्ण र रजत पदक डाटाबेसमा सुरक्षित भयो!")

                ma_bracket.sync_progress_to_db(evt_code)
                
                # Clear Live Match
                conn = db.get_connection()
                conn.cursor().execute("DELETE FROM live_match")
                conn.commit(); conn.close()
                
                st.session_state.active_bout_data = None
                st.toast(f"✅ Result Saved! {winner_name} Winner.")
                st.rerun()

    with c_rst:
        if st.button("🔄 Reset Match", type="secondary", width="stretch"):
            keys_to_delete = [k for k in st.session_state.keys() if k.startswith(prefix)]
            for k in keys_to_delete: del st.session_state[k]
            st.rerun()