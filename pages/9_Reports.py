import streamlit as st
import pandas as pd
import database as db
import plotly.express as px
from config import render_header, render_footer
from utils.document_generator import generate_certificate_pdf

# ==========================================
# ⚙️ पेज कन्फिगरेसन र सेक्युरिटी
# ==========================================
st.set_page_config(page_title="नतिजा विश्लेषण (Reports)", page_icon="📊", layout="wide")

# ------------------------------------------
# हेडर देखाउने
# ------------------------------------------
render_header() # 👈 यो लाइनले सुन्दर ब्यानर बनाउँछ
# ------------------------------------------

# --- PUBLIC VIEW (No Login Required) ---
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.info("👁️ तपाईं 'पब्लिक भ्यु (Public View)' मोडमा हुनुहुन्छ। यहाँबाट नतिजा र पदक तालिका मात्र हेर्न मिल्छ।")

st.title("📊 नतिजा विश्लेषण र प्रतिवेदन (Reports)")

# ==========================================
# 🔄 ट्याब संरचना
# ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏆 पदक तालिका (Medal Tally)", 
    "🥇 इभेन्ट अनुसार (Event Results)", 
    "👤 खेलाडी/टिम खोज (Search)", 
    "📋 सारांश (Summary)",
    "📜 प्रमाणपत्र (Certificates)"
])

# ==========================================
# TAB 1: पदक तालिका (MEDAL TALLY - SHIELD STANDINGS)
# ==========================================
with tab1:
    st.header("🏛️ पालिका स्तरीय पदक तालिका (Shield Standings)")
    st.caption("राष्ट्रपति रनिङ शिल्डको विजेता पालिका निर्धारण गर्नको लागि।")
    
    conn = db.get_connection()
    
    # --- सेटिङ खण्ड ---
    with st.expander("⚙️ सेटिङ (Points & Filters)", expanded=False):
        col_set1, col_set2 = st.columns(2)
        
        with col_set1:
            avail_cats_df = pd.read_sql("SELECT DISTINCT category FROM events", conn)
            available_categories = avail_cats_df['category'].dropna().unique().tolist() if not avail_cats_df.empty else []
            
            selected_categories = st.multiselect(
                "शिल्ड गणनाका लागि समावेश गर्ने विधाहरू:",
                options=available_categories,
                default=available_categories,
                help="केही अवस्थामा मार्सल आर्ट्सको पदक गणना गरिँदैन। यहाँबाट हटाउन सकिन्छ।"
            )
        
        with col_set2:
            point_sys = st.radio("पोइन्ट गणना विधि:", ["Standard (G=5, S=3, B=1)", "Olympic (Count only)"], horizontal=True)
            g_pt, s_pt, b_pt = (5, 3, 1) if "Standard" in point_sys else (10000, 100, 1)

    # --- डाटा तान्ने (PostgreSQL Logic) ---
    if not selected_categories:
        st.warning("कृपया कम्तिमा एउटा विधा (Category) छान्नुहोस्।")
    else:
        # 💡 PostgreSQL को लागि %s प्रयोग गरिएको
        placeholders = ', '.join(['%s'] * len(selected_categories))
        
        query_tally = f"""
            SELECT 
                m.name as "Municipality",
                SUM(CASE WHEN r.medal = 'Gold' THEN 1 ELSE 0 END) as "Gold",
                SUM(CASE WHEN r.medal = 'Silver' THEN 1 ELSE 0 END) as "Silver",
                SUM(CASE WHEN r.medal = 'Bronze' THEN 1 ELSE 0 END) as "Bronze"
            FROM results r
            JOIN events e ON r.event_code = e.code
            LEFT JOIN players p ON r.player_id = p.id AND e.type = 'Individual'
            LEFT JOIN teams t ON r.team_id = t.id AND e.type = 'Team'
            JOIN municipalities m ON m.id = COALESCE(p.municipality_id, t.municipality_id)
            WHERE r.medal IN ('Gold', 'Silver', 'Bronze')
            AND e.category IN ({placeholders})
            GROUP BY m.id, m.name
        """
        
        try:
            df_tally = pd.read_sql_query(query_tally, conn, params=tuple(selected_categories))
            
            if df_tally.empty:
                st.info("छानिएको विधा अनुसार कुनै पदक नतिजा भेटिएन।")
            else:
                df_tally['Total Medals'] = df_tally['Gold'] + df_tally['Silver'] + df_tally['Bronze']
                df_tally['Points'] = (df_tally['Gold'] * g_pt) + (df_tally['Silver'] * s_pt) + (df_tally['Bronze'] * b_pt)
                
                # Ranking Logic
                df_tally = df_tally.sort_values(by=['Points', 'Gold', 'Silver'], ascending=False).reset_index(drop=True)
                df_tally.index += 1
                
                winner = df_tally.iloc[0]
                st.success(f"🏆 हालको अग्रता (Leading): **{winner['Municipality']}** (स्वर्ण: {winner['Gold']} | पोइन्ट: {winner['Points']})")
                
                st.dataframe(
                    df_tally, 
                    use_container_width=True,
                    column_config={
                        "Municipality": "पालिका (Municipality)",
                        "Gold": "🥇 Gold",
                        "Silver": "🥈 Silver",
                        "Bronze": "🥉 Bronze",
                        "Total Medals": "Total",
                        "Points": st.column_config.ProgressColumn("Points", format="%d", min_value=0, max_value=int(df_tally['Points'].max()))
                    }
                )
                
                # Chart
                fig = px.bar(df_tally, x='Municipality', y=['Gold', 'Silver', 'Bronze'], 
                             title="Medal Distribution by Municipality",
                             color_discrete_map={'Gold': '#FFD700', 'Silver': '#C0C0C0', 'Bronze': '#CD7F32'})
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"Error loading medal tally: {e}")

    conn.close()

