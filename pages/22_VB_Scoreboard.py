import streamlit as st
import database as db
import json
from streamlit_autorefresh import st_autorefresh
from config import CONFIG
from datetime import datetime

# ⚙️ टिभीको लागि फुल-स्क्रिन सेटिङ
st.set_page_config(page_title="Volleyball Live TV", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=1000, key="vb_sb_refresh")

# ==========================================
# 🎨 CSS: Header, Vertical Court & Scrolling Roster
# ==========================================
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        header {visibility: hidden;}
        footer {visibility: hidden;}
        .block-container {padding: 0rem 2rem 0rem 2rem !important; background-color: #0f172a;}
        ::-webkit-scrollbar {display: none;}
        
        /* Header Box */
        .header-box { text-align: center; background: linear-gradient(90deg, #1e293b, #0f172a, #1e293b); padding: 15px; border-bottom: 4px solid #ef4444; margin-bottom: 15px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        .match-info { position: absolute; top: 25px; right: 30px; background: rgba(255,255,255,0.1); padding: 10px 20px; border-radius: 10px; color: #cbd5e1; font-weight: bold; border: 1px solid #475569; }

        /* 🏐 Vertical Court CSS */
        .court-wrapper { display: flex; flex-direction: row; gap: 20px; align-items: flex-end; justify-content: center; height: 350px; margin-top: 15px; }
        .bench-area { display: flex; flex-direction: column; gap: 8px; background: #334155; padding: 10px; border-radius: 10px; min-width: 50px; align-items: center; border: 2px solid #475569; }
        .bench-title { color: #94a3b8; font-size: 12px; font-weight: bold; writing-mode: vertical-rl; text-orientation: mixed; transform: rotate(180deg); margin-bottom: 10px; }
        
        .vb-court-vertical { width: 250px; height: 350px; background-color: #f17b37; border: 4px solid white; border-top: 10px solid #1e3a8a; position: relative; box-shadow: 0 10px 20px rgba(0,0,0,0.4); }
        .attack-line { position: absolute; top: 33.33%; left: 0; right: 0; border-top: 4px dashed white; }
        
        /* Player Dots & Roles */
        .p-dot { position: absolute; width: 45px; height: 45px; border-radius: 50%; background: white; color: black; font-weight: bold; font-size: 18px; display: flex; justify-content: center; align-items: center; transform: translate(-50%, -50%); border: 3px solid #334155; z-index: 5; box-shadow: 2px 2px 8px rgba(0,0,0,0.6); }
        .p-dot-bench { position: relative; width: 35px; height: 35px; transform: none; font-size: 14px; box-shadow: none; }
        
        .libero { background-color: #fbbf24 !important; color: #78350f !important; }
        .captain { border-style: double !important; border-width: 6px !important; border-color: #1e293b !important; }
        .serving-dot { border-color: #fbbf24 !important; box-shadow: 0 0 15px 5px #fbbf24 !important; }
        
        /* Cards */
        .card-badge { position: absolute; top: -5px; right: -5px; width: 15px; height: 20px; border-radius: 3px; border: 1px solid black; z-index: 15; box-shadow: 1px 1px 3px rgba(0,0,0,0.5); }
        .card-Yellow { background-color: #fde047; }
        .card-Red { background-color: #ef4444; }
        .card-Expulsion { background: linear-gradient(135deg, #ef4444 50%, #fde047 50%); }
        .card-Disqualified { background: black; border: 1px solid white; }
        
        /* 📜 Scrolling Roster CSS */
        .scroll-container { height: 260px; overflow: hidden; position: relative; background: #1e293b; border-radius: 15px; border: 2px solid #475569; padding: 10px; margin-top: 20px; box-shadow: inset 0 0 20px rgba(0,0,0,0.5); }
        .scroll-content { display: flex; flex-direction: column; gap: 10px; animation: scrollUp 25s linear infinite; }
        .scroll-content:hover { animation-play-state: paused; }
        @keyframes scrollUp { 0% { transform: translateY(100%); } 100% { transform: translateY(-120%); } }
        
        .roster-row { display: flex; align-items: center; gap: 15px; padding: 5px; background: rgba(255,255,255,0.05); border-radius: 10px; }
        .roster-name { color: white; font-size: 16px; font-weight: bold; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 140px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 📡 Fetch Live Data
# ==========================================
try:
    conn = db.get_connection()
    row = conn.execute("SELECT * FROM vb_live_match LIMIT 1").fetchone()
    if row:
        live_match = dict(row)
        match_state = json.loads(live_match.get('state_json', '{}')) if live_match.get('state_json') else {}
    else:
        live_match = None; match_state = {}
except Exception as e:
    live_match = None; match_state = {}
finally:
    try: conn.close()
    except: pass

# ==========================================
# 🏆 Header Section
# ==========================================
now = datetime.now()
st.markdown(f"""
    <div class='header-box'>
        <h1 style='margin:0; font-size: 36px; color: white;'>🏆 {CONFIG['EVENT_TITLE_NP']} - प्रत्यक्ष प्रसारण 🔴</h1>
        <div style='font-size: 20px; color: #FFD700; margin-top: 5px;'>आयोजक: {CONFIG['ORGANIZER_NAME']} &nbsp; | &nbsp; आतिथ्यता: {CONFIG['HOST_NAME']}</div>
        <div style='font-size: 18px; color: #e0e7ff; margin-top: 5px;'>📅 {now.strftime("%Y-%m-%d")} &nbsp;|&nbsp; ⏰ {now.strftime("%I:%M %p")}</div>
    </div>
""", unsafe_allow_html=True)

if not live_match:
    st.markdown("<div style='text-align:center; margin-top:15vh;'><h1 style='font-size:80px; color:#cbd5e1;'>🏐 VOLLEYBALL COURT</h1><p style='font-size:30px; color:#64748b;'>Waiting for operator to start match...</p></div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 📊 UI Setup & Match Info
# ==========================================
t_a, t_b = live_match['team_a'], live_match['team_b']
s_a, s_b = live_match['score_a'], live_match['score_b']
sets_a, sets_b = live_match['sets_a'], live_match['sets_b']
serving = live_match['serving']

best_of = match_state.get('settings', {}).get('best_of', 3)
target_pts = match_state.get('settings', {}).get('points_per_set', 25)
c_set = match_state.get('current_set', 1)
actual_target = 15 if (c_set == best_of) else target_pts

st.markdown(f"<div style='text-align:center; color:#94a3b8; font-size:26px; font-weight:bold; margin-bottom: 10px;'>{live_match.get('match_title', 'Match')}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='match-info'>Best of {best_of} <br> Target: {actual_target} pts</div>", unsafe_allow_html=True)

# 💡 Middle column is slightly wider for names
ca, cmid, cb = st.columns([3.5, 2.2, 3.5])

def get_to_ui(used, color):
    return "".join([f"<div style='width:22px; height:22px; background:{color if i<=used else 'transparent'}; border:{f'3px solid {color}' if i>used else 'none'}; margin:0 4px; display:inline-block; border-radius:50%;'></div>" for i in range(1, 3)])

def render_team_court(team_name, align_bench_left=True):
    lineup = match_state.get('lineup', {}).get(team_name, {"court": [], "bench": [], "captain": None, "libero": []})
    roster = match_state.get('roster', {}).get(team_name, {})
    cards = match_state.get('cards', {}).get(team_name, {})
    c_arr, b_arr = lineup.get('court', []), lineup.get('bench', [])
    
    pos_vert = { 0: ("80%", "85%"), 1: ("80%", "20%"), 2: ("50%", "20%"), 3: ("20%", "20%"), 4: ("20%", "85%"), 5: ("50%", "65%") }

    def make_dot(num, is_court=True, idx=-1):
        cls = ["p-dot" if is_court else "p-dot p-dot-bench"]
        if num in lineup.get('libero', []): cls.append("libero")
        if num == lineup.get('captain'): cls.append("captain")
        if is_court and serving == ('A' if team_name == t_a else 'B') and idx == 0: cls.append("serving-dot")
        
        style = f"left:{pos_vert[idx][0]}; top:{pos_vert[idx][1]};" if is_court else ""
        card_html = f'<div class="card-badge card-{cards[num]}"></div>' if num in cards else ""
        return f'<div class="{" ".join(cls)}" style="{style}" title="{roster.get(num, num)}">{num}{card_html}</div>'

    html = '<div class="court-wrapper">'
    bench_html = f'<div class="bench-area"><div class="bench-title">BENCH</div>{"".join([make_dot(n, False) for n in b_arr])}</div>'
    court_html = f'<div class="vb-court-vertical"><div class="attack-line"></div>{"".join([make_dot(n, True, i) for i, n in enumerate(c_arr)])}</div>'
    
    html += (bench_html + court_html) if align_bench_left else (court_html + bench_html)
    return html + '</div>'

# ==========================================
# 📜 Helper: Scrolling Roster Generator
# ==========================================
def get_roster_html(team_name, color):
    html = f"<div style='color:{color}; text-align:center; font-size:16px; margin: 10px 0 5px 0; border-bottom:2px solid {color}; padding-bottom:5px;'>{team_name}</div>"
    lineup = match_state.get('lineup', {}).get(team_name, {"court": [], "bench": [], "captain": None, "libero": []})
    roster = match_state.get('roster', {}).get(team_name, {})
    cards = match_state.get('cards', {}).get(team_name, {})
    all_players = lineup.get('court', []) + lineup.get('bench', [])
    
    for num in all_players:
        cls = ["p-dot p-dot-bench"] 
        if num in lineup.get('libero', []): cls.append("libero")
        if num == lineup.get('captain'): cls.append("captain")
        card_html = f'<div class="card-badge card-{cards[num]}"></div>' if num in cards else ""
        
        # 💡 यहाँ अगाडिको स्पेस (Indentation) हटाएर एउटै लाइनमा लेखिएको छ
        html += f'<div class="roster-row"><div class="{" ".join(cls)}">{num}{card_html}</div><div class="roster-name">{roster.get(num, f"Player {num}")}</div></div>'
        
    return html

# ==========================================
# 🔴 TEAM A Side
# ==========================================
with ca:
    srv_a = " <span style='color:#fbbf24;'>🏐</span>" if serving == 'A' else ""
    st.markdown(f"""
    <div style='background-color:#1e293b; padding:20px; border-radius:20px; border-bottom: 12px solid #dc2626; color:white; box-shadow: 0 10px 30px rgba(0,0,0,0.5);'>
        <h1 style='font-size:48px; margin:0; text-align:center; text-transform:uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{t_a}{srv_a}</h1>
        <div style='display:flex; justify-content:space-between; align-items:center; padding: 5px 20px;'>
            <div style='font-size:24px; color:#94a3b8;'>T/O: <br>{get_to_ui(live_match['timeout_a'], '#ef4444')}</div>
            <div style='font-size:160px; font-weight:bold; line-height:1; color:#fca5a5;'>{s_a}</div>
            <div style='width:60px;'></div>
        </div>
        {render_team_court(t_a, align_bench_left=True)}
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🏆 SETS, ROSTER & LEGEND (Middle)
# ==========================================
with cmid:
    # 1. Sets Display
    st.markdown(f"""
    <div style='display:flex; flex-direction:column; justify-content:center; align-items:center;'>
        <div style='font-size:28px; color:#64748b; font-weight:bold; margin-bottom:5px;'>SET {c_set}</div>
        <div style='background-color:#1e293b; padding:15px 20px; border-radius:15px; border:3px solid #475569; text-align:center; width:100%; box-shadow: 0 5px 15px rgba(0,0,0,0.4);'>
            <div style='font-size:16px; color:#94a3b8; margin-bottom:5px;'>SETS WON</div>
            <span style='font-size:50px; font-weight:bold; color:#dc2626;'>{sets_a}</span>
            <span style='font-size:35px; color:#64748b; margin:0 10px;'>-</span>
            <span style='font-size:50px; font-weight:bold; color:#2563eb;'>{sets_b}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Scrolling Roster Display
    roster_a_html = get_roster_html(t_a, '#fca5a5')
    roster_b_html = get_roster_html(t_b, '#93c5fd')
    st.markdown(f"""
    <div class="scroll-container">
        <div class="scroll-content">
            {roster_a_html}
            {roster_b_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 3. 💡 नयाँ थपिएको: Legend / Index (सङ्केत)
    st.markdown("""
    <div style='background-color:#1e293b; padding:10px; border-radius:15px; border:2px solid #475569; margin-top:15px; box-shadow: inset 0 0 10px rgba(0,0,0,0.5);'>
        <div style='color:#94a3b8; font-size:13px; font-weight:bold; text-align:center; border-bottom:1px solid #475569; padding-bottom:5px; margin-bottom:8px;'>सङ्केत (Legend)</div>
        <div style='display:flex; flex-wrap:wrap; justify-content:center; gap:8px; font-size:11px; color:#cbd5e1;'>
            <div style='display:flex; align-items:center; gap:4px;'><div style='width:14px; height:14px; border-radius:50%; background:white; border:2px solid #334155;'></div> खेलाडी</div>
            <div style='display:flex; align-items:center; gap:4px;'><div style='width:14px; height:14px; border-radius:50%; background:white; border-style:double; border-width:4px; border-color:#1e293b;'></div> क्याप्टेन</div>
            <div style='display:flex; align-items:center; gap:4px;'><div style='width:14px; height:14px; border-radius:50%; background:#fbbf24; border:1px solid white;'></div> लिबेरो</div>
            <div style='display:flex; align-items:center; gap:4px;'><div style='width:10px; height:14px; background:#fde047; border:1px solid black; border-radius:2px;'></div> पहेँलो कार्ड</div>
            <div style='display:flex; align-items:center; gap:4px;'><div style='width:10px; height:14px; background:#ef4444; border:1px solid black; border-radius:2px;'></div> रातो कार्ड</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🔵 TEAM B Side
# ==========================================
with cb:
    srv_b = " <span style='color:#fbbf24;'>🏐</span>" if serving == 'B' else ""
    st.markdown(f"""
    <div style='background-color:#1e293b; padding:20px; border-radius:20px; border-bottom: 12px solid #2563eb; color:white; box-shadow: 0 10px 30px rgba(0,0,0,0.5);'>
        <h1 style='font-size:48px; margin:0; text-align:center; text-transform:uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{srv_b}{t_b}</h1>
        <div style='display:flex; justify-content:space-between; align-items:center; padding: 5px 20px;'>
            <div style='width:60px;'></div>
            <div style='font-size:160px; font-weight:bold; line-height:1; color:#93c5fd;'>{s_b}</div>
            <div style='font-size:24px; color:#94a3b8;'>T/O: <br>{get_to_ui(live_match['timeout_b'], '#3b82f6')}</div>
        </div>
        {render_team_court(t_b, align_bench_left=False)}
    </div>
    """, unsafe_allow_html=True)