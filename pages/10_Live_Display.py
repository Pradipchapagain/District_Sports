import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import time
from datetime import datetime

import base64
import os

try:
    from streamlit_autorefresh import st_autorefresh
    # ८ सेकेन्डमा पेज रिफ्रेस हुने
    st_autorefresh(interval=8000, limit=None, key="live_dashboard_refresh")
except ImportError:
    st.error("कृपया टर्मिनलमा `pip install streamlit-autorefresh` रन गर्नुहोस्।")
    st.stop()

# ==========================================
# सबैभन्दा माथि: साउन्ड बजाउने फङ्सन राख्ने
# ==========================================
def play_sound(file_name):
    """'sounds' फोल्डरबाट अटोमेटिक साउन्ड खोजेर बजाउने फङ्सन"""
    file_path = os.path.join("sounds", file_name)
    ext = file_name.split('.')[-1]
    
    try:
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            
            # 💡 जादु यहाँ छ: हरेक पटक युनिक ID बनाउन समय (time.time) प्रयोग गरिएको छ
            unique_id = str(time.time()).replace('.', '')
            
            md = f"""
                <audio autoplay id="audio_{unique_id}" class="stAudio">
                    <source src="data:audio/{ext};base64,{b64}" type="audio/{ext}">
                </audio>
            """
            st.markdown(md, unsafe_allow_html=True)
    except FileNotFoundError:
        pass



# १. पेज सेटिङ र अटो-साइकल लजिक
st.set_page_config(page_title="LIVE Scoreboard", page_icon="📺", layout="wide", initial_sidebar_state="collapsed")

if 'display_mode' not in st.session_state:
    st.session_state.display_mode = "TALLY"
    st.session_state.counter = 0

st.session_state.counter += 1
if st.session_state.counter > 3: # २४ सेकेन्ड पछि स्क्रिन परिवर्तन
    st.session_state.display_mode = "SCHEDULE" if st.session_state.display_mode == "TALLY" else "TALLY"
    st.session_state.counter = 0

# २. कस्टम CSS (तपाईंको ओरिजिनल डिजाइन)
st.markdown("""
<style>
    /* यो कोडले टिभी स्क्रिनमा स्क्रोलबार आउन दिँदैन र पूरै फुल-स्क्रिन बनाउँछ */
    html, body, [data-testid="stAppViewContainer"] {
        overflow: hidden !important; 
        max-height: 100vh !important;
    }
    /* माथिको सेतो खाली भाग (Header padding) हटाउन */
    .block-container {
        padding-top: 1rem !important; 
        padding-bottom: 0rem !important;
    }
    .stApp { background-color: #0E1117; color: white; }
    .header-box { text-align: center; background: linear-gradient(90deg, #1565C0 0%, #1E88E5 50%, #1565C0 100%); color: white; padding: 15px; border-radius: 10px; margin-bottom: 20px;}
    .medal-table { width: 100%; text-align: center; font-size: 22px; border-collapse: collapse; }
    .medal-table th { background-color: #1f2937; color: #9ca3af; padding: 12px; font-size: 20px; text-transform: uppercase; }
    .medal-table td { padding: 12px; border-bottom: 1px solid #374151; }
    .medal-table tr:nth-child(even) { background-color: #111827; }
    .medal-table tr:nth-child(odd) { background-color: #1f2937; }
    .gold-cell { color: #FFD700; font-weight: bold; font-size: 26px; text-shadow: 0 0 5px rgba(255,215,0,0.5); }
    .silver-cell { color: #C0C0C0; font-weight: bold; font-size: 24px; }
    .bronze-cell { color: #CD7F32; font-weight: bold; font-size: 24px; }
    .result-card { background-color: #1f2937; border-left: 6px solid #FFD700; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
    
    .live-banner {
        background-color: #111827; border: 2px solid #374151; border-radius: 15px; padding: 20px;
        text-align: center; margin-bottom: 30px; box-shadow: 0 0 16px rgba(255, 0, 0, 0.4);
        animation: pulseBorder 2s infinite;
    }
    .live-title { color: #EF4444; font-size: 24px; font-weight: bold; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; }
    .live-score-grid { display: flex; justify-content: center; align-items: center; gap: 40px; font-size: 50px; font-weight: bold; }
    
    .ticker-wrap { position: fixed; bottom: 0; left: 0; width: 100%; background-color: #b91c1c; color: white; padding: 10px 0; font-size: 24px; font-weight: bold; z-index: 9999; }
    .ticker-move { display: inline-block; white-space: nowrap; animation: ticker 25s linear infinite; }
    @keyframes ticker { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
    @keyframes pulseBorder { 0% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); } 50% { box-shadow: 0 0 25px rgba(239, 68, 68, 0.8); } 100% { box-shadow: 0 0 10px rgba(239, 68, 68, 0.2); } }
    
    .announce-banner {
        background: linear-gradient(90deg, #b91c1c 0%, #dc2626 50%, #b91c1c 100%);
        border: 2px solid #f87171; border-radius: 10px; padding: 20px;
        text-align: center; margin-bottom: 25px; box-shadow: 0 0 20px rgba(220, 38, 38, 0.6);
        animation: slideDown 0.8s ease-out;
    }
    @keyframes slideDown { 0% { opacity: 0; transform: translateY(-30px); } 100% { opacity: 1; transform: translateY(0); } }
</style>
""", unsafe_allow_html=True)

