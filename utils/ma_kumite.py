import streamlit as st
import database as db
import utils.ma_bracket as ma_bracket
from datetime import datetime
import time
import re
import psycopg2.extras
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components 

def render_panel(evt_code, current_event, players_df, bout_info):
    """Advanced WKF 2026 Operator Panel with Countdown, Beeps & Direct DB Sync"""
    
    round_text = bout_info.get('r_name', '')
    bout_id_text = bout_info.get('id', '')
    
    st.markdown(f"<h3 style='text-align:center; color:#1E88E5; margin:0;'>🥊 Kumite - {round_text} {bout_id_text}</h3>", unsafe_allow_html=True)
    
    def get_full_name(p_str):
        return str(p_str).split(" [ID:")[0] if p_str else "Unknown"
        
    p_a_name = get_full_name(bout_info['p1']) # AKA (Red)
    p_b_name = get_full_name(bout_info['p2']) # AO (Blue)

    # ==========================================
    # ⚙️ STATE INITIALIZATION (Session State)
    # ==========================================
    prefix = f"kumite_{evt_code}_{bout_id_text}"
    MAX_TIME = 180.0 # 3 Minutes
    
    if f"{prefix}_init" not in st.session_state:
        st.session_state[f"{prefix}_a"] = 0 
        st.session_state[f"{prefix}_b"] = 0 
        st.session_state[f"{prefix}_pen_a"] = 0 
        st.session_state[f"{prefix}_pen_b"] = 0 
        st.session_state[f"{prefix}_senshu"] = None
        st.session_state[f"{prefix}_hantei"] = None
        
        st.session_state[f"{prefix}_timer_running"] = False
        st.session_state[f"{prefix}_elapsed_time"] = 0.0
        st.session_state[f"{prefix}_last_start_time"] = None
        st.session_state[f"{prefix}_game_over"] = False
        st.session_state[f"{prefix}_winner_revealed"] = False 
        
        # Audio Flags
        st.session_state[f"{prefix}_played_15s"] = False
        st.session_state[f"{prefix}_played_8pt"] = False
        st.session_state[f"{prefix}_played_end"] = False
        
        st.session_state[f"{prefix}_init"] = True

        # पहिलो पटक प्यानल खुल्दा डाटाबेसमा म्याच सुरु भएको जानकारी पठाउने
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM live_match") # पुरानो म्याच हटाउने
        c.execute("""
            INSERT INTO live_match (event_code, bout_id, event_name, round_name, player1, player2, score_a, score_b, pen_a, pen_b, timer)
            VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0, 0, '03:00')
        """, (evt_code, bout_id_text, current_event['name'], round_text, p_a_name, p_b_name))
        conn.commit()
        c.close()
        conn.close()

    # ==========================================
    # ⏱️ TIMER CALCULATION
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
    
    e_mins, e_secs = divmod(int(elapsed), 60)
    timer_display_up = f"{e_mins:02d}:{e_secs:02d}"

    # ==========================================
    # 🎵 AUDIO BEEP SYSTEM
    # ==========================================
    def play_beeps(type):
        js_code = ""
        if type == "15s": js_code = "playBeep(2, 0.2, 800);"
        elif type == "8pt": js_code = "playBeep(8, 0.15, 1000);"
        elif type == "end": js_code = "playBeep(1, 1.0, 600);"
            
        components.html(f"""
        <script>
            function playBeep(times, duration, freq) {{
                let ctx = new (window.AudioContext || window.webkitAudioContext)();
                let i = 0;
                let interval = setInterval(() => {{
                    let osc = ctx.createOscillator();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, ctx.currentTime);
                    osc.connect(ctx.destination);
                    osc.start();
                    osc.stop(ctx.currentTime + duration);
                    i++;
                    if(i >= times) clearInterval(interval);
                }}, (duration * 1000) + 50);
            }}
            {js_code}
        </script>
        """, height=0, width=0)

    # ==========================================
    # 🛑 AUTO GAME OVER TRIGGERS
    # ==========================================
    s_a, s_b = st.session_state[f"{prefix}_a"], st.session_state[f"{prefix}_b"]
    pen_a, pen_b = st.session_state[f"{prefix}_pen_a"], st.session_state[f"{prefix}_pen_b"]
    
    if int(remaining) == 15 and not st.session_state[f"{prefix}_played_15s"]:
        play_beeps("15s"); st.session_state[f"{prefix}_played_15s"] = True

    if abs(s_a - s_b) >= 8 and not st.session_state[f"{prefix}_game_over"]:
        st.session_state[f"{prefix}_game_over"] = True
        st.session_state[f"{prefix}_timer_running"] = False
        if not st.session_state[f"{prefix}_played_8pt"]:
            play_beeps("8pt"); st.session_state[f"{prefix}_played_8pt"] = True
            
    if remaining <= 0 and not st.session_state[f"{prefix}_game_over"]:
        st.session_state[f"{prefix}_elapsed_time"] = MAX_TIME
        st.session_state[f"{prefix}_timer_running"] = False
        st.session_state[f"{prefix}_game_over"] = True
        if not st.session_state[f"{prefix}_played_end"]:
            play_beeps("end"); st.session_state[f"{prefix}_played_end"] = True

    if (pen_a >= 5 or pen_b >= 5) and not st.session_state[f"{prefix}_game_over"]:
        st.session_state[f"{prefix}_game_over"] = True
        st.session_state[f"{prefix}_timer_running"] = False

    is_game_over = st.session_state[f"{prefix}_game_over"]

    # ==========================================
    # 📡 SYNC TO DATABASE (For Mat_Scoreboard.py)
    # ==========================================
    def sync_to_db():
        conn = db.get_connection()
        cur = conn.cursor()
        senshu_val = st.session_state[f"{prefix}_senshu"]
        cur.execute("""
            UPDATE live_match 
            SET score_a=%s, score_b=%s, pen_a=%s, pen_b=%s, senshu=%s, timer=%s
        """, (s_a, s_b, pen_a, pen_b, senshu_val, timer_display_down))
        conn.commit()
        cur.close()
        conn.close()

    # हरेक पटक टाइमर चल्दा डाटाबेस अपडेट गर्ने (२ सेकेन्डमा एकपटक)
    if st.session_state[f"{prefix}_timer_running"] and int(elapsed) % 2 == 0:
        sync_to_db()

    # ==========================================
    # 🎛️ TIMER UI
    # ==========================================
    c_t1, c_t2, c_t3 = st.columns([1, 2, 1])
    with c_t2:
        st.markdown(f"""
        <div style='background:#1e293b; color:#fbbf24; font-size:45px; font-weight:bold; text-align:center; 
                    border:3px solid #fbbf24; border-radius:10px; padding:0px 5px; font-family:monospace; margin-bottom:10px;'>
            {timer_display_down}
            <div style='font-size:14px; color:#cbd5e1; margin-top:-10px; padding-bottom:5px;'>Elapsed: {timer_display_up}</div>
        </div>
        """, unsafe_allow_html=True)
    
    b_t1, b_t2, b_t3 = st.columns([1, 1, 1])
    with b_t1:
        if st.button("▶️ Start", disabled=st.session_state[f"{prefix}_timer_running"] or is_game_over, use_container_width=True):
            st.session_state[f"{prefix}_timer_running"] = True
            st.session_state[f"{prefix}_last_start_time"] = time.time()
            st.rerun()
    with b_t2:
        if st.button("⏸️ Pause", disabled=not st.session_state[f"{prefix}_timer_running"], use_container_width=True):
            st.session_state[f"{prefix}_timer_running"] = False
            sync_to_db(); st.rerun()
    with b_t3:
        if st.button("🛑 End Match", disabled=is_game_over, type="primary", use_container_width=True):
            st.session_state[f"{prefix}_timer_running"] = False
            st.session_state[f"{prefix}_game_over"] = True
            sync_to_db(); st.rerun()

    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

    def get_pen_info(level):
        if level == 0: return "", "#cbd5e1", ""
        colors = ["#facc15", "#fb923c", "#ea580c", "#dc2626", "#7f1d1d"] 
        names = ["Chui 1", "Chui 2", "Chui 3", "Hansoku-Chui", "Hansoku"]
        icons = ["⚠️", "⚠️", "⚠️", "🟥", "❌"]
        return names[level-1], colors[level-1], icons[level-1]

    def update_score(target, pts):
        st.session_state[f"{prefix}_{target}"] = max(0, st.session_state[f"{prefix}_{target}"] + pts)
        opp = 'b' if target == 'a' else 'a'
        if pts > 0 and st.session_state[f"{prefix}_senshu"] is None and st.session_state[f"{prefix}_{opp}"] == 0:
            st.session_state[f"{prefix}_senshu"] = 'Red' if target == 'a' else 'Blue'
        sync_to_db(); st.rerun()

    def update_pen(target, val):
        st.session_state[f"{prefix}_pen_{target}"] = max(0, min(5, st.session_state[f"{prefix}_pen_{target}"] + val))
        sync_to_db(); st.rerun()

    def get_penalty_ui(count):
        squares = ""
        for i in range(1, 6):
            bg_color = get_pen_info(i)[1] if i <= count else "transparent"
            border = "1px solid #cbd5e1" if i > count else "none"
            icon = get_pen_info(i)[2] if i <= count else ""
            shadow = f"box-shadow: 0 0 5px {bg_color};" if i <= count else ""
            squares += f"<div style='width:24px; height:24px; background:{bg_color}; border:{border}; margin:0 3px; display:inline-flex; align-items:center; justify-content:center; border-radius:4px; font-size:12px; {shadow}'>{icon}</div>"
        
        p_name, p_color, _ = get_pen_info(count)
        label = f"<div style='color:{p_color}; font-weight:bold; font-size:16px; margin-top:5px; height:24px;'>{p_name if count > 0 else '&nbsp;'}</div>"
        return f"<div style='text-align:center; margin-top:15px;'><div style='display:flex; justify-content:center; align-items:center;'><span style='font-size:14px; font-weight:bold; color:#64748b; margin-right:8px;'>Penalty:</span>{squares}</div>{label}</div>"

    # ==========================================
    # 🎨 OPERATOR SCOREBOARD (UI)
    # ==========================================
    c_sa, c_mid, c_sb = st.columns([2, 0.8, 2])
    senshu = st.session_state[f"{prefix}_senshu"]
    
    with c_sa:
        st.markdown(f"<div style='border:4px solid #dc2626; border-radius:10px; padding:20px; background-color:#fef2f2;'><h1 style='text-align:center; color:#dc2626; font-size:90px; margin:0;'>{s_a}</h1><h3 style='text-align:center; color:#dc2626; margin:5px 0;'>🔴 AKA</h3><div style='font-size:16px; text-align:center; font-weight:bold; color:#b91c1c;'>{p_a_name}</div>{get_penalty_ui(pen_a)}</div>", unsafe_allow_html=True)

    with c_mid:
        st.markdown("<div style='text-align:center; margin:30px 0 10px 0; font-weight:bold; color:#64748b;'>SENSHU</div>", unsafe_allow_html=True)
        if not senshu:
            c1, c2 = st.columns(2)
            if c1.button("🔴", disabled=is_game_over, use_container_width=True): st.session_state[f"{prefix}_senshu"] = 'Red'; sync_to_db(); st.rerun()
            if c2.button("🔵", disabled=is_game_over, use_container_width=True): st.session_state[f"{prefix}_senshu"] = 'Blue'; sync_to_db(); st.rerun()
        else:
            col = "#dc2626" if senshu == 'Red' else "#2563eb"
            st.markdown(f"<div style='text-align:center; background-color:{col}; color:white; padding:8px; border-radius:5px; font-weight:bold;'>CLAIMED</div>", unsafe_allow_html=True)
            if st.button("❌ Undo", disabled=is_game_over, use_container_width=True): st.session_state[f"{prefix}_senshu"] = None; sync_to_db(); st.rerun()

    with c_sb:
        st.markdown(f"<div style='border:4px solid #2563eb; border-radius:10px; padding:20px; background-color:#eff6ff;'><h1 style='text-align:center; color:#2563eb; font-size:90px; margin:0;'>{s_b}</h1><h3 style='text-align:center; color:#2563eb; margin:5px 0;'>🔵 AO</h3><div style='font-size:16px; text-align:center; font-weight:bold; color:#1d4ed8;'>{p_b_name}</div>{get_penalty_ui(pen_b)}</div>", unsafe_allow_html=True)

    # ==========================================
    # 🎛️ ACTION BUTTONS
    # ==========================================
    st.markdown("<style>.stButton button { height: 50px; font-weight: bold; border-radius: 8px;} .red-zone { border-right: 4px solid #dc2626; padding-right: 15px; } .blue-zone { border-left: 4px solid #2563eb; padding-left: 15px; }</style>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    ac_a, ac_div, ac_b = st.columns([1, 0.05, 1])

    with ac_a:
        st.markdown('<div class="red-zone">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        if col1.button("👊 Yuko (1)", key="k1a", disabled=is_game_over): update_score('a', 1)
        if col2.button("🦵 Waza (2)", key="k2a", disabled=is_game_over): update_score('a', 2)
        if col3.button("💥 Ippon (3)", key="k3a", disabled=is_game_over): update_score('a', 3)
        f_lbl = f"⚠️ Foul ({get_pen_info(pen_a + 1)[0]})" if pen_a < 5 else "🚫 Disqualified"
        f1, f2, f3 = st.columns([1.5, 0.7, 0.8])
        if f1.button(f_lbl, key="fa", disabled=is_game_over or pen_a>=5): update_pen('a', 1)
        if f2.button("➖1", key="ma", disabled=is_game_over): update_score('a', -1)
        if f3.button("🔙", key="ua", disabled=is_game_over): update_pen('a', -1)
        st.markdown('</div>', unsafe_allow_html=True)

    with ac_div: st.markdown("<div style='border-left: 3px dashed #cbd5e1; height: 120px; margin: 0 auto;'></div>", unsafe_allow_html=True)

    with ac_b:
        st.markdown('<div class="blue-zone">', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        if col1.button("👊 Yuko (1)", key="k1b", disabled=is_game_over): update_score('b', 1)
        if col2.button("🦵 Waza (2)", key="k2b", disabled=is_game_over): update_score('b', 2)
        if col3.button("💥 Ippon (3)", key="k3b", disabled=is_game_over): update_score('b', 3)
        f_lbl = f"⚠️ Foul ({get_pen_info(pen_b + 1)[0]})" if pen_b < 5 else "🚫 Disqualified"
        f1, f2, f3 = st.columns([1.5, 0.7, 0.8])
        if f1.button(f_lbl, key="fb", disabled=is_game_over or pen_b>=5): update_pen('b', 1)
        if f2.button("➖1", key="mb", disabled=is_game_over): update_score('b', -1)
        if f3.button("🔙", key="ub", disabled=is_game_over): update_pen('b', -1)
        st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # 🏁 WINNER REVEAL & SAVE
    # ==========================================
    st.divider()
    if is_game_over:
        st.error("🛑 MATCH ENDED - Waiting for Referee's Hand Signal")
        is_tie = (s_a == s_b and not senshu and pen_a < 5 and pen_b < 5)
        
        if is_tie and not st.session_state[f"{prefix}_hantei"]:
            st.warning("⚠️ स्कोर बराबर छ! कृपया जजहरूको निर्णय (HANTEI) अनुसार विजेता छान्नुहोस्:")
            h1, h2 = st.columns(2)
            if h1.button("🚩 AKA Wins (Hantei)", use_container_width=True): st.session_state[f"{prefix}_hantei"] = 'AKA'; st.rerun()
            if h2.button("🎌 AO Wins (Hantei)", use_container_width=True): st.session_state[f"{prefix}_hantei"] = 'AO'; st.rerun()
            st.stop()
            
        if st.session_state[f"{prefix}_hantei"]:
            st.success(f"✅ Hantei Decision Registered: **{st.session_state[f'{prefix}_hantei']}**")

        c_rev, c_rst = st.columns([3, 1])
        with c_rev:
            if not st.session_state[f"{prefix}_winner_revealed"]:
                if st.button("💾 Save Match Result to Bracket", type="primary", use_container_width=True):
                    win_id = None
                    if pen_a >= 5: win_id = bout_info['p2']
                    elif pen_b >= 5: win_id = bout_info['p1']
                    elif s_a > s_b: win_id = bout_info['p1']
                    elif s_b > s_a: win_id = bout_info['p2']
                    elif s_a == s_b and senshu: win_id = bout_info['p1'] if senshu == 'Red' else bout_info['p2']
                    elif s_a == s_b and st.session_state[f"{prefix}_hantei"]: win_id = bout_info['p1'] if st.session_state[f"{prefix}_hantei"] == 'AKA' else bout_info['p2']

                    if win_id:
                        st.session_state[f"{prefix}_winner_revealed"] = True
                        
                        # 💡 टाइसिट (Bracket) अपडेट गर्ने
                        st.session_state[f"winner_{evt_code}_{bout_info['id']}"] = win_id
                        st.session_state[f"published_{evt_code}_{bout_info['id']}"] = True
                        
                        # 💡 यदि यो फाइनल म्याच हो भने, मेडल डाटाबेसमा सेभ गर्ने
                        if round_text == "Final":
                            def ext_ids(s_val):
                                p_match = re.search(r"\[ID:\s*(\d+)\]", s_val)
                                m_match = re.search(r"\[M_ID:\s*(\d+)\]", s_val)
                                return (int(p_match.group(1)) if p_match else None), (int(m_match.group(1)) if m_match else None)
                            
                            loser_id = bout_info['p2'] if win_id == bout_info['p1'] else bout_info['p1']
                            win_pid, win_mid = ext_ids(win_id)
                            lose_pid, lose_mid = ext_ids(loser_id)
                            final_score = f"{s_a}-{s_b}"
                            
                            conn = db.get_connection()
                            c = conn.cursor()
                            if win_pid and win_mid:
                                c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 1, 'Gold', %s)", (evt_code, win_mid, win_pid, f'{{"score": "{final_score}"}}'))
                            if lose_pid and lose_mid:
                                c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 2, 'Silver', %s)", (evt_code, lose_mid, lose_pid, f'{{"score": "{final_score}"}}'))
                            conn.commit(); c.close(); conn.close()
                            st.toast("🎉 स्वर्ण र रजत पदक सुरक्षित भयो!")

                        # क्लाउडमा प्रोग्रेस सेभ गर्ने
                        ma_bracket.sync_progress_to_db(evt_code)
                        
                        # लाइभ म्याच टेबल सफा गर्ने
                        conn = db.get_connection()
                        conn.cursor().execute("DELETE FROM live_match")
                        conn.commit()
                        conn.close()
                        
                        st.session_state.active_bout_data = None
                        st.success(f"✅ Winner Saved! Advancing to next round...")
                        st.rerun()
            else:
                st.success("✅ Winner has been published to Database.")

        with c_rst:
            if st.button("🔄 Reset Scoreboard", type="secondary", use_container_width=True):
                keys_to_delete = [k for k in st.session_state.keys() if k.startswith(prefix)]
                for k in keys_to_delete: del st.session_state[k]
                st.rerun()