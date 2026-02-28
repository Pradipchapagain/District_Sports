import streamlit as st
import pandas as pd
import database as db
from config import render_header

st.set_page_config(page_title="Manual Result Override", page_icon="🛠️", layout="wide")
render_header()

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("🔒 कृपया लगइन गर्नुहोस्।")
    st.stop()

st.title("🛠️ म्यानुअल नतिजा प्रविष्टि (Manual Override)")
st.markdown("इन्टरनेट काटिएको वा लाइभ अपडेट गर्न नभ्याएको अवस्थामा यहाँबाट खेलको नतिजा फोर्स (Force) अपडेट गर्न सकिन्छ।")
st.divider()

# दुईवटा अप्सनका लागि ट्याबहरू
tab_match, tab_medal = st.tabs(["⚔️ १. सिंगल म्याच अपडेट (Bracket Continue)", "🏆 २. सिधै पदक प्रविष्टि (Final Override)"])

# ==========================================
# ⚔️ TAB 1: सिंगल म्याच अपडेट
# ==========================================
with tab_match:
    st.header("⚔️ सिंगल म्याच अपडेट")
    st.info("💡 कुनै एउटा म्याच मात्र छुट्यो भने यहाँबाट विजेता तोक्नुहोस्, त्यसपछि टाइसिट (Bracket) आफैँ अगाडि बढ्नेछ।")
    
    conn = db.get_connection()
    # चल्दै गरेका वा बाँकी रहेका खेलहरूको सूची (तपाईंको 'matches' टेबलअनुसार कोइरी मिलाउनुहोला)
    try:
        # 💡 नोट: यदि 'p1', 'p2' र 'round' कोलम छैनन् भने database अनुसार मिलाउनुपर्ने हुन सक्छ 
        # (जस्तै: comp1_muni_id वा round_name)
        df_matches = pd.read_sql_query("""
            SELECT m.id, e.name as event_name, m.p1, m.p2, m.round 
            FROM matches m 
            JOIN events e ON m.event_code = e.code 
            WHERE m.status != 'Completed'
        """, conn)
    except Exception as e:
        # यदि टेबल वा कोलम मिलेन भने क्र्यास हुनबाट बचाउन
        st.warning(f"ड्यासबोर्ड म्याच लोड गर्न सकिएन: {e}")
        df_matches = pd.DataFrame() 
    finally:
        conn.close()
    
    if not df_matches.empty:
        match_dict = {f"Match #{row['id']} - {row['event_name']} ({row['p1']} VS {row['p2']})": row['id'] for _, row in df_matches.iterrows()}
        sel_match_str = st.selectbox("नतिजा हाल्न बाँकी म्याच छान्नुहोस्:", ["-- छान्नुहोस् --"] + list(match_dict.keys()))
        
        if sel_match_str != "-- छान्नुहोस् --":
            m_id = match_dict[sel_match_str]
            selected_row = df_matches[df_matches['id'] == m_id].iloc[0]
            p1, p2 = selected_row['p1'], selected_row['p2']
            
            with st.form("single_match_override"):
                winner = st.radio("विजेता को भयो?", [p1, p2])
                score = st.text_input("स्कोर / पोइन्ट (Optional)")
                
                if st.form_submit_button("अपडेट गर्नुहोस् (Update Match)", type="primary"):
                    # 💡 सुनिश्चित गर्नुहोस् कि db.override_single_match भित्र पनि %s प्रयोग भएको छ!
                    if db.override_single_match(m_id, winner, score):
                        st.success(f"✅ Match #{m_id} को विजेता '{winner}' सेट गरियो! अब टाइसिट अगाडि बढ्छ।")
                    else:
                        st.error("अपडेट गर्न सकिएन। डाटाबेस टेबल चेक गर्नुहोस्।")
    else:
        st.warning("अहिले नतिजा हाल्न बाँकी कुनै पनि म्याच छैनन् वा टाइसिट बनेको छैन।")

