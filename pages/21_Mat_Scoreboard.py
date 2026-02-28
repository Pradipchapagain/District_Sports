import streamlit as st
import database as db
import psycopg2.extras # 💡 PostgreSQL को डिक्शनरी कर्सरको लागि
from streamlit_autorefresh import st_autorefresh

# ⚙️ म्याट मोनिटरको लागि क्लिन र फुल-स्क्रिन सेटिङ
st.set_page_config(page_title="Mat Scoreboard", layout="wide", initial_sidebar_state="collapsed")

# 🔄 हरेक १ सेकेन्डमा अटो-रिफ्रेस
st_autorefresh(interval=1000, key="mat_sb_refresh")

# 🚫 अनावश्यक मेनु र मार्जिन पूर्ण रूपमा लुकाउने
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding: 0rem 1rem 0rem 1rem !important;}
        /* स्क्रोलबार लुकाउने */
        ::-webkit-scrollbar {display: none;}
    </style>
""", unsafe_allow_html=True)

# डाटाबेसबाट लाइभ म्याच तान्ने (💡 PostgreSQL तरिका)
live_match = None
try:
    conn = db.get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    # सबैभन्दा पछिल्लो लाइभ म्याच तान्ने
    c.execute("SELECT * FROM live_match ORDER BY id DESC LIMIT 1")
    live_match = c.fetchone()
    c.close()
except Exception as e:
    st.error(f"Database Error: {e}")
finally:
    if 'conn' in locals(): conn.close()

# ==========================================
# 🥋 म्याच खाली हुँदाको अवस्था (Idle State)
# ==========================================
if not live_match:
    st.markdown("""
    <div style='display:flex; height:90vh; align-items:center; justify-content:center; flex-direction:column; background-color:#0f172a; color:#cbd5e1;'>
        <h1 style='font-size:80px; letter-spacing:5px;'>MAT READY</h1>
        <p style='font-size:30px;'>Waiting for operator to start the match...</p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ==========================================
# 🥊 म्याट स्कोरबोर्ड (विशुद्ध खेल केन्द्रित)
# ==========================================
# Penalty UI
def get_pen_ui(count, color):
    sq = ""
    for i in range(1, 6):
        bg = color if i <= count else "transparent"
        border = f"3px solid {color}" if i > count else "none"
        sq += f"<div style='width:35px; height:35px; background:{bg}; border:{border}; margin:0 5px; display:inline-block; border-radius:50%;'></div>"
    return sq

# Senshu UI
def get_senshu_ui(has_senshu):
    if has_senshu:
        return "<div style='background-color:#fbbf24; color:#78350f; padding:5px 15px; border-radius:10px; font-weight:bold; font-size:24px; display:inline-block; margin-top:10px;'>SENSHU</div>"
    return "<div style='height:45px; margin-top:10px;'></div>"

# म्याच विवरण
p1_name = live_match.get('player1', 'AKA')
p2_name = live_match.get('player2', 'AO')
score_a = live_match.get('score_a', '0')
score_b = live_match.get('score_b', '0')
pen_a = int(live_match.get('pen_a', 0) or 0)
pen_b = int(live_match.get('pen_b', 0) or 0)
senshu = live_match.get('senshu', None)
timer_val = live_match.get('timer', '00:00')

st.markdown(f"<div style='text-align:center; color:#64748b; font-size:25px; font-weight:bold; padding:10px;'>{live_match.get('event_name', '')} - {live_match.get('round_name', '')}</div>", unsafe_allow_html=True)

# मुख्य लेआउट (२ भागमा बाँडिएको: रातो र नीलो)
ca, cb = st.columns(2)

# 🔴 AKA (Red) Side
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

# 🔵 AO (Blue) Side
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