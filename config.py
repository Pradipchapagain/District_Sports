import streamlit as st
from datetime import datetime

# ==========================================
# ⚙️ १. ग्लोबल कन्फिगरेसन (Central Settings)
# ==========================================
CONFIG = {
    # आयोजक र ठेगाना (अंग्रेजीमा)
    "MUNICIPALITY_NAME_EN": "Suryodaya Municipality",
    "OFFICE_NAME_EN": "Office of the Municipal Executive",
    "EVENT_TITLE_EN": "16th District Level President Running Shield - 2082",
    "ADDRESS_EN": "Fikkal, Ilam",
    "ORGANIZER_NAME_EN": "District Sports Development Committee, Ilam",
    "HOST_NAME_EN": "Suryodaya Municipality",
    "HOST_ROLE_EN": "Locally Managed & Hosted by",

    # आयोजक र ठेगाना (नेपालीमा)
    "MUNICIPALITY_NAME_NP": "सूर्योदय नगरपालिका",
    "OFFICE_NAME_NP": "नगर कार्यपालिकाको कार्यालय",
    "EVENT_TITLE_NP": "१६औं जिल्ला स्तरीय राष्ट्रपति रनिङ शिल्ड प्रतियोगिता २०८२",
    "ADDRESS_NP": "फिक्कल, इलाम",
    "ORGANIZER_NAME_NP": "जिल्ला खेलकुद विकास समिति, इलाम",
    "HOST_NAME_NP": "सूर्योदय नगरपालिका",
    "HOST_ROLE_NP": "स्थानीय व्यवस्थापन तथा आतिथ्यता",
    
    # पुराना कोडसँग मेल खानका लागि (Compatibility)
    "ORGANIZER_NAME": "जिल्ला खेलकुद विकास समिति, इलाम",
    "HOST_NAME": "सूर्योदय नगरपालिका",

    # सिस्टम र खेलाडी नियम (Rule Engine)
    "DEFAULT_PROVINCE": "Koshi Province",
    "DEFAULT_DISTRICT": "Ilam",
    "AGE_LIMIT_DATE": "2064-11-01",
    "MAX_PLAYERS_PER_PALIKA": 88,    
    "ALLOW_MULTIPLE_TEAM_GAMES": False, 

    # ⏱️ एक्सपायरी समय (सेकेन्डमा) - live_state.py को लागि
    "EXPIRE_TIMES": {
        'live_match': 3600,      # १ घण्टा (Live Scoreboard)
        'announcement': 1800,    # ३० मिनेट (Emergency Notice)
        'trigger_schedule': 180, # ३ मिनेट (Schedule View)
        'live_podium': 60,       # १ मिनेट (Winner Celebration)
        'live_match_result': 45, # ४५ सेकेन्ड (Match Result)
        'formal_call': 25,       # २५ सेकेन्ड (Call Room Announcement)
        'kata_result': 45        # ४५ सेकेन्ड (Kata Flags)
    }
}

# ==========================================
# 🎨 २. युनिफर्म युजर इन्टरफेस (UI Components)
# ==========================================

def render_header():
    """सबै पेजको माथि देखिने प्रोफेसनल हेडर"""
    st.markdown(f"""
        <div style='text-align: center; padding: 20px; background: linear-gradient(135deg, #f8f9fa 0%, #e2e8f0 100%); 
                    border-radius: 15px; margin-bottom: 30px; border-bottom: 5px solid #1E88E5; 
                    box-shadow: 0 4px 15px rgba(0,0,0,0.05);'>
            <h1 style='margin: 0; color: #1e3a8a; font-size: 28px; font-weight: 800; line-height: 1.4;'>
                🏆 {CONFIG['EVENT_TITLE_NP']}
            </h1>
            <div style='margin-top: 15px; display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; font-size: 16px;'>
                <div style='background: white; padding: 5px 15px; border-radius: 20px; border: 1px solid #cbd5e1;'>
                    <b>आयोजक:</b> <span style='color: #1E88E5;'>{CONFIG['ORGANIZER_NAME_NP']}</span>
                </div>
                <div style='background: white; padding: 5px 15px; border-radius: 20px; border: 1px solid #cbd5e1;'>
                    <b>{CONFIG['HOST_ROLE_NP']}:</b> <span style='color: #1E88E5;'>{CONFIG['HOST_NAME_NP']}</span>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

def render_footer():
    """सबै पेजको पुछारमा देखिने क्लिन फुटर"""
    current_year = datetime.now().year
    st.markdown("<br><br>", unsafe_allow_html=True) 
    st.markdown(f"""
        <div style='border-top: 2px solid #e2e8f0; padding-top: 20px; text-align: center; color: #475569; font-size: 13px;'>
            <div style='font-weight: bold; font-size: 15px; color: #1e293b; margin-bottom: 5px;'>
                © {current_year} {CONFIG['EVENT_TITLE_EN']}
            </div>
            <div>
                Organized by: <b>{CONFIG['ORGANIZER_NAME_EN']}</b> 
                <span style='color:#cbd5e1;'> | </span> 
                {CONFIG['HOST_ROLE_EN']}: <b>{CONFIG['HOST_NAME_EN']}</b>
            </div>
            <div style='margin-top: 10px; font-size: 11px; color: #cbd5e1;'>
                INTERNAL AUDIT VERSION 2.1 | POWERED BY NEON CLOUD
            </div>
        </div>
    """, unsafe_allow_html=True)