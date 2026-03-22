import streamlit as st
import database as db
import config
from streamlit_cookies_controller import CookieController
import warnings

# Pandas ले दिने DBAPI2 चेतावनीलाई लुकाउने
warnings.filterwarnings('ignore', message='.*pandas only supports SQLAlchemy connectable.*')

# ==========================================
# ⚙️ GLOBAL CONFIGURATION
# ==========================================
st.set_page_config(page_title="President Running Shield - CMS", page_icon="🏆", layout="wide", initial_sidebar_state="expanded")

# 🍪 कुकी कन्ट्रोलर सुरु गर्ने
controller = CookieController()

# ==========================================
# 🎨 CSS डिजाइन 
# ==========================================
st.markdown("""
    <style>
    /* ===== Sidebar Navigation ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
        border-right: 2px solid #cbd5e1;
    }
    [data-testid="stSidebarNavItems"] > div > ul > li > div {
        font-weight: 700 !important;
        font-size: 1.1rem !important;
        padding: 12px 15px !important;
        margin: 10px 10px 5px 10px !important;
        border-radius: 8px !important;
        background: linear-gradient(90deg, #f1f5f9, #ffffff) !important;
        color: #1e293b !important;
        border-left: 5px solid #3b82f6;
        border-bottom: 1px solid #cbd5e1;
        text-transform: none;
        letter-spacing: 0.3px;
        box-shadow: none;
    }
    [data-testid="stSidebarNavLink"] {
        background: transparent !important;
        border-radius: 8px !important;
        margin: 2px 10px !important;
        padding: 8px 15px 8px 20px !important;
        transition: all 0.2s ease;
        font-weight: 500;
        font-size: 1rem !important;
        color: #334155 !important;
        border-left: 3px solid transparent;
    }
    [data-testid="stSidebarNavLink"]:hover {
        background: rgba(59, 130, 246, 0.1) !important;
        color: #1e3a8a !important;
        border-left-color: #3b82f6;
        transform: translateX(3px);
    }
    [data-testid="stSidebarNavLink"][aria-current="page"] {
        background: linear-gradient(90deg, #e6f0ff, #ffffff) !important;
        color: #1e3a8a !important;
        font-weight: 700;
        border-left: 5px solid #fbbf24 !important;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2);
    }
    [data-testid="stSidebarNavItems"] > div > ul > li:nth-child(4) > div { border-left-color: #e11d48; background: linear-gradient(90deg, #fff1f2, #ffffff); }
    [data-testid="stSidebarNavItems"] > div > ul > li:nth-child(5) > div { border-left-color: #8b5cf6; background: linear-gradient(90deg, #ede9fe, #ffffff); }
    .sidebar-footer { text-align: center; color: #94a3b8; font-size: 0.75rem; margin-top: 30px; padding: 10px; border-top: 1px dashed #cbd5e1; }
    .stButton button { background: white; border: 1px solid #cbd5e1; border-radius: 30px; font-weight: 600; color: #1e293b; transition: all 0.2s; }
    .stButton button:hover { background: #fee2e2; border-color: #b91c1c; color: #b91c1c; }
    </style>
""", unsafe_allow_html=True)

# डाटाबेस सुरु गर्ने
try:
    db.create_tables()
    db.create_default_admin()
except Exception as e:
    st.error(f"Database Error: {e}")

# ==========================================
# 🔄 ०. अटो-लगइन लजिक (Auto-Login Check)
# ==========================================
# 📂 Home.py को सुरक्षा घेरा (Security Guard)
import streamlit as st

# 💡 जादु: यदि URL मा 'TV' वा 'Display' शब्द छ भने लगइन चेक नगर्ने
current_page = st.session_state.get("active_page", "")

# यी पेजहरूलाई पासवर्ड चाहिँदैन (Public Pages)
public_pages = ["Live_Display", "Mat_Scoreboard", "VB_Scoreboard", "KB_Scoreboard"]

# यदि पब्लिक पेज होइन र लगइन पनि छैन भने मात्र होममा फर्काउने
if not any(p in st.query_params.get("page", [""])[0] for p in public_pages):
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        # लगइन फर्म देखाउने कोड यहाँ हुन्छ...
        pass


