# pages\0_Dashboard.py
import streamlit as st
import pandas as pd
import altair as alt
import database as db
import utils.live_state as ls
from config import CONFIG, render_header, render_footer

# ==========================================
# 🔐 १. पेज सेटिङ र सुरक्षा
# ==========================================
st.set_page_config(page_title="ड्यासबोर्ड | Dashboard", page_icon="📊", layout="wide", initial_sidebar_state="expanded")

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.warning("कृपया पहिले लगइन गर्नुहोस्।")
    st.stop()

# ==========================================
# 🎨 २. कस्टम CSS (मेट्रिक्स र कार्डका लागि)
# ==========================================
st.markdown("""
<style>
    .dash-card { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); border: 1px solid #e2e8f0; height: 100%; }
    .dash-title { color: #64748b; font-size: 15px; font-weight: 600; text-transform: uppercase; margin-bottom: 10px; }
    .dash-value { color: #0f172a; font-size: 36px; font-weight: 800; line-height: 1.2; }
    .icon-box { display: inline-flex; align-items: center; justify-content: center; width: 45px; height: 45px; border-radius: 10px; font-size: 22px; margin-right: 15px; }
    
    .bg-blue { background: #eff6ff; color: #3b82f6; }
    .bg-green { background: #f0fdf4; color: #22c55e; }
    .bg-pink { background: #fdf2f8; color: #ec4899; }
    .bg-orange { background: #fffbeb; color: #f59e0b; }
    
    .log-row { padding: 10px; border-bottom: 1px solid #f1f5f9; font-size: 14px; display: flex; align-items: center; gap: 10px; }
    .log-row:last-child { border-bottom: none; }
    .log-time { color: #94a3b8; font-size: 12px; min-width: 60px; text-align: right; }
    
    /* Responsive Text */
    @media (max-width: 768px) {
        .dash-value { font-size: 28px; }
    }
</style>
""", unsafe_allow_html=True)

render_header()


# 💡 नयाँ थपिएको: कुकी कन्ट्रोलर तान्ने
from streamlit_cookies_controller import CookieController
controller = CookieController()

# --- Welcome Bar ---
c_wel, c_btn = st.columns([4, 1])
with c_wel:
    role_color = "#1E88E5" if st.session_state.user_role == 'admin' else "#2E7D32"
    role_text = "प्रणाली प्रशासक (Admin)" if st.session_state.user_role == 'admin' else "पालिका प्रयोगकर्ता"
    st.markdown(f"<h3 style='margin:0;'>👋 स्वागत छ, <span style='color:{role_color};'>{st.session_state.username.upper()}</span> ({role_text})</h3>", unsafe_allow_html=True)
    st.write(f"Current Mode: {db.APP_MODE}")

with c_btn:
    if st.button("🚪 सुरक्षित लगआउट", use_container_width=True):
        # १. सेसन क्लिन गर्ने
        st.session_state.clear()
        
        # २. ब्राउजरबाट कुकी मेटाउने (अटो-लगइन रोक्न)
        controller.remove('auth_user')
        
        # ३. होम पेजमा फर्काउने (st.rerun() को सट्टा st.switch_page())
        #st.switch_page("Home.py")
        st.rerun()

st.markdown("<hr style='margin: 15px 0 30px 0;'>", unsafe_allow_html=True)

