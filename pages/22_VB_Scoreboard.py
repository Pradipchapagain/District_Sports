import streamlit as st
import pandas as pd
import json
import os
import database as db
import utils.live_state as ls
from streamlit_autorefresh import st_autorefresh
from config import CONFIG
from datetime import datetime

# ⚙️ १. पेज सेटिङ र अटो-रिफ्रेस
st.set_page_config(page_title="Volleyball Live TV", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=1000, key="vb_sb_refresh")

# 🎨 २. अल्ट्रा-क्लिन मास्टर CSS (सबै मर्ज गरिएको)
st.markdown("""
    <style>
        /* =========================================
           १. स्ट्रिमलिटका सबै डिस्टर्ब गर्ने कुराहरू हटाउने 
           ========================================= */
        [data-testid="stSidebar"], [data-testid="stSidebarNav"], .st-emotion-cache-16idsys {
            display: none !important;
            width: 0px !important;
        }
        header, [data-testid="stHeader"] {
            display: none !important;
        }
        #MainMenu, footer {
            visibility: hidden !important;
            display: none !important;
        }
        
        /* =========================================
           २. पेजलाई फुल-स्क्रिन बनाउने (Padding & Margin Zero) 
           ========================================= */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 2rem !important;
            padding-right: 2rem !important;
            max-width: 100% !important;
            margin-top: 0px !important;
            background-color: #0f172a;
        }
        html, body, [data-testid="stAppViewContainer"], .main {
            background-color: #0E1117;
            overflow: hidden; /* स्क्रोलबार हटाउने */
            height: 100vh;
            margin: 0px !important;
            padding: 0px !important;
        }

        /* =========================================
           ३. भलिबलको आफ्नै कस्टम डिजाइन (Positioning Fixes) 
           ========================================= */
        .header-container { position: relative; width: 100%; margin-bottom: 20px; }
        .header-box { text-align: center; background: linear-gradient(90deg, #1e293b, #0f172a, #1e293b); padding: 15px; border-bottom: 4px solid #ef4444; border-radius: 0 0 20px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); margin: 0px 0px 15px 0px !important; }
        .match-info-badge { position: absolute; top: 15px; right: 20px; background: rgba(30, 41, 59, 0.9); padding: 8px 15px; border-radius: 10px; color: #fbbf24; font-weight: bold; border: 1px solid #475569; font-family: monospace; font-size: 14px; text-align: right; }

        /* 🏐 Court & Players */
        .court-wrapper { display: flex; flex-direction: row; gap: 15px; align-items: flex-end; justify-content: center; height: 360px; margin-top: 10px; }
        .bench-area { display: flex; flex-direction: column; gap: 6px; background: #1e293b; padding: 10px; border-radius: 10px; min-width: 55px; align-items: center; border: 2px solid #334155; box-shadow: inset 0 0 10px rgba(0,0,0,0.5); }
        .vb-court-vertical { width: 240px; height: 350px; background-color: #f17b37; border: 4px solid white; border-top: 8px solid #3b82f6; position: relative; }
        .attack-line { position: absolute; top: 33.33%; left: 0; right: 0; border-top: 3px dashed rgba(255,255,255,0.8); }
        
        .p-dot { position: absolute; width: 44px; height: 44px; border-radius: 50%; background: white; color: black; font-weight: bold; font-size: 18px; display: flex; justify-content: center; align-items: center; transform: translate(-50%, -50%); border: 3px solid #1e293b; z-index: 5; }
        .p-dot-bench { position: relative; width: 34px; height: 34px; font-size: 14px; margin-bottom: 2px; }
        .libero { background-color: #fbbf24 !important; border-color: #b45309 !important; }
        .captain { border: 4px double #1e293b !important; text-decoration: underline; }
        .serving-dot { border-color: #fbbf24 !important; box-shadow: 0 0 15px #fbbf24, inset 0 0 5px #fbbf24 !important; }
        
        /* 📜 Scrolling Roster */
        .scroll-container { height: 260px; overflow: hidden; background: #0f172a; border-radius: 12px; border: 2px solid #334155; padding: 10px; margin-top: 15px; }
        .scroll-content { display: flex; flex-direction: column; gap: 8px; animation: scrollUp 20s linear infinite; }
        @keyframes scrollUp { 0% { transform: translateY(100%); } 100% { transform: translateY(-120%); } }
        .roster-row { display: flex; align-items: center; gap: 10px; padding: 6px; background: rgba(255,255,255,0.03); border-radius: 8px; border-left: 4px solid transparent; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 📡 ३. डाटा तान्ने (Unified State)
# ==========================================
vb_data = ls._get_state("vb_live_match") 

if not vb_data:
    st.markdown("<div style='text-align:center; margin-top:20vh;'><h1 style='font-size:80px; color:#334155;'>🏐 COURT IDLE</h1><p style='color:#475569; font-size:24px;'>Waiting for match data...</p></div>", unsafe_allow_html=True)
    st.stop()

# 💡 सुझाव ३: JSON डिकोडिङ (यदि आवश्यक छ भने)
m_state = vb_data.get('state_json', {})
if isinstance(m_state, str): m_state = json.loads(m_state)

best_of = m_state.get('settings', {}).get('best_of', 3)
target_pts = m_state.get('settings', {}).get('points_per_set', 25)
c_set = m_state.get('current_set', 1)
actual_target = 15 if (c_set == best_of) else target_pts
serving_team = vb_data.get('serving')

# ==========================================
# 🎨 ४. प्लेयर रेन्डर हेल्पर (Portable Logic)
# ==========================================
# 💡 सुझाव २: 'serving' लाई प्यारामिटरको रूपमा पठाइएको छ
def get_player_dot_html(num, team_name, current_serving_team, is_court=True, pos_idx=-1):
    lineup = m_state.get('lineup', {}).get(team_name, {})
    cards = m_state.get('cards', {}).get(team_name, {})
    roster = m_state.get('roster', {}).get(team_name, {})
    
    cls = ["p-dot"]
    if not is_court: cls.append("p-dot-bench")
    if num in lineup.get('libero', []): cls.append("libero")
    if num == lineup.get('captain'): cls.append("captain")
    
    # सर्भिसिङ टिम र प्लेयर पोजिसन चेक
    is_srv_side = (current_serving_team == ('A' if team_name == vb_data.get('team_a') else 'B'))
    if is_court and is_srv_side and pos_idx == 0: cls.append("serving-dot")

    pos_v = { 0: ("80%", "85%"), 1: ("80%", "20%"), 2: ("50%", "20%"), 3: ("20%", "20%"), 4: ("20%", "85%"), 5: ("50%", "65%") }
    style = f"left:{pos_v[pos_idx][0]}; top:{pos_v[pos_idx][1]};" if is_court else ""
    
    card_html = ""
    if num in cards:
        card_html = f'<div style="position:absolute; top:-5px; right:-5px; width:12px; height:18px; background:{"#ef4444" if cards[num]=="Red" else "#fbbf24"}; border:1px solid black; border-radius:2px;"></div>'
    
    return f'<div class="{" ".join(cls)}" style="{style}" title="{roster.get(num, "Player")}">{num}{card_html}</div>'

# 💡 सुझाव ४: टाइमआउटको लागि सर्कल UI
def get_to_dots(count, color):
    return "".join([f"<div style='width:12px; height:12px; background:{color if i<=count else 'transparent'}; border:2px solid {color}; border-radius:50%; display:inline-block; margin:0 3px;'></div>" for i in range(1, 3)])

# ==========================================
# 📊 ५. मुख्य डिस्प्ले रेन्डर
# ==========================================
st.markdown(f"""
    <div class="header-container">
        <div class="header-box">
            <h2 style="color:white; margin:0;">🏆 {CONFIG['EVENT_TITLE_NP']}</h2>
            <div style="color:#fbbf24; font-size:18px;">{vb_data.get('match_title', 'Volleyball Match')}</div>
        </div>
        <div class="match-info-badge">
            SET {c_set} | BEST OF {best_of}<br>
            TARGET: {actual_target} PTS
        </div>
    </div>
""", unsafe_allow_html=True)

ca, cmid, cb = st.columns([3.5, 2.2, 3.5])

# 🔴 TEAM A
with ca:
    srv_a = " 🏐" if serving_team == 'A' else ""
    st.markdown(f"""
    <div style='background:#1e293b; padding:20px; border-radius:20px; border-bottom:10px solid #dc2626; color:white; text-align:center;'>
        <h2 style='margin:0;'>{vb_data['team_a']}{srv_a}</h2>
        <div style='display:flex; justify-content:center; align-items:center; gap:25px;'>
            <div style='font-size:14px; color:#94a3b8;'>T/O<br>{get_to_dots(vb_data['timeout_a'], '#ef4444')}</div>
            <div style='font-size:140px; font-weight:bold; color:#fca5a5;'>{vb_data['score_a']}</div>
        </div>
        <div class="court-wrapper">
            <div class="bench-area">{"".join([get_player_dot_html(n, vb_data['team_a'], serving_team, False) for n in m_state.get('lineup', {}).get(vb_data['team_a'], {}).get('bench', [])])}</div>
            <div class="vb-court-vertical"><div class="attack-line"></div>
                {"".join([get_player_dot_html(n, vb_data['team_a'], serving_team, True, i) for i, n in enumerate(m_state.get('lineup', {}).get(vb_data['team_a'], {}).get('court', []))])}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# 🏆 MIDDLE (Sets & Roster)
with cmid:
    st.markdown(f"""
    <div style='text-align:center; background:#1e293b; padding:15px; border-radius:15px; border:2px solid #334155;'>
        <div style='color:#94a3b8; font-size:14px;'>SETS WON</div>
        <span style='font-size:55px; font-weight:bold; color:#fca5a5;'>{vb_data['sets_a']}</span>
        <span style='font-size:35px; color:#475569;'> - </span>
        <span style='font-size:55px; font-weight:bold; color:#93c5fd;'>{vb_data['sets_b']}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # Scrolling Roster Logic
    lineup_a = m_state.get('lineup', {}).get(vb_data['team_a'], {})
    lineup_b = m_state.get('lineup', {}).get(vb_data['team_b'], {})
    roster_a = m_state.get('roster', {}).get(vb_data['team_a'], {})
    roster_b = m_state.get('roster', {}).get(vb_data['team_b'], {})

    def build_roster_rows(team_name, players, roster_dict, color):
        rows = f"<div style='color:{color}; font-weight:bold; text-align:center; border-bottom:1px solid #334155; margin-bottom:5px;'>{team_name}</div>"
        for p in players:
            rows += f'<div class="roster-row" style="border-left-color:{color}; color:white; font-size:14px;">#{p} {roster_dict.get(p, "Player")}</div>'
        return rows

    all_roster_html = build_roster_rows(vb_data['team_a'], lineup_a.get('court', []) + lineup_a.get('bench', []), roster_a, '#fca5a5')
    all_roster_html += build_roster_rows(vb_data['team_b'], lineup_b.get('court', []) + lineup_b.get('bench', []), roster_b, '#93c5fd')

    st.markdown(f"""<div class="scroll-container"><div class="scroll-content">{all_roster_html}</div></div>""", unsafe_allow_html=True)

# 🔵 TEAM B
with cb:
    srv_b = " 🏐" if serving_team == 'B' else ""
    st.markdown(f"""
    <div style='background:#1e293b; padding:20px; border-radius:20px; border-bottom:10px solid #2563eb; color:white; text-align:center;'>
        <h2 style='margin:0;'>{srv_b}{vb_data['team_b']}</h2>
        <div style='display:flex; justify-content:center; align-items:center; gap:25px;'>
            <div style='font-size:140px; font-weight:bold; color:#93c5fd;'>{vb_data['score_b']}</div>
            <div style='font-size:14px; color:#94a3b8;'>T/O<br>{get_to_dots(vb_data['timeout_b'], '#3b82f6')}</div>
        </div>
        <div class="court-wrapper">
            <div class="vb-court-vertical"><div class="attack-line"></div>
                {"".join([get_player_dot_html(n, vb_data['team_b'], serving_team, True, i) for i, n in enumerate(m_state.get('lineup', {}).get(vb_data['team_b'], {}).get('court', []))])}
            </div>
            <div class="bench-area">{"".join([get_player_dot_html(n, vb_data['team_b'], serving_team, False) for n in m_state.get('lineup', {}).get(vb_data['team_b'], {}).get('bench', [])])}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)