# ==========================================
# TAB 2: इभेन्ट अनुसार (EVENT RESULTS)
# ==========================================
with tab2:
    st.header("🥇 इभेन्ट अनुसार नतिजा (Event-wise Winners)")
    
    conn = db.get_connection()
    q_event = """
        SELECT 
            e.category as "Category",
            e.sub_category as "SubCat",
            e.gender as "Gender",
            e.name as "EventName",
            r.medal as "Medal",
            COALESCE(p.name, t.name) as "WinnerName",
            m.name as "MunicipalityName"
        FROM results r
        JOIN events e ON r.event_code = e.code
        LEFT JOIN players p ON r.player_id = p.id AND e.type = 'Individual'
        LEFT JOIN teams t ON r.team_id = t.id AND e.type = 'Team'
        JOIN municipalities m ON m.id = COALESCE(p.municipality_id, t.municipality_id)
        WHERE r.medal IN ('Gold', 'Silver', 'Bronze')
        ORDER BY e.category, e.sub_category, e.name
    """
    raw_df = pd.read_sql_query(q_event, conn)
    conn.close()

    if raw_df.empty:
        st.info("कुनै पनि इभेन्टको नतिजा प्रकाशित भएको छैन।")
    else:
        pivot_data = []
        grouped = raw_df.groupby(['Category', 'SubCat', 'Gender', 'EventName'])
        
        for (cat, sub, gen, evt), group_df in grouped:
            golds = ", ".join(group_df[group_df['Medal']=='Gold']['MunicipalityName'].unique())
            silvers = ", ".join(group_df[group_df['Medal']=='Silver']['MunicipalityName'].unique())
            bronzes = ", ".join(group_df[group_df['Medal']=='Bronze']['MunicipalityName'].unique())
            
            pivot_data.append({
                "Category": cat, "Sub Category": sub, "Gender": gen, "Event": evt,
                "🥇 Gold": golds, "🥈 Silver": silvers, "🥉 Bronze": bronzes
            })
        
        df_event_view = pd.DataFrame(pivot_data)
        
        def highlight_cat(row):
            c = row['Category']
            cols = {'Athletics': 'background-color: #e8f8f5', 'Team Game': 'background-color: #fef9e7', 'Martial Arts': 'background-color: #f4ecf7'}
            return [cols.get(c, '')] * len(row)

        st.dataframe(df_event_view.style.apply(highlight_cat, axis=1), use_container_width=True, hide_index=True)

# ==========================================
# TAB 3: खेलाडी/टिम खोज (SEARCH)
# ==========================================
with tab3:
    st.header("👤 खेलाडी वा टिमको नतिजा खोज्नुहोस्")
    search_txt = st.text_input("खेलाडीको नाम, विद्यालय वा IEMIS ID टाइप गर्नुहोस्:", placeholder="उदा: Ram, 12345, Bhanubhakta")
    
    if search_txt:
        conn = db.get_connection()
        q_search = f"""
            SELECT p.id as PlayerID, p.name as PlayerName, p.school_name as School, p.iemis_id as EMIS, m.name as Municipality
            FROM players p
            JOIN municipalities m ON p.municipality_id = m.id
            WHERE p.name ILIKE '%%{search_txt}%%' OR p.school_name ILIKE '%%{search_txt}%%' OR p.iemis_id ILIKE '%%{search_txt}%%'
        """
        search_res = pd.read_sql_query(q_search, conn)
        
        if search_res.empty:
            st.error("कुनै विवरण भेटिएन।")
        else:
            st.dataframe(search_res, use_container_width=True, hide_index=True)
            selected_pid = search_res.iloc[0]['PlayerID'] 
            
            st.markdown(f"##### 🏅 {search_res.iloc[0]['PlayerName']} को नतिजा विवरण:")
            # 💡 r.team_id को सट्टा r.player_id र ? को सट्टा %s
            res_q = """
                SELECT e.name as Event, e.category, r.position as rank, r.score as Score, r.medal
                FROM results r
                JOIN events e ON r.event_code = e.code
                WHERE r.player_id = %s AND e.type = 'Individual'
            """
            perf_df = pd.read_sql_query(res_q, conn, params=(int(selected_pid),))
            
            if perf_df.empty: st.info("यो खेलाडीले अहिलेसम्म कुनै पदक जितेको छैन वा नतिजा आएको छैन।")
            else: st.table(perf_df)
            
        conn.close()

