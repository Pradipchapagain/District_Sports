import streamlit as st
import database as db
import json
from streamlit_autorefresh import st_autorefresh
from config import CONFIG
from datetime import datetime
from time import time
import os
import base64

# ==========================================
# ⚙️ १. टिभीको लागि फुल-स्क्रिन सेटिङ
# ==========================================
st.set_page_config(page_title="Kabaddi Live TV", layout="wide", initial_sidebar_state="collapsed")
st_autorefresh(interval=1000, key="kb_tv_refresh")

# ==========================================
# 🧹 २. साइडबार, मेनु र हेडर पूरै लुकाउने CSS
# ==========================================
st.markdown("""
    <style>
        /* १. साइडबार र नेभिगेसन मेनु पूरै बन्द गर्ने */
        [data-testid="stSidebar"], [data-testid="stSidebarNav"], .st-emotion-cache-16idsys {
            display: none !important;
            width: 0px !important;
        }
        /* २. माथिको हेडर (जहाँ मेनु र सेटिङ हुन्छ) हटाउने */
        header, [data-testid="stHeader"] {
            display: none !important;
        }
        /* ३. पेजको चारैतिरको खाली ठाउँ (Margins) हटाउने */
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        /* ४. स्क्रोलबार लुकाउने तर काम गर्ने बनाउने */
        body {
            overflow: hidden;
            background-color: #0E1117;
        }
        /* ५. 'Made with Streamlit' र अन्य फुटर हटाउने */
        footer {visibility: hidden;}
        #MainMenu {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 🖼️ ३. इमेज क्यासिङ
# ==========================================
@st.cache_data
def get_cached_base64_image(filename):
    filepath = os.path.join("assets", filename)
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""
st.markdown("""
    <style>
        #MainMenu, header, footer {visibility: hidden;}
        .block-container {padding: 0rem 2rem 0rem 2rem !important; background-color: #0f172a;}
        ::-webkit-scrollbar {display: none;}

        .header-box { text-align: center; background: linear-gradient(90deg, #1e293b, #0f172a, #1e293b); padding: 15px; border-bottom: 4px solid #facc15; margin-bottom: 15px; border-radius: 0 0 20px 20px; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }

        /* Arena Layout */
        .kb-arena { display: flex; justify-content: center; align-items: stretch; width: 100%; gap: 15px; margin: 20px 0; height: 380px; }
        .kb-bench { display: flex; flex-direction: column; gap: 8px; background: #1e293b; padding: 10px; border-radius: 8px; min-width: 60px; align-items: center; border: 2px solid #475569; overflow: hidden; }
        .bench-title { color: white; font-size: 14px; font-weight: bold; writing-mode: vertical-rl; flex-grow: 1; text-align: center; letter-spacing: 3px; }
        .sitting-block { display: flex; flex-direction: column; justify-content: flex-end; gap: 6px; background: #e2e8f0; padding: 10px; border-radius: 8px; width: 70px; border: 3px solid #cbd5e1; }
        .sit-slot { width: 45px; height: 45px; border-radius: 50%; background: white; border: 2px dashed #94a3b8; display: flex; justify-content: center; align-items: center; font-size: 16px; font-weight: bold; color: #475569; position: relative; margin: 0 auto; }
        .sit-filled { background: #cbd5e1; border: 3px solid #475569; color: black; box-shadow: inset 0 0 5px rgba(0,0,0,0.2); }

        .kb-court { display: flex; width: 100%; max-width: 1200px; height: 100%; background-color: #fcd34d; border: 6px solid white; position: relative; box-shadow: 0 10px 25px rgba(0,0,0,0.4); overflow: hidden; border-radius: 8px; }

        /* Players & Roles */
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

        /* 💡 पपअप म्यासेज */
        .court-popup {
            display: flex; align-items: center; justify-content: center; gap: 20px;
            position: absolute; top: 20%; left: 50%; transform: translateX(-50%);
            background: linear-gradient(135deg, #0f172a, #1e293b); color: #f8fafc;
            padding: 20px 40px; border-radius: 15px; border: 4px solid #facc15;
            font-size: 32px; font-weight: bold; z-index: 100;
            box-shadow: 0px 10px 30px rgba(0,0,0,0.8);
            animation: slideInFadeOut 4.5s forwards;
        }
        .popup-icon {
            width: 70px; height: 70px; object-fit: contain;
            background: rgba(255,255,255,0.1); border-radius: 50%; padding: 8px;
            border: 2px solid rgba(255,255,255,0.3);
        }
        .flip-horizontal { transform: scaleX(-1); }
        @keyframes slideInFadeOut { 
            0% { opacity: 0; top: 15%; } 
            15% { opacity: 1; top: 20%; } 
            80% { opacity: 1; top: 20%; } 
            100% { opacity: 0; top: 15%; display: none; visibility: hidden; } 
        }

        /* 🆕 रेखाहरूको CSS */
        .mid-line { position: absolute; left: 50%; top: 0; bottom: 0; width: 8px; background: rgba(255,255,255,0.8); transform: translateX(-50%); z-index: 2; }
        .baulk-line-left, .baulk-line-right { position: absolute; top: 0; bottom: 0; width: 4px; z-index: 1; transition: all 0.5s; }
        .baulk-line-left { left: 35%; } .baulk-line-right { right: 35%; }
        .bonus-line-left, .bonus-line-right { position: absolute; top: 0; bottom: 0; width: 4px; z-index: 1; transition: all 0.5s; }
        .bonus-line-left { left: 20%; border-left: 4px dashed white; } 
        .bonus-line-right { right: 20%; border-right: 4px dashed white; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 📡 डाटा फेचिङ (utils.live_state प्रयोग)
# ==========================================
import utils.live_state as ls
kb_data = ls._get_state("kb_live_match")

if not kb_data:
    st.markdown("<div style='text-align:center; margin-top:15vh;'><h1 style='font-size:100px; color:#cbd5e1;'>🤼 KABADDI LIVE</h1><p style='font-size:40px; color:#64748b;'>खेल सुरु हुन प्रतिक्षा गर्दै...</p></div>", unsafe_allow_html=True)
    st.stop()

state = kb_data.get('state', {})
if not state or not state.get('match_started'):
    st.markdown("<div style='text-align:center; margin-top:15vh;'><h1 style='font-size:100px; color:#cbd5e1;'>🤼 KABADDI LIVE</h1><p style='font-size:40px; color:#64748b;'>खेल सुरु हुन प्रतिक्षा गर्दै...</p></div>", unsafe_allow_html=True)
    st.stop()

teams = list(state.get('roster', {}).keys())
if len(teams) >= 2:
    p1, p2 = teams[0], teams[1]
else:
    st.error("टोलीको जानकारी मिलेन।")
    st.stop()

# ==========================================
# 🏆 Header
# ==========================================
now = datetime.now()
st.markdown(f"""
    <div class='header-box'>
        <h1 style='margin:0; font-size: 40px; color: white;'>🏆 {CONFIG['EVENT_TITLE_NP']} - लाइभ 🔴</h1>
        <div style='font-size: 24px; color: #facc15; margin-top: 5px;'>आयोजक: {CONFIG['ORGANIZER_NAME']} &nbsp; | &nbsp; आतिथ्यता: {CONFIG['HOST_NAME']}</div>
        <div style='font-size: 18px; color: #e0e7ff;'>{now.strftime("%Y-%m-%d %I:%M %p")}</div>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 🔄 TV Mirroring
# ==========================================
half = state.get('half', 1)
swap_sides = state.get('swap_sides', False)

op_left = p2 if swap_sides else p1
op_right = p1 if swap_sides else p2

left_team = op_right
right_team = op_left

score_left = state['score_a'] if left_team == p1 else state['score_b']
score_right = state['score_a'] if right_team == p1 else state['score_b']

def get_to_icons(team):
    used = state.get('timeouts', {}).get(str(half), {}).get(team, 0)
    return " ".join(["⏱️" if i < used else "⚪" for i in range(2)])

def get_dod_dots(team):
    empties = state.get('empty_raids', {}).get(team, 0)
    return "⚪ ⚪" if empties == 0 else "🔴 ⚪" if empties == 1 else "🔴 🔴 (Do-or-Die)"

# ==========================================
# ⏱️ स्कोरबोर्ड
# ==========================================
c_score_L, c_timer, c_score_R = st.columns([1.5, 1, 1.5])

active_r_team = state.get('raider_team') or state.get('next_raider_team') or left_team
l_role = "🏃 रेडर" if active_r_team == left_team else "🛡️ डिफेन्स"
l_role_bg = "#2563eb" if active_r_team == left_team else "#475569"
r_role = "🏃 रेडर" if active_r_team == right_team else "🛡️ डिफेन्स"
r_role_bg = "#dc2626" if active_r_team == right_team else "#475569"

with c_score_L:
    st.markdown(f"""
        <div style='background:#1e293b; border-bottom:12px solid #2563eb; padding:20px; border-radius:20px; text-align:center; box-shadow: 0 10px 20px rgba(0,0,0,0.6);'>
            <h2 style='color:#93c5fd; margin:0; font-size:45px;'>{left_team}</h2>
            <div style='font-size:120px; font-weight:900; color:white; line-height:1; margin:10px 0;'>{score_left}</div>
            <div style='background:{l_role_bg}; color:white; font-size:20px; padding:5px 20px; border-radius:20px; display:inline-block;'>{l_role}</div>
            <div style='font-size:18px; color:#cbd5e1; margin-top:10px;'>T/O: {get_to_icons(left_team)} &nbsp;|&nbsp; {get_dod_dots(left_team)}</div>
        </div>
    """, unsafe_allow_html=True)

with c_timer:
    timer_seconds = state.get('timer_seconds', 1200)
    st.components.v1.html(f"""
        <div style="text-align:center; font-family:monospace;">
            <div style="background:#0f172a; border:3px solid #475569; color:#cbd5e1; padding:8px; border-radius:15px; display:inline-block; font-size:28px; font-weight:bold; margin-bottom:15px;">HALF {half}</div>
            <div style="font-size:60px; font-weight:bold; color:#facc15; background:#1e293b; padding:10px 25px; border-radius:20px; border:4px solid #334155; display:inline-block; box-shadow: 0 8px 20px rgba(0,0,0,0.6);">
                <span id="min">{timer_seconds//60:02d}</span>:<span id="sec">{timer_seconds%60:02d}</span>
            </div>
            
            <div id="to_box" style="display:{'block' if state.get('timeout_active') else 'none'}; margin-top:15px; font-size:24px; color:#ef4444; font-weight:bold; background:#fee2e2; padding:5px; border-radius:10px; border:3px solid #fca5a5;">
                ⏳ TIMEOUT: <span id="to_sec">30</span>s
            </div>
            
            <div style="margin-top:15px; display:{'block' if state.get('raider_team') and not state.get('timeout_active') else 'none'};">
                <span style="font-size:32px; color:#ef4444; font-weight:bold; background:#fee2e2; padding:8px 25px; border-radius:30px; border:3px solid #fca5a5;">🏃 <span id="r_sec">30</span>s</span>
            </div>
        </div>
        <script>
            let s = {timer_seconds};
            let t = parseInt(sessionStorage.getItem('to_sec')) || 30;
            let r = {30 if state.get('raider_team') else 0};
            
            let running = {'true' if state.get('timer_running') else 'false'};
            let is_to = {'true' if state.get('timeout_active') else 'false'};
            let r_run = {'true' if state.get('raider_team') else 'false'};

            function update() {{ 
                if(running && s>0) {{ s--; }}
                if(is_to && t>0) {{ t--; sessionStorage.setItem('to_sec', t); document.getElementById('to_sec').innerText = t<10?'0'+t:t; }} 
                else if (!is_to) {{ sessionStorage.setItem('to_sec', 30); }}
                if(r_run && r>0) {{ r--; document.getElementById('r_sec').innerText = r<10?'0'+r:r; }}

                let m = Math.floor(s/60); let sec = s%60;
                document.getElementById('sec').innerText = sec<10?'0'+sec:sec; 
                document.getElementById('min').innerText = m<10?'0'+m:m; 
            }}
            window.timer = setInterval(update, 1000);
        </script>
    """, height=280)

with c_score_R:
    st.markdown(f"""
        <div style='background:#1e293b; border-bottom:12px solid #dc2626; padding:20px; border-radius:20px; text-align:center; box-shadow: 0 10px 20px rgba(0,0,0,0.6);'>
            <h2 style='color:#fca5a5; margin:0; font-size:45px;'>{right_team}</h2>
            <div style='font-size:120px; font-weight:900; color:white; line-height:1; margin:10px 0;'>{score_right}</div>
            <div style='background:{r_role_bg}; color:white; font-size:20px; padding:5px 20px; border-radius:20px; display:inline-block;'>{r_role}</div>
            <div style='font-size:18px; color:#cbd5e1; margin-top:10px;'>T/O: {get_to_icons(right_team)} &nbsp;|&nbsp; {get_dod_dots(right_team)}</div>
        </div>
    """, unsafe_allow_html=True)

# ==========================================
# 🤼 कबड्डी कोर्ट
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

c_baulk_l, c_bonus_l = "white", "white"
c_baulk_r, c_bonus_r = "white", "white"
if not tv_is_attacking_right:
    if r_pos >= 2 or baulk_c: c_baulk_l = "#22c55e"
    if r_pos >= 3 or bonus_c: c_bonus_l = "#facc15"
else:
    if r_pos >= 2 or baulk_c: c_baulk_r = "#22c55e"
    if r_pos >= 3 or bonus_c: c_bonus_r = "#facc15"

pos_a = {0:("15%","20%"), 1:("25%","35%"), 2:("35%","50%"), 3:("25%","65%"), 4:("15%","80%"), 5:("10%","35%"), 6:("10%","65%")}
pos_b = {0:("85%","20%"), 1:("75%","35%"), 2:("65%","50%"), 3:("75%","65%"), 4:("85%","80%"), 5:("90%","35%"), 6:("90%","65%")}

def get_sitting_block_html(team, out_list):
    slots_html = ""
    eligible_idx = -1
    for i, p in enumerate(out_list):
        if state['cards'].get(team, {}).get(p) != 'Yellow':
            eligible_idx = i
            break
    for i in range(7):
        if i < len(out_list):
            p_num = out_list[i]
            icon = "✨" if i == eligible_idx else ""
            slots_html += f'<div class="sit-slot sit-filled">{p_num}<span class="revive-icon">{icon}</span></div>'
        else:
            slots_html += '<div class="sit-slot"></div>'
    return f'<div class="sitting-block">{slots_html}</div>'

def make_dot(team, num, is_court=True, idx=-1, is_left=True):
    if is_court and num in state['out_players'].get(team, []): return ""
    if state['cards'].get(team, {}).get(num) == 'Red':
        return f'<div class="p-dot p-dot-bench bg-out">{num}</div>' if not is_court else ""

    cls = ["p-dot" if is_court else "p-dot p-dot-bench"]
    bg_class = "bg-blue" if team == p1 else "bg-red"
    if state['cards'].get(team, {}).get(num) == 'Yellow':
        st_time = state.get('yc_timers', {}).get(team, {}).get(num, 0)
        if time() - st_time >= 120:
            bg_class = "bg-green"
    cls.append(bg_class)

    if num == state['lineup'].get(team, {}).get('captain'): cls.append("captain-dot")

    is_raider = (raider_team == team and state.get('raider_num') == num)
    if is_raider:
        is_dod = state['empty_raids'].get(team, 0) >= 2
        cls.append("raider-dod" if is_dod else "raider-normal")
    if num in state.get('selected_targets', []) and team != raider_team:
        cls.append("target-active")

    style = ""
    if is_court:
        if is_raider:
            if tv_is_attacking_right:
                if r_pos == 0: style_pos = "left:45%; top:50%;"
                elif r_pos == 1: style_pos = "left:55%; top:50%;"
                elif r_pos == 2: style_pos = "left:70%; top:50%;"
                else: style_pos = "left:88%; top:50%;"
            else:
                if r_pos == 0: style_pos = "left:55%; top:50%;"
                elif r_pos == 1: style_pos = "left:45%; top:50%;"
                elif r_pos == 2: style_pos = "left:30%; top:50%;"
                else: style_pos = "left:12%; top:50%;"
        else:
            pos = pos_a if is_left else pos_b
            style_pos = f"left:{pos[idx][0]}; top:{pos[idx][1]};"
        style = style_pos

    return f'<div class="{" ".join(cls)}" style="{style}">{num}</div>'

# Yellow Card Timer Box
yc_html = "<div style='display:flex; justify-content:space-between; width:100%; max-width:1200px; margin: 0 auto; padding: 0 10px;'>"
def get_yc_box(team):
    box_html = "<div style='display:flex; gap:10px;'>"
    for yp, st_time in state.get('yc_timers', {}).get(team, {}).items():
        if state['cards'].get(team, {}).get(yp) != 'Yellow': continue
        elapsed = time() - st_time
        rem = max(0, 120 - int(elapsed))
        m, s = divmod(rem, 60)
        color = "#fde047" if rem > 0 else "#22c55e"
        txt = f"{m:02d}:{s:02d}" if rem > 0 else "भित्र पठाउनुहोस्"
        box_html += f"<div style='background:{color}; color:black; padding:5px 15px; border-radius:8px; font-weight:bold; border:3px solid #334155; font-size:18px; box-shadow:0 5px 10px rgba(0,0,0,0.5);'>🟨 जर्सी {yp} ⏳ {txt}</div>"
    return box_html + "</div>"

yc_html += get_yc_box(left_team) + get_yc_box(right_team) + "</div>"

html = yc_html + '<div class="kb-arena">'
html += f'<div class="kb-bench">{"".join([make_dot(left_team, n, False) for n in b_left])}<div class="bench-title">BENCH</div></div>'
html += get_sitting_block_html(left_team, out_left)

html += '<div class="kb-court">'
html += '<div class="mid-line"></div>'
html += f'<div class="baulk-line-left" style="background-color:{c_baulk_l}; box-shadow:0 0 15px {c_baulk_l};"></div>'
html += f'<div class="bonus-line-left" style="border-left-color:{c_bonus_l}; box-shadow:-5px 0 15px {c_bonus_l};"></div>'
html += f'<div class="baulk-line-right" style="background-color:{c_baulk_r}; box-shadow:0 0 15px {c_baulk_r};"></div>'
html += f'<div class="bonus-line-right" style="border-right-color:{c_bonus_r}; box-shadow:5px 0 15px {c_bonus_r};"></div>'

html += "".join([make_dot(left_team, n, True, i, True) for i, n in enumerate(c_left)])
html += "".join([make_dot(right_team, n, True, i, False) for i, n in enumerate(c_right)])

if state.get('last_event_msg'):
    icon_tag = ""
    if state.get('last_event_icon'):
        b64_str = get_cached_base64_image(state['last_event_icon'])
        if b64_str:
            icon_cls = "popup-icon"
            dir_icons = ["KB_start_raid.png", "kB_raider_out.png", "KB_line_cut.png", "KB_substitution.png"]
            if state['last_event_icon'] in dir_icons and (active_r_team == right_team):
                icon_cls += " flip-horizontal"
            icon_tag = f"<img class='{icon_cls}' src='data:image/png;base64,{b64_str}'>"
    html += f"<div class='court-popup'>{icon_tag}<div>{state['last_event_msg']}</div></div>"
    st.components.v1.html("""
        <script>
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            if(ctx.state === 'suspended') ctx.resume();
            const osc = ctx.createOscillator();
            const gainNode = ctx.createGain();
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(800, ctx.currentTime);
            gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
            osc.connect(gainNode); gainNode.connect(ctx.destination);
            osc.start(); setTimeout(() => { osc.stop(); }, 400);
        </script>
    """, height=0)

html += '</div>'

html += get_sitting_block_html(right_team, out_right)
html += f'<div class="kb-bench">{"".join([make_dot(right_team, n, False) for n in b_right])}<div class="bench-title">BENCH</div></div></div>'

st.markdown(html, unsafe_allow_html=True)