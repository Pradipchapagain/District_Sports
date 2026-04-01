# pages/22_VB_Scoreboard.py
import streamlit as st
import pandas as pd
import json
import utils.live_state as ls
from streamlit_autorefresh import st_autorefresh
from config import CONFIG
import time

# ==========================================
# 📺 जादु: साइडबार र माथिको मेनु पूर्ण रूपमा लुकाउने
# ==========================================
st.markdown("""
    <style>
        /* साइडबारलाई पूरै गायब पार्ने */
        [data-testid="stSidebar"] {
            display: none !important;
        }
        /* साइडबार खोल्ने सानो तीर (Arrow) लुकाउने */
        [data-testid="collapsedControl"] {
            display: none !important;
        }
        /* माथिको खाली भाग र मेनु (Header) लुकाउने */
        [data-testid="stHeader"] {
            display: none !important;
        }
        /* तल र माथिको खाली ठाउँ (Padding) हटाएरक्क स्क्रिनभरि बनाउने */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 1rem !important;
            max-width: 100% !important;
        }
    </style>
""", unsafe_allow_html=True)

# ⚙️ १. पेज सेटिङ
st.set_page_config(page_title="VB Live Pro", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=1000, key="vb_sb_refresh")

# 🎨 २. अल्ट्रा-प्रो डार्क थिम CSS
st.markdown("""
    <style>
        /* 💡 १. स्ट्रीमलिटको हेडरलाई जरैदेखि उखेल्ने (Nuclear Option) */
        header[data-testid="stHeader"] {
            display: none !important;
            visibility: hidden !important;
        }
        
        /* 💡 २. मुख्य कन्टेनरको प्याडिङ शून्य बनाएर जबर्जस्ती माथि तान्ने */
        .main .block-container {
            padding-top: 0px !important;
            margin-top: -85px !important; /* <--- जादु यहाँ छ! यदि धेरै माथि गयो भने -85px लाई -70px बनाउनुहोला */
            padding-bottom: 0px !important;
            max-width: 100% !important;
            background-color: #0f172a;
            font-family: 'Inter', sans-serif;
        }

        /* 💡 ३. स्ट्रीमलिटले भित्र लुकाएर राख्ने अर्को खाली ठाउँलाई पनि हान्ने */
        div[data-testid="stAppViewBlockContainer"] {
            padding-top: 0px !important;
        }
        
        [data-testid="stAppViewContainer"] > .main {
            padding-top: 0px !important;
        }
        
        html, body { 
            background-color: #0f172a; 
            overflow: hidden; 
            height: 100vh; 
            margin: 0; 
            padding: 0; 
        }
        
        /* 💡 जादु: 'margin-top: -45px' ले अदृश्य ग्यापलाई जबरजस्ती माथि तानिदिन्छ! */
        .block-container { 
            padding-top: 0rem !important; 
            padding-bottom: 0rem !important; 
            margin-top: -45px !important; 
            max-width: 100% !important; 
            background-color: #0f172a; 
            font-family: 'Inter', sans-serif; 
        }
        
        
        html, body { background-color: #0f172a; overflow: hidden; height: 100vh; }

        .top-header { display: flex; justify-content: space-between; align-items: center; background: #1e293b; padding: 6px 20px; border-radius: 12px; border-bottom: 2px solid #facc15; margin-bottom: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.3); }
        .header-title { color: white; font-size: 20px; font-weight: bold; margin: 0; display: flex; align-items: center; gap: 10px; }
        .header-stats { color: #facc15; font-size: 16px; font-weight: bold; display: flex; gap: 20px; align-items: center; }
        .clock-box { background: black; padding: 4px 12px; border-radius: 20px; border: 1px solid #facc15; font-family: monospace; font-size: 18px; }

        .side-panel { background: rgba(30, 41, 59, 0.6); border-radius: 16px; border: 1px solid #334155; padding: 10px; height: 490px; display: flex; flex-direction: column; overflow: hidden; }
        .team-name-box { text-align: center; color: white; font-size: 16px; font-weight: 900; margin-bottom: 4px; text-transform: uppercase; white-space: nowrap; overflow: hidden; }
        .big-score-box { text-align: center; background: #0f172a; border-radius: 12px; margin-bottom: 6px; padding: 8px; }
        .big-score { font-size: 65px; font-weight: 900; color: #facc15; line-height: 1; text-shadow: 2px 2px 10px rgba(250, 204, 21, 0.2); }
        .stats-row { display: flex; justify-content: space-between; font-size: 11px; color: #94a3b8; font-weight: bold; padding: 0 5px; margin-top: 4px; }
        
        .roster-list { flex: 1; overflow: hidden; } 
        .roster-card { padding: 4px 8px; border-radius: 6px; margin-bottom: 3px; font-size: 12px; display: flex; justify-content: space-between; align-items: center; border-left: 4px solid transparent; }
        
        /* 💡 ५ वटा प्रस्ट रङहरू (नयाँ: निष्कासित खेलाडीको लागि) */
        .playing-status { background: rgba(34, 197, 94, 0.15) !important; border-left-color: #22c55e !important; color: #e2e8f0; } 
        .libero-status { background: rgba(234, 88, 12, 0.4) !important; border-left-color: #ea580c !important; color: #ffedd5 !important; font-weight: bold; } 
        .replaced-status { background: rgba(168, 85, 247, 0.25) !important; border-left-color: #a855f7 !important; color: #e9d5ff; font-weight: bold; } 
        .bench-status { background: rgba(100, 116, 139, 0.1) !important; border-left-color: #475569 !important; color: #94a3b8; } 
        .expelled-status { background: rgba(239, 68, 68, 0.15) !important; border-left-color: #ef4444 !important; color: #fca5a5; opacity: 0.8; text-decoration: line-through; } /* 🚨 निष्कासित खेलाडी */

        .vb-court-pro { width: 100%; max-width: 800px; height: 330px; margin: 0 auto; background: linear-gradient(145deg, #b45309, #e07c2c); border-radius: 10px; border: 4px solid white; display: flex; position: relative; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .net-line-pro { position: absolute; left: 50%; top: 0; bottom: 0; width: 6px; background: rgba(255,255,255,0.9); z-index: 10; transform: translateX(-50%); box-shadow: 0 0 10px rgba(0,0,0,0.4); }
        
        .player-wrap { position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; z-index: 20; transition: all 0.3s; }
        .p-dot { width: 48px; height: 48px; border-radius: 50%; background: #f8fafc; color: #0f172a; font-weight: 900; font-size: 20px; display: flex; justify-content: center; align-items: center; border: 3px solid #1e293b; position: relative; }
        .p-name { font-size: 11px; color: #f1f5f9; font-weight: bold; margin-top: 4px; background: rgba(0,0,0,0.7); padding: 2px 6px; border-radius: 10px; }
        .libero-dot { background-color: #facc15 !important; border-color: #ea580c !important; border-width: 4px !important; }
        .serving-dot { box-shadow: 0 0 15px 5px #facc15 !important; border-color: #facc15 !important; }
        
        .flash-bar { background: #1e293b; border: 2px solid #facc15; padding: 8px; margin-top: 10px; border-radius: 10px; text-align: center; color: #facc15; font-size: 18px; font-weight: 900; letter-spacing: 1px; animation: pulse 2s infinite; }
        @keyframes pulse { 0% {box-shadow: 0 0 0 0 rgba(250,204,21,0.4);} 70% {box-shadow: 0 0 0 10px rgba(250,204,21,0);} 100% {box-shadow: 0 0 0 0 rgba(250,204,21,0);} }
        .bottom-ticker { margin-top: 10px; background: #1e293b; padding: 6px; border-radius: 20px; color: #facc15; font-weight: 500; font-size: 16px; }
            /* 💡 क्याप्टेन र लिबेरोको ब्याज (Badges) */
        .badge-c { position:absolute; top:-8px; left:-8px; background:#ef4444; color:white; font-size:10px; font-weight:900; width:18px; height:18px; border-radius:50%; border:2px solid white; z-index:30; display:flex; align-items:center; justify-content:center; }
        .badge-l { position:absolute; top:-8px; left:-8px; background:#facc15; color:black; font-size:10px; font-weight:900; width:18px; height:18px; border-radius:50%; border:2px solid #ea580c; z-index:30; display:flex; align-items:center; justify-content:center; }
        
        /* 💡 सर्भरको लागि बल्ने बत्ती (Glowing Light) */
        .serving-glow { box-shadow: 0 0 15px 5px #facc15 !important; border-color: #facc15 !important; animation: serverPulse 1.2s infinite; z-index:25; }
        @keyframes serverPulse { 0% { box-shadow: 0 0 10px 2px #facc15; } 50% { box-shadow: 0 0 25px 8px #facc15; } 100% { box-shadow: 0 0 10px 2px #facc15; } }
    </style>
""", unsafe_allow_html=True)

