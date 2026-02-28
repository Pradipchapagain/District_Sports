import streamlit as st
import database as db

# लगइन चेक (switch_page को सट्टा rerun राखिएको)
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.rerun()

EVENT_NAME = "१६औं जिल्ला स्तरीय राष्ट्रपति रनिङ शिल्ड प्रतियोगिता २०८२"
ORGANIZER_NAME = "जिल्ला खेलकुद विकास समिति, इलाम"
HOST_NAME = "सूर्योदय नगरपालिका, इलाम"

st.markdown(f"""
    <style>
    .main-title {{ font-size: 40px; font-weight: bold; text-align: center; color: #1E88E5; margin-bottom: 5px; }}
    .organizer-box {{ text-align: center; color: #D32F2F; font-size: 20px; font-weight: bold; margin-top: 10px; }}
    .host-box {{ text-align: center; color: #2E7D32; font-size: 20px; font-weight: bold; margin-top: 5px; margin-bottom: 20px; }}
    </style>
    <div class='main-title'>{EVENT_NAME}</div>
    <div class='organizer-box'>आयोजक: {ORGANIZER_NAME}</div>
    <div class='host-box'>आतिथ्य (Host): {HOST_NAME}</div>
    <hr>
""", unsafe_allow_html=True)

# --- Top Bar (Welcome & Logout) ---
wc1, wc2 = st.columns([4, 1])
with wc1:
    if st.session_state.user_role == 'admin':
        st.success(f"👋 स्वागत छ, **{st.session_state.username.upper()}**! तपाईं **Admin** हुनुहुन्छ।")
    else:
        st.info(f"👋 स्वागत छ, **{st.session_state.username.upper()}**! तपाईंले आफ्नो पालिकाको डाटा मात्र व्यवस्थापन गर्न सक्नुहुन्छ।")
        
with wc2:
    if st.button("🚪 लगआउट (Logout)", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.user_role = 'Guest'
        st.session_state.username = None
        st.session_state.municipality_id = None
        st.rerun() # 👈 यहाँ पनि switch_page को सट्टा st.rerun()

# --- Dashboard Metrics ---
try:
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM municipalities")
    num_mun = c.fetchone()[0]
    
    if st.session_state.user_role == 'admin':
        c.execute("SELECT COUNT(*) FROM players")
    else:
        c.execute("SELECT COUNT(*) FROM players WHERE municipality_id=?", (st.session_state.municipality_id,))
    num_players = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM events")
    num_events = c.fetchone()[0]
    conn.close()
except:
    num_mun, num_players, num_events = 0, 0, 0

col1, col2, col3 = st.columns(3)
col1.metric("🏛️ सहभागी पालिकाहरु", f"{num_mun}", "Municipalities")
col2.metric("🏃 " + ("जम्मा दर्ता भएका खेलाडी" if st.session_state.user_role == 'admin' else "तपाईंको पालिकाका खेलाडी"), f"{num_players}", "Players")
col3.metric("🏅 कुल इभेन्टहरु", f"{num_events}", "Sports Categories")

st.markdown("---")
st.info("👈 कृपया काम सुरु गर्न बायाँपट्टिको मेनु (Sidebar) प्रयोग गर्नुहोस्।")

st.markdown(f"<div style='text-align: center; color: grey; font-size: 12px;'><br><br>Managed by: <b>{ORGANIZER_NAME}</b> | Hosted by: <b>{HOST_NAME}</b><br>System v3.0 | Secured Login</div>", unsafe_allow_html=True)