# ==========================================
# TAB 4: सारांश (EXECUTIVE SUMMARY)
# ==========================================
with tab4:
    st.header("📋 प्रतियोगिता सारांश (Summary Stats)")
    
    conn = db.get_connection()
    n_players = pd.read_sql("SELECT COUNT(*) FROM players", conn).iloc[0,0]
    n_muns = pd.read_sql("SELECT COUNT(*) FROM municipalities", conn).iloc[0,0]
    n_regs = pd.read_sql("SELECT COUNT(*) FROM registrations", conn).iloc[0,0]
    n_results = pd.read_sql("SELECT COUNT(*) FROM results WHERE medal IN ('Gold', 'Silver', 'Bronze')", conn).iloc[0,0]
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("कुल खेलाडी (Players)", n_players)
    col2.metric("सहभागी पालिका", n_muns)
    col3.metric("कुल इभेन्ट दर्ता", n_regs)
    col4.metric("वितरण भएका पदक", n_results)
    
    st.divider()
    st.subheader("🌟 उत्कृष्ट खेलाडी (Top Performers - MVP)")
    st.caption("धेरै स्वर्ण पदक जित्ने व्यक्तिगत खेलाडीहरू:")
    
    mvp_q = """
        SELECT p.name as "Player Name", p.school_name as "School", m.name as "Municipality",
               SUM(CASE WHEN r.medal='Gold' THEN 1 ELSE 0 END) as "Golds",
               COUNT(r.id) as "Total Medals"
        FROM results r
        JOIN players p ON r.player_id = p.id
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE r.medal IN ('Gold', 'Silver', 'Bronze') AND e.type = 'Individual'
        GROUP BY p.id, p.name, p.school_name, m.name
        HAVING SUM(CASE WHEN r.medal='Gold' THEN 1 ELSE 0 END) > 0
        ORDER BY "Golds" DESC, "Total Medals" DESC
        LIMIT 5
    """
    mvp_df = pd.read_sql_query(mvp_q, conn)
    
    if not mvp_df.empty:
        st.table(mvp_df)
    else:
        st.info("अहिलेसम्म कुनै नतिजा आएको छैन।")
        
    conn.close()

# ==========================================
# TAB 5: प्रमाणपत्र (CERTIFICATE)
# ==========================================
with tab5:
    # 💡 Indentation फिक्स गरियो!
    st.header("📜 विजेता प्रमाणपत्र (Print Certificates)")

    conn = db.get_connection()
    ev_df = pd.read_sql_query("SELECT code, name, gender FROM events ORDER BY name", conn)
    conn.close()

    if not ev_df.empty:
        ev_dict = {f"{row['name']} ({row['gender']})": row['code'] for _, row in ev_df.iterrows()}
        sel_ev = st.selectbox("प्रमाणपत्र छाप्नको लागि खेल छान्नुहोस्:", ["-- छान्नुहोस् --"] + list(ev_dict.keys()))

        if sel_ev != "-- छान्नुहोस् --":
            ev_code = ev_dict[sel_ev]
            
            conn = db.get_connection()
            # 💡 %s प्रयोग गरियो र COALESCE थपियो
            query = """
                SELECT COALESCE(p.name, t.name) as name, p.school_name, r.position as rank
                FROM results r
                LEFT JOIN players p ON r.player_id = p.id
                LEFT JOIN teams t ON r.team_id = t.id
                WHERE r.event_code = %s AND r.position IN (1, 2, 3)
                ORDER BY r.position
            """
            winners_df = pd.read_sql_query(query, conn, params=(ev_code,))
            conn.close()
            
            if winners_df.empty:
                st.warning("यो खेलको नतिजा आइसकेको छैन वा विजेताहरू तोकिएका छैनन्।")
            else:
                st.success(f"✅ जम्मा {len(winners_df)} जना विजेताहरू भेटिए!")
                st.dataframe(winners_df, use_container_width=True)
                
                if st.button("🚀 PDF प्रमाणपत्र डाउनलोड गर्नुहोस्", type="primary"):
                    try:
                        pdf_buffer = generate_certificate_pdf(sel_ev, winners_df)
                        
                        st.download_button(
                            label="📥 यहाँ क्लिक गरेर PDF डाउनलोड गर्नुहोस्",
                            data=pdf_buffer.getvalue(),
                            file_name=f"Certificates_{ev_code}.pdf",
                            mime="application/pdf"
                        )
                        st.balloons()
                    except Exception as e:
                        st.error(f"प्रमाणपत्र जेनेरेट गर्दा समस्या आयो: {e}")

# ------------------------------------------
# पेजको सबैभन्दा तल फुटर देखाउने
# ------------------------------------------
render_footer()