# ३. हेडर
from config import CONFIG
now = datetime.now()
st.markdown(f"""
    <div class='header-box'>
        <h1 style='margin:0; font-size: 36px;'>🏆 {CONFIG['EVENT_TITLE_NP']} - प्रत्यक्ष प्रसारण 🔴</h1>
        <div style='font-size: 20px; color: #FFD700; margin-top: 5px;'>आयोजक: {CONFIG['ORGANIZER_NAME']} &nbsp; | &nbsp; आतिथ्यता: {CONFIG['HOST_NAME']}</div>
        <div style='font-size: 18px; color: #e0e7ff;'>📅 {now.strftime("%Y-%m-%d")} &nbsp;|&nbsp; ⏰ {now.strftime("%I:%M %p")}</div>
    </div>
""", unsafe_allow_html=True)

# ४. उद्घोषकको सूचना (Announcement)
announcement = ls.get_announcement()
if announcement:
    st.markdown(f"""
        <div class="announce-banner">
            <div style="color: #FFF; font-size: 32px; font-weight: bold;">📢 {announcement['title']}</div>
            <div style="color: #fca5a5; font-size: 24px;">{announcement['subtitle']}</div>
        </div>
    """, unsafe_allow_html=True)

# ५. लाइभ म्याच चल्दैछ भने (Live Match)
live_data = ls.get_live_match()
if live_data:
    st.session_state.display_mode = "TALLY" 
    
    if live_data.get('is_kumite', False):
        # ========================================================
        # 🥋 KUMITE LIVE DISPLAY (Advanced UI with Hantei Wait)
        # ========================================================
        
        p_a_parts = live_data['p_a'].split('|')
        p1_name = p_a_parts[0]
        p1_muni = p_a_parts[1] if len(p_a_parts) > 1 else ""
        
        p_b_parts = live_data['p_b'].split('|')
        p2_name = p_b_parts[0]
        p2_muni = p_b_parts[1] if len(p_b_parts) > 1 else ""

        senshu = live_data.get('senshu')
        pen_a = live_data.get('pen_a', 0)
        pen_b = live_data.get('pen_b', 0)
        timer_str = live_data.get('timer', '03:00')
        status = live_data.get('status', 'Playing')

        def get_pen_html(count):
            html = "<div style='display:flex; justify-content:center; gap:8px; margin-top:20px;'>"
            for i in range(1, 6):
                bg = ["#facc15", "#fb923c", "#ea580c", "#dc2626", "#7f1d1d"][i-1] if i <= count else "transparent"
                border = "none" if i <= count else "2px solid rgba(255,255,255,0.3)"
                shadow = f"box-shadow: 0 0 10px {bg};" if i <= count else ""
                html += f"<div style='width:30px; height:30px; border-radius:5px; background:{bg}; border:{border}; {shadow}'></div>"
            html += "</div>"
            texts = ["", "Chui 1", "Chui 2", "Chui 3", "Hansoku-Chui", "Hansoku"]
            txt_color = ["", "#facc15", "#fb923c", "#ea580c", "#dc2626", "#7f1d1d"][count]
            pen_text = texts[count] if count > 0 else "&nbsp;"
            html += f"<div style='color:{txt_color}; font-size:20px; font-weight:bold; margin-top:10px;'>{pen_text}</div>"
            return html

        senshu_red = "<div style='position:absolute; right:0; top:0; bottom:0; width:50px; background:#FFD700; border-left:3px solid #dc2626; display:flex; align-items:center; justify-content:center;'><span style='writing-mode:vertical-rl; text-orientation:upright; font-weight:900; font-size:24px; letter-spacing:5px; color:#dc2626;'>SENSHU</span></div>" if senshu == 'Red' else ""
        senshu_blue = "<div style='position:absolute; left:0; top:0; bottom:0; width:50px; background:#FFD700; border-right:3px solid #2563eb; display:flex; align-items:center; justify-content:center;'><span style='writing-mode:vertical-rl; text-orientation:upright; font-weight:900; font-size:24px; letter-spacing:5px; color:#2563eb;'>SENSHU</span></div>" if senshu == 'Blue' else ""

        # 💡 HANTEI वा GAME OVER को म्यासेज
        status_html = ""
        if status == "WAITING FOR HANTEI DECISION":
            status_html = """
            <div style='background: #b91c1c; color: #FFD700; font-size: 26px; font-weight: bold; 
                        padding: 15px 20px; border-radius: 15px; margin-top: 30px; 
                        border: 3px solid #facc15; animation: hanteiPulse 1.5s infinite;'>
                ⚖️ WAITING FOR HANTEI DECISION
            </div>
            """
        elif status == "GAME OVER":
            status_html = """
            <div style='background: #334155; color: white; font-size: 30px; font-weight: bold; 
                        padding: 15px 30px; border-radius: 15px; margin-top: 30px;'>
                🛑 GAME OVER
            </div>
            """

        st.markdown(f"""
        <style>
            @keyframes hanteiPulse {{
                0% {{ transform: scale(1); box-shadow: 0 0 10px #b91c1c; }}
                50% {{ transform: scale(1.05); box-shadow: 0 0 25px #FFD700; }}
                100% {{ transform: scale(1); box-shadow: 0 0 10px #b91c1c; }}
            }}
        </style>
        <div style="background: black; padding: 20px; text-align: center; font-family: sans-serif; color: white;">
            <h1 style="color: #fbbf24; font-size: 40px; margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px;">🥋 {live_data['event_name']}</h1>
            <div style="display:flex; justify-content:center; gap:20px; align-items:stretch;">
                <div style="flex:1; background: linear-gradient(145deg, #7f1d1d, #dc2626); border: 5px solid #b91c1c; border-radius: 15px; padding: 30px; position:relative; overflow:hidden;">
                    {senshu_red}
                    <h2 style="font-size: 50px; margin: 0; color: white; text-shadow: 2px 2px 4px black;">{p1_name}</h2>
                    <h3 style="font-size: 24px; color: #fca5a5; margin: 5px 0 20px 0;">{p1_muni}</h3>
                    <div style="font-size: 150px; font-weight: 900; line-height: 1; text-shadow: 4px 4px 15px rgba(0,0,0,0.6);">{live_data['score_a']}</div>
                    <h3 style="color:white; margin-top:20px;">AKA (Red)</h3>
                    {get_pen_html(pen_a)}
                </div>
                <div style="flex:0.6; display:flex; flex-direction:column; justify-content:center; align-items:center;">
                    <div style="font-size: 80px; font-family: monospace; font-weight: bold; color: #fbbf24; background: #1e293b; padding: 10px 30px; border-radius: 20px; border: 4px solid #fbbf24; box-shadow: 0 0 20px rgba(251, 191, 36, 0.4);">
                        {timer_str}
                    </div>
                    <div style="font-size: 60px; font-weight: 900; color: #64748b; margin-top: 20px;">VS</div>
                    {status_html}  </div>
                <div style="flex:1; background: linear-gradient(145deg, #1e3a8a, #2563eb); border: 5px solid #1d4ed8; border-radius: 15px; padding: 30px; position:relative; overflow:hidden;">
                    {senshu_blue}
                    <h2 style="font-size: 50px; margin: 0; color: white; text-shadow: 2px 2px 4px black;">{p2_name}</h2>
                    <h3 style="font-size: 24px; color: #93c5fd; margin: 5px 0 20px 0;">{p2_muni}</h3>
                    <div style="font-size: 150px; font-weight: 900; line-height: 1; text-shadow: 4px 4px 15px rgba(0,0,0,0.6);">{live_data['score_b']}</div>
                    <h3 style="color:white; margin-top:20px;">AO (Blue)</h3>
                    {get_pen_html(pen_b)}
                </div>
                
            </div>
        </div>
        """, unsafe_allow_html=True)        
    else:
        # ========================================================
        # 🏐 TEAM GAMES LIVE DISPLAY (पुरानो भलिबल/कबड्डी डिजाइन)
        # ========================================================
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #0f2027, #203a43, #2c5364); padding: 40px; border-radius: 20px; color: white; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.5); margin-bottom: 30px;">
            <h1 style="font-size: 55px; color: #f1c40f; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 2px;">{live_data['event_name']}</h1>
            <div style="display: flex; justify-content: space-between; align-items: center; margin: 0 50px;">
                <div style="width: 40%;">
                    <h2 style="font-size: 45px; margin: 0; color: #ffffff;">{live_data['p_a']}</h2>
                    <div style="font-size: 90px; font-weight: bold; color: #00ff88; text-shadow: 2px 2px 10px rgba(0,255,136,0.5); line-height: 1.2;">{live_data['score_a']}</div>
                </div>
                <div style="width: 20%;">
                    <div style="font-size: 60px; font-weight: bold; color: #ff4757; text-shadow: 2px 2px 10px rgba(255,71,87,0.5);">VS</div>
                </div>
                <div style="width: 40%;">
                    <h2 style="font-size: 45px; margin: 0; color: #ffffff;">{live_data['p_b']}</h2>
                    <div style="font-size: 90px; font-weight: bold; color: #00ff88; text-shadow: 2px 2px 10px rgba(0,255,136,0.5); line-height: 1.2;">{live_data['score_b']}</div>
                </div>
            </div>
            <div style="background: rgba(255,255,255,0.1); display: inline-block; padding: 15px 40px; border-radius: 50px; margin-top: 30px;">
                <h3 style="font-size: 30px; margin: 0; color: #00d2d3; letter-spacing: 1px;">🟢 {live_data.get('status', 'Playing')}</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ==========================================
