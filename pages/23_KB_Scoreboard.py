import streamlit as st
import database as db
import json
from streamlit_autorefresh import st_autorefresh
from config import CONFIG
from datetime import datetime
from time import time
import os
import base64
import re

# ==========================================
# ⚙️ १. टिभीको लागि फुल-स्क्रिन सेटिङ
# ==========================================
st.set_page_config(page_title="Kabaddi Live TV", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=2000, key="kb_tv_refresh")

# ==========================================
# 🧹 २. साइडबार र मेनु लुकाउने
# ==========================================
st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="stSidebarNav"], .st-emotion-cache-16idsys { display: none !important; width: 0px !important; }
        header, [data-testid="stHeader"] { display: none !important; }
        .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; padding-left: 1rem !important; padding-right: 1rem !important; }
        body { overflow: hidden; background-color: #0E1117; }
        footer, #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

@st.cache_data
def get_cached_base64_image(filename):
    filepath = os.path.join("assets", filename)
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# ==========================================
# 🎨 CSS Layout
# ==========================================
st.markdown("""
    <style>
        .block-container {padding: 0rem 2rem 0rem 2rem !important; background-color: #0f172a;}
        ::-webkit-scrollbar {display: none;}

        .header-box { background: linear-gradient(90deg, #1e293b, #0f172a, #1e293b); padding: 10px 20px; border-bottom: 4px solid #facc15; margin-bottom: 15px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); display: flex; justify-content: space-between; align-items: center; }

        /* 💡 उचाइ ४८०px बनाएर खेलाडीको लिस्ट देखाउन धेरै ठाउँ दिइएको छ */
        /* 💡 एरेनाको ग्याप कम गर्ने */
        .kb-arena { 
            display: flex; 
            justify-content: space-between; 
            align-items: stretch; 
            width: 100%; 
            gap: 5px; /* १५ बाट ५ मा झारियो */
            margin: 5px 0; 
            height: 500px; 
        }

        /* 💡 रोस्टरको बक्सलाई कसिलो बनाउने */
        .roster-scroll { 
            flex: 1.1; 
            min-width: 250px; 
            background: rgba(30, 41, 59, 0.7); 
            border: 2px solid #334155; 
            border-radius: 10px; 
            padding: 5px; /* प्याडिङ घटाइयो */
            display: flex; 
            flex-direction: column; 
            overflow: hidden;
        }
        .roster-title { font-size: 18px; font-weight: bold; color: #facc15; border-bottom: 2px solid #475569; padding-bottom: 5px; margin-bottom: 10px; letter-spacing: 2px; }

        .kb-bench { display: flex; flex-direction: column; gap: 8px; background: #1e293b; padding: 10px; border-radius: 8px; min-width: 60px; align-items: center; border: 2px solid #475569; }
        .bench-title { color: white; font-size: 14px; font-weight: bold; writing-mode: vertical-rl; flex-grow: 1; text-align: center; letter-spacing: 3px; }
        .sitting-block { display: flex; flex-direction: column; justify-content: flex-end; gap: 6px; background: #e2e8f0; padding: 10px; border-radius: 8px; width: 70px; border: 3px solid #cbd5e1; }
        .sit-slot { width: 45px; height: 45px; border-radius: 50%; background: white; border: 2px dashed #94a3b8; display: flex; justify-content: center; align-items: center; font-size: 16px; font-weight: bold; color: #475569; position: relative; margin: 0 auto; }
        .sit-filled { background: #cbd5e1; border: 3px solid #475569; color: black; box-shadow: inset 0 0 5px rgba(0,0,0,0.2); }

        .kb-court { flex: 4; min-width: 600px; max-width: 1200px; background-color: #fcd34d; border: 6px solid white; position: relative; box-shadow: 0 10px 25px rgba(0,0,0,0.4); overflow: hidden; border-radius: 8px; }

        .bg-blue { background-color: #2563eb !important; color: white !important; border: 3px solid white !important; }
        .bg-red { background-color: #dc2626 !important; color: white !important; border: 3px solid white !important; }
        .bg-green { background-color: #22c55e !important; color: white !important; border: 3px solid white !important; }
        .bg-out { background-color: #ef4444 !important; color: white !important; border: 3px solid black !important; }

        .p-dot { position: absolute; width: 45px; height: 45px; border-radius: 50%; font-weight: bold; font-size: 20px; display: flex; justify-content: center; align-items: center; transform: translate(-50%, -50%); z-index: 5; transition: all 0.5s ease-in-out; box-shadow: 2px 2px 8px rgba(0,0,0,0.5); }
        .p-dot-bench { position: relative; width: 38px; height: 38px; transform: none; font-size: 16px; margin-bottom: 5px; box-shadow: none; }
        .captain-dot { border: 5px double white !important; box-shadow: 0 0 10px rgba(0,0,0,0.8); }

        .raider-dod { box-shadow: 0 0 25px #ea580c; transform: translate(-50%, -50%) scale(1.4); z-index: 20; animation: blink 0.8s infinite; }
        .raider-normal { box-shadow: 0 0 20px white; transform: translate(-50%, -50%) scale(1.4); z-index: 20; }
        @keyframes blink { 50% { opacity: 0.7; box-shadow: 0 0 10px #ea580c; } }
        .target-active { border: 5px solid #ef4444 !important; animation: targetPulse 0.5s infinite; scale: 1.2; }
        @keyframes targetPulse { 0% { box-shadow: 0 0 0px red; } 100% { box-shadow: 0 0 20px red; } }

        .mid-line { position: absolute; left: 50%; top: 0; bottom: 0; width: 8px; transform: translateX(-50%); z-index: 2; transition: all 0.3s; }
        .baulk-line-left, .baulk-line-right { position: absolute; top: 0; bottom: 0; width: 4px; z-index: 1; transition: all 0.5s; }
        .baulk-line-left { left: 35%; } .baulk-line-right { right: 35%; }
        .bonus-line-left, .bonus-line-right { position: absolute; top: 0; bottom: 0; width: 4px; z-index: 1; transition: all 0.5s; }
        .bonus-line-left { left: 20%; border-left: 4px dashed white; } 
        .bonus-line-right { right: 20%; border-right: 4px dashed white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 📡 डाटा फेचिङ
# ==========================================
import utils.live_state as ls
kb_data = ls._get_state("kb_live_match")

if not kb_data or not kb_data.get('state', {}).get('match_started'):
    st.markdown("<div style='text-align:center; margin-top:15vh;'><h1 style='font-size:100px; color:#cbd5e1;'>🤼 KABADDI LIVE</h1><p style='font-size:40px; color:#64748b;'>खेल सुरु हुन प्रतिक्षा गर्दै...</p></div>", unsafe_allow_html=True)
    st.stop()

state = kb_data['state']
teams = list(state.get('roster', {}).keys())
if len(teams) >= 2: p1, p2 = teams[0], teams[1]
else: st.error("टोलीको जानकारी मिलेन।"); st.stop()

# ==========================================
# 🧠 जादु: JSON स्टेटबाटै म्याचको विवरण तान्ने (DB को झन्झट खत्तम!)
# ==========================================
match_title = kb_data.get('match_title', '') 
round_name = state.get('round_name', 'Match')
match_no = state.get('match_no', '-')
gender = str(state.get('gender', '')).lower()

db_gender_np = ""
if gender in ['m', 'male', 'boys', 'men'] or "boy" in match_title.lower() or "men" in match_title.lower(): 
    db_gender_np = "छात्र"
elif gender in ['f', 'female', 'girls', 'women'] or "girl" in match_title.lower() or "women" in match_title.lower(): 
    db_gender_np = "छात्रा"

display_game_name = f"🤼 कबड्डी ({db_gender_np})" if db_gender_np else "🤼 कबड्डी"

# ==========================================
# 🏆 3-Column Header (स्मार्ट हेडर)
# ==========================================
now = datetime.now()
st.markdown(f"""
    <div class='header-box'>
        <div style='flex: 1; text-align: left;'>
            <div style='font-size: 24px; color: #38bdf8; font-weight: 900; letter-spacing: 1px;'>{display_game_name}</div>
            <div style='font-size: 18px; color: #cbd5e1; font-weight: bold; margin-top: 5px;'>{round_name} &nbsp;|&nbsp; बाउट नं: <span style='color: white; font-size:22px;'>{match_no}</span></div>
        </div>
        <div style='flex: 2; text-align: center;'>
            <h1 style='margin:0; font-size: 38px; color: white;'>🏆 {CONFIG['EVENT_TITLE_NP']} - लाइभ 🔴</h1>
            <div style='font-size: 20px; color: #facc15; margin-top: 5px;'>आयोजक: {CONFIG['ORGANIZER_NAME']} &nbsp; | &nbsp; आतिथ्यता: {CONFIG['HOST_NAME']}</div>
        </div>
        <div style='flex: 1; text-align: right;'>
            <div style='font-size: 20px; color: #e0e7ff; font-weight: bold;'>{now.strftime("%Y-%m-%d %I:%M %p")}</div>
            <div style='font-size: 18px; color: #fca5a5; font-weight: 900; margin-top: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>
                {p1[:15]} <span style="color:white; font-size:14px; background:#ef4444; padding:2px 8px; border-radius:10px;">V/S</span> {p2[:15]}
            </div>
        </div>
    </div>
""", unsafe_allow_html=True)

half = state.get('half', 1)
swap_sides = state.get('swap_sides', False)
op_left = p2 if swap_sides else p1
op_right = p1 if swap_sides else p2

left_team = op_right
right_team = op_left
score_left = state['score_a'] if left_team == p1 else state['score_b']
score_right = state['score_a'] if right_team == p1 else state['score_b']



def get_dod_dots(team):
    empties = state.get('empty_raids', {}).get(team, 0)
    return "⚪ ⚪" if empties == 0 else "🔴 ⚪" if empties == 1 else "🔴 🔴 (Do-or-Die)"

# 💡 जादु: खेलाडीको स्पष्ट अवस्था, ठूलो फन्ट र बाक्लो रंगिन धर्को
def get_roster_html(team, is_left, state):
    try:
        from utils.kabaddi_match import sort_kabaddi_players
        sorted_players = sort_kabaddi_players(team, state)
        
        roster_names = state.get('roster', {}).get(team, {})
        cards = state.get('cards', {}).get(team, {})
        out_players = state.get('out_players', {}).get(team, [])
        court_players = state.get('lineup', {}).get(team, {}).get('court', [])

        html = ""
        for p in sorted_players:
            s_p = str(p)
            name = roster_names.get(s_p, roster_names.get(int(p), "Unknown"))
            card = cards.get(s_p)
            
            bg_color, text_color, opacity, icon = "#334155", "#ffffff", "1", ""
            
            if card == 'Red':
                bg_color, icon = "#ef4444", "🟥"
            elif card == 'Yellow':
                bg_color, text_color, icon = "#eab308", "#000000", "🟨"
            elif p in out_players:
                bg_color, opacity, icon = "#64748b", "0.5", "❌"
            elif p in court_players:
                bg_color, icon = "#22c55e", "🏃"
            else:
                bg_color, icon = "#0ea5e9", "🪑"
                
            flex_dir = "row" if is_left else "row-reverse"
            icon_style = "background-color: #ffffff; border-radius: 4px; padding: 2px 4px; display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; box-shadow: 0 1px 2px rgba(0,0,0,0.3);"
            
            # 💡 जादु: टिम अनुसार नाम र आइकनको क्रम बदल्ने
            if is_left:
                # बायाँ टिम: [आइकन] [नाम]
                name_icon_html = f"<span style='{icon_style}'>{icon}</span><span style='text-transform: uppercase;'>{name}</span>"
            else:
                # दायाँ टिम: [नाम] [आइकन] (आइकन पछाडि गयो)
                name_icon_html = f"<span style='text-transform: uppercase;'>{name}</span><span style='{icon_style}'>{icon}</span>"
            
            html += f"<div style='background-color: {bg_color}; color: {text_color}; opacity: {opacity}; padding: 6px 10px; margin-bottom: 6px; border-radius: 6px; display: flex; flex-direction: {flex_dir}; justify-content: space-between; align-items: center; font-family: sans-serif; font-size: 15px; font-weight: bold; box-shadow: 0 2px 4px rgba(0,0,0,0.2);'>"
            html += f"<span style='display:flex; align-items:center; gap:8px;'>{name_icon_html}</span>"
            html += f"<span style='background: rgba(0,0,0,0.3); color: #ffffff; padding: 2px 8px; border-radius: 4px; font-size: 16px;'>{p}</span>"
            html += "</div>"
            
        return html
    except Exception as e:
        return f"<div style='color:red;'>Error: {str(e)}</div>"
    
# ==========================================
# ⏱️ स्कोरबोर्ड
# ==========================================
c_score_L, c_timer, c_score_R = st.columns([1.5, 1, 1.5])

active_r_team = state.get('raider_team') or state.get('next_raider_team') or left_team
l_role = "🏃 रेडर" if active_r_team == left_team else "🛡️ डिफेन्स"
l_role_bg = "#2563eb" if active_r_team == left_team else "#475569"
r_role = "🏃 रेडर" if active_r_team == right_team else "🛡️ डिफेन्स"
r_role_bg = "#dc2626" if active_r_team == right_team else "#475569"

def get_to_icons(team):
        used = state.get('timeouts', {}).get(str(half), {}).get(team, 0)
        return " ".join(["⏱️" if i < used else "⚪" for i in range(2)])

with c_score_L:
    st.markdown(f"""
        <div style='background:#1e293b; border-bottom:8px solid #2563eb; border-radius:15px; display:flex; height:160px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); overflow:hidden;'>
            <div style='flex:1; min-width:0; padding:15px 20px; display:flex; flex-direction:column; justify-content:center; align-items:flex-start;'>
                <div style='width:100%; overflow:hidden;'>
                    <marquee behavior="scroll" direction="left" scrollamount="6" style="width:100%;">
                        <h2 style='color:#93c5fd; margin:0; font-size:38px; white-space:nowrap;'>
                            {left_team} &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {left_team}
                        </h2>
                    </marquee>
                </div>
                <div style='display:flex; align-items:center; gap:15px; margin-top:10px;'>
                    <div style='background:{l_role_bg}; color:white; font-size:16px; font-weight:bold; padding:4px 15px; border-radius:15px; box-shadow:0 2px 5px rgba(0,0,0,0.3);'>{l_role}</div>
                    <div style='font-size:16px; color:#cbd5e1; font-weight:bold;'>T/O: {get_to_icons(left_team)}</div>
                </div>
            </div>
            <div style='width:140px; min-width:140px; flex-shrink:0; background:rgba(0,0,0,0.3); display:flex; justify-content:center; align-items:center; font-size:85px; font-weight:900; color:white; border-left:3px solid rgba(255,255,255,0.05); text-shadow: 3px 3px 6px rgba(0,0,0,0.8);'>
                {score_left}
            </div>
        </div>
    """, unsafe_allow_html=True)

with c_timer:
    timer_seconds = state.get('timer_seconds', 1200)
    half_val = state.get('half', 1)
    mid = "tv_live"
    
    st.components.v1.html(f"""
        <div style="text-align:center; font-family:'Courier New', monospace; background:#0f172a; padding:10px; border-radius:15px; border:2px solid #334155;">
            <div style="color:#94a3b8; font-size:18px; font-weight:bold; margin-bottom:5px;">HALF {half_val}</div>
            <div id="main_timer" style="font-size:65px; font-weight:900; color:#facc15; text-shadow: 0 0 20px rgba(250,204,21,0.4); line-height:1;">
                <span id="min">00</span>:<span id="sec">00</span>
            </div>
            <div id="to_box" style="display:{'block' if state.get('timeout_active') else 'none'}; margin-top:10px; font-size:22px; color:#ef4444; font-weight:bold; background:#fee2e2; padding:5px; border-radius:10px; border:2px solid #fca5a5; animation: pulse 1s infinite;">
                ⏳ TIMEOUT: <span id="to_sec">30</span>s
            </div>
            <div id="raid_box" style="margin-top:10px; display:{'block' if state.get('raider_team') and not state.get('timeout_active') else 'none'};">
                <span style="font-size:30px; color:#ffffff; font-weight:900; background:#dc2626; padding:5px 25px; border-radius:30px; border:3px solid #f87171; box-shadow: 0 0 15px rgba(220,38,38,0.5);">
                    🏃 <span id="r_sec">30</span>s
                </span>
            </div>
        </div>
        <script>
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            function whistle(freq, dur) {{
                if(audioCtx.state === 'suspended') audioCtx.resume();
                const osc = audioCtx.createOscillator(); const gain = audioCtx.createGain();
                osc.type = 'triangle'; osc.frequency.value = freq; gain.gain.value = 0.1;
                osc.connect(gain); gain.connect(audioCtx.destination);
                osc.start(); setTimeout(() => osc.stop(), dur);
            }}
            let py_s = {timer_seconds}; 
            let s = parseInt(sessionStorage.getItem('kb_s_{mid}'));
            if (isNaN(s) || Math.abs(s - py_s) > 3) s = py_s;
            let t = parseInt(sessionStorage.getItem('kb_t_{mid}')) || 30;
            let r = parseInt(sessionStorage.getItem('kb_r_{mid}')) || 30;
            let running = {'true' if state.get('timer_running') else 'false'};
            let is_to = {'true' if state.get('timeout_active') else 'false'};
            let is_raid = {'true' if state.get('raider_team') else 'false'};

            function update() {{ 
                if(running && s > 0) {{ 
                    s--; sessionStorage.setItem('kb_s_{mid}', s);
                    if(s <= 5 && s > 0) whistle(400, 200); 
                    if(s === 0) whistle(300, 1500); 
                }}
                if(is_to && t > 0) {{ 
                    t--; sessionStorage.setItem('kb_t_{mid}', t);
                    if(t === 0) whistle(800, 800); 
                }} else if (!is_to) {{ t = 30; sessionStorage.setItem('kb_t_{mid}', 30); }}

                if(is_raid && !is_to && r > 0 && running) {{ 
                    r--; sessionStorage.setItem('kb_r_{mid}', r);
                    if(r <= 3 && r > 0) whistle(1000, 100); 
                }} else if (!is_raid) {{ r = 30; sessionStorage.setItem('kb_r_{mid}', 30); }}

                document.getElementById('min').innerText = Math.floor(s/60).toString().padStart(2, '0'); 
                document.getElementById('sec').innerText = (s%60).toString().padStart(2, '0'); 
                document.getElementById('to_sec').innerText = t;
                document.getElementById('r_sec').innerText = r;
            }}
            if(window.kbInterval) clearInterval(window.kbInterval);
            window.kbInterval = setInterval(update, 1000); update(); 
        </script>
        <style>@keyframes pulse {{ 0% {{ opacity: 1; }} 50% {{ opacity: 0.7; }} 100% {{ opacity: 1; }} }}</style>
    """, height=220)

    # 💡 जादु: ठूलो आइकन र म्यासेज बक्स
    if state.get('last_event_msg'):
        icon_tag = ""
        if state.get('last_event_icon'):
            b64_str = get_cached_base64_image(state['last_event_icon'])
            if b64_str:
                icon_cls = "event-highlight-icon"
                dir_icons = ["KB_start_raid.png", "KB_raider_out.png", "KB_bonus_point.png", "KB_do_or_die.png"]
                if state['last_event_icon'] in dir_icons and (active_r_team == right_team):
                    icon_cls += " flip-horizontal"
                # 🖼️ उचाइ १२०px बनाइयो
                icon_tag = f"<img class='{icon_cls}' src='data:image/png;base64,{b64_str}' style='height: 120px; width: auto; filter: drop-shadow(0 0 15px rgba(255,255,255,0.4));'>"
        
        # 📦 बक्सलाई घडीको ठीक तल तन्काइयो (margin-top हटाइयो र padding बढाइयो)
        st.markdown(f"""
            <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; background: rgba(30, 41, 59, 0.95); border: 3px solid #facc15; padding: 20px; border-radius: 15px; box-shadow: 0 10px 25px rgba(0,0,0,0.6); animation: popIn 0.3s ease-out; margin-top: -10px; z-index: 10;">
                {icon_tag}
                <div style="font-size: 26px; font-weight: 900; color: white; text-align: center; line-height: 1.2; text-shadow: 2px 2px 5px rgba(0,0,0,0.8);">
                    {state['last_event_msg']}
                </div>
            </div>
            <style>
                .flip-horizontal {{ transform: scaleX(-1); }}
                @keyframes popIn {{ from {{ opacity: 0; transform: scale(0.8); }} to {{ opacity: 1; transform: scale(1); }} }}
            </style>
        """, unsafe_allow_html=True)

with c_score_R:
    st.markdown(f"""
        <div style='background:#1e293b; border-bottom:8px solid #dc2626; border-radius:15px; display:flex; height:160px; box-shadow: 0 5px 15px rgba(0,0,0,0.5); overflow:hidden;'>
            <div style='width:140px; min-width:140px; flex-shrink:0; background:rgba(0,0,0,0.3); display:flex; justify-content:center; align-items:center; font-size:85px; font-weight:900; color:white; border-right:3px solid rgba(255,255,255,0.05); text-shadow: 3px 3px 6px rgba(0,0,0,0.8);'>
                {score_right}
            </div>
            <div style='flex:1; min-width:0; padding:15px 20px; display:flex; flex-direction:column; justify-content:center; align-items:flex-end;'>
                <div style='width:100%; overflow:hidden;'>
                    <marquee behavior="scroll" direction="left" scrollamount="6" style="width:100%;">
                        <h2 style='color:#fca5a5; margin:0; font-size:38px; white-space:nowrap;'>
                            {right_team} &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; {right_team}
                        </h2>
                    </marquee>
                </div>
                <div style='display:flex; align-items:center; gap:15px; margin-top:10px;'>
                    <div style='font-size:16px; color:#cbd5e1; font-weight:bold;'>T/O: {get_to_icons(right_team)}</div>
                    <div style='background:{r_role_bg}; color:white; font-size:16px; font-weight:bold; padding:4px 15px; border-radius:15px; box-shadow:0 2px 5px rgba(0,0,0,0.3);'>{r_role}</div>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🤼 कबड्डी कोर्ट (विथ रोस्टर स्क्रोलिङ)
# ==========================================
l1 = state.get('lineup', {}).get(left_team, {})
l2 = state.get('lineup', {}).get(right_team, {})
c_left, c_right = l1.get('court', []), l2.get('court', [])
b_left, b_right = l1.get('bench', []), l2.get('bench', [])
out_left = state.get('out_players', {}).get(left_team, [])
out_right = state.get('out_players', {}).get(right_team, [])

raider_team = state.get('raider_team')
tv_is_attacking_right = (raider_team == left_team)
r_pos = state.get('raid_pos', 0)
baulk_c = state.get('baulk_crossed', False)
bonus_c = state.get('bonus_crossed', False)

is_mid_crossed = state.get('midline_crossed', False) 
c_mid = "#ef4444" if is_mid_crossed else "rgba(255,255,255,0.8)"
shadow_mid = f"0 0 15px {c_mid}" if is_mid_crossed else "none"

c_baulk_l, c_bonus_l = "white", "white"
c_baulk_r, c_bonus_r = "white", "white"

if not tv_is_attacking_right:
    if r_pos >= 2 or baulk_c: c_baulk_l = "#22c55e"
    if r_pos >= 3 or bonus_c: c_bonus_l = "#22c55e" 
else:
    if r_pos >= 2 or baulk_c: c_baulk_r = "#22c55e"
    if r_pos >= 3 or bonus_c: c_bonus_r = "#22c55e" 

pos_a = {0:("15%","20%"), 1:("25%","35%"), 2:("35%","50%"), 3:("25%","65%"), 4:("15%","80%"), 5:("10%","35%"), 6:("10%","65%")}
pos_b = {0:("85%","20%"), 1:("75%","35%"), 2:("65%","50%"), 3:("75%","65%"), 4:("85%","80%"), 5:("90%","35%"), 6:("90%","65%")}

def get_sitting_block_html(team, out_list):
    slots_html = ""
    eligible_idx = -1
    for i, p in enumerate(out_list):
        if state['cards'].get(team, {}).get(p) != 'Yellow':
            eligible_idx = i; break
    for i in range(7):
        if i < len(out_list):
            icon = "✨" if i == eligible_idx else ""
            slots_html += f'<div class="sit-slot sit-filled">{out_list[i]}<span class="revive-icon">{icon}</span></div>'
        else: slots_html += '<div class="sit-slot"></div>'
    return f'<div class="sitting-block">{slots_html}</div>'

def make_dot(team, num, is_court=True, idx=-1, is_left=True):
    if is_court and num in state['out_players'].get(team, []): return ""
    if state['cards'].get(team, {}).get(num) == 'Red':
        return f'<div class="p-dot p-dot-bench bg-out">{num}</div>' if not is_court else ""

    cls = ["p-dot" if is_court else "p-dot p-dot-bench"]
    bg_class = "bg-blue" if team == p1 else "bg-red"
    if state['cards'].get(team, {}).get(num) == 'Yellow':
        if time() - state.get('yc_timers', {}).get(team, {}).get(num, 0) >= 120: bg_class = "bg-green"
    cls.append(bg_class)

    if num == state['lineup'].get(team, {}).get('captain'): cls.append("captain-dot")

    is_raider = (raider_team == team and state.get('raider_num') == num)
    if is_raider:
        cls.append("raider-dod" if state['empty_raids'].get(team, 0) >= 2 else "raider-normal")
    if num in state.get('selected_targets', []) and team != raider_team:
        cls.append("target-active")

    style = ""
    if is_court:
        if is_raider:
            if tv_is_attacking_right:
                style_pos = ["left:45%; top:50%;", "left:55%; top:50%;", "left:70%; top:50%;", "left:88%; top:50%;"][min(r_pos, 3)]
            else:
                style_pos = ["left:55%; top:50%;", "left:45%; top:50%;", "left:30%; top:50%;", "left:12%; top:50%;"][min(r_pos, 3)]
        else:
            pos = pos_a if is_left else pos_b
            style_pos = f"left:{pos[idx][0]}; top:{pos[idx][1]};"
        style = style_pos

    return f'<div class="{" ".join(cls)}" style="{style}">{num}</div>'

# 🟨 पहेँलो कार्डको टाइमर बक्स
yc_html = "<div style='display:flex; justify-content:space-between; width:100%; margin: 0 auto; padding: 0 10px;'>"

def get_yc_box(team):
    box_html = "<div style='display:flex; gap:10px;'>"
    for yp, st_time in state.get('yc_timers', {}).get(team, {}).items():
        
        # 💡 जादु: जर्सी नम्बर स्ट्रिङ होस् या नम्बर, दुवै तरिकाले चेक गर्ने!
        s_yp = str(yp)
        cards_dict = state.get('cards', {}).get(team, {})
        c_val = cards_dict.get(s_yp) or cards_dict.get(int(yp) if s_yp.isdigit() else 0)
        
        # यदि पहेँलो कार्ड होइन भने नदेखाउने
        if c_val != 'Yellow': continue
        
        # बाँकी समय निकाल्ने
        from time import time
        rem = max(0, 120 - int(time() - st_time))
        
        # रङ्ग र म्यासेज मिलाउने
        color = "#fde047" if rem > 0 else "#22c55e"
        txt = f"{rem//60:02d}:{rem%60:02d}" if rem > 0 else "✅ भित्र पठाउनुहोस्"
        
        box_html += f"<div style='background:{color}; color:black; padding:5px 15px; border-radius:8px; font-weight:bold; border:3px solid #334155; font-size:18px; box-shadow:0 5px 10px rgba(0,0,0,0.5);'>🟨 जर्सी {yp} ⏳ {txt}</div>"
    
    return box_html + "</div>"


# ==========================================
# 🤼 कबड्डी कोर्ट (विथ नयाँ रङ्गीन रोस्टर र कन्टिन्यू मार्क्यू)
# ==========================================
yc_html += get_yc_box(left_team) + get_yc_box(right_team) + "</div>"

html = yc_html + '<div class="kb-arena">'

# 💡 मार्क्यूलाई निरन्तर बनाउन खेलाडीको लिस्टलाई छुट्टै भेरिएबलमा तान्ने
left_roster = get_roster_html(left_team, True, state)
right_roster = get_roster_html(right_team, False, state)

# ✅ बायाँ (Left) टिमको निरन्तर लिस्ट
html += '<div class="roster-scroll">'
html += '<div class="roster-title">PLAYERS</div>'
html += '<marquee direction="up" scrollamount="3" style="height:100%; padding-right:5px;">'
html += left_roster + "<div style='height: 50px;'></div>" + left_roster 
html += '</marquee></div>'

# बायाँ बेन्च र आउट
html += f'<div class="kb-bench">{"".join([make_dot(left_team, n, False) for n in b_left])}<div class="bench-title">BENCH</div></div>'
html += get_sitting_block_html(left_team, out_left)

# मुख्य कोर्ट
html += '<div class="kb-court">'
html += f'<div class="mid-line" style="background-color:{c_mid}; box-shadow:{shadow_mid};"></div>'
html += f'<div class="baulk-line-left" style="background-color:{c_baulk_l}; box-shadow:0 0 15px {c_baulk_l};"></div>'
html += f'<div class="bonus-line-left" style="border-left-color:{c_bonus_l}; box-shadow:-5px 0 15px {c_bonus_l};"></div>'
html += f'<div class="baulk-line-right" style="background-color:{c_baulk_r}; box-shadow:0 0 15px {c_baulk_r};"></div>'
html += f'<div class="bonus-line-right" style="border-right-color:{c_bonus_r}; box-shadow:5px 0 15px {c_bonus_r};"></div>'

html += "".join([make_dot(left_team, n, True, i, True) for i, n in enumerate(c_left)])
html += "".join([make_dot(right_team, n, True, i, False) for i, n in enumerate(c_right)])
html += '</div>'

# दायाँ आउट र बेन्च
html += get_sitting_block_html(right_team, out_right)
html += f'<div class="kb-bench">{"".join([make_dot(right_team, n, False) for n in b_right])}<div class="bench-title">BENCH</div></div>'

# ✅ दायाँ (Right) टिमको निरन्तर लिस्ट
html += '<div class="roster-scroll">'
html += '<div class="roster-title">PLAYERS</div>'
html += '<marquee direction="up" scrollamount="3" style="height:100%; padding-left:5px;">'
html += right_roster + "<div style='height: 50px;'></div>" + right_roster 
html += '</marquee></div>'

# मुख्य एरिना बन्द गर्ने
html += '</div>' 

# अन्तिममा रेन्डर गर्ने
st.markdown(html, unsafe_allow_html=True)

# ==========================================================
# 🎉 जादु: टिभीमा सेलिब्रेसन र 'अर्को यात्रा'
# ==========================================================
import psycopg2.extras

try:
    cel = state.get('tv_celebration') or {}
    if cel.get('show'):
        is_match_win = "CHAMPION" in str(cel.get('title', '')).upper()
        if st.session_state.get('kb_last_cel_type') != cel.get('title'):
            st.balloons()
            if is_match_win: st.snow() 
            st.session_state['kb_last_cel_type'] = cel.get('title')

        next_journey_html = ""
        if is_match_win:
            try:
                conn = db.get_connection(); c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                p1_name = list(state.get('roster', {}).keys())[0] if state.get('roster') else ""
                c.execute("SELECT * FROM matches WHERE status='Completed' AND (p1_name=%s OR p2_name=%s) ORDER BY match_no DESC LIMIT 1", (p1_name, p1_name))
                cur_m = c.fetchone()
                
                if cur_m:
                    c.execute("SELECT * FROM matches WHERE event_code=%s", (cur_m['event_code'],))
                    nxt_m = next((x for x in c.fetchall() if x.get('source_match1') == cur_m['match_no'] or x.get('source_match2') == cur_m['match_no']), None)
                    if nxt_m:
                        def cln_nm(n): return re.sub(r'[\u0900-\u097F]+|\(\s*\)', '', str(n)).strip()
                        opp_name = nxt_m.get('p1_name') if "Winner" not in str(nxt_m.get('p1_name')) and cln_nm(cel.get('winner')) not in str(nxt_m.get('p1_name')) else nxt_m.get('p2_name') if "Winner" not in str(nxt_m.get('p2_name')) and cln_nm(cel.get('winner')) not in str(nxt_m.get('p2_name')) else None
                        
                        if opp_name: nj_txt = f"Next Match: #{nxt_m['match_no']} ({nxt_m['round_name']}) vs {cln_nm(opp_name)}"
                        else: nj_txt = f"Next Match: #{nxt_m['match_no']} ({nxt_m['round_name']}) vs Winner of #{nxt_m.get('source_match2') if nxt_m.get('source_match1') == cur_m['match_no'] else nxt_m.get('source_match1')}"
                    else: nj_txt = "Tournament Champion! 🏆"
                    next_journey_html = f"<div style='background:#10b981; color:white; padding:10px 40px; border-radius:30px; font-size:35px; font-weight:bold; margin-top:20px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); border:3px solid white;'>⏭️ {nj_txt}</div>"
                c.close(); conn.close()
            except Exception as e: pass

        bg_color, trophy_size, title_size = ("rgba(15, 23, 42, 0.95)", "150px", "80px") if is_match_win else ("rgba(15, 23, 42, 0.85)", "100px", "60px")
        st.markdown(f"""
        <div style='position:fixed; top:0; left:0; width:100vw; height:100vh; background:{bg_color}; z-index:99999; display:flex; flex-direction:column; justify-content:center; align-items:center; backdrop-filter: blur(10px);'>
            <div style='font-size:{trophy_size}; animation: bounce 1s infinite;'>🏆</div>
            <h1 style='font-size:{title_size}; color:#facc15; font-weight:900; margin:10px 0; text-shadow: 0 10px 30px rgba(250,204,21,0.6); text-align:center;'>{cel.get('title')}</h1>
            <h2 style='font-size:120px; color:white; font-weight:900; margin:0; text-transform:uppercase; letter-spacing:4px; text-shadow: 4px 4px 15px black; text-align:center;'>{cel.get('winner')}</h2>
            <div style='background:#ef4444; padding:20px 60px; border-radius:50px; border:5px solid white; margin-top:30px; box-shadow: 0 10px 20px rgba(0,0,0,0.5); text-align:center;'>
                <span style='font-size:50px; color:white; font-weight:bold;'>SCORE: {cel.get('score')}</span>
            </div>
            {next_journey_html}
        </div>
        <style> @keyframes bounce {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-30px); }} }} </style>
        """, unsafe_allow_html=True)
except Exception as e: pass