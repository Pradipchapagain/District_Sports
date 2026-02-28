import streamlit as st
from datetime import datetime

# ग्लोबल कन्फिगरेसन फाइल
CONFIG = {
    # रिपोर्ट र प्रमाणपत्रको हेडरको लागि (अंग्रेजीमा)
    "MUNICIPALITY_NAME_EN": "Suryodaya Municipality",
    "OFFICE_NAME_EN": "Office of the Municipal Executive",
    "EVENT_TITLE_EN": "16th District Level President Running Shield - 2082",
    "ADDRESS_EN": "Fikkal, Ilam",
    
    # नेपालीमा (आवश्यक परेमा)
    "MUNICIPALITY_NAME_NP": "सूर्योदय नगरपालिका",
    "OFFICE_NAME_NP": "नगर कार्यपालिकाको कार्यालय",
    "EVENT_TITLE_NP": "१६औं जिल्ला स्तरीय राष्ट्रपति रनिङ शिल्ड प्रतियोगिता २०८२",
    "ADDRESS_NP": "फिक्कल, इलाम",
    "ORGANIZER_NAME": "जिल्ला खेलकुद विकास समिति, इलाम",
    "HOST_NAME": "सूर्योदय नगरपालिका",
    
    # आयोजक र व्यवस्थापक विवरण (अद्यावधिक गरिएको)
    "ORGANIZER_NAME_EN": "District Sports Development Committee, Ilam",
    "ORGANIZER_NAME_NP": "जिल्ला खेलकुद विकास समिति, इलाम",
    "HOST_NAME_EN": "Suryodaya Municipality",
    "HOST_NAME_NP": "सूर्योदय नगरपालिका",
    "HOST_ROLE_NP": "स्थानीय व्यवस्थापन तथा आतिथ्यता", # 👈 नयाँ थपिएको
    "HOST_ROLE_EN": "Locally Managed & Hosted by", # 👈 नयाँ थपिएको
    
    # सिस्टम सेटिङ
    "DEFAULT_PROVINCE": "Koshi Province",
    "DEFAULT_DISTRICT": "Ilam",

    # खेलाडी नियम
    'AGE_LIMIT_DATE': '2064-11-01',
    'MAX_PLAYERS_PER_PALIKA': 88,    
    'ALLOW_MULTIPLE_TEAM_GAMES': False, 
}

def render_header():
    """सबै पेजको माथि देखिने एकरूपता भएको हेडर"""
    st.markdown(f"""
        <div style='text-align: center; padding: 15px 10px; background: linear-gradient(to right, #f8f9fa, #e9ecef, #f8f9fa); border-radius: 10px; margin-bottom: 25px; border-bottom: 4px solid #1E88E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
            <h2 style='margin: 0; color: #0f172a; font-size: 26px; padding-bottom: 8px; font-weight: bold;'>
                🏆 {CONFIG['EVENT_TITLE_NP']}
            </h2>
            <div style='display: flex; justify-content: center; align-items: center; gap: 20px; font-size: 15px; color: #334155; flex-wrap: wrap;'>
                <span><b>आयोजक:</b> <span style='color: #1E88E5;'>{CONFIG['ORGANIZER_NAME_NP']}</span></span>
                <span style='color:#cbd5e1;'>|</span>
                <span><b>{CONFIG['HOST_ROLE_NP']}:</b> <span style='color: #1E88E5;'>{CONFIG['HOST_NAME_NP']}</span></span>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_footer():
    """सबै पेजको पुछारमा देखिने फुटर"""
    current_year = datetime.now().year
    st.markdown("<br><br>", unsafe_allow_html=True) 
    st.markdown(f"""
        <hr style='margin: 0px 0px 15px 0px; border-top: 1px solid #e2e8f0;'>
        <div style='text-align: center; color: #64748b; font-size: 13px; line-height: 1.6;'>
            <strong>© {current_year} {CONFIG['EVENT_TITLE_EN']}</strong><br>
            Organized by: <b>{CONFIG['ORGANIZER_NAME_EN']}</b> &nbsp;|&nbsp; {CONFIG['HOST_ROLE_EN']}: <b>{CONFIG['HOST_NAME_EN']}</b><br>
            <i>{CONFIG['ADDRESS_EN']}, {CONFIG['DEFAULT_DISTRICT']}, {CONFIG['DEFAULT_PROVINCE']}</i>
        </div>
    """, unsafe_allow_html=True)