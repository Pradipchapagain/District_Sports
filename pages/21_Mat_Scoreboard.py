#pages\21_Mat_Scoreboard.py
import streamlit as st
import database as db
import utils.live_state as ls
from streamlit_autorefresh import st_autorefresh

# १. सेटिङ - एक पटक मात्र
st.set_page_config(page_title="MAT SCOREBOARD", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=1000, key="mat_sb_refresh")

# २. CSS लुकाउने (मेनु, हेडर, स्क्रोल)
# २. CSS लुकाउने र फुल-स्क्रिन बनाउने (Complete Overhaul)
st.markdown("""
    <style>
        /* १. साइडबार र नेभिगेसन पूर्ण रूपमा बन्द */
        [data-testid="stSidebar"], [data-testid="stSidebarNav"], .st-emotion-cache-16idsys {
            display: none !important;
            width: 0px !important;
        }
        
        /* २. माथिको हेडर पट्टी हटाउने */
        header, [data-testid="stHeader"] {
            display: none !important;
        }
        
        /* ३. पेजको प्याडिङ 'जिरो' गर्ने (ताकि बोर्ड बोर्डरमा टाँसियोस्) */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
        }
        
        /* ४. मेन्यु, फुटर र स्क्रोलबार चटक्कै पार्ने */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        ::-webkit-scrollbar {display: none;}
        body {
            overflow: hidden;
            background-color: #0f172a; /* म्याटको डार्क ब्याकग्राउन्डसँग मिलाउन */
        }
    </style>
""", unsafe_allow_html=True)

# ३. ls बाट लाइभ म्याच लिने (छिटो र भरपर्दो)
live_match = ls.get_live_match()

# ४. यदि म्याच छैन भने आइडल स्क्रिन
if not live_match:
    st.markdown("""
    <div style='display:flex; height:90vh; align-items:center; justify-content:center; flex-direction:column; background-color:#0f172a; color:#cbd5e1;'>
        <h1 style='font-size:80px; letter-spacing:5px;'>MAT READY</h1>
        <p style='font-size:30px;'>प्रतिक्षा गर्दै...</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 🥊 म्याट स्कोरबोर्ड रेन्डर
# ==========================================
# सजिलोको लागि भेरिएबलमा राख्ने
p1_name = live_match.get('p_a', 'AKA')
p2_name = live_match.get('p_b', 'AO')
score_a = live_match.get('score_a', '0')
score_b = live_match.get('score_b', '0')
pen_a = int(live_match.get('pen_a', 0) or 0)
pen_b = int(live_match.get('pen_b', 0) or 0)
senshu = live_match.get('senshu')
timer_val = live_match.get('timer', '00:00')
event_name = live_match.get('event_name', '')
round_name = live_match.get('round_name', '')

# Penalty UI
def get_pen_ui(count, color):
    squares = []
    for i in range(1, 6):
        bg = color if i <= count else "transparent"
        border = f"3px solid {color}" if i > count else "none"
        squares.append(f"<div style='width:35px; height:35px; background:{bg}; border:{border}; margin:0 5px; display:inline-block; border-radius:50%;'></div>")
    return "".join(squares)

# Senshu UI
def get_senshu_ui(has_senshu):
    if has_senshu:
        return "<div style='background-color:#fbbf24; color:#78350f; padding:5px 15px; border-radius:10px; font-weight:bold; font-size:24px; display:inline-block; margin-top:10px;'>SENSHU</div>"
    return "<div style='height:45px; margin-top:10px;'></div>"

# इभेन्ट र राउन्ड देखाउने
if event_name or round_name:
    st.markdown(f"<div style='text-align:center; color:#64748b; font-size:25px; font-weight:bold; padding:10px;'>{event_name} - {round_name}</div>", unsafe_allow_html=True)

# दुई कोलम
ca, cb = st.columns(2)

# 🔴 AKA side
with ca:
    has_senshu_a = (senshu == 'Red')
    st.markdown(f"""
    <div style='background-color:#dc2626; padding:20px; border-radius:15px; border: 8px solid #991b1b; color:white; height:75vh; display:flex; flex-direction:column; justify-content:space-between; align-items:center;'>
        <h1 style='font-size:60px; margin:0; text-transform:uppercase; text-align:center; line-height:1.1;'>{p1_name}</h1>
        {get_senshu_ui(has_senshu_a)}
        <div style='font-size:250px; font-weight:bold; line-height:1; margin:20px 0;'>{score_a}</div>
        <div>{get_pen_ui(pen_a, 'white')}</div>
    </div>
    """, unsafe_allow_html=True)

# 🔵 AO side
with cb:
    has_senshu_b = (senshu == 'Blue')
    st.markdown(f"""
    <div style='background-color:#2563eb; padding:20px; border-radius:15px; border: 8px solid #1e40af; color:white; height:75vh; display:flex; flex-direction:column; justify-content:space-between; align-items:center;'>
        <h1 style='font-size:60px; margin:0; text-transform:uppercase; text-align:center; line-height:1.1;'>{p2_name}</h1>
        {get_senshu_ui(has_senshu_b)}
        <div style='font-size:250px; font-weight:bold; line-height:1; margin:20px 0;'>{score_b}</div>
        <div>{get_pen_ui(pen_b, 'white')}</div>
    </div>
    """, unsafe_allow_html=True)

# ⏱️ Timer (तल बीचमा)
st.markdown(f"""
    <div style='position:fixed; bottom:20px; left:50%; transform:translateX(-50%); background:#0f172a; border: 5px solid #fbbf24; color:#fbbf24; padding:10px 40px; border-radius:20px; font-size:80px; font-weight:bold; font-family:monospace; box-shadow: 0 10px 30px rgba(0,0,0,0.5); z-index:100;'>
        {timer_val}
    </div>
""", unsafe_allow_html=True)