# 📡 ३. डाटा तान्ने
vb_data = ls._get_state("vb_live_match") 
if not vb_data:
    st.markdown("<div style='text-align:center; margin-top:30vh; color:#475569;'><h1>🏐 COURT IDLE</h1></div>", unsafe_allow_html=True)
    st.stop()

m_state = vb_data.get('state_json', {})
if isinstance(m_state, str): m_state = json.loads(m_state)

c_set = m_state.get('current_set', 1)
serving_team = vb_data.get('serving')

is_tv_swapped = m_state.get('tv_swapped', False)
left_team = vb_data['team_b'] if is_tv_swapped else vb_data['team_a']
right_team = vb_data['team_a'] if is_tv_swapped else vb_data['team_b']

# ⏱️ मुख्य घडी (Main Clock) र पज लजिक (१००% सिंक भर्सन)
import time
start_ms = int(m_state.get('match_start_time') or 0)
acc_time = int(m_state.get('accumulated_time') or 0)
last_start = int(m_state.get('last_start_time') or start_ms)
is_paused = m_state.get('clock_paused', False)
cd_title = str(m_state.get('countdown_title') or 'TIMEOUT').replace("'", "")

current_ms = int(time.time() * 1000)
cd_rem = 0
total_ms = acc_time

if not is_paused:
    if current_ms < last_start:
        # 💡 जादु १: भविष्यको समय छ भने काउन्टडाउन चल्छ!
        cd_rem = int((last_start - current_ms) / 1000)
    else:
        # 💡 जादु २: काउन्टडाउन सकिएपछि अटोमेटिक मुख्य घडी चल्छ!
        total_ms += (current_ms - last_start)
        
