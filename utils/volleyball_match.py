import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import json
import psycopg2.extras 
import time
import re


# ==========================================
# 🎵 १. साउन्ड र स्पिच इन्जिन (The Master Engine)
# ==========================================
def audio_name(name):
    if not name: return ""
    import re
    # नेपाली अक्षर र कोष्ठकहरू हटाउने
    clean = re.sub(r'[\u0900-\u097F]+|\(.*?\)', '', str(name))
    # 'Municipality' जस्ता लामा अङ्ग्रेजी शब्दहरू हटाउने
    clean = re.sub(r'(?i)\b(Rural Municipality|Municipality|Metropolitan City|Sub-Metropolitan City)\b', '', clean)
    
    # 💡 जादु: सबै क्यापिटल अक्षरलाई Title Case (पहिलो अक्षर ठूलो, अरू सानो) बनाउने
    return clean.strip().title()

def spell_num(n):
    n = int(n)
    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if n < 20: return ones[n]
    return tens[n // 10] + ("" if n % 10 == 0 else " " + ones[n % 10])

def set_audio(m_id, speech_text=None, beep_args=None):
    """अडियो र स्पिचलाई Queue मा राख्ने फङ्सन"""
    st.session_state[f"audio_q_{m_id}"] = {"speech": speech_text, "beep": beep_args}

# ==========================================
# 🏐 २. DB र खेलाडी तान्ने फङ्सनहरू
# ==========================================
def ensure_columns_exist():
    conn = db.get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='matches'")
        existing_columns = [row[0] for row in c.fetchall()]
        if 'score_summary' not in existing_columns: c.execute("ALTER TABLE matches ADD COLUMN score_summary TEXT")
        if 'winner_id' not in existing_columns: c.execute("ALTER TABLE matches ADD COLUMN winner_id TEXT")
        conn.commit()
    except Exception as e: conn.rollback()
    finally: c.close(); conn.close()

def fetch_team_players(event_code, team_name):
    conn = db.get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    clean_team = str(team_name).strip()
    c.execute("SELECT municipality_id FROM teams WHERE event_code=%s AND name LIKE %s", (event_code, f"%{clean_team}%"))
    team_info = c.fetchone()
    if team_info and team_info['municipality_id']:
        muni_id = team_info['municipality_id']
        c.execute("""SELECT p.id as player_id, p.name, r.jersey_no FROM registrations r JOIN players p ON r.player_id = p.id WHERE r.event_code = %s AND p.municipality_id = %s""", (event_code, muni_id))
        players = c.fetchall()
        c.close(); conn.close()
        if players: 
            return [{'player_id': p['player_id'], 'name': p['name'], 'jersey': str(p['jersey_no']) if p['jersey_no'] is not None and str(p['jersey_no']) != 'None' else ''} for p in players]
    c.close(); conn.close()
    return [{'player_id': None, 'name': f"Player {i}", 'jersey': ''} for i in range(1, 13)]


def load_match_state(event_code, m_id, p1, p2):
    s_key = f"vb_state_{m_id}"
    if s_key not in st.session_state:
        
        # 💡 १. डाटाबेसबाट पुरानो 'History' तान्ने प्रयास गर्ने
        conn = db.get_connection()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT live_state FROM matches WHERE match_no=%s AND event_code=%s", (m_id, event_code))
        row = c.fetchone()
        c.close(); conn.close()
        
        if row and row['live_state']:
            saved_state = row['live_state']
            if isinstance(saved_state, str):
                import json
                saved_state = json.loads(saved_state)
            
            # =========================================================
            # 💡 जादुई समाधान (JSON Bug Fix):
            # JSON ले सेभ गर्दा 1, 2, 3 लाई "1", "2", "3" (String) बनाइदिन्छ।
            # यसलाई फेरि नम्बरमै (Integer) परिवर्तन गर्नुपर्छ, नत्र कोड क्र्यास हुन्छ!
            # =========================================================
            if 'scores' in saved_state:
                saved_state['scores'] = {int(k): v for k, v in saved_state['scores'].items()}
            if 'timeouts' in saved_state:
                saved_state['timeouts'] = {int(k): v for k, v in saved_state['timeouts'].items()}
            
            # यदि पुरानो म्याचमा यी नयाँ सेटिङहरू छैनन् भने डिफल्ट हाल्दिने
            if 'settings' not in saved_state:
                saved_state['settings'] = {"points_per_set": 25, "deciding_set_pts": 15, "best_of": 3}
            if 'officials' not in saved_state:
                saved_state['officials'] = {"referee": "", "umpire": "", "mgr_a": "", "mgr_b": ""}
                
            st.session_state[s_key] = saved_state
            
        else:
            # 💡 २. यदि नयाँ म्याच हो भने मात्र Set 1 र 0-0 बाट सुरु गर्ने
            st.session_state[s_key] = {
                "setup_complete": False, "match_started": False,
                "p1_name": p1, "p2_name": p2,
                "current_set": 1, "sets_won": {p1: 0, p2: 0},
                "scores": {i: {p1: 0, p2: 0} for i in range(1, 6)},
                "timeouts": {i: {p1: 0, p2: 0} for i in range(1, 6)},
                "serving": p1, "status": "In Progress", 
                "settings": {"points_per_set": 25, "deciding_set_pts": 15, "best_of": 3},
                "roster": {p1: {}, p2: {}}, 
                "lineup": { p1: {"court": [], "bench": [], "captain": None, "libero": []}, p2: {"court": [], "bench": [], "captain": None, "libero": []} },
                "cards": {p1: {}, p2: {}},
                "libero_tracking": {p1: {"current_libero": None, "replaced_player": None}, p2: {"current_libero": None, "replaced_player": None}},
                "rally_completed": True, "substitutions": {p1: 0, p2: 0},
                "match_start_time": None,
                "officials": {"referee": "", "umpire": "", "mgr_a": "", "mgr_b": ""}
            }
    return s_key


def save_match_scores(event_code, match_id, state):
    ensure_columns_exist()
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE matches SET live_state=%s, score_summary=%s WHERE match_no=%s AND event_code=%s", (json.dumps(state), json.dumps(state), match_id, event_code))
    conn.commit(); c.close(); conn.close()
    

def update_match_winner_in_db(event_code, match_id, winner_name, winner_id, final_score_str, state):
    import json
    import streamlit as st
    try:
        conn = db.get_connection()
        c = conn.cursor()
        
        # १. विजेताको नगरपालिका ID पत्ता लगाउने (Winner Muni ID)
        winner_muni_id = None
        if winner_id:
            c.execute("SELECT municipality_id FROM teams WHERE id=%s", (winner_id,))
            res = c.fetchone()
            if res:
                # यदि डिक्सनरी हो भने डिक्सनरीबाट, नत्र इन्डेक्सबाट
                winner_muni_id = res['municipality_id'] if isinstance(res, dict) else res[0]
        
        # २. डाटाबेसमा ३ वटा मुख्य कुरा अपडेट गर्ने: status, winner_team_id, winner_muni_id
        # तपाईंको टेबलमा 'winner_name' नभएकोले यसलाई live_state र score_summary मा राख्छौँ
        c.execute("""
            UPDATE matches 
            SET 
                status='Completed',
                winner_team_id=%s, 
                winner_muni_id=%s, 
                live_state=%s, 
                score_summary=%s 
            WHERE match_no=%s AND event_code=%s
        """, (winner_id, winner_muni_id, json.dumps(state), final_score_str, match_id, event_code))
        
        conn.commit(); c.close(); conn.close()
    except Exception as e:
        st.error(f"🚨 डाटाबेस अपडेट एरर: {e}")

def update_live_tv(match_title, state, m_id=None):
    import utils.live_state as ls
    import json
    import time
    import streamlit as st
    
    try:
        teams = list(state.get('lineup', {}).keys())
        if len(teams) < 2: return
        t1, t2 = teams[0], teams[1]
        c_set = state.get('current_set', 1)
        
        if m_id is None:
            m_id = state.get('match_id', '')
            
        audio_data = st.session_state.get(f"audio_q_{m_id}")
        
        # 💡 जादु १: म्याच सकिएको हो कि होइन भनेर जाँच्ने
        is_match_completed = state.get('match_completed', False)
        
        # 💡 जादु २: म्यासेज र ब्यानरलाई अवस्था अनुसार अटो-कन्ट्रोल गर्ने
        if audio_data and "speech" in audio_data:
            
            # टिभीमा देखाउन छुट्टै म्यासेज (tv_msg) छ भने त्यो तान्ने, नत्र बोल्ने कुरा नै देखाउने
            banner_text = audio_data.get("tv_msg", audio_data["speech"])
            
            state['latest_event'] = {
                "id": int(time.time() * 1000),
                "type": "announcement",
                "speech": audio_data["speech"],     # 🔊 स्पिकरमा यो बज्छ (इमोजी नभएको)
                "banner_msg": banner_text,          # 📺 टिभीमा यो देखिन्छ (इमोजी भएको)
                "banner_color": "#facc15" 
            }
        elif is_match_completed:
            # म्याच सकिएपछि 'Set is running' नदेखाएर च्याम्पियन देखाउने
            winner_name = state.get('tv_celebration', {}).get('winner', 'Unknown')
            state['latest_event'] = {
                "id": int(time.time() * 1000),
                "type": "announcement",
                "speech": f"Match Completed. {winner_name} is the champion.",
                "banner_msg": f"🏆 Match Completed! Winner: {winner_name} 🏆",
                "banner_color": "#10b981" # हरियो रङ (विजेताको लागि)
            }
        else:
            # खेल चलिरहेको बेला मात्र यो देखाउने
            state['latest_event'] = {"speech": f"📢 Set {c_set} is running..."}
        
        # स्कोर र टाइमआउट तान्ने
        scores_dict = state.get('scores', {})
        current_scores = scores_dict.get(c_set, scores_dict.get(str(c_set), {}))
        timeouts_dict = state.get('timeouts', {})
        current_timeouts = timeouts_dict.get(c_set, timeouts_dict.get(str(c_set), {}))
        
        # state_json भित्र सबै कुरा (सेलिब्रेसन, अर्को यात्रा) अटोमेटिक जान्छ
        try: state_str = json.dumps(state)
        except: state_str = "{}"

        live_data = {
            "match_title": str(match_title) if match_title else "Live Volleyball",
            "team_a": str(t1),
            "team_b": str(t2),
            "score_a": int(current_scores.get(t1, 0)),
            "score_b": int(current_scores.get(t2, 0)),
            "sets_a": int(state.get('sets_won', {}).get(t1, 0)),
            "sets_b": int(state.get('sets_won', {}).get(t2, 0)),
            "timeout_a": int(current_timeouts.get(t1, 0)),
            "timeout_b": int(current_timeouts.get(t2, 0)),
            "serving": "A" if state.get('serving') == t1 else "B",
            "state_json": state_str
        }
        
        ls._save_state("vb_live_match", live_data)
        st.toast("📡 टिभी अपडेट भयो!", icon="📺")
        
    except Exception as e:
        st.error(f"🚨 Live TV Update Error: {e}")
# ==========================================
# 🏐 ३. अपरेटर कोर्ट UI
# ==========================================
def render_operator_court(state, p1, p2):
    left_team = p2 if state.get('ui_swapped', False) else p1
    right_team = p1 if state.get('ui_swapped', False) else p2
    
    st.markdown("""
    <style>
        .arena { display: flex; justify-content: center; align-items: center; width: 100%; gap: 15px; margin: 10px 0; }
        .bench { display: flex; flex-direction: column; gap: 5px; background: #334155; padding: 10px; border-radius: 10px; min-width: 55px; align-items: center; }
        .bench-title { color: white; font-size: 10px; font-weight: bold; margin-bottom: 5px; }
        .vb-court-op { display: flex; width: 100%; max-width: 650px; aspect-ratio: 2/1; background-color: #f17b37; border: 3px solid white; position: relative; box-shadow: 0 5px 10px rgba(0,0,0,0.2); }
        .net-line-op { position: absolute; top: -5px; bottom: -5px; left: 50%; width: 8px; background-color: #1e3a8a; transform: translateX(-50%); z-index: 10; border-left: 2px solid white; border-right: 2px solid white; }
        .half-op { width: 50%; height: 100%; position: relative; }
        .attack-left { position: absolute; top: 0; bottom: 0; right: 33.33%; border-right: 3px dashed white; }
        .attack-right { position: absolute; top: 0; bottom: 0; left: 33.33%; border-left: 3px dashed white; }
        
        /* 💡 जादु १: प्लेयर र नामलाई राख्ने Wrapper (कोर्ट र बेन्च दुवैको लागि छुट्टाछुट्टै) */
        .player-wrap-court { position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; z-index: 15; }
        .player-wrap-bench { position: relative; display: flex; flex-direction: column; align-items: center; margin-bottom: 8px; }
        
        /* 💡 जादु २: p-dot को पोजिसन हटाइयो ताकि यो Wrapper भित्र मज्जाले बसोस् */
        .p-dot { position: relative; width: 35px; height: 35px; border-radius: 50%; background: white; color: black; font-weight: bold; font-size: 14px; display: flex; justify-content: center; align-items: center; border: 2px solid #334155; box-shadow: 1px 1px 3px rgba(0,0,0,0.5); }
        .p-dot-bench { width: 30px; height: 30px; font-size: 12px; }
        
        .libero { background-color: #fbbf24 !important; color: #78350f !important; }
        .captain { border-style: double !important; border-width: 4px !important; border-color: #1e293b !important; }
        .serving-dot { border-color: #fbbf24 !important; box-shadow: 0 0 8px 3px #fbbf24 !important; }
        .card-badge { position: absolute; top: -4px; right: -4px; width: 12px; height: 16px; border-radius: 2px; border: 1px solid black; z-index: 20; }
        .card-Yellow { background-color: #fde047; }
        .card-Red { background-color: #ef4444; }
        
        /* 💡 जादु ३: नामको डिजाइन (Line सँग नजुधोस् भनेर Text Shadow राखिएको छ) */
        .p-name { font-size: 10px; color: white; text-shadow: 1px 1px 2px black, 0 0 3px black; font-weight: bold; margin-top: 3px; white-space: nowrap; text-align: center; line-height: 1.1; }
        /* 💡 जादु ४: बटन भित्रको टेक्स्ट र आइकनलाई ठ्याक्कै सेन्टरमा ल्याउने */
        div[data-testid="stButton"] button {
            display: flex !important;
            justify-content: center !important;
            align-items: center !important;
            text-align: center !important;
            gap: 5px !important; /* आइकन र अक्षरको बीचमा थोरै खाली ठाउँ */
        }
        
        /* बीचको कोलमलाई अझ चिटिक्क देखाउन */
        div[data-testid="column"]:nth-of-type(3) {
            padding: 0 10px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    pos_a = {0:("20%","80%"), 1:("80%","80%"), 2:("80%","50%"), 3:("80%","20%"), 4:("20%","20%"), 5:("40%","50%")}
    pos_b = {0:("80%","20%"), 1:("20%","20%"), 2:("20%","50%"), 3:("20%","80%"), 4:("80%","80%"), 5:("60%","50%")}

    def make_dot(team, num, is_court=True, idx=-1, is_left_side=True):
        is_lib = num in state['lineup'][team]['libero']
        is_cap = num == state['lineup'][team]['captain']
        
        full_name = state['roster'][team].get(num, str(num))
        first_name = str(full_name).split()[0][:10] 
        
        # 💡 जादु २: नामबाट (C) र (L) हटाइयो (अब नाम एकदम सफा देखिन्छ)
        display_text = f"{first_name}"

        cls = ["p-dot"]
        if not is_court: cls.append("p-dot-bench")
        if is_lib: cls.append("libero")
        if is_cap: cls.append("captain")
        if is_court and state['serving'] == team and idx == 0: cls.append("serving-dot")
        
        pos_map = pos_a if is_left_side else pos_b
        inline_style = f"left:{pos_map[idx][0]}; top:{pos_map[idx][1]};" if is_court else ""
        wrapper_cls = "player-wrap-court" if is_court else "player-wrap-bench"
        
        # 💡 क्याप्टेन (C) र लिबेरो (L) को लागि सानो ब्याजहरू
        cap_badge_html = '<div style="position:absolute; top:-5px; left:-5px; background:#2563eb; color:white; font-size:9px; font-weight:bold; width:15px; height:15px; border-radius:50%; display:flex; justify-content:center; align-items:center; border:1px solid white; z-index:15; box-shadow: 0 1px 2px rgba(0,0,0,0.5);" title="Captain">C</div>' if is_cap else ""
        lib_badge_html = '<div style="position:absolute; bottom:-5px; right:-5px; background:#ea580c; color:white; font-size:9px; font-weight:bold; width:15px; height:15px; border-radius:50%; display:flex; justify-content:center; align-items:center; border:1px solid white; z-index:15; box-shadow: 0 1px 2px rgba(0,0,0,0.5);" title="Libero">L</div>' if is_lib else ""
        
        card = state['cards'][team].get(num)
        card_html = f'<div class="card-badge card-{card}" title="{card} Card"></div>' if card else ""
        
        # HTML निर्माण
        dot_div = f'<div class="{" ".join(cls)}" title="{full_name}">{cap_badge_html}{lib_badge_html}{num}{card_html}</div>'
        name_div = f'<div class="p-name" title="{full_name}">{display_text}</div>'
        
        return f'<div class="{wrapper_cls}" style="{inline_style}">{dot_div}{name_div}</div>'

    html = '<div class="arena">'
    html += f'<div class="bench"><div class="bench-title">BENCH</div>{"".join([make_dot(left_team, n, False) for n in state["lineup"][left_team]["bench"]])}</div>'
    html += '<div class="vb-court-op"><div class="net-line-op"></div>'
    html += '<div class="half-op"><div class="attack-left"></div>' + "".join([make_dot(left_team, n, True, i, is_left_side=True) for i, n in enumerate(state['lineup'][left_team]['court'])]) + '</div>'
    html += '<div class="half-op"><div class="attack-right"></div>' + "".join([make_dot(right_team, n, True, i, is_left_side=False) for i, n in enumerate(state['lineup'][right_team]['court'])]) + '</div>'
    html += '</div>'
    html += f'<div class="bench"><div class="bench-title">BENCH</div>{"".join([make_dot(right_team, n, False) for n in state["lineup"][right_team]["bench"]])}</div></div>'
    st.markdown(html, unsafe_allow_html=True)

# ==========================================
# 🏐 ४. मुख्य रेन्डर फङ्सन (Full Match Control)
# ==========================================
def render_match(event_code, match):


    m_id, p1, p2 = match['id'], match['p1'], match['p2']

    # ==========================================
    # 🔍 डिबग: अडियो क्यूको अवस्था ट्र्याक गर्ने
    # ==========================================
    if 'debug' not in st.session_state:
        st.session_state.debug = {}
        
    st.session_state.debug['audio_q_exists'] = f"audio_q_{m_id}" in st.session_state
    
    if f"audio_q_{m_id}" in st.session_state:
        st.session_state.debug['audio_q'] = st.session_state[f"audio_q_{m_id}"]
    else:
        st.session_state.debug['audio_q'] = "No Audio in Queue"
    # ==========================================
    
    conn = db.get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    c.execute("SELECT name, gender FROM events WHERE code=%s", (event_code,))
    evt_info = c.fetchone()
    c.close(); conn.close()
    
    match_title = f"{evt_info['name']} ({evt_info['gender']}) - Match #{m_id}" if evt_info else f"Volleyball Match #{m_id}"
    s_key = load_match_state(event_code, m_id, p1, p2) 
    state = st.session_state[s_key]

    # Ensure match_completed flag exists
    if 'match_completed' not in state:
        state['match_completed'] = False

    # ==============================================================
    # 🔊 जादुई साउन्ड रनर (Unique ID & Iframe Bypass)
    # ==============================================================
    import streamlit.components.v1 as components
    import time # 💡 समय तान्नको लागि
    
    audio_q = st.session_state.pop(f"audio_q_{m_id}", None)
    if audio_q:
        bp = audio_q.get('beep')
        sp = audio_q.get('speech', '')
        
        b_freq = bp[0] if bp else 800
        b_dur = bp[1] if bp else 0.2
        b_rep = bp[2] if bp else 1
        b_pause = bp[3] if bp else 0.2
        b_type = bp[4] if (bp and len(bp) > 4) else 'normal'
        has_beep = 'true' if bp else 'false'
        
        sp_clean = str(sp).replace("'", "\\'").replace('"', '\\"').replace('\n', ' ').strip()
        
        # 💡 मुख्य जादु: हरेक मिलिसेकेन्डमा नयाँ आइडी! यसले Streamlit लाई सधैँ नयाँ कोड हो भनी झुक्याउँछ।
        unique_id = str(time.time()).replace(".", "") 
        
        js_code = f"""
        <div id="audio_trigger_{unique_id}" style="display:none;"></div>
        <script>
            (function() {{
                var p = window.parent || window;
                var hasBeep = {has_beep};
                var beepTime = 0;
                
                // 🔊 भाग १: सिट्ठी (Beep)
                if(hasBeep) {{
                    try {{
                        var ctx = new (p.AudioContext || p.webkitAudioContext)();
                        var osc = ctx.createOscillator(), gain = ctx.createGain();
                        osc.connect(gain); gain.connect(ctx.destination); osc.type = 'sine';
                        if('{b_type}' === 'descend') {{
                            osc.frequency.setValueAtTime({b_freq}, ctx.currentTime);
                            osc.frequency.exponentialRampToValueAtTime({b_freq}/2, ctx.currentTime + {b_dur});
                        }} else {{
                            osc.frequency.value = {b_freq};
                        }}
                        gain.gain.setValueAtTime(0.1, ctx.currentTime);
                        gain.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + {b_dur});
                        osc.start(); osc.stop(ctx.currentTime + {b_dur});
                        beepTime = {b_dur} * 1000 + 100; 
                    }} catch(e) {{
                        console.log("Beep Blocked:", e);
                        beepTime = 0; 
                    }}
                }}
                
                // 🗣️ भाग २: स्पिच (Speech) - यो जसरी पनि चल्छ!
                var txt = "{sp_clean}";
                if(txt) {{
                    p.setTimeout(() => {{
                        try {{
                            var synth = p.speechSynthesis;
                            if(synth) {{
                                synth.cancel(); // पुरानो आवाज मेटाउने
                                var u = new p.SpeechSynthesisUtterance(txt);
                                u.lang = 'hi-IN'; // 💡 इन्डियन टोन (English)
                                u.rate = 1.0;
                                p.__my_utterance = u; 
                                synth.speak(u);
                            }}
                        }} catch(e) {{
                            console.log("Speech Error:", e);
                        }}
                    }}, beepTime);
                }}
            }})();
        </script>
        """
        # 💡 उचाइ १ राख्नैपर्छ नत्र क्रोमले ब्लक गर्छ
        components.html(js_code, height=1, width=1)

    if state['status'] != "Completed":
        can_edit = (state['current_set'] == 1 and state['scores'][1][p1] == 0 and state['scores'][1][p2] == 0)
        with st.expander("⚙️ म्याच नियम (Rules)", expanded=can_edit):
            # 💡 ३ वटा कोलम बनाइएको
            cr1, cr2, cr3 = st.columns(3)
            
            # कुन भ्यालु सेभ छ, त्यसैलाई डिफल्ट देखाउने लजिक
            cur_pts = state['settings'].get('points_per_set', 25)
            cur_dec = state['settings'].get('deciding_set_pts', 15)
            cur_bst = state['settings'].get('best_of', 3)
            
            n_pts = cr1.selectbox("सामान्य सेट (Points):", [25, 21, 15], index=[25, 21, 15].index(cur_pts) if cur_pts in [25, 21, 15] else 0)
            n_dec = cr2.selectbox("निर्णायक सेट (Deciding):", [15, 21, 25], index=[15, 21, 25].index(cur_dec) if cur_dec in [15, 21, 25] else 0)
            n_bst = cr3.selectbox("फर्म्याट (Format):", [3, 5], index=[3, 5].index(cur_bst) if cur_bst in [3, 5] else 0, format_func=lambda x: f"Best of {x}")
            
            if st.button("💾 अपडेट नियम", type="primary", use_container_width=True):
                state['settings']['points_per_set'] = n_pts
                state['settings']['deciding_set_pts'] = n_dec  # 💡 नयाँ रुल सेभ भयो
                state['settings']['best_of'] = n_bst
                save_match_scores(event_code, m_id, state)
                st.toast("✅ म्याचको नियम अपडेट भयो!")
                st.rerun()

    if state['status'] == "Completed":
        st.success(f"✅ यो म्याच सम्पन्न भइसकेको छ।")
        return

    # -------------------------------------------------------------
    # PHASE 1: LINE-UP MANAGER 
    # -------------------------------------------------------------
    if not state.get("setup_complete"):
        st.info(f"📋 **Set {state['current_set']} को लागि भलिबल लाइन-अप तयार गर्नुहोस्।**")
        c_t1, c_t2 = st.columns(2)
        
        def setup_team(team_name, col):
            with col:
                st.markdown(f"### 🏐 {team_name}")
                players_data = fetch_team_players(event_code, team_name)
                
                # 💡 जादु १: खेलाडीको नाम र ID को गोप्य म्यापिङ बनाउने
                id_map = {p['name']: p['player_id'] for p in players_data}
                
                df_key = f"vb_setup_v2_{m_id}_{team_name}_{state['current_set']}"
                
                if df_key not in st.session_state:
                    df_data = []
                    for i, p in enumerate(players_data):
                        df_data.append({
                            "Player Name": p['name'], "Jersey": p['jersey'], # 💡 यहाँ player_id राखिएन (ताकि Streamlit ले नमेटोस्)
                            "1": True if i == 0 else False, "2": True if i == 1 else False,
                            "3": True if i == 2 else False, "4": True if i == 3 else False,
                            "5": True if i == 4 else False, "6": True if i == 5 else False,
                            "L": True if i == 6 else False, "C": True if i == 0 else False
                        })
                    st.session_state[df_key] = pd.DataFrame(df_data)
                
                config = {
                    "Player Name": st.column_config.TextColumn("नाम", disabled=True), 
                    "Jersey": st.column_config.TextColumn("जर्सी", disabled=False, required=True, max_chars=3), 
                    "1": st.column_config.CheckboxColumn("1"), "2": st.column_config.CheckboxColumn("2"),
                    "3": st.column_config.CheckboxColumn("3"), "4": st.column_config.CheckboxColumn("4"),
                    "5": st.column_config.CheckboxColumn("5"), "6": st.column_config.CheckboxColumn("6"),
                    "L": st.column_config.CheckboxColumn("L"), "C": st.column_config.CheckboxColumn("C")
                }
                
                edited_df = st.data_editor(st.session_state[df_key], column_config=config, num_rows="fixed", key=f"vb_ed_mat_{m_id}_{team_name}_{state['current_set']}", width="stretch", hide_index=True)
                
                valid, error_msg = True, ""
                role_cols = ["1", "2", "3", "4", "5", "6", "L"]
                edited_df['Role_Count'] = edited_df[role_cols].sum(axis=1)
                
                if (edited_df['Role_Count'] > 1).any(): valid, error_msg = False, "एक जना खेलाडीलाई एउटा मात्र पोजिसन दिन मिल्छ।"
                if valid:
                    for pos in ["1", "2", "3", "4", "5", "6"]:
                        if edited_df[pos].sum() != 1: valid, error_msg = False, f"पोजिसन '{pos}' मा ठ्याक्कै १ जना हुनुपर्छ।"; break
                if valid and edited_df["L"].sum() > 2: valid, error_msg = False, "बढीमा २ जना मात्र लिबेरो राख्न मिल्छ।"
                if valid and edited_df["C"].sum() != 1: valid, error_msg = False, "ठ्याक्कै १ जना क्याप्टेन (C) हुनुपर्छ।"
                if valid:
                    active_players = edited_df[edited_df['Role_Count'] == 1]
                    if active_players['Jersey'].str.strip().eq("").any() or active_players['Jersey'].isna().any():
                        valid, error_msg = False, "कोर्टमा जाने खेलाडीको जर्सी नम्बर खाली छ।"
                
                if valid:
                    clean_df = edited_df[edited_df['Player Name'].str.strip() != ""]
                    roster = {str(row['Jersey']).strip(): row['Player Name'] for _, row in clean_df.iterrows() if str(row['Jersey']).strip() != ""}
                    starters = [""] * 6
                    for i, pos in enumerate(["1", "2", "3", "4", "5", "6"]):
                        j_num = clean_df[clean_df[pos] == True]['Jersey'].iloc[0]
                        starters[i] = str(j_num).strip()
                        
                    liberos = clean_df[clean_df["L"] == True]['Jersey'].astype(str).str.strip().tolist()
                    cap_j = str(clean_df[clean_df['C'] == True]['Jersey'].iloc[0]).strip()
                    bench = [j for j in roster.keys() if j not in starters]
                    
                    return roster, starters, liberos, bench, cap_j, clean_df, id_map
                else:
                    st.error(f"⚠️ {error_msg}")
                    return None, [], [], [], None, None, {}

        ta_rost, ta_start, ta_lib, ta_bench, ta_cap, ta_df, ta_id_map = setup_team(p1, c_t1)
        tb_rost, tb_start, tb_lib, tb_bench, tb_cap, tb_df, tb_id_map = setup_team(p2, c_t2)

        # 📋 रेफ्री र म्यानेजरको जानकारी
        st.markdown("---")
        st.subheader("👥 Match Officials & Managers")
        o_col1, o_col2 = st.columns(2)
        if 'officials' not in state: state['officials'] = {}
        state['officials']['referee'] = o_col1.text_input("First Referee:", state['officials'].get('referee', ''))
        state['officials']['umpire'] = o_col2.text_input("Second Referee (Umpire):", state['officials'].get('umpire', ''))
        state['officials']['mgr_a'] = o_col1.text_input(f"{p1} Manager:", state['officials'].get('mgr_a', ''))
        state['officials']['mgr_b'] = o_col2.text_input(f"{p2} Manager:", state['officials'].get('mgr_b', ''))

        st.divider()
        if len(ta_start) == 6 and len(tb_start) == 6:
            btn_lbl = "🚀 म्याच सुरु गर्नुहोस् (Start Match)" if state['current_set'] == 1 else f"🚀 Set {state['current_set']} सुरु गर्नुहोस्"
            if st.button(btn_lbl, type="primary", width="stretch"):
                
                # 💾 जर्सी नम्बर मुख्य डाटाबेसमा अटोमेटिक अपडेट गर्ने 
                conn = db.get_connection()
                c = conn.cursor()
                for df, id_map in [(ta_df, ta_id_map), (tb_df, tb_id_map)]:
                    if df is not None:
                        for _, row in df.iterrows():
                            p_name = row['Player Name']
                            p_id = id_map.get(p_name)
                            if p_id:
                                j_no = str(row['Jersey']).strip() if pd.notna(row['Jersey']) and str(row['Jersey']).strip() != "" else None
                                c.execute("UPDATE registrations SET jersey_no = %s WHERE player_id = %s AND event_code = %s", 
                                          (j_no, p_id, event_code))
                conn.commit(); c.close(); conn.close()
                st.toast("✅ जर्सी नम्बरहरू डाटाबेसमा सुरक्षित भए!")

                state['roster'][p1], state['roster'][p2] = ta_rost, tb_rost
                state['lineup'][p1] = {"court": ta_start, "bench": ta_bench, "captain": ta_cap, "libero": ta_lib}
                state['lineup'][p2] = {"court": tb_start, "bench": tb_bench, "captain": tb_cap, "libero": tb_lib}
                state["setup_complete"] = True
                state['match_started'] = True
                state['whistle_blown'] = False
                
                # 📺 १. टिभीको लागि स्थायी म्यासेज सेट गर्ने (इमोजीसहित)
                state['latest_event'] = {"tv_msg": f"📢 PREPARING FOR SET {state['current_set']}..."}
                
                # 🎤 टिम र रेफ्रीको नाम तान्ने
                t1_name = audio_name(p1)
                t2_name = audio_name(p2)
                ref1 = state.get('officials', {}).get('referee', '').strip()
                ref2 = state.get('officials', {}).get('umpire', '').strip()
                
                # 💡 रेफ्रीको नाम छ भने मात्र वाक्यमा जोड्ने
                ref_speech = ""
                if ref1 and ref2:
                    ref_speech = f" First referee is {ref1}, and second referee is {ref2}."
                elif ref1:
                    ref_speech = f" First referee is {ref1}."
                
                # 🔊 २. स्पिकरलाई बोल्न र २ पटक सिट्ठी बजाउन अर्डर दिने
                full_speech = f"Preparing for set {state['current_set']} between {t1_name} and {t2_name}.{ref_speech} Teams, please take your positions."
                
                st.session_state[f"audio_q_{m_id}"] = {
                    "speech": full_speech, 
                    "beep": (800, 0.4, 2, 0.2, 'normal')
                }
                
                save_match_scores(event_code, m_id, state)
                try: update_live_tv(match_title, state, m_id=m_id)
                except: pass
                st.rerun()
        return

    # -------------------------------------------------------------
    # PHASE 2: LIVE MATCH CONTROL (NEW FINISHING STYLE)
    # -------------------------------------------------------------
    c_set = state['current_set']
    
    # 💡 ब्याकवार्ड कम्प्याटिबिलिटी (पुरानो चलिरहेको म्याच छ भने नबिग्रियोस् भनेर)
    if state['scores'][c_set][p1] > 0 or state['scores'][c_set][p2] > 0:
        state['whistle_blown'] = True


    # 🔍 डिबग जानकारीलाई साइडबारमा देखाउने
    with st.sidebar.expander("🔍 डिबग जानकारी (Audio Tracking)", expanded=True):
        st.write("**अडियो क्यू अवस्था:**")
        st.json(st.session_state.debug) # 💡 json ले अझै प्रस्ट देखाउँछ
        
# ==========================================================
    # 💡 जादु: टस र सिट्ठीको प्यानल (Toss & Whistle Panel)
    # ==========================================================
    if not state.get('whistle_blown', False):
        st.markdown("---")
        
        is_deciding = (c_set == state['settings'].get('best_of', 3))
        if c_set == 1 or is_deciding:
            panel_title = f"🪙 Set {c_set} : Toss & First Serve"
            panel_desc = "टस जित्ने वा सर्भिस रोज्ने टिम छान्नुहोस्। रेफ्रीले सिट्ठी फुकेपछि घडी सुरु हुनेछ।"
        else:
            panel_title = f"🏐 Set {c_set} : First Serve"
            panel_desc = "नियम अनुसार (पालैपालो) यो सेटमा पहिलो सर्भिस गर्ने टिम छान्नुहोस्। सिट्ठी फुकेपछि घडी सुरु हुनेछ।"
            
        st.markdown(f"<h3 style='text-align:center; color:#facc15;'>{panel_title}</h3>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns([1, 2, 1])
        with c2:
            st.info(panel_desc)
            first_serve = st.radio("पहिलो सर्भिस कुन टिमको?", [p1, p2], horizontal=True)
            
            if st.button("🌬️ सिट्ठी फुक्नुहोस् (Blow Whistle & Start)", type="primary", use_container_width=True):
                state['serving'] = first_serve
                state['whistle_blown'] = True
                
                # 💡 बग फिक्स: हरेक सेटको सुरुमा टाइमर सेट गर्ने (घडी क्र्यास हुनबाट बचाउने)
                state['match_start_time'] = int(time.time() * 1000)
                
                if c_set == 1:
                    set_audio(m_id, speech_text=f"Match begins. {audio_name(first_serve)} to serve.", beep_args=(1200, 0.8, 1, 0, 'normal'))
                elif is_deciding:
                    set_audio(m_id, speech_text=f"Deciding set begins. {audio_name(first_serve)} to serve.", beep_args=(1200, 0.8, 1, 0, 'normal'))
                else:
                    set_audio(m_id, speech_text=f"Set {c_set} begins. {audio_name(first_serve)} to serve.", beep_args=(1200, 0.8, 1, 0, 'normal'))
                
                state['latest_event'] = {"speech": f"📣 MATCH STARTED: {first_serve[:12]} to serve!"}
                
                save_match_scores(event_code, m_id, state)
                try: update_live_tv(match_title, state, m_id=m_id)
                except: pass
                st.rerun()
                
        st.markdown("<br>", unsafe_allow_html=True)
        render_operator_court(state, p1, p2)
        return  # 🛑 यो नथिचेसम्म तलको स्कोर प्यानल लोड हुँदैन!
    # ==========================================================

    c_set = state['current_set']
    
    # 🏆 SET & MATCH WINNING LOGIC
    target_pts = state['settings'].get('points_per_set', 25)
    deciding_pts = state['settings'].get('deciding_set_pts', 15) # 💡 नयाँ रुल तान्ने
    best_of = state['settings'].get('best_of', 3)
    
    req_sets_to_win = (best_of // 2) + 1  
    
    # 💡 अब हार्डकोड '15' को सट्टा 'deciding_pts' प्रयोग हुन्छ
    actual_target = deciding_pts if c_set == best_of else target_pts 
    
    score_a = state['scores'][c_set][p1]
    score_b = state['scores'][c_set][p2]
    
    set_winner = None
    if score_a >= actual_target and (score_a - score_b) >= 2:
        set_winner = p1
    elif score_b >= actual_target and (score_b - score_a) >= 2:
        set_winner = p2

    # ⏱️ घडीको समय तान्ने (Python Crash-Proof & Auto Countdown)
    import time
    start_ts = state.get('match_start_time')
    if not start_ts:
        start_ts = int(time.time() * 1000)
        state['match_start_time'] = start_ts
        state['last_start_time'] = start_ts
        state['accumulated_time'] = 0
        state['clock_paused'] = False
        
    # 💡 जादु १: पाइथनलाई क्र्यास हुनबाट बचाउने एकदम सुरक्षित तरिका (None आयो भने 0 बनाउने)
    raw_acc = state.get('accumulated_time')
    acc_time = int(raw_acc) if raw_acc else 0
    
    raw_last = state.get('last_start_time')
    last_start = int(raw_last) if raw_last else start_ts
    
    is_paused = 1 if state.get('clock_paused') else 0

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center; background:#1e293b; padding:10px 20px; border-radius:10px; border-bottom:4px solid #3b82f6; margin-bottom:10px;">
        <h3 style="margin:0; color:white;">🏐 Set {c_set} | 🔴 {audio_name(p1)} vs 🔵 {audio_name(p2)}</h3>
        <div style="background:#0f172a; color:#fbbf24; padding:5px 15px; border-radius:8px; border:2px solid #475569; font-family:monospace; font-size:22px; font-weight:bold;">
            ⏱️ <span id="main_clock_{m_id}">00:00</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # 💡 जादु २: पुरानै ढाँचामा उल्टो घडी र अटो-क्लिक लजिक मिसाइएको
    clock_js = f"""
    <script>
        (function() {{
            var stTime = {last_start};
            var accTime = {acc_time};
            var isP = {is_paused};
            var clockId = "main_clock_{m_id}";
            var parentWin = window.parent;
            var lastCdRem = -1; // 💡 काउन्टडाउन ट्र्याक गर्ने नयाँ रिएबल
            
            if(parentWin['timer_' + clockId]) clearInterval(parentWin['timer_' + clockId]);
            
            parentWin['timer_' + clockId] = setInterval(function() {{
                try {{
                    var now = Date.now();
                    var diffMs = accTime;
                    var cdRem = 0;
                    
                    if (isP === 0) {{
                        if (now < stTime) {{
                            // भविष्यको समय छ भने काउन्टडाउन चल्छ
                            cdRem = Math.ceil((stTime - now) / 1000);
                        }} else {{
                            // नत्र साधारण घडी चल्छ
                            diffMs += (now - stTime);
                        }}
                    }}
                    
                    // ==========================================
                    // 🤖 JS अटोमेसन: ० सेकेन्ड पुग्दा आफैँ बटन थिच्ने!
                    // ==========================================
                    if (lastCdRem > 0 && cdRem === 0) {{
                        var btns = parentWin.document.querySelectorAll('button');
                        for (var i=0; i<btns.length; i++) {{
                            // 'T/O Over' लेखिएको बटन खोजेर क्लिक गर्ने
                            if (btns[i].innerText.includes('T/O Over')) {{
                                btns[i].click(); 
                                break;
                            }}
                        }}
                    }}
                    lastCdRem = cdRem; // अर्को सेकेन्डको लागि सेभ गर्ने
                    // ==========================================
                    
                    var el = parentWin.document.getElementById(clockId);
                    if(el) {{ 
                        if (cdRem > 0) {{
                            // 🔴 टाइमआउटमा रातो रङको उल्टो घडी
                            el.innerText = '⏳ ' + cdRem + 's';
                            el.style.color = '#ef4444';
                        }} else {{
                            // 🟡 साधारण अवस्थामा पहेँलो रङको घडी
                            var diffSec = Math.floor(diffMs / 1000);
                            if (diffSec < 0) diffSec = 0;
                            var m = String(Math.floor(diffSec / 60)).padStart(2, '0');
                            var s = String(diffSec % 60).padStart(2, '0');
                            el.innerText = (isP === 1) ? '⏸️ ' + m + ':' + s : m + ':' + s;
                            el.style.color = '#fbbf24';
                        }}
                    }}
                }} catch(e) {{}}
            }}, 1000);
        }})();
    </script>
    """
    import streamlit.components.v1 as components
    components.html(clock_js, height=0, width=0)


    # ==========================================================
    # 💡 जादु: निर्णायक सेटमा कोर्ट साट्ने (Court Switch) लजिक
    # ==========================================================
    is_deciding_set = (c_set == best_of)
    switch_pt = (deciding_pts // 2) + 1  
    
    # 💡 बग फिक्स: '==' को सट्टा '>=' राखिएको छ, ताकि अङ्क १४ पुगे पनि यो म्यासेज नहराओस्!
    if is_deciding_set and (score_a >= switch_pt or score_b >= switch_pt) and not state.get('deciding_court_switched', False):
        
        st.markdown(f"""
        <div style="background-color: #f59e0b; padding: 15px; border-radius: 10px; text-align: center; border: 3px solid #b45309; margin-bottom: 15px; animation: blinker 1.5s linear infinite;">
            <h2 style="color: white; margin: 0; text-shadow: 1px 1px 2px black;">⚠️ COURT SWITCH! ({switch_pt} POINTS)</h2>
            <p style="color: white; font-weight: bold; margin: 0;">निर्णायक सेटमा {switch_pt} अङ्क पुग्यो। कृपया कोर्ट साट्नुहोस्!</p>
        </div>
        <style>@keyframes blinker {{ 50% {{ opacity: 0.7; }} }}</style>
        """, unsafe_allow_html=True)
        
        if st.button("🔄 Swap Courts Now (कोर्ट साट्नुहोस्)", type="primary", use_container_width=True):
            state['ui_swapped'] = not state.get('ui_swapped', False)
            state['tv_swapped'] = not state.get('tv_swapped', False)
            state['deciding_court_switched'] = True
            
            # 💡 को अगाडि छ (Leader) र को पछाडि छ (Trailer) भनेर आफैँ पत्ता लगाउने
            score_p1 = state['scores'][c_set][p1]
            score_p2 = state['scores'][c_set][p2]
            
            if score_p1 > score_p2:
                lead_team, trail_team = p1, p2
            else:
                lead_team, trail_team = p2, p1
            
            lead_name = audio_name(lead_team)
            lead_pts = state['scores'][c_set][lead_team]
            trail_name = audio_name(trail_team)
            trail_pts = state['scores'][c_set][trail_team]
            
            # 🎤 एकदमै कडा र प्रोफेसनल एनाउन्समेन्ट स्क्रिप्ट
            swap_speech = f"Attention please! Court change. {lead_name} has reached {lead_pts} points. The score is {lead_pts} to {trail_pts}. Both teams, please switch your courts immediately without delay. You have 30 seconds. Hurry up!"
            
            # 🔊 ३ पटक छिटो-छिटो कडा सिट्ठी बजाउने र फलाक्ने
            st.session_state[f"audio_q_{m_id}"] = {
                "speech": swap_speech, 
                "beep": (1200, 0.3, 3, 0.1, 'normal')
            }
            state['latest_event'] = {"speech": "🔄 TEAMS ARE CHANGING COURTS!"}
            
            save_match_scores(event_code, m_id, state)
            try: update_live_tv(match_title, state, m_id=m_id)
            except: pass
            st.rerun()

    # ==============================================================
    # ACTION FUNCTIONS (Audio-Safe Version)
    # ==============================================================
    def action_point(scorer, loser):
        state['scores'][c_set][scorer] += 1
        state['rally_completed'] = True 
        score_s = state['scores'][c_set][scorer]
        score_l = state['scores'][c_set][loser]
        spoken_team = audio_name(scorer)
        
        # 💡 अडियो सुरक्षित राख्ने भाँडो
        audio_data = {} 
        
        if state['serving'] != scorer:
            state['serving'] = scorer
            c = state['lineup'][scorer]['court']
            state['lineup'][scorer]['court'] = [c[1], c[2], c[3], c[4], c[5], c[0]]
            audio_data = {"speech": f"Service change, {spoken_team}. {spell_num(score_s)}, {spell_num(score_l)}.", "beep": (800, 0.15, 1, 0, 'normal')}
            
            track = state['libero_tracking'][scorer]
            if track['current_libero']:
                curr_lib = track.get('current_libero')
                court_players = state['lineup'][scorer]['court']

                if curr_lib and curr_lib in court_players:
                    lib_idx = court_players.index(curr_lib)
                else:
                    lib_idx = -1 
                    track['current_libero'] = None
                    
                if lib_idx in [1, 2, 3]: 
                    lib_j = state['lineup'][scorer]['court'][lib_idx]
                    rep_j = track['replaced_player']
                    rep_name = state['roster'][scorer].get(rep_j, '')
                    state['lineup'][scorer]['court'][lib_idx] = rep_j
                    track['current_libero'] = None; track['replaced_player'] = None
                    if rep_j in state['lineup'][scorer]['bench']: state['lineup'][scorer]['bench'].remove(rep_j)
                    if lib_j not in state['lineup'][scorer]['bench']: state['lineup'][scorer]['bench'].append(lib_j)
                    audio_data["speech"] += f" Libero out, {spoken_team}. Jersey {spell_num(rep_j)}, {rep_name} in."
                    st.toast(f"🔄 {scorer} को लिबेरो आउट, {rep_j} IN!")
        else:
            audio_data = {"speech": f"Point, {spoken_team}. {spell_num(score_s)}, {spell_num(score_l)}.", "beep": (800, 0.15, 1, 0, 'normal')}
            
        st.session_state[f"audio_q_{m_id}"] = audio_data.copy()
        save_match_scores(event_code, m_id, state)
        
        try: update_live_tv(match_title, state, m_id=m_id)
        except: pass
        
        # 💡 जादु: टिभीले खाएको भए पनि स्पिकरको लागि फेरि रिस्टोर गरिदिने!
        st.session_state[f"audio_q_{m_id}"] = audio_data.copy()

    def action_undo(team_name):
        if state['scores'][c_set][team_name] > 0:
            state['scores'][c_set][team_name] -= 1
            audio_data = {"speech": "Score corrected.", "beep": (500, 0.4, 1, 0, 'descend')}
            st.session_state[f"audio_q_{m_id}"] = audio_data.copy()
            save_match_scores(event_code, m_id, state)
            try: update_live_tv(match_title, state, m_id=m_id)
            except: pass
            st.session_state[f"audio_q_{m_id}"] = audio_data.copy() # 💡 Restore

    def action_to(team_name):
        import time
        used_to = state['timeouts'][c_set][team_name]
        if used_to < 2:
            state['timeouts'][c_set][team_name] += 1
            audio_data = {"tv_msg": f"⏳ TIME OUT: {team_name[:12]}", "speech": f"Time out, {audio_name(team_name)}.", "beep": (600, 0.3, 2, 0.2, 'normal')}
            st.session_state[f"audio_q_{m_id}"] = audio_data.copy()
            
            curr = int(time.time() * 1000)
            if not state.get('clock_paused', False):
                if curr > state.get('last_start_time', curr):
                    state['accumulated_time'] = state.get('accumulated_time', 0) + (curr - state.get('last_start_time', curr))
            
            state['clock_paused'] = False
            state['last_start_time'] = curr + 30000 
            
            save_match_scores(event_code, m_id, state)
            try: update_live_tv(match_title, state, m_id=m_id)
            except: pass
            
            st.session_state[f"audio_q_{m_id}"] = audio_data.copy() # 💡 Restore
        else:
            st.toast("❌ २ वटै टाइम-आउट सकियो!")

    left_team = p2 if state.get('ui_swapped', False) else p1
    right_team = p1 if state.get('ui_swapped', False) else p2

    def render_team_controls(team_name, col_obj, color_hex, is_p1):
        with col_obj:
            team_emoji = "🔴" if is_p1 else "🔵"
            short_name = audio_name(team_name)
            
            st.markdown(f"""
            <div style='text-align:center; padding: 12px 10px; background: {color_hex}11; border-radius: 8px; border: 2px solid {color_hex}44; margin-bottom: 12px;'>
                <span style='color:{color_hex}; font-size: 18px; font-weight: bold;'>{team_emoji} {short_name}</span>
            </div>
            <div style='text-align:center; padding: 25px 10px; background: #ffffff; border-radius: 12px; border: 3px solid {color_hex}88; margin-bottom: 20px; box-shadow: 0 4px 10px rgba(0,0,0,0.08); display: flex; justify-content: center; align-items: center; min-height: 250px;'>
                <span style='font-size:200px; font-weight: 900; color: {color_hex}; line-height: 1;'>{state['scores'][c_set][team_name]}</span>
            </div>
            """, unsafe_allow_html=True)
            
            if not set_winner and not state.get('match_completed'):
                
                opp_team = p2 if team_name == p1 else p1
                st.button(f"➕ Point", key=f"pt_{team_name}", type="primary", use_container_width=True, on_click=action_point, args=(team_name, opp_team))
                
                c_undo, c_to = st.columns(2)
                with c_undo: st.button("⏪ Undo", key=f"undo_{team_name}", use_container_width=True, on_click=action_undo, args=(team_name,))
                with c_to:
                    used_to = state['timeouts'][c_set][team_name]
                    st.button(f"⏳ T/O ({used_to}/2)", key=f"to_{team_name}", use_container_width=True, on_click=action_to, args=(team_name,))

    # ---------- Action panels ----------
    def render_team_actions(team_name, opp_team, col_obj):
        t_safe = team_name.replace(" ", "_").replace("-", "_")
        
        # 💡 जादु: कुन एक्सपाण्डर खुल्ला राख्ने भनेर ट्र्याक गर्ने फङ्सनहरू
        def set_open_exp(exp_name):
            st.session_state['active_exp'] = exp_name
            
        def close_exp():
            st.session_state['active_exp'] = None
            
        # हाल कुन एक्सपाण्डर एक्टिभ छ भनेर हेर्ने
        active_exp = st.session_state.get('active_exp')

        with col_obj:
            # ==========================================
            # १. Sub Expander
            # ==========================================
            with st.expander(f"🔄 Sub ({state['substitutions'][team_name]}/6){' ' * state.get(f't_sub_{t_safe}', 0)}", expanded=(active_exp == f"sub_{t_safe}")):
                cc1, cb1 = st.columns(2)
                valid_court_subs = [p for p in state['lineup'][team_name]['court'] if p not in state['lineup'][team_name]['libero']]
                valid_bench_subs = [p for p in state['lineup'][team_name]['bench'] if p not in state['lineup'][team_name]['libero']]
                
                # 💡 on_change थपियो, जसले रेडियो थिच्नासाथ यो एक्सपाण्डरलाई 'एक्टिभ' बनाउँछ
                op = cc1.radio("Out (Court):", valid_court_subs, key=f"cout_{t_safe}", on_change=set_open_exp, args=(f"sub_{t_safe}",), format_func=lambda x: f":red[**{x}**] • {state['roster'][team_name].get(x, '')[:12]}")
                ip = cb1.radio("In (Bench):", valid_bench_subs, key=f"bin_{t_safe}", on_change=set_open_exp, args=(f"sub_{t_safe}",), format_func=lambda x: f":green[**{x}**] • {state['roster'][team_name].get(x, '')[:12]}")
                
                if st.button("🔄 Swap Player", key=f"btn_sub_{t_safe}", type="primary", use_container_width=True):
                    if state['substitutions'][team_name] >= 6: st.error("❌ Max 6 subs reached!")
                    elif not op or not ip: st.warning("दुवै खेलाडी छान्नुहोस्!")
                    else:
                        close_exp() # 💡 काम सकिएपछि आफैँ बन्द गर्न कमान्ड!
                        c_idx, b_idx = state['lineup'][team_name]['court'].index(op), state['lineup'][team_name]['bench'].index(ip)
                        state['lineup'][team_name]['court'][c_idx], state['lineup'][team_name]['bench'][b_idx] = ip, op
                        state['substitutions'][team_name] += 1
                        ip_name = state['roster'][team_name].get(ip, '')
                        op_name = state['roster'][team_name].get(op, '')
                        speech_txt = f"Substitution, {audio_name(team_name)}. Jersey {spell_num(ip)}, {ip_name} in. Jersey {spell_num(op)}, {op_name} out."
                        st.session_state[f"audio_q_{m_id}"] = {"speech": speech_txt, "beep": (700, 0.2, 1, 0, 'normal'), "tv_msg": f"🔄 SUB ({team_name[:12]}): #{ip} {ip_name} IN, #{op} {op_name} OUT"}
                        state[f't_sub_{t_safe}'] = state.get(f't_sub_{t_safe}', 0) + 1
                        save_match_scores(event_code, m_id, state)
                        try: update_live_tv(match_title, state, m_id=m_id)
                        except: pass
                        st.toast(f"✅ Sub: {ip} IN, {op} OUT ({team_name})")
                        st.rerun()

            # ==========================================
            # २. Libero Expander
            # ==========================================
            with st.expander(f"🛡️ Libero{' ' * state.get(f't_lib_{t_safe}', 0)}", expanded=(active_exp == f"lib_{t_safe}")):
                if state['lineup'][team_name]['libero']:
                    track = state['libero_tracking'][team_name]
                    if track['current_libero'] is None:
                        court = state['lineup'][team_name]['court']
                        back_row_players = [court[0], court[4], court[5]] 
                        valid_out_for_libero = [p for p in back_row_players if p not in state['lineup'][team_name]['libero']]
                        
                        c_lin, c_lout = st.columns(2)
                        l_in = c_lin.radio("Libero IN:", state['lineup'][team_name]['libero'], key=f"lin_{t_safe}", on_change=set_open_exp, args=(f"lib_{t_safe}",), format_func=lambda x: f":green[**{x}**] • {state['roster'][team_name].get(x, '')[:12]}")
                        p_out = c_lout.radio("Player OUT:", valid_out_for_libero, key=f"lout_{t_safe}", on_change=set_open_exp, args=(f"lib_{t_safe}",), format_func=lambda x: f":red[**{x}**] • {state['roster'][team_name].get(x, '')[:12]}")
                        
                        if st.button("⬇️ Libero IN", key=f"btn_lin_{t_safe}", type="primary", use_container_width=True):
                            if not state.get('rally_completed', True): st.warning("⏳ र्याली नसकिई रिप्लेस गर्न मिल्दैन!")
                            elif not l_in or not p_out: st.warning("खेलाडी छान्नुहोस्!")
                            else:
                                close_exp() # 💡 क्लोज कमान्ड
                                c_idx = state['lineup'][team_name]['court'].index(p_out)
                                state['lineup'][team_name]['court'][c_idx] = l_in
                                track['current_libero'], track['replaced_player'] = l_in, p_out
                                state['rally_completed'] = False
                                if l_in in state['lineup'][team_name]['bench']: state['lineup'][team_name]['bench'].remove(l_in)
                                if p_out not in state['lineup'][team_name]['bench']: state['lineup'][team_name]['bench'].append(p_out)
                                l_in_name, p_out_name = state['roster'][team_name].get(l_in, ''), state['roster'][team_name].get(p_out, '')
                                speech_txt = f"Libero in, {audio_name(team_name)}. Libero {l_in}, {l_in_name}, replaces Jersey {spell_num(p_out)}, {p_out_name}."
                                st.session_state[f"audio_q_{m_id}"] = {"speech": speech_txt, "beep": (700, 0.2, 1, 0, 'normal'), "tv_msg": f"🛡️ LIBERO IN ({team_name[:12]}): #{l_in} {l_in_name} replaces #{p_out} {p_out_name}"}
                                state[f't_lib_{t_safe}'] = state.get(f't_lib_{t_safe}', 0) + 1
                                save_match_scores(event_code, m_id, state)
                                try: update_live_tv(match_title, state, m_id=m_id)
                                except: pass
                                st.toast(f"✅ Libero {l_in} IN!")
                                st.rerun()
                    else:
                        st.info(f"On Court: {track['current_libero']} | Replaced: {track['replaced_player']}")
                        if st.button("⬆️ Libero OUT", key=f"btn_lout_{t_safe}", use_container_width=True):
                            if not state.get('rally_completed', True): st.warning("⏳ र्याली नसकिई निकाल्न मिल्दैन!")
                            else:
                                close_exp() # 💡 क्लोज कमान्ड
                                lib_j, rep_j = track['current_libero'], track['replaced_player']
                                c_idx = state['lineup'][team_name]['court'].index(lib_j)
                                state['lineup'][team_name]['court'][c_idx] = rep_j
                                track['current_libero'], track['replaced_player'] = None, None
                                state['rally_completed'] = False
                                if rep_j in state['lineup'][team_name]['bench']: state['lineup'][team_name]['bench'].remove(rep_j)
                                if lib_j not in state['lineup'][team_name]['bench']: state['lineup'][team_name]['bench'].append(lib_j)
                                lib_name = state['roster'][team_name].get(lib_j, '')
                                rep_name = state['roster'][team_name].get(rep_j, '')
                                speech_txt = f"Libero out, {audio_name(team_name)}. Libero {lib_j}, {lib_name} out. Jersey {spell_num(rep_j)}, {rep_name} in."
                                st.session_state[f"audio_q_{m_id}"] = {"speech": speech_txt, "beep": (700, 0.2, 1, 0, 'normal'), "tv_msg": f"🛡️ LIBERO OUT ({team_name[:12]}): #{lib_j} {lib_name} out, #{rep_j} {rep_name} in"}
                                state[f't_lib_{t_safe}'] = state.get(f't_lib_{t_safe}', 0) + 1
                                save_match_scores(event_code, m_id, state)
                                try: update_live_tv(match_title, state, m_id=m_id)
                                except: pass
                                st.toast("✅ Libero OUT!")
                                st.rerun()
                else: st.caption("No libero assigned.")

            # ==========================================
            # ३. Fouls Expander
            # ==========================================
            with st.expander(f"❌ Fouls{' ' * state.get(f't_foul_{t_safe}', 0)}", expanded=(active_exp == f"foul_{t_safe}")):
                fault_type = st.radio("गल्तीको प्रकार:", ["Net Fault (नेट)", "Center Line Crossing (सेन्टर लाइन)", "Screening (FIVB)", "Double Contact (डबल)", "8-Second Fault (८ सेकेन्ड)"], key=f"ftype_{t_safe}", on_change=set_open_exp, args=(f"foul_{t_safe}",))
                if st.button("🚨 Issue Foul", key=f"btn_foul_{t_safe}", type="primary", use_container_width=True):
                    if not fault_type: st.warning("प्रकार छान्नुहोस्!")
                    elif "Double Contact" in fault_type: st.success("✅ New FIVB Rule: दोस्रो हिटमा डबल कन्ट्याक्ट फाउल मानिँदैन!")
                    else:
                        close_exp() # 💡 क्लोज कमान्ड
                        f_name = fault_type.split(" (")[0] 
                        st.session_state[f"audio_q_{m_id}"] = {"speech": f"{f_name}, {audio_name(team_name)}.", "beep": (1200, 0.4, 3, 0.2, 'normal'), "tv_msg": f"❌ FOUL ({team_name[:12]}): {f_name}"}
                        state['scores'][c_set][opp_team] += 1
                        state['rally_completed'] = True 
                        if state['serving'] != opp_team:
                            state['serving'] = opp_team
                            c = state['lineup'][opp_team]['court']
                            state['lineup'][opp_team]['court'] = [c[1], c[2], c[3], c[4], c[5], c[0]]
                            track = state['libero_tracking'][opp_team]
                            if track['current_libero']:
                                court_players = state['lineup'][opp_team]['court']
                                if track['current_libero'] in court_players:
                                    lib_idx = court_players.index(track['current_libero'])
                                    if lib_idx in [1, 2, 3]: 
                                        lib_j = court_players[lib_idx]
                                        rep_j = track['replaced_player']
                                        state['lineup'][opp_team]['court'][lib_idx] = rep_j
                                        track['current_libero'], track['replaced_player'] = None, None
                                        if rep_j in state['lineup'][opp_team]['bench']: state['lineup'][opp_team]['bench'].remove(rep_j)
                                        if lib_j not in state['lineup'][opp_team]['bench']: state['lineup'][opp_team]['bench'].append(lib_j)
                                        st.session_state[f"audio_q_{m_id}"]["speech"] += f" Libero out, {audio_name(opp_team)}."
                        state[f't_foul_{t_safe}'] = state.get(f't_foul_{t_safe}', 0) + 1
                        save_match_scores(event_code, m_id, state)
                        try: update_live_tv(match_title, state, m_id=m_id)
                        except: pass
                        st.toast(f"✅ {f_name} foul recorded for {team_name}!")
                        st.rerun()

            # ==========================================
            # ४. Cards Expander
            # ==========================================
            with st.expander(f"⚠️ Cards{' ' * state.get(f't_card_{t_safe}', 0)}", expanded=(active_exp == f"card_{t_safe}")):
                c_c1, c_c2 = st.columns(2)
                all_roster_p = list(state['roster'][team_name].keys())
                ps = c_c1.radio("Player:", all_roster_p, key=f"cp_{t_safe}", on_change=set_open_exp, args=(f"card_{t_safe}",), format_func=lambda x: f"{'🟥 ' if x not in state['lineup'][team_name]['court'] + state['lineup'][team_name]['bench'] else ':orange['}**{x}**{']' if x in state['lineup'][team_name]['court'] + state['lineup'][team_name]['bench'] else ''} • {state['roster'][team_name].get(x, '')[:12]}")
                cd = c_c2.radio("Card:", ["Yellow (चेतावनी)", "Red (पोइन्ट विपक्षीलाई)", "Expulsion (निष्कासन)", "Disqualified"], key=f"cc_{t_safe}", on_change=set_open_exp, args=(f"card_{t_safe}",))
                is_expelled = "Expulsion" in cd or "Disqualified" in cd
                is_on_court = ps in state['lineup'][team_name]['court']
                is_active = ps in state['lineup'][team_name]['court'] + state['lineup'][team_name]['bench']
                rep_player = None
                if is_expelled and is_on_court:
                    valid_rep_subs = [p for p in state['lineup'][team_name]['bench'] if p not in state['lineup'][team_name]['libero']]
                    rep_player = st.radio("Bench In:", valid_rep_subs, key=f"rep_{t_safe}", horizontal=True, on_change=set_open_exp, args=(f"card_{t_safe}",))

                btn_issue, btn_remove = st.columns(2)
                if btn_issue.button("🚨 Issue Card", key=f"btn_card_{t_safe}", type="primary", use_container_width=True):
                    if not ps or not cd: st.warning("खेलाडी र कार्ड छान्नुहोस्!")
                    elif is_expelled and is_on_court and not rep_player: st.warning("भित्र पठाउने खेलाडी छान्नुहोस्!")
                    elif not is_active and is_expelled: st.warning("यो खेलाडी पहिल्यै बाहिर छ!")
                    else:
                        close_exp() # 💡 क्लोज कमान्ड
                        card_key = cd.split(" ")[0] 
                        state['cards'][team_name][ps] = card_key
                        audio_data = {"tv_msg": f"⚠️ {card_key.upper()} CARD ({team_name[:12]}): #{ps} {state['roster'][team_name].get(ps, '')}"}
                        
                        if card_key == "Yellow": 
                            audio_data.update({"speech": f"Yellow card, {audio_name(team_name)}. Jersey {spell_num(ps)}.", "beep": (1000, 0.3, 1, 0, 'normal')})
                        elif card_key == "Red": 
                            audio_data.update({"speech": f"Red card, {audio_name(team_name)}. Jersey {spell_num(ps)}.", "beep": (1000, 0.3, 2, 0.1, 'normal')})
                            state['scores'][c_set][opp_team] += 1
                            state['rally_completed'] = True 
                            if state['serving'] != opp_team:
                                state['serving'] = opp_team
                                c = state['lineup'][opp_team]['court']
                                state['lineup'][opp_team]['court'] = [c[1], c[2], c[3], c[4], c[5], c[0]]
                        else: 
                            audio_data.update({"speech": f"{card_key}, {audio_name(team_name)}. Jersey {spell_num(ps)} is out.", "beep": (1000, 0.5, 3, 0.1, 'normal')})
                            if ps in state['lineup'][team_name]['bench']: state['lineup'][team_name]['bench'].remove(ps)
                            if is_on_court and rep_player:
                                c_idx = state['lineup'][team_name]['court'].index(ps)
                                state['lineup'][team_name]['court'][c_idx] = rep_player
                                state['lineup'][team_name]['bench'].remove(rep_player)
                                
                        st.session_state[f"audio_q_{m_id}"] = audio_data
                        state[f't_card_{t_safe}'] = state.get(f't_card_{t_safe}', 0) + 1
                        save_match_scores(event_code, m_id, state)
                        try: update_live_tv(match_title, state, m_id=m_id)
                        except: pass
                        st.session_state[f"audio_q_{m_id}"] = audio_data.copy() # 💡 Restore Audio for speaker
                        st.toast(f"✅ {card_key} Card issued to {ps}!")
                        st.rerun()

                if btn_remove.button("🗑️ Remove Card", key=f"btn_rm_{t_safe}", use_container_width=True):
                    if ps in state.get('cards', {}).get(team_name, {}):
                        close_exp() # 💡 क्लोज कमान्ड
                        removed_card = state['cards'][team_name].pop(ps)
                        if removed_card in ["Expulsion", "Disqualified"] and not is_active:
                            state['lineup'][team_name]['bench'].append(ps)
                        st.session_state[f"audio_q_{m_id}"] = {"speech": f"✅ CARD REMOVED ({team_name[:12]}): #{ps}"}
                        save_match_scores(event_code, m_id, state)
                        try: update_live_tv(match_title, state, m_id=m_id)
                        except: pass
                        st.toast(f"✅ Card removed for {ps}!")
                        st.rerun()
                    else:
                        st.info("यो खेलाडीसँग कुनै कार्ड छैन।")

            # ==========================================
            # ५. Jersey Edit Expander (Smart Form Version)
            # ==========================================
            with st.expander("✏️ Quick Jersey Edit (No Sub)"):
                # 💡 जादु: 'st.form' प्रयोग गरेपछि बटन नथिचुन्जेल पेज रिफ्रेस हुँदैन!
                with st.form(key=f"form_jer_{t_safe}", clear_on_submit=True):
                    all_p = state['lineup'][team_name]['court'] + state['lineup'][team_name]['bench']
                    c1, c2 = st.columns(2)
                    
                    # यहाँ on_change हटाइएको छ, किनकि फर्मभित्र यसको जरुरत पर्दैन
                    old_j = c1.selectbox("Old:", all_p, key=f"old_{t_safe}")
                    new_j = c2.text_input("New #:", key=f"new_{t_safe}").strip()
                    
                    # फर्मको आफ्नै सबमिट बटन हुन्छ
                    if st.form_submit_button("💾 Update Jersey", use_container_width=True):
                        if new_j and new_j not in all_p:
                            name = state['roster'][team_name].pop(old_j)
                            state['roster'][team_name][new_j] = name
                            for l_key in ['court', 'bench', 'libero']:
                                if old_j in state['lineup'][team_name][l_key]:
                                    i = state['lineup'][team_name][l_key].index(old_j)
                                    state['lineup'][team_name][l_key][i] = new_j
                            if state['lineup'][team_name]['captain'] == old_j: state['lineup'][team_name]['captain'] = new_j
                            
                            st.session_state[f"audio_q_{m_id}"] = {"speech": f"✏️ JERSEY EDIT ({team_name[:12]}): #{old_j} ➡️ #{new_j}"}
                            save_match_scores(event_code, m_id, state)
                            try: update_live_tv(match_title, state, m_id=m_id)
                            except: pass
                            st.rerun()
                        elif new_j in all_p:
                            st.error("यो जर्सी नम्बर पहिले नै छ!")

    # ==============================================================
    # MAIN LAYOUT (Left & Right Controls, Middle Court)
    # ==============================================================
    st.markdown("<br>", unsafe_allow_html=True)
    c_left, c_mid, c_right = st.columns([1.3, 3.8, 1.3])

    # Side control panels (scores, point/undo/to buttons)
    render_team_controls(left_team, c_left, "#dc2626" if left_team==p1 else "#2563eb", left_team==p1)
    render_team_controls(right_team, c_right, "#dc2626" if right_team==p1 else "#2563eb", right_team==p1)

    # Middle column: Set history, court, and action panels 
    with c_mid:
        past_sets_html = ""
        if c_set > 1:
            past_scores = []
            for s in range(1, c_set):
                score_l = state['scores'][s][left_team]
                score_r = state['scores'][s][right_team]
                past_scores.append(f"<span style='background:#f1f5f9; border:1px solid #cbd5e1; padding:2px 10px; border-radius:12px; font-size:12px; margin:0 4px; color:#475569;'><b>Set {s}:</b> {score_l} - {score_r}</span>")
            past_sets_html = "<div style='margin-top:8px; display:flex; justify-content:center; flex-wrap:wrap; gap:5px;'>" + "".join(past_scores) + "</div>"

        st.markdown(f"""
        <div style='text-align:center; background:#ffffff; padding:10px; border-radius:10px; border:2px solid #e2e8f0; margin-bottom:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);'>
            <div style='font-size:18px; font-weight:bold; color:#1e293b;'>🏆 Sets Won: {state['sets_won'][left_team]} - {state['sets_won'][right_team]}</div>
            {past_sets_html}
        </div>
        """, unsafe_allow_html=True)
       
        # Court rendering
        render_operator_court(state, p1, p2)
        st.markdown("<div style='margin-top:15px;'></div>", unsafe_allow_html=True)

        # =========================================================
        # 💡 CONDITIONAL UI BASED ON SET WINNER
        # =========================================================
        if not set_winner and not state.get('match_completed'):
            # SET IS ONGOING – show action panels
            ca_left, ca_mid_inner, ca_right = st.columns([2.1, 0.8, 2.1])
            
            if not state.get('ui_swapped', False):
                render_team_actions(p1, p2, ca_left)
                render_team_actions(p2, p1, ca_right)
            else:
                render_team_actions(p2, p1, ca_left)
                render_team_actions(p1, p2, ca_right)
                
            with ca_mid_inner:
                st.markdown("<div style='text-align:center; font-weight:bold; color:gray; font-size:12px; margin-bottom:5px;'>Clock</div>", unsafe_allow_html=True)
                
                is_paused = state.get('clock_paused', False)
                if is_paused:
                    if st.button("▶️ Play", type="primary", use_container_width=True):
                        import time
                        state['clock_paused'] = False
                        state['last_start_time'] = int(time.time() * 1000)
                        save_match_scores(event_code, m_id, state)
                        try: update_live_tv(match_title, state, m_id=m_id)
                        except: pass
                        st.rerun()
                else:
                    if st.button("⏸️ Pause", type="secondary", use_container_width=True):
                        import time
                        curr = int(time.time() * 1000)
                        if curr > state.get('last_start_time', curr):
                            state['accumulated_time'] = state.get('accumulated_time', 0) + (curr - state.get('last_start_time', curr))
                        state['clock_paused'] = True
                        state['last_start_time'] = curr
                        save_match_scores(event_code, m_id, state)
                        try: update_live_tv(match_title, state, m_id=m_id)
                        except: pass
                        st.rerun()
                    
                                    
                st.markdown("<div style='text-align:center; font-weight:bold; color:gray; font-size:12px; margin-top:10px; margin-bottom:5px;'>Swap</div>", unsafe_allow_html=True)
                
                def action_swap_panel():
                    state['ui_swapped'] = not state.get('ui_swapped', False)
                    save_match_scores(event_code, m_id, state)
                st.button("💻 Me", type="secondary", use_container_width=True, on_click=action_swap_panel)
                
                def action_swap_tv():
                    state['tv_swapped'] = not state.get('tv_swapped', False)
                    save_match_scores(event_code, m_id, state)
                    update_live_tv(match_title, state, m_id=m_id)
                st.button("📺 TV", type="primary", use_container_width=True, on_click=action_swap_tv)

                st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
                if st.button("🧹 T/O Over", type="secondary", use_container_width=True, help="टाइमआउट सकिएको घोषणा गर्ने र टिभी सफा गर्ने"):
                    
                    # १. टिभीको स्क्रिन सफा गरेर 'Set is running' देखाउने
                    state['latest_event'] = {"speech": f"📢 Set {c_set} is running..."}
                    
                    # २. स्पिकरलाई "टाइमआउट सकियो" भनेर बोल्न लगाउने र २ पटक बीप बजाउने
                    st.session_state[f"audio_q_{m_id}"] = {
                        "speech": "Time out is over. Teams, please return to the court.", 
                        "tv_msg": f"📢 Set {c_set} is running...",
                        "beep": (800, 0.4, 2, 0.2, 'normal') 
                    }
                    
                    save_match_scores(event_code, m_id, state)
                    try: update_live_tv(match_title, state, m_id=m_id)
                    except: pass
                    st.rerun()

                


# =========================================================
        # 💡 अवस्था २: सेट सकियो (विजेता घोषणा र अर्को सेटको तयारी)
        # =========================================================
        elif set_winner and not state.get('match_completed'):
            
            # १. 'म्याच नै जितेको हो कि?' भनेर 'टेम्पोररी' गणना गर्ने
            sets_won_a = state['sets_won'][p1] + (1 if set_winner == p1 else 0)
            sets_won_b = state['sets_won'][p2] + (1 if set_winner == p2 else 0)
            
            match_winner = None
            if sets_won_a == req_sets_to_win: match_winner = p1
            elif sets_won_b == req_sets_to_win: match_winner = p2

            # २. सेट जितेको अडियो सुरक्षित राख्ने
            audio_data = {
                "speech": f"Set {c_set} won by {audio_name(set_winner)}.",
                "beep": (900, 0.5, 3, 0.2, 'normal'), # ३ पटक सिट्ठी
                "tv_msg": f"🎉 SET {c_set} WON BY {set_winner}!"
            }
            st.session_state[f"audio_q_{m_id}"] = audio_data.copy()
            
            # ३. टिभीलाई सेटको सेलिब्रेसन देखाउन अर्डर (म्याच जितेको छैन भने मात्र)
            if not match_winner:
                state['tv_celebration'] = {
                    "show": True,
                    "title": f"🎉 SET {c_set} WINNER 🎉",
                    "winner": audio_name(set_winner).upper(),
                    "score": f"{state['scores'][c_set][p1]} - {state['scores'][c_set][p2]}"
                }
            
            save_match_scores(event_code, m_id, state)
            try: update_live_tv(match_title, state, m_id=m_id)
            except: pass
            
            # अडियो रिस्टोर गर्ने
            st.session_state[f"audio_q_{m_id}"] = audio_data.copy()
            
            st.markdown("---")
            
            # ==========================================
            # ४. अपरेटरलाई देखाउने प्यानल (बटनहरू)
            # ==========================================
            if match_winner:
                st.balloons()
                st.error(f"🏆 **MATCH WON BY {audio_name(match_winner).upper()}!**")
                
                # म्याच सकिएको बेला देखाउने बटन
                if st.button("🏁 Finish Match & Publish Result", type="primary", use_container_width=True):
                    state['sets_won'][set_winner] += 1
                    state['match_completed'] = True
                    state['status'] = "Completed"
                    
                    winner_id = match.get('p1_id') if match_winner == p1 else match.get('p2_id')
                    final_score_str = f"{state['sets_won'][p1]} - {state['sets_won'][p2]}"
                    
                    update_match_winner_in_db(event_code, m_id, match_winner, winner_id, final_score_str, state)
                    save_match_scores(event_code, m_id, state)
                    update_live_tv(match_title, state, m_id=m_id)
                    st.rerun()
            else:
                st.success(f"🎉 **SET {c_set} WON BY {audio_name(set_winner).upper()}!** ({score_a} - {score_b})")
                
                # अर्को सेटमा जाने बटन
                if st.button(f"➡️ Proceed to Set {c_set + 1}", type="primary", use_container_width=True):
                    state['sets_won'][set_winner] += 1
                    state['current_set'] += 1
                    nxt = state['current_set']
                    state['scores'][nxt] = {p1: 0, p2: 0}
                    state['timeouts'][nxt] = {p1: 0, p2: 0}
                    state['substitutions'] = {p1: 0, p2: 0}
                    state['ui_swapped'] = not state.get('ui_swapped', False)
                    state['tv_swapped'] = not state.get('tv_swapped', False)
                    state['setup_complete'] = False
                    
                    state['whistle_blown'] = False  
                    state['tv_celebration'] = {"show": False} # नयाँ सेटमा जाँदा सेलिब्रेसन हटाउने
                    
                    save_match_scores(event_code, m_id, state)
                    update_live_tv(match_title, state, m_id=m_id)
                    st.rerun()
        # =========================================================
        # 💡 अवस्था ३: म्याच पूर्ण रूपमा समाप्त भयो (Podium Celebration)
        # =========================================================
        elif state.get('match_completed'):
            # १. विजेता र उप-विजेता छुट्ट्याउने
            final_winner = p1 if state['sets_won'][p1] > state['sets_won'][p2] else p2
            runner_up = p2 if final_winner == p1 else p1
            
            # (भविष्यको लागि) थर्ड प्लेसको नाम डाटाबेसबाट तान्न सकिन्छ, अहिले खाली राखेको छ
            third_place = "TBD (तेस्रो स्थान)" 
            
            # 🎈 स्क्रिनमा बेलुन उडाउने जादु
            if not state.get('celebrated', False):
                st.balloons()
                state['celebrated'] = True
                save_match_scores(event_code, m_id, state)
            
            # 🏆 २. भव्य पोडियम (Podium) को HTML/CSS डिजाइन
            st.markdown(f"""
            <div style="background: #1e293b; padding: 20px; border-radius: 15px; border: 4px solid #3b82f6; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.5);">
                <h2 style="text-align: center; color: white; margin-bottom: 30px; text-transform: uppercase; letter-spacing: 2px;">🏆 Medal Ceremony 🏆</h2>
                
                <div style="display: flex; justify-content: center; align-items: flex-end; height: 220px; gap: 10px; margin-top: 20px;">
                    
                    <div style="display: flex; flex-direction: column; align-items: center; width: 30%; animation: slideUp 1s ease-out;">
                        <h3 style="color: #cbd5e1; margin-bottom: 5px; font-size: 18px; text-shadow: 1px 1px 2px black;">🥈 Silver</h3>
                        <span style="color: white; font-weight: bold; text-align: center; font-size: 16px; margin-bottom: 8px;">{runner_up}</span>
                        <div style="background: linear-gradient(to top, #64748b, #cbd5e1); height: 120px; width: 100%; border-radius: 10px 10px 0 0; display: flex; justify-content: center; align-items: center; color: white; font-size: 40px; font-weight: 900; box-shadow: inset 0 0 15px rgba(0,0,0,0.3); border-top: 3px solid #f8fafc;">2</div>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; align-items: center; width: 35%; z-index: 10; animation: slideUp 0.8s ease-out;">
                        <h3 style="color: #fde047; margin-bottom: 5px; font-size: 22px; text-shadow: 1px 1px 2px black;">🥇 Gold</h3>
                        <span style="color: white; font-weight: 900; text-align: center; font-size: 20px; margin-bottom: 8px; text-transform: uppercase;">{final_winner}</span>
                        <div style="background: linear-gradient(to top, #b45309, #fde047); height: 160px; width: 100%; border-radius: 10px 10px 0 0; display: flex; justify-content: center; align-items: center; color: white; font-size: 50px; font-weight: 900; box-shadow: inset 0 0 20px rgba(0,0,0,0.4), 0 -10px 20px rgba(253, 224, 71, 0.4); border-top: 4px solid #fffbeb;">1</div>
                    </div>
                    
                    <div style="display: flex; flex-direction: column; align-items: center; width: 30%; animation: slideUp 1.2s ease-out;">
                        <h3 style="color: #d97706; margin-bottom: 5px; font-size: 18px; text-shadow: 1px 1px 2px black;">🥉 Bronze</h3>
                        <span style="color: #94a3b8; font-weight: bold; text-align: center; font-size: 14px; margin-bottom: 8px;">{third_place}</span>
                        <div style="background: linear-gradient(to top, #78350f, #d97706); height: 90px; width: 100%; border-radius: 10px 10px 0 0; display: flex; justify-content: center; align-items: center; color: white; font-size: 35px; font-weight: 900; box-shadow: inset 0 0 10px rgba(0,0,0,0.3); border-top: 3px solid #fef3c7;">3</div>
                    </div>
                    
                </div>
            </div>
            
            <style>
                @keyframes slideUp {{
                    from {{ transform: translateY(50px); opacity: 0; }}
                    to {{ transform: translateY(0); opacity: 1; }}
                }}
            </style>
            """, unsafe_allow_html=True)
            
            # 📢 ३. म्यानुअल एनाउन्समेन्ट बटन (ब्रोडकास्टरको लागि)
            if st.button("📢 Announce Winners (विजेता घोषणा)", type="primary", use_container_width=True):
                # कडा एनाउन्समेन्ट स्क्रिप्ट
                champ_speech = f"Ladies and gentlemen, the match is completed! The silver medal goes to {audio_name(runner_up)}. And the gold medal, and the ultimate champion is... {audio_name(final_winner)}! Congratulations!"
                
                audio_data = {
                    "speech": champ_speech,
                    "beep": (1000, 0.4, 4, 0.2, 'normal'), 
                    "tv_msg": f"🥇 CHAMPION: {final_winner} | 🥈 RUNNER-UP: {runner_up}"
                }
                
                # ==========================================
                # 💡 जादु यहाँ छ: टिभीलाई सेलिब्रेसन देखाउन अर्डर!
                # ==========================================
                state['tv_celebration'] = {
                    "show": True,
                    "title": "🏆 MATCH CHAMPION 🏆",
                    "winner": audio_name(final_winner).upper(),
                    "score": f"{state['sets_won'][p1]} - {state['sets_won'][p2]}"
                }
                
                state['latest_event'] = {"tv_msg": f"🥇 CHAMPION: {final_winner} | 🥈 RUNNER-UP: {runner_up}"}
                st.session_state[f"audio_q_{m_id}"] = audio_data.copy()
                
                save_match_scores(event_code, m_id, state)
                try: update_live_tv(match_title, state, m_id=m_id)
                except: pass
                st.session_state[f"audio_q_{m_id}"] = audio_data.copy() # Restore Magic
                st.rerun()


        

    st.divider()

