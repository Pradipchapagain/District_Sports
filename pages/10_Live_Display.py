import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import time, base64, os
from datetime import datetime
from config import CONFIG

# ==========================================
# ⚙️ १. कन्फिगरेसन र क्यासिङ (TTL = 5s)
# ==========================================
st.set_page_config(page_title="LIVE Scoreboard", page_icon="📺", layout="wide", initial_sidebar_state="collapsed")

@st.cache_data(ttl=5)
def fetch_cached_data():
    """५ सेकेन्डको क्यासिङसहित सबै डाटा तान्छ"""
    data = {'active_matches': [], 'tally': pd.DataFrame(), 'headlines': "", 
            'announcement': None, 'podium': None, 'match_result': None}
    conn = db.get_connection()
    try:
        data['active_matches'] = ls.get_all_active_matches()
        data['tally'] = pd.read_sql_query("SELECT m.name, SUM(CASE WHEN r.medal='Gold' THEN 1 ELSE 0 END) as G FROM results r LEFT JOIN players p ON r.player_id=p.id LEFT JOIN teams t ON r.team_id=t.id JOIN municipalities m ON m.id=COALESCE(p.municipality_id, t.municipality_id) GROUP BY m.name ORDER BY G DESC LIMIT 8", conn)
        data['headlines'] = ls.get_ticker_headlines(conn)
        data['announcement'] = ls.get_announcement()
        data['podium'] = ls.get_podium()
        data['match_result'] = ls.get_match_result()
    finally:
        conn.close()
    return data

# ==========================================
# 🔊 २. साउन्ड र फ्ल्यास न्यूज लजिक
# ==========================================
def play_once(file_name):
    """नयाँ विनर आउँदा मात्र साउन्ड बजाउने र फ्ल्यास देखाउने"""
    conn = db.get_connection()
    curr_golds = pd.read_sql_query("SELECT COUNT(*) FROM results WHERE medal='Gold'", conn).iloc[0,0]
    conn.close()
    
    if 'last_g' not in st.session_state: st.session_state.last_g = curr_golds
    
    if curr_golds > st.session_state.last_g:
        st.session_state.last_g = curr_golds
        st.session_state.show_f = True
        # साउन्ड बजाउने (Base64)
        play_sound_base64(file_name)

def play_sound_base64(file):
    path = os.path.join("sounds", file)
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.markdown(f'<audio autoplay><source src="data:audio/wav;base64,{b64}"></audio>', unsafe_allow_html=True)

# ==========================================
# 🎨 ३. CSS (Fixed Height & Pointer Events Fix)
# ==========================================
st.markdown("""
<style>
    html, body, [data-testid="stAppViewContainer"] { background: #0E1117; color: white; overflow: hidden; height: 100vh; }
    .header-box { text-align: center; background: linear-gradient(90deg, #1565C0, #1E88E5); padding: 8px; border-bottom: 3px solid #FFD700; }
    .flash-overlay { 
        position: fixed; top: 0; left: 0; width: 100%; height: 100%; 
        background: rgba(0,0,0,0.9); z-index: 10000; display: flex; 
        align-items: center; justify-content: center; 
        pointer-events: none; /* फेड आउट हुँदा क्लिक रोक्दैन */
        animation: fadeOut 4s forwards;
    }
    @keyframes fadeOut { 0% { opacity: 1; pointer-events: auto; } 90% { opacity: 1; } 100% { opacity: 0; pointer-events: none; } }
    .ticker-wrap { position: fixed; bottom: 0; left: 0; width: 100%; background: #b91c1c; padding: 8px 0; font-size: 22px; z-index: 999; }
    .ticker-move { display: inline-block; white-space: nowrap; animation: ticker 25s linear infinite; }
    @keyframes ticker { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 📺 ४. ड्यासबोर्ड रेन्डर (Execution)
# ==========================================
from streamlit_autorefresh import st_autorefresh
st_autorefresh(interval=8000, key="live_ref")

d = fetch_cached_data()
play_once("cheer.wav")

# हेडर र अनाउन्समेन्ट
st.markdown(f"<div class='header-box'><h2 style='margin:0;'>🏆 {CONFIG['EVENT_TITLE_NP']}</h2></div>", unsafe_allow_html=True)
if d['announcement']:
    st.warning(f"📢 {d['announcement']['title']}: {d['announcement']['subtitle']}")

# फ्ल्यास ओभरले (यदि नयाँ विनर छ भने)
if st.session_state.get('show_f'):
    st.markdown('<div class="flash-overlay"><div style="text-align:center; border:5px solid gold; padding:50px; border-radius:20px; background:#1e1b4b;"><h1>🥇 नयाँ स्वर्ण पदक विजेता!</h1><h2>बधाई छ!</h2></div></div>', unsafe_allow_html=True)
    st.session_state.show_f = False

# मुख्य भाग: लाइभ म्याच वा ट्याली वा पोडियम
if d['podium']:
    st.success(f"🎊 {d['podium']['event_name']} को नतिजा सार्वजनिक भयो!")
    st.stop() # पोडियम प्राथमिकता

if d['active_matches']:
    cols = st.columns(len(d['active_matches'][:3]))
    for i, m in enumerate(d['active_matches'][:3]):
        with cols[i]:
            st.markdown(f"<div style='background:#111827; padding:20px; border-radius:10px; border-top:5px solid #1E88E5; text-align:center;'><h4>{m['event_name']}</h4><h1 style='font-size:60px;'>{m['score_a']} - {m['score_b']}</h1><p>{m['player1'].split('|')[0]} vs {m['player2'].split('|')[0]}</p></div>", unsafe_allow_html=True)
else:
    # पदक तालिका
    st.markdown("<h3 style='text-align:center; color:#FFD700;'>🥇 पदक तालिका (Top Standing)</h3>", unsafe_allow_html=True)
    st.table(d['tally'])

# टिकर
st.markdown(f"<div class='ticker-wrap'><div class='ticker-move'>⚡ हेडलाइन्स: {d['headlines']} | {CONFIG['EVENT_TITLE_NP']}</div></div>", unsafe_allow_html=True)