# मुख्य घडीको समय निकाल्ने
seconds = int(total_ms / 1000)
if seconds < 0: seconds = 0
elapsed = f"{seconds//60:02d}:{seconds%60:02d}"
if is_paused or cd_rem > 0:
    elapsed = f"⏸️ {elapsed}"
    
# ⏳ काउन्टडाउन घडी (Timeout / Side Change) को UI
countdown_html = ""
if cd_rem > 0 and not is_paused:
    countdown_html = f"<div style='background:#ef4444; color:white; padding:4px 30px; border-radius:20px; font-size:24px; font-weight:900; margin:15px auto 0 auto; width:fit-content; border:2px solid #facc15; animation: pulse 1s infinite; box-shadow: 0 4px 10px rgba(0,0,0,0.5);'>⏳ {cd_title}: {cd_rem}s</div>"
    
# 🚨 चेतावनी: यसको तल 'if start_ms > 0:' वाला कोड छ भने त्यसलाई पुरै डिलिट गरिदिनुहोला!

def get_to_dots(count): return "".join(["🔴 " for _ in range(count)]) if count > 0 else "0"

def render_side_panel(team_name, color_hex, is_left):
    lineup = m_state.get('lineup', {}).get(team_name, {})
    roster = m_state.get('roster', {}).get(team_name, {})
    cards = m_state.get('cards', {}).get(team_name, {}) # 💡 कार्डको डाटा तान्ने
    
    subs_count = m_state.get('substitutions', {}).get(team_name, 0)
    liberos = lineup.get('libero', [])
    lib_track = m_state.get('libero_tracking', {}).get(team_name, {})
    rep_player = lib_track.get('replaced_player')
    
    score = vb_data['score_b'] if (is_left and is_tv_swapped) or (not is_left and not is_tv_swapped) else vb_data['score_a']
    sets = vb_data['sets_b'] if (is_left and is_tv_swapped) or (not is_left and not is_tv_swapped) else vb_data['sets_a']
    timeouts = vb_data['timeout_b'] if (is_left and is_tv_swapped) or (not is_left and not is_tv_swapped) else vb_data['timeout_a']
    
    html = f"<div class='side-panel' style='border-top: 5px solid {color_hex};'>"
    html += f"""
    <div class='team-name-box' style='color:{color_hex};'>{team_name}</div>
    <div class='big-score-box' style='border-bottom: 3px solid {color_hex};'>
        <div class='big-score'>{score}</div>
        <div class='stats-row'><span>SETS: {sets}</span><span>T/O: {get_to_dots(timeouts)}</span><span>SUB: {subs_count}/6</span></div>
    </div><div class='roster-list'>
    """
    
    # 💡 कार्डको इमोजी देखाउने फङ्सन
    def get_card_icon(player_num):
        card = cards.get(player_num)
        if card == "Yellow": return " 🟨"
        if card in ["Red", "Expulsion", "Disqualified"]: return " 🟥"
        return ""

    # १. कोर्टका खेलाडी
    for idx, j in enumerate(lineup.get('court', [])):
        name = roster.get(j, j)[:13]
        is_cap = (j == lineup.get('captain'))
        is_lib = (j in liberos)
        role = "(C)" if is_cap else ("(L)" if is_lib else "")
        status_cls = "libero-status" if is_lib else "playing-status"
        html += f"<div class='roster-card {status_cls}'><span><b>#{j}</b> {name} {role}{get_card_icon(j)}</span><small>P{idx+1}</small></div>"
        
    # २. बेन्चका खेलाडी
    for j in sorted(lineup.get('bench', []), key=lambda x: int(x) if x.isdigit() else 999):
        name = roster.get(j, j)[:13]
        is_lib = (j in liberos)
        if is_lib:
            status_cls = "libero-status"; role = "(L)"; txt = "BENCH"
        elif j == rep_player:
            status_cls = "replaced-status"; role = "🔄"; txt = "REPLACED"
        else:
            status_cls = "bench-status"; role = ""; txt = "BENCH"
        html += f"<div class='roster-card {status_cls}'><span><b>#{j}</b> {name} {role}{get_card_icon(j)}</span><small>{txt}</small></div>"

    # 🚨 ३. निष्कासित खेलाडी (Expelled/Disqualified) खोज्ने
    # जो खेलाडी रोस्टरमा छन् तर कोर्ट र बेन्च दुवैमा छैनन्, ती निकालिएका हुन्!
    all_active = lineup.get('court', []) + lineup.get('bench', [])
    expelled_players = [p for p in roster.keys() if p not in all_active]
    
    for j in sorted(expelled_players, key=lambda x: int(x) if x.isdigit() else 999):
        name = roster.get(j, j)[:14]
        html += f"<div class='roster-card expelled-status'><span><b>#{j}</b> {name} 🟥</span><small>OUT</small></div>"
        
    html += "</div></div>"
    return html

