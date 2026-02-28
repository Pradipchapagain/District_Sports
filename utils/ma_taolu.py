import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import utils.ma_bracket as ma_bracket
from datetime import datetime
import re
import psycopg2.extras # 💡 थपिएको

def render_panel(evt_code, current_event, players_df, bout_info):
    """IWUF 2024-26 Taolu Panel with 5-Judge Average Logic & Direct DB Sync"""
    
    round_text = bout_info.get('r_name', '')
    bout_id_text = bout_info.get('id', '')
    
    st.markdown(f"<h3 style='text-align:center; color:#1E88E5; margin:0;'>🐉 Wushu Taolu - {round_text} {bout_id_text}</h3>", unsafe_allow_html=True)
    st.caption("<p style='text-align:center;'>Technical (Max 5.0) + Presentation (5-Judge Avg) - Deduction = Total</p>", unsafe_allow_html=True)
    
    def get_full_name(p_str):
        return str(p_str).split(" [ID:")[0] if p_str else "Unknown"
        
    p_a_name = get_full_name(bout_info['p1'])
    p_b_name = get_full_name(bout_info['p2'])

    prefix = f"taolu_{evt_code}_{bout_info['id']}"
    
    if f"{prefix}_init" not in st.session_state:
        # Player A States
        st.session_state[f"{prefix}_tech_a"] = 0.00
        st.session_state[f"{prefix}_judges_a"] = [0.00] * 5
        st.session_state[f"{prefix}_ded_a"] = 0.00
        # Player B States
        st.session_state[f"{prefix}_tech_b"] = 0.00
        st.session_state[f"{prefix}_judges_b"] = [0.00] * 5
        st.session_state[f"{prefix}_ded_b"] = 0.00
        st.session_state[f"{prefix}_init"] = True

        # 💡 पहिलो पटक प्यानल खुल्दा डाटाबेसमा म्याच पठाउने
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM live_match") 
        c.execute("""
            INSERT INTO live_match (event_code, bout_id, event_name, round_name, player1, player2, score_a, score_b)
            VALUES (%s, %s, %s, %s, %s, %s, '0.00', '0.00')
        """, (evt_code, bout_id_text, current_event['name'], f"Taolu - {round_text}", p_a_name, p_b_name))
        conn.commit()
        c.close(); conn.close()

    def calculate_taolu_score(tech, judges, ded):
        """५ जजको अङ्कबाट उच्च र न्यून हटाएर औसत निकाल्ने र अन्तिम स्कोर दिने"""
        valid_judges = sorted(judges)
        # उच्च र न्यून हटाउने (Middle 3)
        middle_three = valid_judges[1:4]
        avg_presentation = sum(middle_three) / 3 if sum(middle_three) > 0 else 0
        final_score = max(0.00, (tech + avg_presentation) - ded)
        return final_score, avg_presentation

    c_sa, c_mid, c_sb = st.columns([2, 0.1, 2])
    
    # ⬛ Player 1 (Black)
    with c_sa:
        st.markdown("<div style='border:4px solid #1f2937; border-radius:10px; padding:15px; background-color:#f8fafc;'>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align:center; color:#1f2937; margin:0;'>⬛ {p_a_name}</h4>", unsafe_allow_html=True)
        
        t_a = st.number_input("Technical (Max 5.0)", 0.0, 5.0, step=0.01, key=f"{prefix}_t_a")
        
        st.write("Presentation Group B (5 Judges):")
        cols = st.columns(5)
        j_scores_a = []
        for i in range(5):
            val = cols[i].number_input(f"J{i+1}", 0.0, 5.0, step=0.01, key=f"{prefix}_j{i}_a", label_visibility="collapsed")
            j_scores_a.append(val)
        
        d_a = st.number_input("Deduction (扣分)", 0.0, 5.0, step=0.1, key=f"{prefix}_d_a")
        
        f_score_a, avg_p_a = calculate_taolu_score(t_a, j_scores_a, d_a)
        st.markdown(f"<h1 style='text-align:center; color:#1f2937; font-size:60px; margin:0;'>{f_score_a:.2f}</h1>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align:center;'>Group B Avg: {avg_p_a:.2f}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 🟥 Player 2 (Red)
    with c_sb:
        st.markdown("<div style='border:4px solid #dc2626; border-radius:10px; padding:15px; background-color:#fef2f2;'>", unsafe_allow_html=True)
        st.markdown(f"<h4 style='text-align:center; color:#dc2626; margin:0;'>🟥 {p_b_name}</h4>", unsafe_allow_html=True)
        
        t_b = st.number_input("Technical (Max 5.0)", 0.0, 5.0, step=0.01, key=f"{prefix}_t_b")
        
        st.write("Presentation Group B (5 Judges):")
        cols = st.columns(5)
        j_scores_b = []
        for i in range(5):
            val = cols[i].number_input(f"J{i+1}", 0.0, 5.0, step=0.01, key=f"{prefix}_j{i}_b", label_visibility="collapsed")
            j_scores_b.append(val)
            
        d_b = st.number_input("Deduction (扣分)", 0.0, 5.0, step=0.1, key=f"{prefix}_d_b")
        
        f_score_b, avg_p_b = calculate_taolu_score(t_b, j_scores_b, d_b)
        st.markdown(f"<h1 style='text-align:center; color:#dc2626; font-size:60px; margin:0;'>{f_score_b:.2f}</h1>", unsafe_allow_html=True)
        st.caption(f"<p style='text-align:center;'>Group B Avg: {avg_p_b:.2f}</p>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # ==========================================
    # 📡 LIVE TV SYNC (PostgreSQL)
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📡 Broadcast Scores to TV", type="secondary", use_container_width=True):
        conn = db.get_connection()
        cur = conn.cursor()
        # ताओलुको स्कोर '10.00' जस्तो आउने भएकोले यसलाई STRING/VARCHAR को रूपमा पठाउनुपर्छ, 
        # तर हाम्रो live_match को score_a INTEGER छ भने अलिकति समस्या हुन सक्छ।
        # हामीले database.py मा score_a र score_b लाई VARCHAR बनाएको भए उत्तम हुन्थ्यो, 
        # तर अहिलेलाई यसलाई Integer मै Cast गरेर वा छुट्टै तरिकाले पठाउन सक्छौँ।
        # (नोट: यदि एरर आयो भने live_match टेबलको score_a र score_b लाई VARCHAR(50) बनाउनुहोला।)
        try:
            cur.execute("""
                UPDATE live_match 
                SET score_a=%s, score_b=%s, timer='10.00'
            """, (int(f_score_a), int(f_score_b))) # Temporary integer cast
            conn.commit()
            st.toast("✅ TV Display Updated!")
        except Exception as e:
            st.error(f"Database sync error: {e}")
        finally:
            cur.close(); conn.close()

    # ==========================================
    # 🏁 SAVE RESULT (IWUF Tie-Breaker)
    # ==========================================
    st.divider()
    c_res, c_rst = st.columns([3, 1])
    with c_res:
        if st.button("💾 Save Match Result & Confirm", type="primary", use_container_width=True):
            if f_score_a == 0 and f_score_b == 0:
                st.warning("⚠️ कृपया अङ्क प्रविष्ट गर्नुहोस्।")
                return

            win_id = None
            if f_score_a > f_score_b: win_id = bout_info['p1']
            elif f_score_b > f_score_a: win_id = bout_info['p2']
            elif f_score_a == f_score_b:
                # 💡 Tie-Breaker: Higher Group B (Presentation) Average
                if avg_p_a > avg_p_b: win_id = bout_info['p1']
                elif avg_p_b > avg_p_a: win_id = bout_info['p2']
                else:
                    st.warning("⚠️ पूर्ण रूपमा बराबर! रिम्याच वा गोलाप्रथा गर्नुहोस्।")
                    return

            if win_id:
                # 💡 Bracket Update
                st.session_state[f"winner_{evt_code}_{bout_info['id']}"] = win_id
                st.session_state[f"published_{evt_code}_{bout_info['id']}"] = True
                
                # 💡 Final Medal Save (PostgreSQL)
                if round_text == "Final":
                    def ext_ids(s_val):
                        p_match = re.search(r"\[ID:\s*(\d+)\]", s_val)
                        m_match = re.search(r"\[M_ID:\s*(\d+)\]", s_val)
                        return (int(p_match.group(1)) if p_match else None), (int(m_match.group(1)) if m_match else None)
                    
                    loser_id = bout_info['p2'] if win_id == bout_info['p1'] else bout_info['p1']
                    win_pid, win_mid = ext_ids(win_id)
                    lose_pid, lose_mid = ext_ids(loser_id)
                    final_score = f"{max(f_score_a, f_score_b):.2f}"
                    
                    conn = db.get_connection()
                    c = conn.cursor()
                    if win_pid and win_mid:
                        c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 1, 'Gold', %s)", (evt_code, win_mid, win_pid, f'{{"score": "{final_score}"}}'))
                    if lose_pid and lose_mid:
                        c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 2, 'Silver', %s)", (evt_code, lose_mid, lose_pid, f'{{"score": "{min(f_score_a, f_score_b):.2f}"}}'))
                    conn.commit(); c.close(); conn.close()
                    st.toast("🎉 स्वर्ण र रजत पदक डाटाबेसमा सुरक्षित भयो!")

                ma_bracket.sync_progress_to_db(evt_code)
                
                # Clear Live Match
                conn = db.get_connection()
                conn.cursor().execute("DELETE FROM live_match")
                conn.commit(); conn.close()
                
                st.session_state.active_bout_data = None
                st.success("✅ नतिजा सुरक्षित भयो!"); st.rerun()

    with c_rst:
        if st.button("🔄 Reset Match", type="secondary", use_container_width=True):
            keys_to_del = [k for k in st.session_state.keys() if k.startswith(prefix)]
            for k in keys_to_del: del st.session_state[k]
            st.rerun()