# 📢 फर्मल कल डिस्प्ले (Formal Call Display)
# ==========================================
call_data = ls.get_call()

if call_data:
    # play_sound("alert_bell.mp3") # साउन्ड फाइल छ भने यहाँ राख्ने
    
    st.markdown(f"""
        <div style='background-color: #f8f9fa; border: 5px solid {call_data['color']}; border-radius: 20px; padding: 50px; text-align: center; margin-top: 50px; box-shadow: 0 10px 30px rgba(0,0,0,0.2); animation: pulse 2s infinite;'>
            <h1 style='color: {call_data['color']}; font-size: 80px; margin: 0;'>📢 {call_data['call_type']}</h1>
            <h2 style='font-size: 50px; color: #333; margin-top: 20px;'>{call_data['event_name']}</h2>
            <h1 style='font-size: 60px; color: #666;'>{call_data['round_name']}</h1>
            <p style='font-size: 30px; color: #555; margin-top: 30px;'>Please report to the Call Room immediately.</p>
        </div>
        
        <style>
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.02); }}
                100% {{ transform: scale(1); }}
            }}
        </style>
    """, unsafe_allow_html=True)
    st.stop() # कल देखिउन्जेल अरू टेबल/ट्याली नदेखाउन

# ६. 🏆 अटोमेटिक पोडियम (Podium Celebration)
podium_data = ls.get_podium()
if podium_data:
    # 💡 अब सिधै फाइलको नाम मात्र पठाए पुग्छ (यसले आफैँ sounds फोल्डरभित्र खोज्छ)
    play_sound("cheer.wav") 
    
    st.markdown(f"<h1 style='text-align: center; color: #FFD700; font-size: 50px; animation: fadeIn 1s;'>🎉 {podium_data['event_name']} - अन्तिम नतिजा 🎉</h1><br>", unsafe_allow_html=True)
    
    c_s, c_g, c_b = st.columns([1, 1.2, 1])
    
    # 🥇 GOLD (बिचको ठूलो कोलममा)
    with c_g:
        if podium_data['gold']:
            g = podium_data['gold']
            st.markdown(f"<div style='background: linear-gradient(145deg, #FFF8DC, #FFD700); padding: 30px; border-radius: 15px; text-align: center; color: black; transform: scale(1.05); box-shadow: 0 10px 20px rgba(0,0,0,0.2);'><h1 style='font-size: 60px; margin:0;'>🥇</h1><h2 style='margin: 5px 0;'>GOLD</h2><h1 style='color: #8B6508; margin: 0;'>{g.get('score', '')}</h1><h3 style='margin: 15px 0 5px 0;'>{g.get('name', '')}</h3><h4 style='color: #333; margin: 0;'>📍 {g.get('municipality', '')}</h4></div>", unsafe_allow_html=True)
            
    # 🥈 SILVER (देब्रे कोलममा)
    with c_s:
        if podium_data['silver']:
            s = podium_data['silver']
            st.markdown(f"<div style='background: linear-gradient(145deg, #F8F9FA, #C0C0C0); padding: 25px; border-radius: 15px; text-align: center; color: black; margin-top: 30px; box-shadow: 0 8px 15px rgba(0,0,0,0.1);'><h1 style='font-size: 50px; margin:0;'>🥈</h1><h3 style='margin: 5px 0;'>SILVER</h3><h2 style='color: #4F4F4F; margin: 0;'>{s.get('score', '')}</h2><h3 style='margin: 15px 0 5px 0;'>{s.get('name', '')}</h3><h5 style='color: #333; margin: 0;'>📍 {s.get('municipality', '')}</h5></div>", unsafe_allow_html=True)
            