def get_player_html(num, team_name, is_left_side):
    lineup = m_state.get('lineup', {}).get(team_name, {})
    roster = m_state.get('roster', {}).get(team_name, {})
    cards = m_state.get('cards', {}).get(team_name, {})
    
    court = lineup.get('court', [])
    try: idx = court.index(num)
    except: idx = 0
    
    # 💡 क्याप्टेन र लिबेरो चिन्ने
    is_cap = str(num) == str(lineup.get('captain'))
    is_lib = str(num) in [str(x) for x in lineup.get('libero', [])]
    
    badge_html = ""
    if is_cap: badge_html = "<div class='badge-c'>C</div>"
    elif is_lib: badge_html = "<div class='badge-l'>L</div>"
    
    # 💡 कार्डको सानो ब्याज
    player_card = cards.get(num)
    card_html = ""
    if player_card:
        bg_color = "#facc15" if player_card == "Yellow" else "#ef4444"
        card_html = f'<div style="position:absolute; top:-4px; right:-4px; width:14px; height:18px; background:{bg_color}; border:2px solid white; border-radius:3px; z-index:25;"></div>'
    
    pos_left = { 0: ("12%", "80%"), 1: ("38%", "80%"), 2: ("38%", "50%"), 3: ("38%", "20%"), 4: ("12%", "20%"), 5: ("22%", "50%") }
    pos_right = { 0: ("88%", "20%"), 1: ("62%", "20%"), 2: ("62%", "50%"), 3: ("62%", "80%"), 4: ("88%", "80%"), 5: ("78%", "50%") }
    
    x, y = pos_left[idx] if is_left_side else pos_right[idx]
    
    # 💡 सर्भर भए बत्ती बाल्ने
    is_srv = (serving_team == team_name) and idx == 0
    cls = f"p-dot {'libero-dot' if is_lib else ''} {'serving-glow' if is_srv else ''}"
    
    return f"""<div class='player-wrap' style='left:{x}; top:{y};'>
        <div class='{cls}'>{num}{card_html}{badge_html}</div>
        <div class='p-name'>{str(roster.get(num, num)).split()[0][:8]}</div>
    </div>"""