# 💡 जादु यहाँ छ: कुकी पढ्न एकैछिन समय लाग्ने भएकोले 'auth_checked' फ्ल्याग राख्ने
if 'auth_checked' not in st.session_state:
    auth_data = controller.get('auth_user')
    if auth_data and isinstance(auth_data, dict):
        st.session_state.logged_in = True
        st.session_state.user_role = auth_data.get('role')
        st.session_state.username = auth_data.get('username')
        st.session_state.municipality_id = auth_data.get('muni_id')
    else:
        st.session_state.logged_in = False
    
    st.session_state.auth_checked = True

# डिफल्ट भ्यालुहरू
if 'user_role' not in st.session_state: st.session_state.user_role = 'Guest'
if 'username' not in st.session_state: st.session_state.username = None
if 'municipality_id' not in st.session_state: st.session_state.municipality_id = None

# ==========================================
# 🔐 १. लगइन पेज (Login UI)
# ==========================================
def login_page_ui():
    DISTRICT_NAME = config.CONFIG.get('DEFAULT_DISTRICT', 'Ilam')
    EVENT_NAME = config.CONFIG.get('EVENT_TITLE_NP', 'राष्ट्रपति रनिङ शिल्ड प्रतियोगिता')
    ORGANIZER_NAME = config.CONFIG.get('ORGANIZER_NAME_NP', 'जिल्ला खेलकुद विकास समिति')
    
    st.markdown(f"""
        <style>.login-container {{ background: linear-gradient(135deg, #f8fafc, #e2e8f0); padding: 30px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.1); margin-bottom: 30px; text-align:center; }}</style>
        <div class="login-container">
            <div style="background:#E3F2FD; padding:6px 15px; border-radius:20px; border:1px solid #1E88E5; color:#1565C0; font-weight:bold; display:inline-block; margin-bottom:15px;">📍 जिल्ला: {DISTRICT_NAME}</div>
            <h1 style="color:#1E88E5; margin:0; text-shadow: 1px 1px 2px rgba(0,0,0,0.1);">🏆 {EVENT_NAME}</h1>
            <h3 style="color:#b91c1c; margin-top:10px;">आयोजक: {ORGANIZER_NAME}</h3>
        </div>
    """, unsafe_allow_html=True)

    c1, c_mid, c3 = st.columns([1, 1.2, 1])
    with c_mid:
        with st.form("login_form", border=True):
            st.markdown("<h3 style='text-align: center; color:#334155; margin-bottom:20px;'>🔐 प्रणालीमा प्रवेश गर्नुहोस्</h3>", unsafe_allow_html=True)
            username = st.text_input("👤 युजरनेम (Username)")
            password = st.text_input("🔑 पासवर्ड (Password)", type="password")
            
            if st.form_submit_button("लगइन (Login) 🚀", type="primary", use_container_width=True):
                user = db.authenticate_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_role = user['role']
                    st.session_state.username = user['username']
                    st.session_state.municipality_id = user['municipality_id']
                    
                    # 💡 ब्राउजर कुकीमा सेभ गर्ने (७ दिनको लागि)
                    controller.set('auth_user', {
                        'username': user['username'],
                        'role': user['role'],
                        'muni_id': user['municipality_id']
                    }, max_age=604800)
                    
                    st.rerun() 
                else:
                    st.error("❌ युजरनेम वा पासवर्ड मिलेन।")