# ==========================================
# 📡 ३. डाटा प्रोसेसिङ (Cached & Parameterized)
# ==========================================
#@st.cache_data(ttl=60)
def fetch_dashboard_data(role, muni_id):
    conn = db.get_connection()
    data = {'num_mun': 0, 'num_events': 0, 'gender': pd.DataFrame(), 'sports': pd.DataFrame(), 'recent': pd.DataFrame(), 'tally': pd.DataFrame()}
    try:
        data['num_mun'] = pd.read_sql_query("SELECT COUNT(*) FROM municipalities", conn).iloc[0,0]
        data['num_events'] = pd.read_sql_query("SELECT COUNT(*) FROM events", conn).iloc[0,0]
        
        if role == 'admin':
            data['gender'] = pd.read_sql_query("SELECT gender, COUNT(*) as c FROM players GROUP BY gender", conn)
            data['sports'] = pd.read_sql_query("SELECT e.category, COUNT(r.id) as count FROM events e LEFT JOIN registrations r ON e.code = r.event_code GROUP BY e.category", conn)
            data['recent'] = pd.read_sql_query("SELECT p.name, m.name as muni, p.gender FROM players p JOIN municipalities m ON p.municipality_id = m.id ORDER BY p.id DESC LIMIT 5", conn)
            
            # 💡 समाधान: PostgreSQL को लागि कोलम Alias मा Double Quotes (") प्रयोग गरिएको
            data['tally'] = pd.read_sql_query("""
                SELECT m.name as "पालिका", 
                SUM(CASE WHEN r.medal='Gold' THEN 1 ELSE 0 END) as "स्वर्ण",
                SUM(CASE WHEN r.medal='Silver' THEN 1 ELSE 0 END) as "रजत",
                SUM(CASE WHEN r.medal='Bronze' THEN 1 ELSE 0 END) as "कास्य",
                COUNT(*) as "कुल"
                FROM results r JOIN municipalities m ON r.municipality_id = m.id 
                WHERE r.medal IN ('Gold', 'Silver', 'Bronze')
                GROUP BY m.name 
                ORDER BY "स्वर्ण" DESC, "रजत" DESC, "कास्य" DESC LIMIT 5
            """, conn)
        else:
            data['gender'] = pd.read_sql_query("SELECT gender, COUNT(*) as c FROM players WHERE municipality_id = %s GROUP BY gender", conn, params=(muni_id,))
            data['sports'] = pd.read_sql_query("SELECT e.category, COUNT(r.id) as count FROM events e JOIN registrations r ON e.code = r.event_code WHERE r.municipality_id = %s GROUP BY e.category", conn, params=(muni_id,))
            data['recent'] = pd.read_sql_query("SELECT name, 'तपाईंको पालिका' as muni, gender FROM players WHERE municipality_id = %s ORDER BY id DESC LIMIT 5", conn, params=(muni_id,))
            
            # 💡 समाधान: यहाँ पनि Double Quotes (")
            data['tally'] = pd.read_sql_query("""
                SELECT e.name as "विधा", r.medal as "पदक" 
                FROM results r JOIN events e ON r.event_code = e.code
                WHERE r.municipality_id = %s AND r.medal IN ('Gold', 'Silver', 'Bronze')
                ORDER BY r.id DESC LIMIT 5
                
                                              
            """, conn, params=(muni_id,))
            
    except Exception as e:
        st.error(f"डाटा तान्दा समस्या: {e}")
    finally:
        conn.close()
    return data
# क्यास गरिएको डाटा तान्ने
role = st.session_state.user_role
muni_id = st.session_state.get('municipality_id', 0)
dash_data = fetch_dashboard_data(role, muni_id)

df_gender = dash_data['gender']
g_dict = dict(zip(df_gender['gender'], df_gender['c'])) if not df_gender.empty else {}
# 💡 'Male' वा 'Boys' जे भए पनि गन्ने
m_count = g_dict.get('Male', 0) + g_dict.get('Boys', 0) + g_dict.get('Boy', 0)
# 💡 'Female' वा 'Girls' जे भए पनि गन्ने
f_count = g_dict.get('Female', 0) + g_dict.get('Girls', 0) + g_dict.get('Girl', 0)
total_players = m_count + f_count

# लाइभ म्याच (क्यास नगर्ने, live_state बाट सिधै तान्ने)
active_matches = ls.get_all_active_matches() 