# 📊 ६. मेन रेन्डर
best_of = m_state.get('settings', {}).get('best_of', 3)
target = m_state.get('settings', {}).get('points_per_set', 25)

st.markdown(f"""
    <div class="top-header">
        <div class="header-title">🏆 {CONFIG.get('EVENT_TITLE_NP')}</div>
        <div class="header-stats">
            <span>{vb_data.get('match_title')}</span>
            <span class="clock-box">⏱️ {elapsed}</span>
            <span style="background:#334155; padding:4px 12px; border-radius:10px;">SET {c_set} | TARGET {target} | BEST OF {best_of}</span>
        </div>
    </div>
""", unsafe_allow_html=True)

col_l, col_m, col_r = st.columns([1.6, 4, 1.6])

with col_l:
    st.markdown(render_side_panel(left_team, "#ef4444" if left_team==vb_data['team_a'] else "#3b82f6", True), unsafe_allow_html=True)

with col_m:
    court_html = f"""<div class='vb-court-pro'>
        <div class='net-line-pro'></div>
        <div style='position:absolute; right:33%; top:0; bottom:0; border-right:3px dashed rgba(255,255,255,0.6);'></div>
        <div style='position:absolute; left:33%; top:0; bottom:0; border-left:3px dashed rgba(255,255,255,0.6);'></div>
        {''.join([get_player_html(j, left_team, True) for j in m_state.get('lineup',{}).get(left_team,{}).get('court',[])])}
        {''.join([get_player_html(j, right_team, False) for j in m_state.get('lineup',{}).get(right_team,{}).get('court',[])])}
    </div>"""
    st.markdown(court_html, unsafe_allow_html=True)

    ev = m_state.get('latest_event', {})
    flash_txt = ev.get('tv_msg', ev.get('speech', "MATCH IN PROGRESS"))
    st.markdown(f"<div class='flash-bar'>📢 {flash_txt}</div>", unsafe_allow_html=True)
    
    off = m_state.get('officials', {})
    
    # 💡 कोर्टको हालको अवस्था (Left/Right) अनुसार मेनेजर र रङ (Color) छुट्याउने
    is_swapped = m_state.get('tv_swapped', False)
    
    if is_swapped:
        left_mgr_name = off.get('mgr_b', '-')
        right_mgr_name = off.get('mgr_a', '-')
        # स्वाप हुँदा: Left मा Team B (नीलो), Right मा Team A (रातो)
        left_color = "#3b82f6"  # Blue
        right_color = "#ef4444" # Red
    else:
        left_mgr_name = off.get('mgr_a', '-')
        right_mgr_name = off.get('mgr_b', '-')
        # स्वाप नहुँदा: Left मा Team A (रातो), Right मा Team B (नीलो)
        left_color = "#ef4444"  # Red
        right_color = "#3b82f6" # Blue

    # 🎨 डाइनामिक कलरसहितको छरितो डिजाइन (L र R मात्र)
    st.markdown(f"""
    <div style='display:flex; justify-content:space-evenly; align-items:center; background: linear-gradient(90deg, #0f172a, #1e293b, #0f172a); padding:8px 15px; margin-top:12px; border-radius:12px; border:1px solid #475569; font-size:13px; color:#e2e8f0; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
        <span style='display:flex; align-items:center; gap:5px;'>
            <span style='color:#94a3b8;'>👨‍⚖️ 1st Ref:</span> 
            <span style='color:#facc15; font-weight:bold; letter-spacing: 0.5px;'>{off.get('referee','-')}</span>
        </span>
        <span style='color:#475569;'>|</span>
        <span style='display:flex; align-items:center; gap:5px;'>
            <span style='color:#94a3b8;'>🧑‍⚖️ 2nd Ref:</span> 
            <span style='color:#facc15; font-weight:bold; letter-spacing: 0.5px;'>{off.get('umpire','-')}</span>
        </span>
        <span style='color:#475569;'>|</span>
        <span style='display:flex; align-items:center; gap:5px;'>
            <span style='color:#94a3b8;'>👔 Mgr (L):</span> 
            <span style='color:{left_color}; font-weight:bold;'>{left_mgr_name}</span>
        </span>
        <span style='color:#475569;'>|</span>
        <span style='display:flex; align-items:center; gap:5px;'>
            <span style='color:#94a3b8;'>👔 Mgr (R):</span> 
            <span style='color:{right_color}; font-weight:bold;'>{right_mgr_name}</span>
        </span>
    </div>
    {countdown_html}
    """, unsafe_allow_html=True)