# ==========================================
# 🧭 २. DYNAMIC NAVIGATION
# ==========================================
p_login  = st.Page(login_page_ui, title="लगइन (Login)", icon="🔐", default=True)
p_dash   = st.Page("pages/0_Dashboard.py", title="Home Dashboard", icon="🏠")
p_rules  = st.Page("pages/0_Rules_and_Regulations.py", title="नियम र सर्तहरू", icon="📜")
p_muni   = st.Page("pages/1_Municipality_Setup.py", title="Municipality Setup", icon="🏛️")
p_reg    = st.Page("pages/2_Player_Registration.py", title="Individual Registration", icon="📝")
p_bulk   = st.Page("pages/3_Bulk_Upload.py", title="Bulk Upload (Excel)", icon="📑")
p_val    = st.Page("pages/4_Rule_Validation.py", title="Rule Validation", icon="⚠️")
p_ath    = st.Page("pages/5_Athletics.py", title="Athletics Control", icon="🏃")
p_team   = st.Page("pages/6_Team_Games.py", title="Team Games Control", icon="🏐") 
p_ma     = st.Page("pages/7_Martial_Arts.py", title="Martial Arts Control", icon="🥋")
p_manual = st.Page("pages/13_Manual_Override.py", title="Manual Result Override", icon="🛠️")
p_evt    = st.Page("pages/8_Event_Settings.py", title="Event Settings", icon="⚙️")
p_rep    = st.Page("pages/9_Reports.py", title="Reports & Certificates", icon="📊")
p_sch    = st.Page("pages/12_Schedule_Manager.py", title="Schedule Manager", icon="📅")
p_ann    = st.Page("pages/11_Announcer.py", title="Announcer Dashboard", icon="🎙️")
p_judge  = st.Page("pages/20_Judge_Tablet.py", title="Judge Tablet (Mobile)", icon="📱")
p_live   = st.Page("pages/10_Live_Display.py", title="Main Live Display", icon="📺")
p_mat    = st.Page("pages/21_Mat_Scoreboard.py", title="Mat Scoreboard", icon="🖥️") 
p_vb_tv  = st.Page("pages/22_VB_Scoreboard.py", title="Volleyball TV", icon="🖥️") 
p_kb_tv  = st.Page("pages/23_KB_Scoreboard.py", title="Kabaddi TV", icon="🖥️")   

# ==========================================
# 🎯 ३. ROLE-BASED ACCESS
# ==========================================
pages = {}

# 💡 जादु यहाँ छ: यदि लगइन छ भने ड्यासबोर्डलाई default=True बनाउने
if not st.session_state.get('logged_in', False):
    pages = {
        "प्रणाली (System)": [p_login],
        "डिस्प्ले स्क्रिन (Displays)": [p_live, p_mat, p_vb_tv, p_kb_tv], 
        "जज प्यानल (Judges)": [p_judge]  
    }
elif st.session_state.user_role == 'admin':
    # लगइन भएपछि ड्यासबोर्ड नै डिफल्ट (पहिलो) पेज हुन्छ
    p_dash = st.Page("pages/0_Dashboard.py", title="Home Dashboard", icon="🏠", default=True)
    pages = {
        "मुख्य पृष्ठ (Home)": [p_dash, p_rules],
        "सेटअप र दर्ता (Setup & Reg)": [p_evt, p_muni, p_reg, p_bulk, p_val], 
        "खेल सञ्चालन (Games Control)": [p_sch, p_ath, p_team, p_ma, p_manual], 
        "प्रसारण र नतिजा (Live & Reports)": [p_ann, p_rep],
        "डिस्प्ले स्क्रिन (Displays)": [p_live, p_mat, p_vb_tv, p_kb_tv, p_judge] 
    }
else:
    p_dash = st.Page("pages/0_Dashboard.py", title="Home Dashboard", icon="🏠", default=True)
    pages = {
        "मुख्य पृष्ठ (Home)": [p_dash, p_rules],
        "खेलाडी दर्ता (Registration)": [p_reg, p_bulk, p_val], 
        "नतिजा र रिपोर्ट (Results)": [p_rep],
        "डिस्प्ले स्क्रिन (Displays)": [p_live]
    }

# ==========================================
# 🚀 ४. SIDEBAR FOOTER & LOGOUT
# ==========================================
if st.session_state.get('logged_in', False):
    with st.sidebar:
        st.markdown("<hr style='margin-bottom:10px;'>", unsafe_allow_html=True)
        st.markdown(f"**Logged in as:** <span style='color:#1E88E5; font-weight:600;'>{st.session_state.username}</span>", unsafe_allow_html=True)
        if st.button("🚪 लगआउट (Logout)", use_container_width=True):
            controller.remove('auth_user')
            st.session_state.clear()
            st.rerun()
            
        st.markdown("""<div class="sidebar-footer">PRS CMS v3.1 Pro<br>Developed for DSDC Ilam</div>""", unsafe_allow_html=True)

# नेभिगेसन चलाउने
pg = st.navigation(pages)
pg.run()