# ==========================================
# 🏆 TAB 2: सिधै पदक प्रविष्टि
# ==========================================
with tab_medal:
    st.header("🏆 सिधै पदक प्रविष्टि (Direct Medal Entry)")
    st.error("⚠️ चेतावनी: यो अप्सन खेल पूर्ण रूपमा सकिएपछि वा टाइसिट नचलाउने निर्णय गरेपछि मात्र प्रयोग गर्नुहोस्। यसले सिधै पदक तालिका (Medal Tally) अपडेट गर्छ।")
    
    conn = db.get_connection()
    df_events = pd.read_sql_query("SELECT code, name, category, type FROM events ORDER BY name", conn)
    
    if not df_events.empty:
        ev_dict = {f"{row['name']} ({row['category']})": (row['code'], row['type']) for _, row in df_events.iterrows()}
        sel_ev = st.selectbox("खेल छान्नुहोस्:", ["-- छान्नुहोस् --"] + list(ev_dict.keys()), key="man_ev")
        
        if sel_ev != "-- छान्नुहोस् --":
            ev_code, ev_type = ev_dict[sel_ev]
            is_team = (ev_type == 'Team')
            
            try:
                # 💡 SQLite को ? लाई PostgreSQL को %s ले रिप्लेस गरियो
                if is_team:
                    df_entities = pd.read_sql_query("SELECT t.id, t.name || ' (' || m.name || ')' as display_name FROM teams t JOIN municipalities m ON t.municipality_id = m.id WHERE t.event_code = %s", conn, params=(ev_code,))
                else:
                    df_entities = pd.read_sql_query("SELECT p.id, p.name || ' (' || m.name || ')' as display_name FROM registrations r JOIN players p ON r.player_id = p.id JOIN municipalities m ON p.municipality_id = m.id WHERE r.event_code = %s", conn, params=(ev_code,))
            except Exception as e:
                st.error(f"Error loading players/teams: {e}")
                df_entities = pd.DataFrame()
            finally:
                conn.close()
            
            if df_entities.empty:
                st.info("यो खेलमा कोही पनि दर्ता भएका छैनन्।")
            else:
                entity_dict = {row['display_name']: row['id'] for _, row in df_entities.iterrows()}
                entity_list = ["-- छान्नुहोस् --"] + list(entity_dict.keys())
                
                with st.form("manual_medal_form"):
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        g_win = st.selectbox("🥇 प्रथम (Gold)", entity_list, key="g_win")
                        g_score = st.text_input("स्कोर/समय", key="g_score")
                    with c2:
                        s_win = st.selectbox("🥈 द्वितीय (Silver)", entity_list, key="s_win")
                        s_score = st.text_input("स्कोर/समय", key="s_score")
                    with c3:
                        b_win = st.selectbox("🥉 तृतीय (Bronze)", entity_list, key="b_win")
                        b_score = st.text_input("स्कोर/समय", key="b_score")
                        
                    if st.form_submit_button("💾 पदक सुरक्षित गर्नुहोस् (Save Medals)", type="primary"):
                        saved = False
                        # 💡 सुनिश्चित गर्नुहोस् कि db.save_manual_result भित्र पनि %s प्रयोग भएको छ!
                        if g_win != "-- छान्नुहोस् --": 
                            db.save_manual_result(ev_code, entity_dict[g_win], is_team, 1, 'Gold', g_score)
                            saved = True
                        if s_win != "-- छान्नुहोस् --": 
                            db.save_manual_result(ev_code, entity_dict[s_win], is_team, 2, 'Silver', s_score)
                            saved = True
                        if b_win != "-- छान्नुहोस् --": 
                            db.save_manual_result(ev_code, entity_dict[b_win], is_team, 3, 'Bronze', b_score)
                            saved = True
                            
                        if saved:
                            st.success("✅ पदकहरू सफलतापूर्वक अपडेट भए! अब लाइभ डिस्प्लेमा देखिनेछ।")
                            st.balloons()