# 🥉 BRONZE (दाहिने कोलममा)
    with c_b:
        if podium_data['bronze']:
            b_data = podium_data['bronze']
            
            # 💡 यदि मार्सल आर्ट्स हो र २ जना कास्य विजेता छन् भने (List Check)
            if isinstance(b_data, list):
                names_html = "".join([f"<h3 style='margin: 10px 0 2px 0;'>{b.get('name', '')}</h3><h6 style='color: #333; margin: 0; border-bottom:1px solid #d4a373; padding-bottom:5px;'>📍 {b.get('municipality', '')}</h6>" for b in b_data])
                st.markdown(f"<div style='background: linear-gradient(145deg, #FFF5EE, #CD7F32); padding: 25px; border-radius: 15px; text-align: center; color: black; margin-top: 30px; box-shadow: 0 8px 15px rgba(0,0,0,0.1);'><h1 style='font-size: 50px; margin:0;'>🥉 🥉</h1><h3 style='margin: 5px 0;'>JOINT BRONZE</h3>{names_html}</div>", unsafe_allow_html=True)
            
            # यदि भलिबल/अन्य खेल हो र १ जना मात्र कास्य विजेता छ भने (Dict Check)
            else:
                b = b_data
                st.markdown(f"<div style='background: linear-gradient(145deg, #FFF5EE, #CD7F32); padding: 25px; border-radius: 15px; text-align: center; color: black; margin-top: 30px; box-shadow: 0 8px 15px rgba(0,0,0,0.1);'><h1 style='font-size: 50px; margin:0;'>🥉</h1><h3 style='margin: 5px 0;'>BRONZE</h3><h2 style='color: #8B4513; margin: 0;'>{b.get('score', '')}</h2><h3 style='margin: 15px 0 5px 0;'>{b.get('name', '')}</h3><h5 style='color: #333; margin: 0;'>📍 {b.get('municipality', '')}</h5></div>", unsafe_allow_html=True)    
    st.stop() # 🔴 पोडियम आउँदा अरु कुरा लुकाउने