with col_r:
    st.markdown(render_side_panel(right_team, "#3b82f6" if right_team==vb_data['team_b'] else "#ef4444", False), unsafe_allow_html=True)

ticker = ls.get_ticker_headlines()
st.markdown(f"<div class='bottom-ticker'><marquee scrollamount='6'>{ticker}</marquee></div>", unsafe_allow_html=True)


# ==========================================================
# 🎉 जादु: टिभीमा सेलिब्रेसन र 'अर्को यात्रा' (TV Celebration Overlay)
# ==========================================================
import json
import utils.live_state as ls
import database as db
import psycopg2.extras
import re

try:
    live_data = ls._get_state("vb_live_match")
    if live_data is None: live_data = {}

    m_state = json.loads(live_data.get("state_json", "{}"))
    cel = m_state.get('tv_celebration', {})
    
    if cel.get('show'):
        c_set_tv = m_state.get('current_set', 1)
        is_match_win = "CHAMPION" in cel.get('title', '')
        
        if st.session_state.get('last_cel_set') != c_set_tv or st.session_state.get('last_cel_type') != cel.get('title'):
            st.balloons()
            if is_match_win: st.snow() 
            st.session_state['last_cel_set'] = c_set_tv
            st.session_state['last_cel_type'] = cel.get('title')

        # 💡 जादु २: म्याच जितेको बेला डाटाबेसबाट 'अर्को यात्रा' खोज्ने
        next_journey_html = ""
        if is_match_win:
            try:
                conn = db.get_connection()
                c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                p1_name = m_state.get('p1_name', '')
                c.execute("SELECT * FROM matches WHERE status='Completed' AND p1_name=%s ORDER BY match_no DESC LIMIT 1", (p1_name,))
                cur_m = c.fetchone()
                
                if cur_m:
                    c.execute("SELECT * FROM matches WHERE event_code=%s", (cur_m['event_code'],))
                    all_m = c.fetchall()
                    nxt_m = next((x for x in all_m if x.get('source_match1') == cur_m['match_no'] or x.get('source_match2') == cur_m['match_no']), None)
                    
                    if nxt_m:
                        win_name = cel.get('winner', '')
                        opp_src = nxt_m.get('source_match2') if nxt_m.get('source_match1') == cur_m['match_no'] else nxt_m.get('source_match1')
                        p1_n, p2_n = str(nxt_m.get('p1_name', '')), str(nxt_m.get('p2_name', ''))
                        def cln_nm(n): return re.sub(r'[\u0900-\u097F]+|\(\s*\)', '', str(n)).strip()
                        
                        opp_name = None
                        if "Winner" not in p1_n and cln_nm(win_name).lower() not in p1_n.lower(): opp_name = p1_n
                        elif "Winner" not in p2_n and cln_nm(win_name).lower() not in p2_n.lower(): opp_name = p2_n
                        
                        if opp_name:
                            nj_txt = f"Next Match: #{nxt_m['match_no']} ({nxt_m['round_name']}) vs {cln_nm(opp_name)}"
                        else:
                            nj_txt = f"Next Match: #{nxt_m['match_no']} ({nxt_m['round_name']}) vs Winner of #{opp_src}"
                    else:
                        nj_txt = "Tournament Champion! 🏆"
                        
                    next_journey_html = f"<div style='background:#10b981; color:white; padding:10px 40px; border-radius:30px; font-size:35px; font-weight:bold; margin-top:20px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); border:3px solid white;'>⏭️ {nj_txt}</div>"
                c.close(); conn.close()
            except Exception as e:
                pass

        bg_color = "rgba(15, 23, 42, 0.95)" if is_match_win else "rgba(15, 23, 42, 0.85)"
        trophy_size = "150px" if is_match_win else "100px"
        title_size = "80px" if is_match_win else "60px"
        
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
        <style>
            @keyframes bounce {{ 0%, 100% {{ transform: translateY(0); }} 50% {{ transform: translateY(-30px); }} }}
        </style>
        """, unsafe_allow_html=True)
except Exception as e:
    pass
# ==========================================================