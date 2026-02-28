import streamlit as st
import pandas as pd
import database as db
import utils.ma_bracket as ma_bracket
from datetime import datetime
import re
import psycopg2.extras # 💡 थपिएको

def render_panel(evt_code, current_event, players_df, bout_info):
    """WT 2026 Rules - Taekwondo Poomsae Operator Panel with Direct DB Sync"""
    
    round_text = bout_info.get('r_name', '')
    bout_id_text = bout_info.get('id', '')
    
    st.markdown(f"<h3 style='text-align:center; color:#1E88E5; margin:0;'>🧘 Poomsae (WT 2026) - {round_text} {bout_id_text}</h3>", unsafe_allow_html=True)
    st.caption("<p style='text-align:center; font-weight:bold;'>Technical (기술) 4.0 + Presentation (표현) 6.0 - Gam-jeom (감점) = 10.0</p>", unsafe_allow_html=True)
    
    def get_full_name(p_str):
        return str(p_str).split(" [ID:")[0] if p_str else "Unknown"
        
    p_a_name = get_full_name(bout_info['p1']) # Chung (Blue)
    p_b_name = get_full_name(bout_info['p2']) # Hong (Red)

    # ==========================================
    # ⚙️ STATE INITIALIZATION
    # ==========================================
    prefix = f"poomsae_{evt_code}_{bout_info['id']}"
    
    if f"{prefix}_init" not in st.session_state:
        st.session_state[f"{prefix}_tech_a"] = 0.00
        st.session_state[f"{prefix}_pres_a"] = 0.00
        st.session_state[f"{prefix}_ded_a"] = 0.00 # Gam-jeom (Deduction)
        
        st.session_state[f"{prefix}_tech_b"] = 0.00
        st.session_state[f"{prefix}_pres_b"] = 0.00
        st.session_state[f"{prefix}_ded_b"] = 0.00 # Gam-jeom (Deduction)
        
        st.session_state[f"{prefix}_init"] = True

        # 💡 पहिलो पटक प्यानल खुल्दा डाटाबेसमा म्याच पठाउने
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM live_match") 
        c.execute("""
            INSERT INTO live_match (event_code, bout_id, event_name, round_name, player1, player2, score_a, score_b)
            VALUES (%s, %s, %s, %s, %s, %s, '0.00', '0.00')
        """, (evt_code, bout_id_text, current_event['name'], f"Poomsae - {round_text}", p_a_name, p_b_name))
        conn.commit()
        c.close(); conn.close()

    # ==========================================
    # 📡 LIVE TV SYNC (PostgreSQL)
    # ==========================================
    def sync_live_display(total_a, total_b):
        conn = db.get_connection()
        cur = conn.cursor()
        try:
            # 💡 score_a र score_b लाई STRING को रूपमा पठाउँदैछौँ
            cur.execute("""
                UPDATE live_match 
                SET score_a=%s, score_b=%s, timer='10.00'
            """, (f"{total_a:.2f}", f"{total_b:.2f}"))
            conn.commit()
            st.toast("✅ Scores updated on Live TV!")
        except Exception as e:
            st.error(f"Database sync error: {e}")
        finally:
            cur.close(); conn.close()

    # ==========================================
    # 🎨 OPERATOR SCOREBOARD & INPUTS
    # ==========================================
    st.markdown("""
    <style>
        .score-input input { text-align: center; font-size: 20px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

    c_sa, c_mid, c_sb = st.columns([2, 0.2, 2])
    
    # 🔵 CHUNG (청 - Blue)
    with c_sa:
        st.markdown(f"""
        <div style='border:4px solid #2563eb; border-radius:10px; padding:15px; background-color:#eff6ff;'>
            <h4 style='text-align:center; color:#2563eb; margin:5px 0;'>🔵 CHUNG (청)</h4>
            <div style='font-size:18px; text-align:center; font-weight:bold; color:#1d4ed8; margin-bottom:15px;'>{p_a_name}</div>
        """, unsafe_allow_html=True)
        
        tech_a = st.number_input("Technical (기술 점수) - Max 4.0", min_value=0.00, max_value=4.00, step=0.10, format="%.2f", key=f"{prefix}_tech_a")
        pres_a = st.number_input("Presentation (표현 점수) - Max 6.0", min_value=0.00, max_value=6.00, step=0.10, format="%.2f", key=f"{prefix}_pres_a")
        ded_a = st.number_input("Deduction (감점) - 0.1 / 0.3 / 0.6", min_value=0.00, max_value=10.00, step=0.10, format="%.2f", key=f"{prefix}_ded_a")
        
        total_a = max(0.00, (tech_a + pres_a) - ded_a)
        st.markdown(f"<h1 style='text-align:center; color:#2563eb; font-size:70px; margin-top:10px; line-height:1;'>{total_a:.2f}</h1>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # 🔴 HONG (홍 - Red)
    with c_sb:
        st.markdown(f"""
        <div style='border:4px solid #dc2626; border-radius:10px; padding:15px; background-color:#fef2f2;'>
            <h4 style='text-align:center; color:#dc2626; margin:5px 0;'>🔴 HONG (홍)</h4>
            <div style='font-size:18px; text-align:center; font-weight:bold; color:#b91c1c; margin-bottom:15px;'>{p_b_name}</div>
        """, unsafe_allow_html=True)
        
        tech_b = st.number_input("Technical (기술 점수) - Max 4.0", min_value=0.00, max_value=4.00, step=0.10, format="%.2f", key=f"{prefix}_tech_b")
        pres_b = st.number_input("Presentation (표현 점수) - Max 6.0", min_value=0.00, max_value=6.00, step=0.10, format="%.2f", key=f"{prefix}_pres_b")
        ded_b = st.number_input("Deduction (감점) - 0.1 / 0.3 / 0.6", min_value=0.00, max_value=10.00, step=0.10, format="%.2f", key=f"{prefix}_ded_b")
        
        total_b = max(0.00, (tech_b + pres_b) - ded_b)
        st.markdown(f"<h1 style='text-align:center; color:#dc2626; font-size:70px; margin-top:10px; line-height:1;'>{total_b:.2f}</h1>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Broadcast Button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📡 Broadcast Scores to TV", type="secondary", use_container_width=True):
        sync_live_display(total_a, total_b)

    # ==========================================
    # 🏁 SAVE RESULT (WT 2026 Tie-Breaker Logic)
    # ==========================================
    st.divider()
    
    c_res, c_rst = st.columns([3, 1])
    with c_res:
        if st.button("💾 Save Match Result & Confirm", type="primary", use_container_width=True):
            win_id = None
            
            # 💡 WT 2026 Winner Logic (Tie-Breaker: Presentation Score)
            if total_a > total_b:
                win_id = bout_info['p1']
            elif total_b > total_a:
                win_id = bout_info['p2']
            elif total_a == total_b and total_a > 0:
                # Tie Breaker 1: Higher Presentation Score
                if pres_a > pres_b:
                    win_id = bout_info['p1']
                    st.toast("Tie broken by Higher Presentation Score! (Chung)")
                elif pres_b > pres_a:
                    win_id = bout_info['p2']
                    st.toast("Tie broken by Higher Presentation Score! (Hong)")
                else:
                    st.warning("⚠️ अङ्क र Presentation दुवै बराबर छ। कृपया 'Deduction' घटाएर वा म्यानुअल रूपमा टाई-ब्रेकर मिलाउनुहोस्।")
                    return
            else:
                st.warning("⚠️ कृपया अङ्क प्रविष्ट गर्नुहोस्।")
                return

            if win_id:
                winner_name = get_full_name(win_id)
                
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
                    final_score = f"{max(total_a, total_b):.2f}"
                    
                    conn = db.get_connection()
                    c = conn.cursor()
                    if win_pid and win_mid:
                        c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 1, 'Gold', %s)", (evt_code, win_mid, win_pid, f'{{"score": "{final_score}"}}'))
                    if lose_pid and lose_mid:
                        c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) VALUES (%s, %s, %s, 2, 'Silver', %s)", (evt_code, lose_mid, lose_pid, f'{{"score": "{min(total_a, total_b):.2f}"}}'))
                    conn.commit(); c.close(); conn.close()
                    st.toast("🎉 स्वर्ण र रजत पदक डाटाबेसमा सुरक्षित भयो!")

                ma_bracket.sync_progress_to_db(evt_code)
                
                # Clear Live Match
                conn = db.get_connection()
                conn.cursor().execute("DELETE FROM live_match")
                conn.commit(); conn.close()
                
                st.session_state.active_bout_data = None
                st.success(f"✅ Result Saved! {winner_name} Winner.")
                st.rerun()

    with c_rst:
        if st.button("🔄 Reset Match", type="secondary", use_container_width=True):
            keys_to_delete = [k for k in st.session_state.keys() if k.startswith(prefix)]
            for k in keys_to_delete: del st.session_state[k]
            st.rerun()