# ७. 🏐 र 🥋 सिंगल म्याच नतिजा (एउटै ठाउँमा पालैपालो)
match_result = ls.get_match_result()
kata_result = ls.get_kata_result()

if kata_result:
    # 🥋 कराते (Kata) को नतिजा आएमा (५ वटा बत्तीसहित)
    play_sound("cheer.wav") # साउन्ड बजाउने
    
    # भोटलाई रातो र नीलो गोलो बत्तीमा परिणत गर्ने
    flags_html = ""
    for v in kata_result['votes']:
        if v == 'Aka':
            flags_html += "<div style='background-color:#DC2626; width:80px; height:80px; border-radius:50%; border:5px solid white; box-shadow:0 0 15px #DC2626;'></div>"
        elif v == 'Ao':
            flags_html += "<div style='background-color:#2563EB; width:80px; height:80px; border-radius:50%; border:5px solid white; box-shadow:0 0 15px #2563EB;'></div>"

    winner_color = "#DC2626" if kata_result['winner'] == "AKA" else "#2563EB"
    winner_name = kata_result['aka_name'] if kata_result['winner'] == "AKA" else kata_result['ao_name']
    
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #111827, #1f2937); padding: 50px; border-radius: 20px; text-align: center; border: 4px solid {winner_color}; margin-bottom: 30px;'>
            <h2 style='color: #9CA3AF; font-size: 35px; text-transform: uppercase;'>🥋 {kata_result['event_name']} - {kata_result['bout_id']}</h2>
            <h1 style='font-size: 60px; color: {winner_color}; margin: 20px 0;'>🏆 {winner_name} WINS! ({kata_result['winner']})</h1>
            <div style='margin: 40px 0;'>
                <p style='color: white; font-size: 24px; margin-bottom: 15px;'>Judges' Decision</p>
                <div style='display:flex; justify-content:center; gap:30px;'>
                    {flags_html}
                </div>
            </div>
            <h3 style='color: #6B7280; font-size: 28px;'>🔴 {kata_result['aka_name']} VS 🔵 {kata_result['ao_name']}</h3>
        </div>
    """, unsafe_allow_html=True)
    st.stop() # 🔴 नतिजा देखाउँदा अरु कुरा लुकाउने

elif match_result:
    # 🏐 भलिबल/अन्य खेलको नतिजा आएमा (पुरानै डिजाइन)
    st.markdown(f"""
        <div style='background: linear-gradient(135deg, #1e3a8a, #3b82f6); padding: 40px; border-radius: 20px; text-align: center; color: white; border: 4px solid #60A5FA; margin-bottom: 30px;'>
            <h2 style='color: #93C5FD; font-size: 30px;'>🏁 {match_result['match_title']} - नतिजा</h2>
            <h1 style='font-size: 50px; color: #FFD700; margin: 20px 0;'>🏆 {match_result['winner']} WON!</h1>
            <h3 style='font-size: 30px;'>Score/Sets: <span style='background: white; color: #1e3a8a; padding: 5px 15px; border-radius: 10px;'>{match_result['score']}</span></h3>
            <h4 style='color: #E5E7EB; margin-top: 20px;'>Defeated: {match_result['loser']}</h4>
        </div>
    """, unsafe_allow_html=True)
    st.stop() # 🔴 नतिजा देखाउँदा अरु कुरा लुकाउने


# ८. साइकल मोड (SCHEDULE vs TALLY)
if st.session_state.display_mode == "SCHEDULE":
    st.markdown("<h2 style='text-align: center; color: #60a5fa;'>📅 आजका बाँकी खेलहरू (Upcoming Schedule)</h2>", unsafe_allow_html=True)
    
    # तपाईंको ओरिजिनल ३-कोलम भ्यु (Heats/Bracket सहित) 
    conn = db.get_connection()
    # Schedules टेबलबाट डाटा तान्ने (Completed नभएका मात्र)
    q_sch = """
        SELECT s.event_code as code, s.event_name as name, s.phase as gender, e.category 
        FROM schedules s JOIN events e ON s.event_code = e.code 
        WHERE s.is_completed = 0 ORDER BY s.schedule_order ASC
    """
    try:
        df_sch = pd.read_sql_query(q_sch, conn)
    except Exception as e:
        # यदि टेबल वा कोलम छैन भने सफ्टवेयर क्र्यास हुँदैन, खाली डाटा देखाउँछ
        df_sch = pd.DataFrame() 
        st.warning("खेल तालिका (Schedule) लोड हुन सकेन। (टेबल अपडेट हुँदैछ)")
    conn.close()
    
    if not df_sch.empty:
        c_ath, c_team, c_ma = st.columns(3)
        
        def render_category_schedule(col, cat_name, icon):
            cat_events = df_sch[df_sch['category'] == cat_name]
            with col:
                st.markdown(f"<h3 style='text-align:center; color:#FFD700; background:#1f2937; padding:10px; border-radius:10px;'>{icon} {cat_name}</h3>", unsafe_allow_html=True)
                if cat_events.empty:
                    st.caption("बाँकी छैन।")
                else:
                    for _, row in cat_events.iterrows():
                        with st.container(border=True):
                            st.markdown(f"<div style='font-size:18px; font-weight:bold; color:#60A5FA;'>{row['name']} <span style='color:#FFF;'>({row['gender']})</span></div>", unsafe_allow_html=True)
                            
                            fix = ls.get_fixture(row['code'])
                            if fix:
                                if fix['type'] == 'bracket':
                                    round_1 = [m for m in fix['data'] if m['round'] == 1 and (not m.get('winner') or m['winner'] == 'None')]
                                    for m in round_1[:2]: # धेरै लामो नहोस् भनेर २ वटा मात्र देखाउने
                                        p1 = m['p1'] if m['p1'] != 'BYE' else '(BYE)'
                                        p2 = m['p2'] if m['p2'] != 'BYE' else '(BYE)'
                                        st.markdown(f"<div style='font-size:14px;'>⚔️ Match #{m['id']}: {p1} vs {p2}</div>", unsafe_allow_html=True)
                                elif fix['type'] == 'heats':
                                    heats_list = set(h['heat'] for h in fix['data'])
                                    for h in sorted(heats_list)[:2]:
                                        h_name = "FINAL" if str(h) == "FINAL" else f"Heat {h}"
                                        st.markdown(f"<div style='font-size:14px;'>🔥 {h_name}</div>", unsafe_allow_html=True)
                            else:
                                st.caption("टाइ-सिट तयार हुँदै...")

        render_category_schedule(c_ath, "Athletics", "🏃")
        render_category_schedule(c_team, "Team Game", "🏐")
        render_category_schedule(c_ma, "Martial Arts", "🥋")
    else:
        st.info("सबै खेलहरू सम्पन्न भए वा तालिका खाली छ।")

else:
# ९. पदक तालिका र ताजा अपडेट (Corrected SQL for Player & Team)
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.markdown("<h2 style='color:#FCD34D;'>🏅 पदक तालिका (Medal Standing)</h2>", unsafe_allow_html=True)
        conn = db.get_connection()
        
        # 👈 यहाँ सच्याइएको छ: Player र Team दुवैको पालिका तान्ने
        q_tally = """
            SELECT m.name as Municipality, 
            SUM(CASE WHEN r.medal = 'Gold' THEN 1 ELSE 0 END) as Gold, 
            SUM(CASE WHEN r.medal = 'Silver' THEN 1 ELSE 0 END) as Silver, 
            SUM(CASE WHEN r.medal = 'Bronze' THEN 1 ELSE 0 END) as Bronze 
            FROM results r 
            LEFT JOIN players p ON r.player_id = p.id
            LEFT JOIN teams t ON r.team_id = t.id
            JOIN municipalities m ON m.id = COALESCE(p.municipality_id, t.municipality_id)
            WHERE r.medal IN ('Gold', 'Silver', 'Bronze')
            GROUP BY m.id, m.name 
            ORDER BY Gold DESC, Silver DESC, Bronze DESC LIMIT 10
        """
        try:
            df_tally = pd.read_sql_query(q_tally, conn)
            
            if not df_tally.empty:
                html = "<table class='medal-table'><tr><th>स्थान</th><th style='text-align:left;'>पालिका (Municipality)</th><th>🥇</th><th>🥈</th><th>🥉</th></tr>"
                for idx, row in df_tally.iterrows():
                    pos_icon = "👑 १" if idx == 0 else "⭐ २" if idx == 1 else "🌟 ३" if idx == 2 else f"#{idx+1}"
                    html += f"<tr><td>{pos_icon}</td><td style='text-align:left; font-weight:bold;'>{row['Municipality']}</td><td class='gold-cell'>{row['Gold']}</td><td class='silver-cell'>{row['Silver']}</td><td class='bronze-cell'>{row['Bronze']}</td></tr>"
                html += "</table>"
                st.markdown(html, unsafe_allow_html=True)
            else:
                st.info("नतिजा आउन बाँकी छ...")
        except Exception as e:
            st.error(f"तालिका लोड हुन सकेन: {e}")

    with c2:
        st.markdown("<h2 style='color:#FCA5A5;'>🔥 ताजा नतिजाहरू (Latest)</h2>", unsafe_allow_html=True)
        
        # 👈 यहाँ पनि सच्याइएको छ: टिमले जितेको बेला टिमको नाम र पालिका देखाउने
        q_latest = """
            SELECT e.name as Event, 
                   COALESCE(p.name, t.name) as Winner, 
                   m.name as Palika, 
                   r.medal 
            FROM results r 
            JOIN events e ON r.event_code = e.code 
            LEFT JOIN players p ON r.player_id = p.id 
            LEFT JOIN teams t ON r.team_id = t.id
            JOIN municipalities m ON m.id = COALESCE(p.municipality_id, t.municipality_id)
            WHERE r.medal IN ('Gold', 'Silver', 'Bronze')
            ORDER BY r.id DESC LIMIT 5
        """
        try:
            df_lat = pd.read_sql_query(q_latest, conn)
            
            if not df_lat.empty:
                for _, row in df_lat.iterrows():
                    mc = "#FFD700" if row['medal'] == 'Gold' else "#C0C0C0" if row['medal'] == 'Silver' else "#CD7F32"
                    mi = "🥇" if row['medal'] == 'Gold' else "🥈" if row['medal'] == 'Silver' else "🥉"
                    st.markdown(f"<div class='result-card' style='border-left-color: {mc};'><div style='font-size: 16px; color: #60A5FA;'>{row['Event']}</div><div style='font-size: 20px; color: white; font-weight: bold;'>{row['Winner']} <span style='font-size:16px; color:{mc};'>({mi})</span></div><div style='font-size: 16px; color: #9CA3AF;'>🏛️ {row['Palika']}</div></div>", unsafe_allow_html=True)
            else:
                st.write("प्रतियोगिता भर्खरै सुरु हुँदैछ...")
        except Exception as e:
            st.error("ताजा नतिजा लोड हुन सकेन।")
            
        conn.close()
        
# १०. स्कुलिङ टेक्स्ट
st.markdown("<br><br><br>", unsafe_allow_html=True)
marquee_text = f"⭐⭐⭐ {CONFIG['EVENT_TITLE_NP']} प्रत्यक्ष प्रसारण (LIVE) | आयोजक: {CONFIG['ORGANIZER_NAME']} | आतिथ्यता: {CONFIG['HOST_NAME']} ⭐⭐⭐"
st.markdown(f"<div class='ticker-wrap'><div class='ticker-move'>{marquee_text} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; {marquee_text}</div></div>", unsafe_allow_html=True)


