import streamlit as st
import database as db
import config # 💡 कन्फिग फाइलबाट विवरण तान्नको लागि

# ==========================================
# ⚙️ GLOBAL CONFIGURATION 
# ==========================================
st.set_page_config(
    page_title="President Running Shield - CMS", 
    page_icon="🏆", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🎨 साइडबारको कस्टम डिजाइन (CSS)
st.markdown("""
    <style>
        /* साइडबारको ब्याकग्राउन्ड र फन्ट */
        [data-testid="stSidebar"] {
            background-color: #f8fafc;
            border-right: 1px solid #e2e8f0;
        }
        /* मेनुको ग्रुप हेडिङ (जस्तै: ⚙️ सेटअप र दर्ता) */
        [data-testid="stSidebarNavItems"] > div > ul > li > div {
            color: #1e293b !important;
            font-weight: bold !important;
            font-size: 14px !important;
            background-color: #e2e8f0;
            padding: 8px 10px;
            border-radius: 5px;
            margin-top: 15px;
            margin-bottom: 5px;
            text-transform: uppercase;
        }
        /* मेनुका लिङ्कहरू होभर गर्दाको इफेक्ट */
        [data-testid="stSidebarNavLink"]:hover {
            background-color: #dbeafe !important;
            color: #1d4ed8 !important;
            border-radius: 5px;
        }
        /* सेलेक्ट भएको (एक्टिभ) मेनुको डिजाइन */
        [data-testid="stSidebarNavLink"][aria-current="page"] {
            background-color: #1E88E5 !important;
            color: white !important;
            border-radius: 5px;
            font-weight: bold;
        }
        [data-testid="stSidebarNavLink"][aria-current="page"] svg {
            fill: white !important;
            stroke: white !important;
        }
    </style>
""", unsafe_allow_html=True)

try:
    db.create_tables()
    db.create_default_admin()
except Exception as e:
    st.error(f"Database Initialization Error: {e}")

if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = 'Guest'
if 'username' not in st.session_state: st.session_state.username = None
if 'municipality_id' not in st.session_state: st.session_state.municipality_id = None

# ==========================================
# 🔐 १. लगइन पेजको डिजाइन (Function)
# ==========================================
def login_page_ui():
    # 💡 config.py बाट सिधै विवरण तानिएको
    DISTRICT_NAME = config.CONFIG.get('DEFAULT_DISTRICT', 'Ilam')
    EVENT_NAME = config.CONFIG.get('EVENT_TITLE_NP', 'राष्ट्रपति रनिङ शिल्ड प्रतियोगिता')
    ORGANIZER_NAME = config.CONFIG.get('ORGANIZER_NAME_NP', 'जिल्ला खेलकुद विकास समिति')
    HOST_NAME = config.CONFIG.get('HOST_NAME_NP', 'स्थानीय पालिका')
    HOST_ROLE = config.CONFIG.get('HOST_ROLE_NP', 'स्थानीय व्यवस्थापन तथा आतिथ्यता')

    st.markdown(f"""
        <style>
        .login-container {{
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .main-title {{ font-size: 38px; font-weight: bold; text-align: center; color: #1E88E5; margin-bottom: 5px; text-shadow: 1px 1px 2px rgba(0,0,0,0.1); }}
        .center-badge {{ text-align: center; margin-bottom: 15px; }}
        .district-badge {{ background-color: #E3F2FD; padding: 6px 15px; border-radius: 20px; border: 1px solid #1E88E5; font-weight: bold; color: #1565C0; font-size:14px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }}
        .org-text {{ text-align: center; color: #b91c1c; font-size: 22px; font-weight: bold; margin-top: 15px; }}
        .host-text {{ text-align: center; color: #15803d; font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
        </style>
        
        <div class="login-container">
            <div class='center-badge'><span class='district-badge'>📍 जिल्ला: {DISTRICT_NAME}</span></div>
            <div class='main-title'>🏆 {EVENT_NAME}</div>
            <div class='org-text'>आयोजक: {ORGANIZER_NAME}</div>
            <div class='host-text'>{HOST_ROLE}: {HOST_NAME}</div>
        </div>
    """, unsafe_allow_html=True)

    c1, c_mid, c3 = st.columns([1, 1.2, 1])
    with c_mid:
        with st.form("login_form", border=True):
            st.markdown("<h3 style='text-align: center; color:#334155; margin-bottom:20px;'>🔐 प्रणालीमा प्रवेश गर्नुहोस्</h3>", unsafe_allow_html=True)
            username = st.text_input("👤 युजरनेम (Username)", placeholder="e.g. admin or suryodaya")
            password = st.text_input("🔑 पासवर्ड (Password)", type="password", placeholder="********")
            
            st.write("") # अलिकति खाली ठाउँ
            if st.form_submit_button("लगइन (Login) 🚀", type="primary", use_container_width=True):
                user = db.authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user['role']
                    st.session_state.username = user['username']
                    st.session_state.municipality_id = user['municipality_id']
                    st.rerun() 
                else:
                    st.error("❌ युजरनेम वा पासवर्ड मिलेन। कृपया पुन: प्रयास गर्नुहोस्।")

# ==========================================
# 🧭 २. DYNAMIC NAVIGATION MENU
# ==========================================
p_login = st.Page(login_page_ui, title="लगइन (Login)", icon="🔐", default=True)
p_dash  = st.Page("pages/0_Dashboard.py", title="Home Dashboard", icon="🏠")
p_muni  = st.Page("pages/1_Municipality_Setup.py", title="Municipality Setup", icon="🏛️")
p_reg   = st.Page("pages/2_Player_Registration.py", title="Individual Registration", icon="📝")
p_bulk  = st.Page("pages/3_Bulk_Upload.py", title="Bulk Upload (Excel)", icon="📑")
p_val   = st.Page("pages/4_Rule_Validation.py", title="Rule Validation", icon="⚠️")

# --- Game Operations ---
p_ath   = st.Page("pages/5_Athletics.py", title="Athletics Control", icon="🏃")
p_team  = st.Page("pages/6_Team_Games.py", title="Team Games Control", icon="🏐") 
p_ma    = st.Page("pages/7_Martial_Arts.py", title="Martial Arts Control", icon="🥋")

# --- Settings & Others ---
p_manual = st.Page("pages/13_Manual_Override.py", title="Manual Result Override", icon="🛠️")
p_evt   = st.Page("pages/8_Event_Settings.py", title="Event Settings", icon="⚙️")
p_rep   = st.Page("pages/9_Reports.py", title="Reports & Certificates", icon="📊")
p_sch   = st.Page("pages/12_Schedule_Manager.py", title="Schedule Manager", icon="📅")
p_ann   = st.Page("pages/11_Announcer.py", title="Announcer Dashboard", icon="🎙️")

# --- Public / Display Screens ---
p_judge = st.Page("pages/20_Judge_Tablet.py", title="Judge Tablet (Mobile)", icon="📱")
p_live  = st.Page("pages/10_Live_Display.py", title="Main Live Display", icon="📺")
p_mat   = st.Page("pages/21_Mat_Scoreboard.py", title="Mat Scoreboard", icon="🖥️") 
p_vb_tv = st.Page("pages/22_VB_Scoreboard.py", title="Volleyball TV", icon="🖥️") 
p_kb_tv = st.Page("pages/23_KB_Scoreboard.py", title="Kabaddi TV", icon="🖥️")   

# ==========================================
# 🎯 ३. रोल अनुसार मेनु देखाउने (Role-based Access)
# ==========================================
pages = {}

if not st.session_state.get('logged_in', False):
    pages = {
        "प्रणाली (System)": [p_login],
        "डिस्प्ले स्क्रिन (Displays)": [p_live, p_mat, p_vb_tv, p_kb_tv], 
        "जज प्यानल (Judges)": [p_judge]  
    }

elif st.session_state.user_role == 'admin':
    # 💡 प्रष्ट र लजिकल ग्रुपिङ
    pages = {
        "मुख्य पृष्ठ (Home)": [p_dash],
        "सेटअप र दर्ता (Setup & Reg)": [p_evt, p_muni, p_reg, p_bulk, p_val], 
        "खेल सञ्चालन (Games Control)": [p_sch, p_ath, p_team, p_ma, p_manual], 
        "प्रसारण र नतिजा (Live & Reports)": [p_ann, p_rep],
        "डिस्प्ले स्क्रिन (Displays)": [p_live, p_mat, p_vb_tv, p_kb_tv, p_judge] 
    }

else:
    # 💡 पालिका (Municipality) युजरको लागि सिम्पल मेनु
    pages = {
        "मुख्य पृष्ठ (Home)": [p_dash],
        "खेलाडी दर्ता (Registration)": [p_reg, p_bulk, p_val], 
        "नतिजा र रिपोर्ट (Results)": [p_rep],
        "डिस्प्ले स्क्रिन (Displays)": [p_live]
    }

# ==========================================
# 🚀 ४. नेभिगेसन रन गर्ने र साइडबार फुटर
# ==========================================
# साइडबारमा सफ्टवेयरको भर्सन र लगआउट बटन देखाउन
if st.session_state.get('logged_in', False):
    with st.sidebar:
        st.markdown("<hr style='margin-bottom:10px;'>", unsafe_allow_html=True)
        st.markdown(f"**Logged in as:** <span style='color:#1E88E5;'>{st.session_state.username}</span>", unsafe_allow_html=True)
        if st.button("🚪 लगआउट (Logout)", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_role = 'Guest'
            st.session_state.username = None
            st.rerun()
            
        st.markdown("""
            <div style='text-align:center; color:#94a3b8; font-size:11px; margin-top:15px;'>
                PRS CMS v3.1 Pro<br>Developed for DSDC Ilam
            </div>
        """, unsafe_allow_html=True)

pg = st.navigation(pages)
pg.run()