# ==========================================
# 📈 ४. मुख्य मेट्रिक्स (Top KPI Cards)
# ==========================================
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f'<div class="dash-card"><div class="dash-title"><span class="icon-box bg-blue">👥</span> कुल खेलाडी दर्ता</div><div class="dash-value">{total_players}</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="dash-card"><div class="dash-title"><span class="icon-box bg-green">👨</span> पुरुष खेलाडी</div><div class="dash-value">{m_count}</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="dash-card"><div class="dash-title"><span class="icon-box bg-pink">👩</span> महिला खेलाडी</div><div class="dash-value">{f_count}</div></div>', unsafe_allow_html=True)
with m4:
    if role == 'admin':
        st.markdown(f'<div class="dash-card"><div class="dash-title"><span class="icon-box bg-orange">🏛️</span> जम्मा पालिका</div><div class="dash-value">{dash_data["num_mun"]}</div></div>', unsafe_allow_html=True)
    else:
        quota = CONFIG['MAX_PLAYERS_PER_PALIKA']
        pct = min(total_players / quota, 1.0)
        color = "#ef4444" if pct >= 1 else "#f59e0b"
        st.markdown(f"""
        <div class="dash-card">
            <div class="dash-title"><span class="icon-box bg-orange">🎯</span> दर्ता कोटा प्रगति</div>
            <div class="dash-value" style="color:{color};">{total_players} <span style="font-size:20px; color:#94a3b8;">/ {quota}</span></div>
            <div style="background:#e2e8f0; height:8px; border-radius:5px; margin-top:10px; overflow:hidden;">
                <div style="background:{color}; width:{pct*100}%; height:100%; transition: width 0.5s;"></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📊 ५. भिजुअल चार्ट र विश्लेषण
# ==========================================
c_chart1, c_chart2 = st.columns(2)

with c_chart1:
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.subheader("🎯 खेल विधा अनुसार दर्ता")
    df_sports = dash_data['sports']
    if not df_sports.empty and df_sports['count'].sum() > 0:
        chart = alt.Chart(df_sports).mark_arc(innerRadius=60, cornerRadius=5).encode(
            theta=alt.Theta(field="count", type="quantitative"),
            color=alt.Color(field="category", type="nominal", legend=alt.Legend(title="विधा")),
            tooltip=['category', 'count']
        ).properties(height=300).interactive()
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("डेटा उपलब्ध छैन।")
    st.markdown('</div>', unsafe_allow_html=True)

with c_chart2:
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    if role == 'admin':
        st.subheader("🥇 शीर्ष ५ पदक तालिका (Live)")
        df_t = dash_data['tally']
        if not df_t.empty and df_t['कुल'].sum() > 0:
            st.dataframe(df_t.style.highlight_max(axis=0, subset=['स्वर्ण'], color='#fef08a'), use_container_width=True, hide_index=True)
        else:
            st.info("कुनै पनि नतिजा अपडेट भएको छैन।")
    else:
        st.subheader("🏅 तपाईंको पालिकाको नतिजा")
        if not dash_data['tally'].empty:
            st.dataframe(dash_data['tally'], use_container_width=True, hide_index=True)
        else:
            st.info("तपाईंको पालिकाले हालसम्म कुनै पदक जितेको छैन।")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# 📝 ६. लग्स र प्रत्यक्ष खेल (Logs & Live Matches)
# ==========================================
c_log, c_live = st.columns([1, 1.2])

with c_log:
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.subheader("🕒 भर्खरै दर्ता भएका खेलाडीहरू")
    df_rec = dash_data['recent']
    if not df_rec.empty:
        for _, row in df_rec.iterrows():
            icon = "👦" if row['gender'] == 'Boy' else "👧"
            st.markdown(f"""
            <div class="log-row">
                <div style="font-size:20px;">{icon}</div>
                <div style="flex-grow:1;"><b>{row['name']}</b><br><span style="color:#64748b; font-size:12px;">{row['muni']}</span></div>
                <div class="log-time">भर्खरै</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("हालसम्म कुनै दर्ता भएको छैन।")
    st.markdown('</div>', unsafe_allow_html=True)

with c_live:
    st.markdown('<div class="dash-card" style="background: linear-gradient(135deg, #1e293b, #0f172a); color: white; border: none;">', unsafe_allow_html=True)
    st.subheader("🔴 प्रत्यक्ष भइरहेका खेलहरू (Live)")
    if active_matches:
        for match in active_matches[:3]: # धेरै भए ३ वटा मात्र देखाउने
            p1 = str(match.get('player1', match.get('p_a', 'Team A'))).split('|')[0]
            p2 = str(match.get('player2', match.get('p_b', 'Team B'))).split('|')[0]
            s1 = match.get('score_a', 0)
            s2 = match.get('score_b', 0)
            st.markdown(f"""
            <div style="background: rgba(255,255,255,0.1); padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 4px solid #ef4444;">
                <div style="color: #94a3b8; font-size: 13px; font-weight: bold; margin-bottom: 5px;">{match.get('event_name', 'Match')}</div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 18px; font-weight: bold;">
                    <div style="width: 40%; text-align: right;">{p1}</div>
                    <div style="width: 20%; text-align: center; color: #fbbf24; font-size: 24px;">{s1} - {s2}</div>
                    <div style="width: 40%; text-align: left;">{p2}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="text-align:center; padding: 30px 10px;">
            <div style="font-size: 40px; margin-bottom: 10px; opacity:0.5;">🏟️</div>
            <div style="color: #94a3b8;">हाल कुनै पनि खेल प्रत्यक्ष भइरहेको छैन।</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# ७. फुटर
# ==========================================
render_footer()