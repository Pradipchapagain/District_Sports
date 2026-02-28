import streamlit as st
import database as db
import utils.ma_bracket as ma_bracket  # 💡 नयाँ थपिएको
from streamlit_autorefresh import st_autorefresh
import psycopg2.extras # 👈 Dictionary को रूपमा डाटा तान्न यो चाहिन्छ

def render_panel(evt_code, current_event, players_df, bout_info):
    bout_id, p1, p2 = bout_info['id'], bout_info['p1'], bout_info['p2']
    st.markdown(f"<h4 style='color:#d32f2f; text-align:center;'>⚡ लाइभ: {bout_id}</h4>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center; font-size:18px; font-weight:bold;'>🔴 {p1.split(' [ID:')[0]} <br>VS<br> 🔵 {p2.split(' [ID:')[0]}</p>", unsafe_allow_html=True)

    # १. PostgreSQL को लागि Cursor र DictCursor को प्रयोग
    conn = db.get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT * FROM live_match WHERE event_code = %s AND bout_id = %s", (evt_code, bout_id))
    live_row = c.fetchone()
    conn.close()

    is_voting_open = False
    votes = [None] * 5
    if live_row:
        is_voting_open = bool(live_row['voting_open'])
        votes = [live_row['j1_vote'], live_row['j2_vote'], live_row['j3_vote'], live_row['j4_vote'], live_row['j5_vote']]

    if not is_voting_open:
        st.info("⏳ खेलाडी प्रदर्शन गर्दैछन्... प्रदर्शन सकिएपछि भोटिङ खुल्ला गर्नुहोस्।")
        if st.button("🚦 भोटिङ खुल्ला गर्नुहोस्", type="primary", use_container_width=True):
            try:
                conn = db.get_connection()
                c = conn.cursor()
                
                # पहिले उक्त bout_id छ कि छैन चेक गर्ने, छैन भने INSERT, छ भने UPDATE
                c.execute("SELECT id FROM live_match WHERE event_code = %s AND bout_id = %s", (evt_code, bout_id))
                if c.fetchone():
                    c.execute("UPDATE live_match SET voting_open = 1 WHERE event_code = %s AND bout_id = %s", (evt_code, bout_id))
                else:
                    c.execute("INSERT INTO live_match (event_code, bout_id, voting_open) VALUES (%s, %s, 1)", (evt_code, bout_id))
                conn.commit()
            except Exception as e: 
                st.error(f"सिस्टम इरर: {e}")
            finally: 
                conn.close()
            st.rerun()
    else:
        st_autorefresh(interval=2000, key=f"operator_refresh_{bout_id}")
        st.success("🟢 भोटिङ खुल्ला छ। जजहरूको भोट प्रतीक्षा गर्दै...")
        
        aka_votes = sum(1 for v in votes if v == 'AKA')
        ao_votes = sum(1 for v in votes if v == 'AO')
        
        for j in range(1, 6):
            c0, c_aka, c_ao = st.columns([1, 2, 2])
            with c0: st.markdown(f"**जज {j}**")
            v = votes[j-1]
            with c_aka:
                if st.button("✅ 🔴 AKA" if v == 'AKA' else "🔴 AKA", key=f"op_btn_aka_{j}", disabled=(v == 'AKA')):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute(f"UPDATE live_match SET j{j}_vote = 'AKA' WHERE event_code=%s AND bout_id=%s", (evt_code, bout_id))
                    conn.commit(); conn.close()
                    st.rerun()
            with c_ao:
                if st.button("✅ 🔵 AO" if v == 'AO' else "🔵 AO", key=f"op_btn_ao_{j}", disabled=(v == 'AO')):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute(f"UPDATE live_match SET j{j}_vote = 'AO' WHERE event_code=%s AND bout_id=%s", (evt_code, bout_id))
                    conn.commit(); conn.close()
                    st.rerun()

        st.markdown(f"<h2 style='text-align:center;'>📊 🔴 {aka_votes} - 🔵 {ao_votes}</h2>", unsafe_allow_html=True)
        
        if (aka_votes + ao_votes) == 5:
            st.warning("⚠️ ५ वटै भोट प्राप्त भयो। नतिजा पक्का गर्नुहोस्:")
            winner = "AKA" if aka_votes > ao_votes else "AO"
            winning_player = bout_info['p1'] if winner == "AKA" else bout_info['p2']
            
            c_conf, c_reset = st.columns(2)
            with c_conf:
                if st.button("✅ पक्का (Confirm)", type="primary", use_container_width=True):
                    import utils.live_state as ls
                    ls.trigger_kata_result(current_event['name'], bout_id, p1.split(' [ID:')[0], p2.split(' [ID:')[0], votes, winner)
                    
                    st.session_state[f"winner_{evt_code}_{bout_id}"] = winning_player
                    st.session_state[f"published_{evt_code}_{bout_id}"] = True
                    st.session_state[f"votes_{evt_code}_{bout_id}"] = votes  
                    st.session_state.active_bout_data = None 
                    
                    # 💡 नयाँ: डाटाबेसमा पर्मानेन्ट सेभ गर्ने
                    ma_bracket.sync_progress_to_db(evt_code)
                    
                    conn = db.get_connection()
                    c = conn.cursor()
                    # भोटिङ पक्का भएपछि सो बाउटको भोटिङ बन्द गर्ने
                    c.execute("UPDATE live_match SET voting_open = 0 WHERE event_code=%s AND bout_id=%s", (evt_code, bout_id))
                    conn.commit(); conn.close()
                    st.toast("नतिजा सुरक्षित भयो!"); st.rerun()
            with c_reset:
                if st.button("🔄 भोट रिसेट गर्नुहोस्", type="secondary", use_container_width=True):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("UPDATE live_match SET j1_vote=NULL, j2_vote=NULL, j3_vote=NULL, j4_vote=NULL, j5_vote=NULL WHERE event_code=%s AND bout_id=%s", (evt_code, bout_id))
                    conn.commit(); conn.close()
                    st.rerun()