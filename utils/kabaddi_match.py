# utils\kabaddi_match.py
import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import json
import time
import os
import base64
import time
from datetime import datetime

# ==========================================
# 🖼️ ०. Image Caching System
# ==========================================
@st.cache_data
def get_cached_base64_image(filename):
    filepath = os.path.join("assets", filename)
    if os.path.exists(filepath):
        with open(filepath, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

# ==========================================
# 🛠️ १. DB र Helper Functions
# ==========================================
def fetch_team_players(event_code, team_name):
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT municipality_id FROM teams WHERE event_code=%s AND name ILIKE %s", (event_code, f"%{team_name.strip()}%"))
    team_info = c.fetchone()
    
    if team_info and team_info[0]:
        muni_id = team_info[0]
        # 💡 फिक्स: डाटाबेसबाट नाम र जर्सी नम्बर सँगै तानिएको छ!
        c.execute("""
            SELECT p.name, r.jersey_no FROM registrations r 
            JOIN players p ON r.player_id = p.id 
            WHERE r.event_code = %s AND p.municipality_id = %s
        """, (event_code, muni_id))
        players = c.fetchall()
        c.close()
        conn.close()
        # डिक्सनरी (Dictionary) को रूपमा डाटा फर्काउने
        if players: return [{'name': p[0], 'jersey': str(p[1]) if p[1] else ''} for p in players]
        
    c.close()
    conn.close()
    return [{'name': f"Player {i}", 'jersey': str(i)} for i in range(1, 13)]

def audio_name(name):
    if not name: return ""
    import re
    clean = re.sub(r'[\u0900-\u097F]+|\(.*?\)', '', str(name))
    clean = re.sub(r'(?i)\b(Rural Municipality|Municipality|Metropolitan City|Sub-Metropolitan City)\b', '', clean)
    return clean.strip().title()

def spell_num(n):
    n = int(n)
    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    if n < 20: return ones[n]
    return tens[n // 10] + ("" if n % 10 == 0 else " " + ones[n % 10])

def load_kabaddi_scores(event_code, match_id, p1, p2):
    state_key = f"kabaddi_{event_code}_{match_id}"
    
    if state_key not in st.session_state:
        conn = db.get_connection()
        c = conn.cursor()
        # 💡 PostgreSQL Syntax
        c.execute("SELECT live_state, status FROM matches WHERE match_no=%s AND event_code=%s", (match_id, event_code))
        row = c.fetchone()
        c.close()
        conn.close()
        
        saved_state = None
        if row and row[0] and row[1] != 'Completed':
            try: 
                saved_state = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            except: pass
            
        if saved_state:
            if 'out_players' not in saved_state: saved_state['out_players'] = {p1: [], p2: []}
            if 'empty_raids' not in saved_state: saved_state['empty_raids'] = {p1: 0, p2: 0}
            if 'cards' not in saved_state: saved_state['cards'] = {p1: {}, p2: {}}
            if 'yc_timers' not in saved_state: saved_state['yc_timers'] = {p1: {}, p2: {}} 
            if 'raider_team' not in saved_state: saved_state['raider_team'] = None
            if 'raider_num' not in saved_state: saved_state['raider_num'] = None
            if 'selected_targets' not in saved_state: saved_state['selected_targets'] = []
            if 'swap_sides' not in saved_state: saved_state['swap_sides'] = False
            if 'lona_transition' not in saved_state: saved_state['lona_transition'] = None
            if 'raid_pos' not in saved_state: saved_state['raid_pos'] = 0 
            if 'baulk_crossed' not in saved_state: saved_state['baulk_crossed'] = False
            if 'bonus_crossed' not in saved_state: saved_state['bonus_crossed'] = False
            if 'match_started' not in saved_state: saved_state['match_started'] = False 
            if 'timer_running' not in saved_state: saved_state['timer_running'] = False 
            if 'timeout_active' not in saved_state: saved_state['timeout_active'] = False 
            if 'next_raider_team' not in saved_state: saved_state['next_raider_team'] = None
            if 'first_half_starter' not in saved_state: saved_state['first_half_starter'] = None 
            if 'last_event_msg' not in saved_state: saved_state['last_event_msg'] = "" 
            if 'last_event_icon' not in saved_state: saved_state['last_event_icon'] = "" 
            
            st.session_state[state_key] = saved_state
            st.session_state[state_key]['timeouts'] = {int(k): v for k, v in saved_state.get('timeouts', {1: {p1: 0, p2: 0}, 2: {p1: 0, p2: 0}}).items()}
        else:
            st.session_state[state_key] = {
                'setup_complete': False, 'match_started': False, 'timer_running': False, 'timeout_active': False,
                'score_a': 0, 'score_b': 0, 'half': 1, 'status': 'Playing',
                'timeouts': {1: {p1: 0, p2: 0}, 2: {p1: 0, p2: 0}}, 
                'subs': {p1: 0, p2: 0}, 'roster': {p1: {}, p2: {}}, 
                'lineup': { p1: {"court": [], "bench": [], "captain": None}, p2: {"court": [], "bench": [], "captain": None} },
                'out_players': {p1: [], p2: []}, 'empty_raids': {p1: 0, p2: 0},   
                'cards': {p1: {}, p2: {}}, 'yc_timers': {p1: {}, p2: {}},       
                'raider_team': None, 'raider_num': None, 'selected_targets': [],
                'swap_sides': False, 'lona_transition': None, 'raid_pos': 0, 'baulk_crossed': False, 'bonus_crossed': False,
                'next_raider_team': None, 'first_half_starter': None, 'last_event_msg': "", 'last_event_icon': ""
            }
        
        st.session_state[f"{state_key}_show_subs_{p1}"] = False; st.session_state[f"{state_key}_show_subs_{p2}"] = False
        st.session_state[f"{state_key}_show_cards_{p1}"] = False; st.session_state[f"{state_key}_show_cards_{p2}"] = False
        
    return state_key

def save_kabaddi_scores(event_code, match_id, state):
    conn = db.get_connection()
    c = conn.cursor()
    # 💡 PostgreSQL JSONB save logic
    c.execute("UPDATE matches SET live_state=%s WHERE match_no=%s AND event_code=%s", (json.dumps(state), match_id, event_code))
    conn.commit()
    c.close()
    conn.close()
    
    # ==========================================
    # 💡 जादु: स्कोरबोर्ड (टिभी) लाई लाइभ डाटा पठाउने तार!
    # ==========================================
    import utils.live_state as ls
    ls._save_state("kb_live_match", {"state": state})

def update_live_tv(event_name, state, p1, p2):
    import utils.live_state as ls
    import streamlit as st
    
    # 💡 जादु (र सुरक्षा): डिक्सनरी खाली भए पनि क्र्यास हुन नदिने
    match_info = st.session_state.get('selected_match', {})
    
    # यदि match_info डिक्सनरी होइन वा खाली छ भने डिफल्ट भ्यालु राख्ने
    if isinstance(match_info, dict):
        round_name = match_info.get('round', 'Match')
        match_no = match_info.get('id', '-')
    else:
        round_name = 'Match'
        match_no = '-'
    
    # नाम तयार गर्ने
    real_match_title = f"{event_name} - {round_name} #{match_no}"
    
    c_half = state.get('half', 1)
    t_1 = state.get('timeouts', {}).get(str(c_half), {}).get(p1, 0)
    t_2 = state.get('timeouts', {}).get(str(c_half), {}).get(p2, 0)
    status_text = f"Half {c_half} | T/O: {p1}({t_1}), {p2}({t_2})"
    
    # पुरानो अपडेट लजिक
    try:
        ls.update_live_match(event_name, p1, p2, str(state.get('score_a', 0)), str(state.get('score_b', 0)), status=status_text)
    except Exception:
        pass # यहाँ एरर आए पनि क्र्यास हुन नदिने
        
    # ==========================================
    # 💡 नयाँ जादु: खेलाडीहरूलाई क्रमबद्ध (Sort) गर्ने
    # ==========================================
    from utils.kabaddi_match import sort_kabaddi_players
    
    # (यहाँबाट त्यो 'team' वाला बिग्रिएको लाइन हटाइयो)
    sorted_p1 = sort_kabaddi_players(p1, state)
    sorted_p2 = sort_kabaddi_players(p2, state)
    
    # टिभी प्यानलको लागि नयाँ डाटा
    tv_data = {
        "match_title": real_match_title,
        "state": state,
        "team_a_players": sorted_p1,  # 👈 सर्टिङ भएको टिम १ को लिस्ट
        "team_b_players": sorted_p2   # 👈 सर्टिङ भएको टिम २ को लिस्ट
    }
    
    try:
        ls._set_state("kb_live_match", tv_data)
    except Exception:
        pass

# ==========================================
# 🤼 २. कबड्डी कोर्ट रेन्डर (Visual Engine) - 🚀 FRAGMENTED
# ==========================================
@st.fragment
def render_kabaddi_court(state, p1, p2):
    import time
    try:
        # १. टिम र खेलाडीको डाटा तान्ने (सुरक्षित तरिकाले)
        left_team = p2 if state.get('swap_sides') else p1
        right_team = p2 if not state.get('swap_sides') else p1 # 👈 यहाँ सुधार गरिएको छ
        
        l1, l2 = state.get('lineup', {}).get(left_team, {}), state.get('lineup', {}).get(right_team, {})
        c_left, c_right = l1.get('court', []), l2.get('court', [])
        b_left, b_right = l1.get('bench', []), l2.get('bench', [])
        out_left, out_right = state.get('out_players', {}).get(left_team, []), state.get('out_players', {}).get(right_team, [])

        # २. रनिङ र रेडर लजिक
        is_attacking_right = (state.get('raider_team') == left_team)
        r_pos = state.get('raid_pos', 0)
        baulk_c, bonus_c = state.get('baulk_crossed', False), state.get('bonus_crossed', False)
        
        # ३. लाइनका रङ्गहरू (Colors)
        c_mid = "#ef4444" if r_pos >= 1 else "white" 
        c_baulk_l = "#22c55e" if (not is_attacking_right and r_pos >= 2) else "#facc15" if (not is_attacking_right and baulk_c) else "white"
        c_bonus_l = "#22c55e" if (not is_attacking_right and r_pos >= 3) else "#facc15" if (not is_attacking_right and bonus_c) else "white"
        c_baulk_r = "#22c55e" if (is_attacking_right and r_pos >= 2) else "#facc15" if (is_attacking_right and baulk_c) else "white"
        c_bonus_r = "#22c55e" if (is_attacking_right and r_pos >= 3) else "#facc15" if (is_attacking_right and bonus_c) else "white"

        # ४. CSS स्टाइल (अघिको जस्तै, तर सुरक्षित)
        st.markdown(f"""<style>
            .kb-arena {{ display: flex; justify-content: center; align-items: stretch; width: 100%; gap: 10px; margin: 10px 0; height: 340px; }}
            .kb-bench {{ display: flex; flex-direction: column; gap: 5px; background: #1e293b; padding: 5px; border-radius: 5px; min-width: 45px; align-items: center; border: 2px solid #475569; }}
            .bench-title {{ color: white; font-size: 10px; font-weight: bold; writing-mode: vertical-rl; text-align: center; letter-spacing: 2px; flex-grow: 1; }}
            .sitting-block {{ display: flex; flex-direction: column; justify-content: flex-end; gap: 4px; background: #e2e8f0; padding: 5px; border-radius: 5px; width: 50px; border: 2px solid #cbd5e1; }}
            .sit-slot {{ width: 34px; height: 34px; border-radius: 50%; background: white; border: 2px dashed #94a3b8; display: flex; justify-content: center; align-items: center; font-size: 12px; font-weight: bold; }}
            .sit-filled {{ background: #cbd5e1; border: 2px solid #475569; color: black; }}
            .kb-court {{ display: flex; width: 100%; max-width: 800px; height: 100%; background-color: #fcd34d; border: 5px solid white; position: relative; border-radius: 8px; overflow: hidden; }}
            .mid-line {{ position: absolute; left: 50%; width: 6px; height: 100%; background: {c_mid}; transform: translateX(-50%); z-index: 10; box-shadow: 0 0 10px {c_mid}; }}
            .baulk-line-left {{ position: absolute; left: 25%; width: 4px; height: 100%; background: {c_baulk_l}; }}
            .baulk-line-right {{ position: absolute; right: 25%; width: 4px; height: 100%; background: {c_baulk_r}; }}
            .p-dot {{ position: absolute; width: 34px; height: 34px; border-radius: 50%; font-weight: bold; display: flex; justify-content: center; align-items: center; transform: translate(-50%, -50%); z-index: 5; box-shadow: 1px 1px 5px rgba(0,0,0,0.5); }}
            .bg-blue {{ background-color: #2563eb; color: white; border: 2px solid white; }}
            .bg-red {{ background-color: #dc2626; color: white; border: 2px solid white; }}
            .raider-normal {{ transform: translate(-50%, -50%) scale(1.4); z-index: 20; box-shadow: 0 0 15px white; }}
        </style>""", unsafe_allow_html=True)

        # ५. एरिना कोर्न सुरु गर्ने
        html = '<div class="kb-arena">'
        
        # बायाँ टिम (Bench & Out)
        html += f'<div class="kb-bench">{"".join([make_dot(left_team, n, False) for n in b_left])}<div class="bench-title">BENCH</div></div>'
        html += get_sitting_block_html(left_team, out_left)

        # मुख्य कोर्ट (Lines & Players)
        html += f'<div class="kb-court"><div class="mid-line"></div><div class="baulk-line-left"></div><div class="baulk-line-right"></div>'
        html += "".join([make_dot(left_team, n, True, i, True) for i, n in enumerate(c_left)])
        html += "".join([make_dot(right_team, n, True, i, False) for i, n in enumerate(c_right)])
        html += '</div>'

        # दायाँ टिम (Out & Bench)
        html += get_sitting_block_html(right_team, out_right)
        html += f'<div class="kb-bench">{"".join([make_dot(right_team, n, False) for n in b_right])}<div class="bench-title">BENCH</div></div>'
        
        html += '</div>'
        
        # ६. अन्तिम रेन्डर
        st.markdown(html, unsafe_allow_html=True)

    except Exception as e:
        # 🚨 यही जादुले भोलि बिहान हजुरलाई "किन भएन" भन्ने जवाफ दिनेछ!
        st.error(f"🚨 कोर्ट लोड गर्दा समस्या भयो: {str(e)}")
        st.info("यो म्यासेज आउनुको अर्थ 'make_dot' वा 'get_sitting_block_html' कतै हराएको छ।")


# ==========================================
# 🎮 ३. Main Render Function
# ==========================================
def render_match(evt_code, sel_m):
    mid = sel_m['id']
    p1, p2 = sel_m['p1'], sel_m['p2']
    
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT name, gender FROM events WHERE code=%s", (evt_code,))
    evt_info = c.fetchone()
    c.close()
    conn.close()
    
    match_title = f"{evt_info[0]} ({evt_info[1]}) - Match #{mid}" if evt_info else f"Kabaddi Match #{mid}"
    is_women = evt_info[1] == 'Girls' if evt_info else False

    state_key = load_kabaddi_scores(evt_code, mid, p1, p2)
    state = st.session_state[state_key]
    
    # 💡 जादु यहाँ छ: बनेको टाइटल र राउन्डलाई 'state' भित्र टाँसिदिने!
    state['match_title'] = match_title
    state['round_name'] = sel_m.get('round', 'Match')
    state['match_no'] = str(mid)
    state['gender'] = evt_info[1] if evt_info else 'Boys'
    
    if state.get('status') == 'Completed':
        st.success("✅ यो म्याच सम्पन्न भइसकेको छ।")
        return

    # --- SETUP PHASE ---
    if not state.get("setup_complete"):
        st.info("📋 **कबड्डी लाइन-अप तयार गर्नुहोस् (७ जनामा टिक लगाउनुहोस्)।**")
        c_t1, c_t2 = st.columns(2)
        
        def setup_team(team_name, col):
            with col:
                st.markdown(f"### 🤼 {team_name}")
                players_data = fetch_team_players(evt_code, team_name)
                df_key = f"kb_setup_{mid}_{team_name}"
                
                if df_key not in st.session_state:
                    # 💡 फिक्स: सुरुका ७ जनालाई अटोमेटिक 'टिक' लाग्ने बनाइएको छ
                    df_data = []
                    for i, p in enumerate(players_data):
                        df_data.append({
                            "Player Name": p['name'],
                            "Jersey": p['jersey'],
                            "Is Starter": True if i < 7 else False,
                            "Captain": True if i == 0 else False
                        })
                    st.session_state[df_key] = pd.DataFrame(df_data)
                
                # 💡 फिक्स: ड्रपडाउनको सट्टा Checkbox प्रयोग र जर्सी नम्बरलाई Read-Only बनाइएको
                config = {
                    "Player Name": st.column_config.TextColumn("खेलाडीको नाम", disabled=True), 
                    "Jersey": st.column_config.TextColumn("जर्सी नं.", disabled=True), 
                    "Is Starter": st.column_config.CheckboxColumn("कोर्टमा (७ जना)?", default=False),
                    "Captain": st.column_config.CheckboxColumn("क्याप्टेन (C)", default=False)
                }
                
                edited_df = st.data_editor(st.session_state[df_key], column_config=config, num_rows="fixed", key=f"kb_ed_{mid}_{team_name}", width="stretch", hide_index=True)
                
                valid, error_msg = True, ""
                active_mask = edited_df['Is Starter'] == True
                
                # गल्ती चेक गर्ने (Validation)
                if edited_df[active_mask]['Jersey'].str.strip().eq("").any(): 
                    valid, error_msg = False, "कोर्टमा खेल्ने खेलाडीको जर्सी नम्बर खाली छ। कृपया दर्ता सच्याउनुहोस्।"
                else:
                    if edited_df['Is Starter'].sum() != 7: valid, error_msg = False, "ठ्याक्कै ७ जना खेलाडीमा मात्र टिक लगाउनुहोस्।"
                    if valid and edited_df['Captain'].sum() != 1: valid, error_msg = False, "१ जनालाई मात्र क्याप्टेन बनाउनुहोस्।"
                    if valid:
                        cap_row = edited_df[edited_df['Captain'] == True].iloc[0]
                        if not cap_row['Is Starter']: valid, error_msg = False, "क्याप्टेन 'कोर्टमा खेल्ने (७ जना)' भित्रै हुनुपर्छ।"
                        
                        active_j = edited_df[active_mask]['Jersey'].astype(str).str.strip().tolist()
                        if len(active_j) != len(set(active_j)): valid, error_msg = False, "एउटै जर्सी नम्बर दुई जनालाई दिन मिल्दैन।"
                
                if valid:
                    clean_df = edited_df[edited_df['Player Name'].str.strip() != ""]
                    roster = {str(row['Jersey']).strip(): row['Player Name'] for _, row in clean_df.iterrows() if str(row['Jersey']).strip() != ""}
                    starters = clean_df[clean_df['Is Starter'] == True]['Jersey'].astype(str).str.strip().tolist()
                    bench = [b for b in clean_df[clean_df['Is Starter'] == False]['Jersey'].astype(str).str.strip().tolist() if b != ""]
                    cap_j = str(clean_df[clean_df['Captain'] == True]['Jersey'].iloc[0]).strip()
                    return roster, starters, bench, cap_j
                else:
                    st.error(f"⚠️ {error_msg}")
                    return None, [], [], None

        # दुवै टिमको डाटा लिने
        ta_rost, ta_start, ta_bench, ta_cap = setup_team(p1, c_t1)
        tb_rost, tb_start, tb_bench, tb_cap = setup_team(p2, c_t2)
        
        # 💡 जादु: लाइन-अप पूर्ण नभएसम्म बटन थिच्न नै नदिने (Disabled बनाउने)
        is_ready = True
        error_msg = ""
        
        # यदि कुनै पनि टिमको डाटा 'None' आयो (अर्थात् माथि validation फेल भयो) भने
        if ta_start is None or tb_start is None:
            is_ready = False
        # यदि ७ जना छानेको छैन भने
        elif len(ta_start) != 7 or len(tb_start) != 7:
            is_ready = False
            error_msg = f"दुवै टिमबाट कोर्टमा खेल्ने ठ्याक्कै ७/७ जना खेलाडी छान्नुहोस्। (अहिले: {p1}={len(ta_start) if ta_start else 0}, {p2}={len(tb_start) if tb_start else 0})"
        
        # बटन देखाउने (तर लाइन-अप अधुरो छ भने थिच्न नमिल्ने बनाउने)
        st.markdown("<hr style='margin: 20px 0;'>", unsafe_allow_html=True)
        if st.button("🚀 लाइन-अप लक गर्नुहोस्", type="primary", use_container_width=True, disabled=not is_ready, help="लाइन-अप पूरा भएपछि मात्र यो बटन खुल्छ।"):
            state['roster'][p1], state['roster'][p2] = ta_rost, tb_rost
            state['lineup'][p1] = {"court": ta_start, "bench": ta_bench, "captain": ta_cap}
            state['lineup'][p2] = {"court": tb_start, "bench": tb_bench, "captain": tb_cap}
            state["setup_complete"] = True
            save_kabaddi_scores(evt_code, mid, state)
            st.rerun()
            
        # यदि बटन 'Disabled' छ भने रातो अक्षरमा कारण देखाइदिने
        if not is_ready and error_msg:
            st.warning(f"⚠️ {error_msg}")
        
        # 🛑 लाइन-अप लक नभएसम्म तलको कुनै पनि कोड (कोर्ट/स्कोरबोर्ड) नदेखाउन यहीँ रोकिदिने!
        return

    # -------------------------------------------------------------
    # PHASE 2: LIVE MATCH CONTROL 
    # -------------------------------------------------------------
    c_half = state.get('half', 1)
    left_team = p2 if state.get('swap_sides') else p1
    right_team = p1 if state.get('swap_sides') else p2
    
    if state.get('lona_transition'):
        team_out = state['lona_transition']
        opponent = p2 if team_out == p1 else p1
        
        # 💡 १. सुरक्षित तरिकाले स्कोर बढाउने (२ अङ्क)
        if opponent == p1:
            state['score_a'] = state.get('score_a', 0) + 2
        else:
            state['score_b'] = state.get('score_b', 0) + 2
            
        state['last_event_msg'] = f"🚨 LONA! {opponent} लाई +2 अङ्क!" 
        state['last_event_icon'] = "KB_lona_allout.png" 
        
        # 🔊 २. स्पिच सेट गर्ने
        sc_a_word = spell_num(state.get('score_a', 0))
        sc_b_word = spell_num(state.get('score_b', 0))
        score_speech = f"Score, {sc_a_word} to {sc_b_word}."
        
        st.session_state[f"audio_q_{mid}"] = {
            "speech": f"All out! Lona! 2 points to {audio_name(opponent)}. {score_speech}",
            "beep": (1000, 0.5, 2, 0.2, 'normal') 
        }
        
        # 💡 ३. आउट भएका खेलाडी (कार्ड पाएका बाहेक) फर्काउने लजिक (KeyError नआउने गरी)
        safe_out = []
        out_list = state.get('out_players', {}).get(team_out, [])
        cards_dict = state.get('cards', {}).get(team_out, {})
        
        for p in out_list:
            # जर्सी नम्बर स्ट्रिङ र नम्बर जे भए पनि नझुक्किने
            s_num = str(p)
            c_val = cards_dict.get(s_num) or cards_dict.get(int(p) if s_num.isdigit() else 0)
            
            # यदि रातो वा पहेँलो कार्ड पाएको छ भने मात्र बाहिर (Out) राख्ने
            if c_val in ['Yellow', 'Red']: 
                safe_out.append(p)
                
        # अपडेटेड लिस्टलाई सेभ गर्ने
        if 'out_players' not in state: state['out_players'] = {}
        state['out_players'][team_out] = safe_out
        
        # 💡 ४. ट्रान्जिसन क्लोज र रिफ्रेस
        state['lona_transition'] = None
        state['next_raider_team'] = team_out # अल आउट हुने टिमकै रेड आउँछ
        
        save_kabaddi_scores(evt_code, mid, state)
        st.rerun() # 🚀 अब कतै नअड्किई सिधै रिफ्रेस हुन्छ!

    def add_score_and_revive(team, points, is_bonus=False):
        """
        स्कोर अपडेट गर्ने, बोनस बाहेकको अङ्कमा खेलाडी रिभाइभ गर्ने 
        र पहेँलो कार्डको समय सकिएको छ भने एनाउन्स गर्ने मुख्य फङ्सन।
        """
        # १. स्कोर अपडेट गर्ने
        if team == p1: 
            state['score_a'] += points
        else: 
            state['score_b'] += points
        
        # २. रिभाइभल लजिक (बोनसमा रिभाइभ हुँदैन, टेक्निकल वा टच/ट्याकलमा हुन्छ)
        if not is_bonus and points > 0:
            for _ in range(points):
                out_list = state.get('out_players', {}).get(team, [])
                for i, p in enumerate(out_list):
                    # 💡 नियम: यदि खेलाडीले पहेँलो वा रातो कार्ड पाएको छैन भने मात्र रिभाइभ गर्ने
                    s_p = str(p)
                    card_type = state.get('cards', {}).get(team, {}).get(s_p)
                    
                    if card_type not in ['Yellow', 'Red']:
                        state['out_players'][team].pop(i)
                        break 

        # ==========================================
        # 🔊 जादु १: मुख्य स्कोर घोषणा (TTS Speech)
        # ==========================================
        if points > 0:
            t_name = audio_name(team)
            pts_word = "point" if points == 1 else "points"
            
            sc_a_word = spell_num(state['score_a'])
            sc_b_word = spell_num(state['score_b'])
            score_speech = f"Score, {sc_a_word} to {sc_b_word}."

            if is_bonus:
                speech_text = f"Bonus point, {t_name}. {score_speech}"
                beep_sound = (600, 0.3, 1, 0.1, 'normal')
            else:
                # टेक्निकल प्वाइन्ट वा टच प्वाइन्टको लागि
                speech_text = f"{points} {pts_word}, {t_name}. {score_speech}"
                beep_sound = (800, 0.4, 1, 0.1, 'normal')
                
            st.session_state[f"audio_q_{mid}"] = {"speech": speech_text, "beep": beep_sound}

        # =========================================================
        # 📢 जादु २: पहेँलो कार्डको अटोमेटिक चेक र घोषणा
        # =========================================================
        import time
        if state.get('match_started'):
            expired_players = []
            
            # घोषणाको रेकर्ड राख्ने डिक्सनरी छैन भने बनाउने
            if 'yc_announced' not in state:
                state['yc_announced'] = {}

            for t in [p1, p2]:
                if t not in state['yc_announced']: state['yc_announced'][t] = {}
                
                # सबै पहेँलो कार्ड पाएका खेलाडीहरूको टाइमर चेक गर्ने
                timers = state.get('yc_timers', {}).get(t, {})
                for yp, st_time in timers.items():
                    s_yp = str(yp)
                    # अझै पनि पहेँलो कार्डमै छ र २ मिनेट (१२० सेकेन्ड) पुरा भयो भने
                    if state.get('cards', {}).get(t, {}).get(s_yp) == 'Yellow':
                        if time.time() - st_time >= 120:
                            # यदि अहिलेसम्म यो खेलाडीको लागि घोषणा गरिएको छैन भने
                            if not state['yc_announced'][t].get(s_yp):
                                expired_players.append(f"Jersey {yp}")
                                state['yc_announced'][t][s_yp] = True 

            # यदि समय सकिएका खेलाडी छन् भने अघिल्लो स्पिचको पछाडि थपिदिने
            if expired_players:
                announcement = f". Suspension time is over for {', '.join(expired_players)}. Please enter the court."
                audio_key = f"audio_q_{mid}"
                
                if audio_key in st.session_state and "speech" in st.session_state[audio_key]:
                    # स्कोरको स्पिच पछि यो थपिनेछ
                    st.session_state[audio_key]["speech"] += announcement
                else:
                    # यदि स्कोर आएको थिएन (points=0) भने सिधै यो मात्र बोल्ने
                    st.session_state[audio_key] = {"speech": announcement, "beep": (800, 0.5, 1, 0, 'normal')}

        # 💾 डाटाबेसमा सेभ गर्ने र लाइभ टिभी अपडेट गर्ने
        save_kabaddi_scores(evt_code, mid, state)
        update_live_tv(match_title, state, p1, p2)
    
def sort_kabaddi_players(team, state):
    court_players = state.get('lineup', {}).get(team, {}).get('court', [])
    bench_players = state.get('lineup', {}).get(team, {}).get('bench', [])
    out_players = state.get('out_players', {}).get(team, [])
    cards = state.get('cards', {}).get(team, {})

    live, yellow, dead, subs, red = [], [], [], [], []
    all_players = court_players + bench_players

    for p in all_players:
        s_p = str(p)
        card = cards.get(s_p)
        if card == 'Red': red.append(p)
        elif card == 'Yellow': yellow.append(p)
        elif p in out_players: dead.append(p)
        elif p in court_players: live.append(p)
        else: subs.append(p)

    return live + yellow + dead + subs + red
    

    #=================================================================
    # 💡 SCOREBOARD
    #=================================================================

    c_timer, c_score_L, c_score_R, c_half_info = st.columns([1.5, 4, 4, 1.5])
    score_left = state['score_b'] if state['swap_sides'] else state['score_a']
    score_right = state['score_a'] if state['swap_sides'] else state['score_b']
    
    c_L_main = "#2563eb" if left_team == p1 else "#dc2626"
    c_L_text = "#93c5fd" if left_team == p1 else "#fca5a5"
    
    c_R_main = "#2563eb" if right_team == p1 else "#dc2626"
    c_R_text = "#93c5fd" if right_team == p1 else "#fca5a5"
    
    active_r_team = state.get('raider_team') or state.get('next_raider_team') or left_team
    l_role = "🏃 रेडर टिम (Raider)" if active_r_team == left_team else "🛡️ डिफेन्स टिम (Defence)"
    l_role_bg = c_L_main if active_r_team == left_team else "#475569"
    r_role = "🏃 रेडर टिम (Raider)" if active_r_team == right_team else "🛡️ डिफेन्स टिम (Defence)"
    r_role_bg = c_R_main if active_r_team == right_team else "#475569"
    
    with c_timer:
        import time 
        
        # १. म्याचको प्रकार अनुसार सुरुवाती समय तय गर्ने
        max_min = 15 if is_women else 20
        max_sec = max_min * 60
        
        # २. डाटाबेसमा टाइमर छैन भने नयाँ सेट गर्ने
        if 'remaining_seconds' not in state:
            state['remaining_seconds'] = max_sec
            
        # ३. अहिलेको ठ्याक्कै समय निकाल्ने (Master Calculation)
        if state.get('timer_running') and 'last_start_time' in state:
            elapsed = time.time() - state['last_start_time']
            current_sec = max(0, int(state['remaining_seconds'] - elapsed))
        else:
            current_sec = max(0, int(state.get('remaining_seconds', max_sec)))

        # 💡 ४. टिभीलाई पठाउनको लागि 'timer_seconds' सेट गर्ने
        state['timer_seconds'] = current_sec

        # ५. अपरेटर प्यानलको डिस्प्ले (जाभास्क्रिप्ट)
        st.components.v1.html(f"""
            <div style="font-family:monospace; background:#1e293b; color:white; padding:10px; border-radius:8px; text-align:center;">
                <div style="font-size:26px; font-weight:bold;"><span id="min">00</span>:<span id="sec">00</span></div>
                <div id="to_box" style="display:{'block' if state.get('timeout_active') else 'none'}; margin-top:5px; font-size:14px; color:#ef4444; font-weight:bold; background:#fee2e2; padding:2px; border-radius:5px;">
                    ⏳ <span id="to_sec">30</span>s
                </div>
            </div>
            <script>
                const actx = new (window.AudioContext || window.webkitAudioContext)();
                function playBeep(type) {{
                    if(actx.state === 'suspended') actx.resume();
                    const osc = actx.createOscillator(); osc.type = 'sine'; 
                    if(type==='long') {{ osc.frequency.value = 300; osc.start(); setTimeout(()=>osc.stop(), 1500); }}
                    else {{ osc.frequency.value = 600; osc.start(); setTimeout(()=>osc.stop(), 800); }}
                    osc.connect(actx.destination);
                }}

                if(!sessionStorage.getItem('to_sec')) sessionStorage.setItem('to_sec', 30);
                
                let s = {current_sec}; 
                let t = parseInt(sessionStorage.getItem('to_sec'));
                let running = { 'true' if state.get('timer_running') else 'false' };
                let is_to = { 'true' if state.get('timeout_active') else 'false' };
                
                function update() {{ 
                    if(running && s>0) {{ s--; if(s===0) playBeep('long'); }}
                    
                    if(is_to && t>0) {{
                        t--; sessionStorage.setItem('to_sec', t);
                        document.getElementById('to_sec').innerText = t<10?'0'+t:t;
                        if(t===0) playBeep('short');
                    }} else if (!is_to) {{ sessionStorage.setItem('to_sec', 30); }}

                    let m = Math.floor(s/60); let sec = s%60;
                    document.getElementById('sec').innerText = sec<10?'0'+sec:sec; 
                    document.getElementById('min').innerText = m<10?'0'+m:m; 
                }}
                
                if(window.timer) clearInterval(window.timer);
                window.timer = setInterval(update, 1000);
                update(); 
            </script>
        """, height=110)
        
    with c_score_L:
        st.markdown(f"""
            <div style='background:#1e293b; border-bottom:8px solid #2563eb; padding:15px; border-radius:15px; text-align:center; box-shadow: 0 5px 15px rgba(0,0,0,0.5);'>
                <h2 style='color:#93c5fd; margin:0; font-size:32px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{left_team}</h2>
                <div style='font-size:80px; font-weight:900; color:white; line-height:1.1; text-shadow: 3px 3px 6px rgba(0,0,0,0.6);'>{score_left}</div>
                <div style='background:{l_role_bg}; color:white; font-size:14px; font-weight:bold; padding:4px 15px; border-radius:15px; display:inline-block; margin-top:5px;'>{l_role}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c_score_R:
        st.markdown(f"""
            <div style='background:#1e293b; border-bottom:8px solid #dc2626; padding:15px; border-radius:15px; text-align:center; box-shadow: 0 5px 15px rgba(0,0,0,0.5);'>
                <h2 style='color:#fca5a5; margin:0; font-size:32px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{right_team}</h2>
                <div style='font-size:80px; font-weight:900; color:white; line-height:1.1; text-shadow: 3px 3px 6px rgba(0,0,0,0.6);'>{score_right}</div>
                <div style='background:{r_role_bg}; color:white; font-size:14px; font-weight:bold; padding:4px 15px; border-radius:15px; display:inline-block; margin-top:5px;'>{r_role}</div>
            </div>
        """, unsafe_allow_html=True)
        
    with c_half_info:
        prev_h = ""
        if c_half == 2:
            prev_score = state.get('half_1_score', '0-0').split('-')
            ps_l = prev_score[1] if state['swap_sides'] else prev_score[0]
            ps_r = prev_score[0] if state['swap_sides'] else prev_score[1]
            prev_h = f"<div style='font-size:12px; color:gray; margin-top:5px;'>H1: {ps_l}-{ps_r}</div>"
        st.markdown(f"<div style='background:#f1f5f9; padding:10px; border-radius:8px; text-align:center; border:1px solid #cbd5e1;'><div style='font-size:14px; color:gray;'>SET</div><h3 style='margin:0; color:#334155;'>{c_half}</h3>{prev_h}</div>", unsafe_allow_html=True)

    raid_active = "true" if state.get('raider_team') else "false"
    st.components.v1.html(f"""
        <div style="text-align:center; font-family:monospace; margin-bottom:-10px; display:{'block' if state.get('raider_team') else 'none'};">
            <span style="font-size:14px; color:#64748b; font-weight:bold; vertical-align:middle;">RAID </span>
            <span style="font-size:24px; font-weight:bold; color:#ef4444; background:#fee2e2; padding:2px 10px; border-radius:15px; border:2px solid #fca5a5;"><span id="r_sec">30</span>s</span>
        </div>
        <script>
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            function beepWarn() {{
                if(audioCtx.state === 'suspended') audioCtx.resume();
                const osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 1000;
                osc.connect(audioCtx.destination); osc.start(); setTimeout(() => osc.stop(), 150);
            }}
            let r = {30 if state.get('raider_team') else 0}; let r_run = {raid_active};
            if(r_run) {{
                window.rtimer = setInterval(() => {{
                    if(r>0) {{ 
                        r--; 
                        document.getElementById('r_sec').innerText = r<10?'0'+r:r; 
                        
                        // 💡 जादु: ३, २ र १ सेकेन्ड बाँकी हुँदा मात्र छोटो अलर्ट बजाउने, ० मा केही नबजाउने!
                        if(r <= 3 && r > 0) beepWarn(); 
                    }}
                }}, 1000);
            }}
        </script>
    """, height=50)

    # कोर्ट रेन्डर गर्ने
    court_container = st.empty()
    with court_container:
        render_kabaddi_court(state, p1, p2)
    
    def get_dod_dots(team):
        empties = state.get('empty_raids', {}).get(team, 0)
        return "⚪ ⚪" if empties == 0 else "🔴 ⚪" if empties == 1 else "🔴 🔴 (Do-or-Die)"
    def get_to_icons(team):
        used = state.get('timeouts', {}).get(str(c_half), {}).get(team, 0)
        return " ".join(["⏱️" if i < used else "⚪" for i in range(2)])

    c_ind_l, c_ind_r = st.columns(2)
    c_ind_l.markdown(f"<div style='text-align:center; font-size:14px; color:#64748b;'>Do-or-Die: {get_dod_dots(left_team)} | T/O: {get_to_icons(left_team)}</div>", unsafe_allow_html=True)
    c_ind_r.markdown(f"<div style='text-align:center; font-size:14px; color:#64748b;'>T/O: {get_to_icons(right_team)} | Do-or-Die: {get_dod_dots(right_team)}</div>", unsafe_allow_html=True)

    st.markdown("---")

    def reset_raid(is_cancel=False):
        if not is_cancel:
            state['next_raider_team'] = left_team if state['raider_team'] == right_team else right_team
        state['raider_team'] = None; state['raider_num'] = None; state['selected_targets'] = []
        state['raid_pos'] = 0; state['baulk_crossed'] = False; state['bonus_crossed'] = False

    # ==========================================
    # 🏃 SMART MATCH FLOW & AUTO-SCORING
    # ==========================================
    
    if not state.get('match_started'):
        st.markdown("<div style='text-align:center; padding:20px; background:#f8fafc; border-radius:10px; border:2px dashed #cbd5e1;'>", unsafe_allow_html=True)
        if c_half == 1:
            if not state.get('next_raider_team'):
                st.markdown("<h3 style='color:#334155;'>🪙 टस (Toss) र साइड छनौट</h3>", unsafe_allow_html=True)
                if st.button("🔄 कोर्टको साइड परिवर्तन गर्नुहोस् (Swap Sides)", width="stretch"):
                    state['swap_sides'] = not state['swap_sides']; save_kabaddi_scores(evt_code, mid, state); st.rerun()
                    
                st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                st.markdown("<h4 style='color:#475569;'>पहिलो रेड कुन टिमको?</h4>", unsafe_allow_html=True)
                ct1, ct2 = st.columns(2)
                lbl_color_L = "नीलो" if left_team == p1 else "रातो"
                lbl_color_R = "नीलो" if right_team == p1 else "रातो"
                
                if ct1.button(f"👈 {left_team} ({lbl_color_L})", width="stretch"):
                    state['next_raider_team'] = left_team; state['first_half_starter'] = left_team; save_kabaddi_scores(evt_code, mid, state); st.rerun()
                if ct2.button(f"{right_team} ({lbl_color_R}) 👉", width="stretch"):
                    state['next_raider_team'] = right_team; state['first_half_starter'] = right_team; save_kabaddi_scores(evt_code, mid, state); st.rerun()
            else:
                t_color_active = "#2563eb" if state['next_raider_team'] == p1 else "#dc2626"
                st.markdown(f"<h3 style='color:#334155;'>पहिलो रेड: <span style='color:{t_color_active};'>{state['next_raider_team']}</span></h3>", unsafe_allow_html=True)
                if st.button("🔄 टस सच्याउनुहोस् (Reset Toss)"):
                    state['next_raider_team'] = None; state['first_half_starter'] = None; save_kabaddi_scores(evt_code, mid, state); st.rerun()
                
                st.markdown("<br><h4 style='color:#475569;'>रेफ्रीको सिट्ठी कुरेर खेल सुरु गर्नुहोस् 👇</h4>", unsafe_allow_html=True)
                c_btn = st.columns([1,2,1])
                if c_btn[1].button("▶️ खेल सुरु गर्नुहोस् (Start Match)", type="primary", width="stretch"):
                    state['match_started'] = True; state['timer_running'] = True
                    state['last_event_msg'] = "▶️ म्याच सुरु भयो!"
                    state['last_event_icon'] = "KB_start_raid.png" 
                    st.session_state[f"audio_q_{mid}"] = {"speech": "Match started. Ready for the first raid.", "beep": (1000, 0.6, 1, 0, 'normal')}
                    save_kabaddi_scores(evt_code, mid, state); st.rerun()
        else:
            st.markdown("<h3 style='color:#334155;'>⏳ दोस्रो हाफ सुरु गर्न तयार हुनुहोस्</h3>", unsafe_allow_html=True)
            t_color_active = "#2563eb" if state.get('next_raider_team') == p1 else "#dc2626"
            st.markdown(f"<p style='font-size:18px;'>नियम अनुसार दोस्रो हाफको पहिलो रेड: <b><span style='color:{t_color_active};'>{state.get('next_raider_team')}</span></b> को हुन्छ।</p>", unsafe_allow_html=True)
            c_btn = st.columns([1,2,1])
            if c_btn[1].button("▶️ दोस्रो हाफ सुरु गर्नुहोस्", type="primary", width="stretch"):
                state['match_started'] = True; state['timer_running'] = True
                state['last_event_msg'] = "▶️ दोस्रो हाफ सुरु!"
                state['last_event_icon'] = "KB_start_raid.png" 
                st.session_state[f"audio_q_{mid}"] = {"speech": "Second half started.", "beep": (1000, 0.6, 1, 0, 'normal')}
                save_kabaddi_scores(evt_code, mid, state); st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.stop() 

    # ==========================================
    # 🔘 Play / Pause बटनको लजिक (म्याच सुरु भएपछि मात्र देखिने)
    # ==========================================
    st.markdown("<br>", unsafe_allow_html=True)
    c_t_toggle, c_gap = st.columns([2, 6])
    
    if state.get('timer_running'):
        if c_t_toggle.button("⏸️ टाइमर रोक्नुहोस् (Pause)", width="stretch"):
            state['timer_running'] = False
            state['remaining_seconds'] = current_sec # पज गर्दा समय सुरक्षित गर्ने
            state['timer_seconds'] = current_sec     # टिभीको लागि
            save_kabaddi_scores(evt_code, mid, state)
            st.rerun()
    else:
        if c_t_toggle.button("▶️ टाइमर चलाउनुहोस् (Play)", type="primary", width="stretch"):
            state['timer_running'] = True
            state['timeout_active'] = False
            state['last_start_time'] = time.time()   # सुरु गरेको समय
            state['remaining_seconds'] = current_sec # Play थिच्दाको विन्दु
            state['timer_seconds'] = current_sec     # टिभीको लागि
            save_kabaddi_scores(evt_code, mid, state)
            st.rerun()

    # --- RAIDER SELECTION ---
    if not state['raider_team']:
        next_t = state.get('next_raider_team')
        if not next_t: next_t = left_team 
        
        c_r1, c_r2 = st.columns(2)
        
        def set_raider(team, num):
            state['raider_team'] = team; state['raider_num'] = num; state['selected_targets'] = []
            state['raid_pos'] = 0; state['baulk_crossed'] = False; state['bonus_crossed'] = False
            if state.get('empty_raids', {}).get(team, 0) >= 2:
                state['last_event_msg'] = "🔥 डु-अर-डाइ रेड!"
                state['last_event_icon'] = "KB_do_or_die.png" 
                st.session_state[f"audio_q_{mid}"] = {"speech": "Do or die raid!", "beep": (1200, 0.3, 3, 0.1, 'normal')}
                
            save_kabaddi_scores(evt_code, mid, state); st.rerun()
            
        st.markdown("""<style>.team-btn-blue button[kind="primary"] { background-color: #2563eb !important; border-color: #2563eb !important; color: white !important; } .team-btn-red button[kind="primary"] { background-color: #dc2626 !important; border-color: #dc2626 !important; color: white !important; }</style>""", unsafe_allow_html=True)
        
        active_p = [n for n in state['lineup'].get(next_t, {}).get('court', []) if n not in state.get('out_players', {}).get(next_t, [])]
        btn_class = "team-btn-blue" if next_t == p1 else "team-btn-red"
        
        target_col = c_r1 if next_t == left_team else c_r2
        with target_col:
            st.markdown(f"<div style='text-align:center; font-weight:bold; color:#475569; margin-bottom:5px;'>१. {next_t} को रेडर छान्नुहोस्:</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='{btn_class}'>", unsafe_allow_html=True)
            cols = st.columns(7)
            for i, n in enumerate(active_p):
                if cols[i%7].button(str(n), key=f"rs_{next_t}_{n}", type="primary", width="stretch"): set_raider(next_t, n)
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        raider_t = state['raider_team']
        defender_t = p1 if raider_t == p2 else p2
        r_num = state['raider_num']
        active_defenders = [n for n in state['lineup'].get(defender_t, {}).get('court', []) if n not in state.get('out_players', {}).get(defender_t, [])]
        is_dod = state.get('empty_raids', {}).get(raider_t, 0) >= 2
        is_att_right = (raider_t == left_team)
        r_pos = state['raid_pos']
        
        def handle_line(btn_action):
            if btn_action == "mid_in": state['raid_pos'] = 1
            elif btn_action == "baulk_in": state['raid_pos'] = 2; state['baulk_crossed'] = True
            elif btn_action == "bonus_in": state['raid_pos'] = 3; state['bonus_crossed'] = True
            elif btn_action == "bonus_out": state['raid_pos'] = 2
            elif btn_action == "baulk_out": state['raid_pos'] = 1
            elif btn_action == "safe_home":
                touch_count = len(state['selected_targets'])
                bonus_pts = 1 if (state['bonus_crossed'] and len(active_defenders) >= 6) else 0
                total_pts = touch_count + bonus_pts
                
                if total_pts > 0:
                    state['out_players'][defender_t].extend(state['selected_targets'])
                    add_score_and_revive(raider_t, total_pts)
                    state['empty_raids'][raider_t] = 0 
                    
                    if total_pts >= 3: 
                        state['last_event_msg'] = f"🚀 सुपर रेड! ({touch_count} टच + {bonus_pts} बोनस)"
                        state['last_event_icon'] = "KB_touch_point.png"
                        # 👇 यहाँ स्कोर स्पिच थप्ने
                        score_speech = f"Score, {spell_num(state['score_a'])} to {spell_num(state['score_b'])}."
                        st.session_state[f"audio_q_{mid}"] = {"speech": f"Super Raid! {total_pts} points to {audio_name(raider_t)}. {score_speech}", "beep": (1000, 0.4, 3, 0.1, 'normal')}
                    else: 
                        state['last_event_msg'] = f"✅ रेड सफल! ({touch_count} टच + {bonus_pts} बोनस)"
                        state['last_event_icon'] = "KB_touch_point.png" if touch_count > 0 else "KB_bonus_point.png"
                        # 👇 यहाँ पनि स्कोर स्पिच थप्ने
                        score_speech = f"Score, {spell_num(state['score_a'])} to {spell_num(state['score_b'])}."
                        st.session_state[f"audio_q_{mid}"] = {"speech": f"Successful raid. {total_pts} point{'s' if total_pts>1 else ''} to {audio_name(raider_t)}. {score_speech}", "beep": (800, 0.3, 1, 0, 'normal')}
                else:
                    if state['baulk_crossed']:
                        state['empty_raids'][raider_t] += 1
                        if is_dod:
                            state['out_players'][raider_t].append(r_num)
                            add_score_and_revive(defender_t, 1) # 💡 पहिला पोइन्ट बढाउने
                            state['empty_raids'][raider_t] = 0
                            state['last_event_msg'] = "❌ Do-or-Die मा अङ्क नल्याउँदा रेडर आउट!"
                            state['last_event_icon'] = "kB_raider_out.png"
                            
                            # 🔊 यहाँ स्कोरसहित ओभरराइड गर्ने
                            score_speech = f"Score, {spell_num(state['score_a'])} to {spell_num(state['score_b'])}."
                            st.session_state[f"audio_q_{mid}"] = {
                                "speech": f"Raider out on do or die. 1 point to {audio_name(defender_t)}. {score_speech}", 
                                "beep": (900, 0.4, 2, 0.1, 'normal')
                            } 
                        else:
                            state['last_event_msg'] = "⏭️ खाली रेड (Empty Raid)"
                            state['last_event_icon'] = "KB_start_raid.png" 
                            # यहाँ अङ्क जोडिएको छैन, त्यसैले पुरानै ठिक छ
                            st.session_state[f"audio_q_{mid}"] = {"speech": "Empty raid.", "beep": (600, 0.2, 1, 0, 'normal')}
                    else:
                        state['last_event_msg'] = "❌ Baulk line क्रस नभएकोले रेडर आउट!"
                        state['last_event_icon'] = "KB_line_cut.png"
                        state['out_players'][raider_t].append(r_num)
                        add_score_and_revive(defender_t, 1) # 💡 पहिला पोइन्ट बढाउने
                        
                        # 🔊 यहाँ पनि स्कोरसहित ओभरराइड गर्ने
                        score_speech = f"Score, {spell_num(state['score_a'])} to {spell_num(state['score_b'])}."
                        st.session_state[f"audio_q_{mid}"] = {
                            "speech": f"Raider out. 1 point to {audio_name(defender_t)}. {score_speech}", 
                            "beep": (900, 0.4, 2, 0.1, 'normal')
                        }
                
                reset_raid(); save_kabaddi_scores(evt_code, mid, state); st.rerun(); return
            save_kabaddi_scores(evt_code, mid, state); st.rerun()

        st.markdown(f"""
        <style>
            .def-btn button[kind="primary"] {{ background-color: #facc15 !important; color: black !important; border: 2px solid black !important; box-shadow: 0 0 10px #facc15; }}
            .def-btn button[kind="secondary"] {{ background-color: {'#2563eb' if defender_t==p1 else '#dc2626'} !important; border-color: {'#2563eb' if defender_t==p1 else '#dc2626'} !important; color: white !important; }}
            div.mid-btn button {{ background-color: #ef4444 !important; color: white !important; font-weight: bold; border: 2px solid #991b1b !important; }}
            div.baulk-btn button {{ background-color: #22c55e !important; color: white !important; font-weight: bold; border: 2px solid #14532d !important; }}
            div.bonus-btn button {{ background-color: #22c55e !important; color: white !important; font-weight: bold; border: 2px solid #14532d !important; }}
        </style>
        """, unsafe_allow_html=True)
        
        c_r1, c_r2 = st.columns(2)
        target_col = c_r1 if defender_t == left_team else c_r2
        
        with target_col:
            if r_pos == 0:
                st.markdown("<div style='text-align:center; font-size:16px; font-weight:bold; color:#475569; margin-bottom:5px;'>रेडरलाई भित्र पठाउनुहोस्:</div>", unsafe_allow_html=True)
                c_mid_l1, c_mid_l2, c_mid_l3 = st.columns(3)
                if not is_att_right:
                    with c_mid_l3:
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("◀️ Mid ┃", width="stretch"): handle_line("mid_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                else:
                    with c_mid_l1:
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("┃ Mid ▶️", width="stretch"): handle_line("mid_in")
                        st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:center; font-size:16px; font-weight:bold; color:#475569; margin-bottom:5px;'>डिफेन्डर ({defender_t}): टच भएमा छान्नुहोस्</div>", unsafe_allow_html=True)
                c_l1, c_l2, c_l3 = st.columns(3)
                if not is_att_right: 
                    with c_l1: 
                        st.markdown("<div class='bonus-btn'>", unsafe_allow_html=True)
                        if st.button("Bonus ║", disabled=(r_pos<2), width="stretch"): handle_line("bonus_out" if r_pos>=3 else "bonus_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l2: 
                        st.markdown("<div class='baulk-btn'>", unsafe_allow_html=True)
                        if st.button("Baulk ┃", disabled=(r_pos<1), width="stretch"): handle_line("baulk_out" if r_pos>=2 else "baulk_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l3: 
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("◀️ Safe", width="stretch"): handle_line("safe_home") 
                        st.markdown("</div>", unsafe_allow_html=True)
                else: 
                    with c_l1: 
                        st.markdown("<div class='mid-btn'>", unsafe_allow_html=True)
                        if st.button("Safe ▶️", width="stretch"): handle_line("safe_home") 
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l2: 
                        st.markdown("<div class='baulk-btn'>", unsafe_allow_html=True)
                        if st.button("┃ Baulk", disabled=(r_pos<1), width="stretch"): handle_line("baulk_out" if r_pos>=2 else "baulk_in")
                        st.markdown("</div>", unsafe_allow_html=True)
                    with c_l3: 
                        st.markdown("<div class='bonus-btn'>", unsafe_allow_html=True)
                        if st.button("║ Bonus", disabled=(r_pos<2), width="stretch"): handle_line("bonus_out" if r_pos>=3 else "bonus_in")
                        st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                cols = st.columns(7)
                st.markdown("<div class='def-btn'>", unsafe_allow_html=True)
                for i, n in enumerate(active_defenders):
                    is_sel = n in state['selected_targets']
                    if cols[i%7].button(str(n), key=f"def_{n}", type="primary" if is_sel else "secondary", width="stretch"):
                        if is_sel: state['selected_targets'].remove(n)
                        else: state['selected_targets'].append(n)
                        save_kabaddi_scores(evt_code, mid, state); st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br><hr style='margin:10px 0;'>", unsafe_allow_html=True)
        c_act1, c_act2, c_act3 = st.columns([1, 2, 1])
        with c_act2:
            cc1, cc2 = st.columns(2)
            if cc1.button("🛡️ ट्याकल/आउट", type="primary", width="stretch"):
                is_super_tackle = len(active_defenders) <= 3
                tackle_pts = 2 if is_super_tackle else 1
                state['out_players'][raider_t].append(r_num)
                add_score_and_revive(defender_t, tackle_pts) # 💡 यहाँ पोइन्ट अपडेट भयो
                state['empty_raids'][raider_t] = 0 
                
                state['last_event_icon'] = "kB_raider_out.png"
                
                # 💡 दुवैको लागि एउटै स्कोर स्पिच निकाल्ने
                score_speech = f"Score, {spell_num(state['score_a'])} to {spell_num(state['score_b'])}."
                
                if is_super_tackle:
                    state['last_event_msg'] = f"🌟 सुपर ट्याकल! (+2 अङ्क)"
                    # 🔊 सुपर ट्याकल स्पिच (स्कोर सहित)
                    st.session_state[f"audio_q_{mid}"] = {
                        "speech": f"Super Tackle! 2 points to {audio_name(defender_t)}. {score_speech}",
                        "beep": (1000, 0.4, 2, 0.1, 'normal')
                    }
                else:
                    state['last_event_msg'] = f"🛡️ ट्याकल! (+1 अङ्क)"
                    # 🔊 नर्मल ट्याकल स्पिच (स्कोर सहित)
                    st.session_state[f"audio_q_{mid}"] = {
                        "speech": f"Tackle! 1 point to {audio_name(defender_t)}. {score_speech}", 
                        "beep": (800, 0.3, 1, 0, 'normal')
                    }
                    
                reset_raid(); save_kabaddi_scores(evt_code, mid, state); st.rerun()
                
            if cc2.button("🔙 क्यान्सिल", width="stretch"):
                state['last_event_msg'] = "🔙 रेड रद्द गरियो!" 
                state['last_event_icon'] = "KB_cant_broken.png"
                st.session_state[f"audio_q_{mid}"] = {"speech": "Raid cancelled.", "beep": (600, 0.2, 1, 0, 'normal')}
                reset_raid(is_cancel=True); save_kabaddi_scores(evt_code, mid, state); st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    c_end1, c_end2, c_end3 = st.columns([1, 2, 1])
    btn_label = "⏸️ पहिलो हाफ समाप्त गर्नुहोस्" if c_half == 1 else "🏁 म्याच समाप्त गर्नुहोस्"
    
    # 💡 बटन थिचेपछि मात्रै सबै लजिक चल्छ
    if c_end2.button(btn_label, width="stretch", type="secondary"):
        if c_half == 1:
            state['half'] = 2; state['swap_sides'] = not state['swap_sides']; state['half_1_score'] = f"{state['score_a']}-{state['score_b']}"
            state['match_started'] = False; state['timer_running'] = False; state['next_raider_team'] = p2 if state.get('first_half_starter') == p1 else p1 
            state['last_event_msg'] = "🔄 हाफ परिवर्तन भयो!"
            state['last_event_icon'] = "KB_match_end.png"
            # 🔊 हाफ टाइमको स्पिच
            st.session_state[f"audio_q_{mid}"] = {"speech": "First half completed. Court change.", "beep": (1000, 0.5, 2, 0.2, 'normal')}
            save_kabaddi_scores(evt_code, mid, state); st.rerun()
        else:
            # १. सबैभन्दा पहिले विजेता (winner) पत्ता लगाउने
            winner = p1 if state['score_a'] > state['score_b'] else p2 if state['score_b'] > state['score_a'] else "Tie"
            winner_team_id = sel_m['p1_id'] if winner == p1 else sel_m['p2_id'] if winner == p2 else None
            winner_muni_id = sel_m['p1_muni'] if winner == p1 else sel_m['p2_muni'] if winner == p2 else None
            
            state['last_event_msg'] = f"🏁 म्याच सम्पन्न! {winner} विजयी!" 
            state['last_event_icon'] = "KB_match_end.png"
            
            # ==========================================
            # २. 💡 सेलिब्रेसन र स्पिच पठाउने!
            # ==========================================
            if winner != "Tie":
                win_score = max(state['score_a'], state['score_b'])
                lose_score = min(state['score_a'], state['score_b'])
                state['tv_celebration'] = {
                    "show": True,
                    "title": "🏆 MATCH CHAMPION 🏆",
                    "winner": str(winner).upper(),
                    "score": f"{win_score} - {lose_score}"
                }
                # 🔊 च्याम्पियन स्पिच थप्ने
                champ_speech = f"Match completed. The ultimate champion is {audio_name(winner)}!"
                st.session_state[f"audio_q_{mid}"] = {
                    "speech": champ_speech,
                    "beep": (1000, 0.4, 4, 0.2, 'normal') # ४ पटक लामो सिट्ठी
                }
            else:
                state['tv_celebration'] = {
                    "show": True,
                    "title": "🤝 MATCH TIED 🤝",
                    "winner": "TIE (बराबरी)",
                    "score": f"{state['score_a']} - {state['score_b']}"
                }
                # 🔊 बराबरी हुँदाको स्पिच
                st.session_state[f"audio_q_{mid}"] = {
                    "speech": "Match completed. The match is a tie.",
                    "beep": (1000, 0.4, 4, 0.2, 'normal') 
                }
                
            # ३. डाटाबेस अपडेट गर्ने (एक पटक मात्र)
            conn = db.get_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE matches SET winner_name=%s, winner_team_id=%s, winner_muni_id=%s, live_state=%s, status='Completed' 
                WHERE match_no=%s AND event_code=%s
            """, (winner, winner_team_id, winner_muni_id, json.dumps(state), mid, evt_code))
            conn.commit()
            c.close()
            conn.close()
            
            save_kabaddi_scores(evt_code, mid, state)
            st.balloons()
            st.stop()
    
    
            
            # ==========================================
            # 💡 जादु: टिभीलाई च्याम्पियन सेलिब्रेसन देखाउन अर्डर!
            # ==========================================
            if winner != "Tie":
                win_score = max(state['score_a'], state['score_b'])
                lose_score = min(state['score_a'], state['score_b'])
                state['tv_celebration'] = {
                    "show": True,
                    "title": "🏆 MATCH CHAMPION 🏆",
                    "winner": str(winner).upper(),
                    "score": f"{win_score} - {lose_score}"
                }
            else:
                state['tv_celebration'] = {
                    "show": True,
                    "title": "🤝 MATCH TIED 🤝",
                    "winner": "TIE (बराबरी)",
                    "score": f"{state['score_a']} - {state['score_b']}"
                }
            
            conn = db.get_connection()
            c = conn.cursor()
            c.execute("""
                UPDATE matches SET winner_name=%s, winner_team_id=%s, winner_muni_id=%s, live_state=%s, status='Completed' 
                WHERE match_no=%s AND event_code=%s
            """, (winner, winner_team_id, winner_muni_id, json.dumps(state), mid, evt_code))
            conn.commit()
            c.close()
            conn.close()
            
            save_kabaddi_scores(evt_code, mid, state)
            st.balloons()
            st.stop()


    # ==========================================
    # ⚙️ SIDE PANELS & HIDDEN SETTINGS
    # ==========================================
    st.divider()
    
    with st.expander("⚙️ म्यानुअल कन्ट्रोल (गल्ती सच्याउन)"):
        c_mc1, c_mc2 = st.columns(2)
        if c_mc1.button("🔄 पालो (Turn) परिवर्तन गर्नुहोस्", width="stretch"):
            if state.get('next_raider_team'): state['next_raider_team'] = left_team if state['next_raider_team'] == right_team else right_team; st.rerun()
        if c_mc2.button("🔄 कोर्टको साइड स्वाप (Swap Sides)", width="stretch"):
            state['swap_sides'] = not state['swap_sides']
            state['last_event_msg'] = "🔄 म्यानुअल साइड स्वाप!"
            state['last_event_icon']="KB_substitution.png"
            # 🔊 कोर्ट चेन्ज स्पिच
            st.session_state[f"audio_q_{mid}"] = {"speech": "Courts changed.", "beep": (1000, 0.3, 2, 0.1, 'normal')}
            save_kabaddi_scores(evt_code, mid, state); st.rerun()

    def toggle_state(key):
        st.session_state[key] = not st.session_state.get(key, False); st.rerun()

    def render_side_panel(team, col):
        with col:
            # 💡 १. जादु: डाटाबेसबाट तान्दा कुनै 'Key' छुटेको छ भने क्र्यास हुन नदिन .get() को प्रयोग
            lineup_data = state.get('lineup', {}).get(team, {})
            court_p = lineup_data.get('court', [])
            bench_p = lineup_data.get('bench', [])
            out_p = state.get('out_players', {}).get(team, [])
            cards_dict = state.get('cards', {}).get(team, {})
            
            # कोर्टमा भएका एक्टिभ खेलाडी गन्ने (सुरक्षित तरिका)
            active_p = len([n for n in court_p if n not in out_p])
            
            c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
            t_icon = "🔵" if team == left_team else "🔴"
            
            is_subs_open = st.session_state.get(f"{state_key}_show_subs_{team}", False)
            btn_subs_type = "primary" if is_subs_open else "secondary"
            icon_subs = "🔽" if is_subs_open else "▶️"
            
            is_cards_open = st.session_state.get(f"{state_key}_show_cards_{team}", False)
            btn_cards_type = "primary" if is_cards_open else "secondary"
            icon_cards = "🔽" if is_cards_open else "▶️"

            if c1.button(f"{t_icon} {icon_subs} Subs({5-state.get('subs', {}).get(team, 0)})", key=f"bs_{team}", width="stretch", type=btn_subs_type): 
                st.session_state[f"{state_key}_show_subs_{team}"] = not is_subs_open
                st.session_state[f"{state_key}_show_cards_{team}"] = False
                st.rerun()

            if c2.button(f"{t_icon} {icon_cards} Cards", key=f"bc_{team}", width="stretch", type=btn_cards_type): 
                st.session_state[f"{state_key}_show_cards_{team}"] = not is_cards_open
                st.session_state[f"{state_key}_show_subs_{team}"] = False
                st.rerun()

            if c3.button(f"{t_icon} ⚙️ Tech Pt", key=f"bt_{team}", width="stretch"): 
                add_score_and_revive(team, 1)
                state['last_event_msg'] = f"⚙️ {team} लाई प्राविधिक अङ्क (+1)"
                state['last_event_icon'] = "KB_touch_point.png"
                score_speech = f"Score, {spell_num(state.get('score_a', 0))} to {spell_num(state.get('score_b', 0))}."
                st.session_state[f"audio_q_{mid}"] = {"speech": f"Technical point, {audio_name(team)}. {score_speech}", "beep": (1000, 0.4, 2, 0.1, 'normal')}
                save_kabaddi_scores(evt_code, mid, state); st.rerun()

            if c4.button(f"{t_icon} ⏳ Time", key=f"bto_{team}", width="stretch"): 
                if state.get('timeouts', {}).get(str(c_half), {}).get(team, 0) < 2: 
                    # 💡 डिक्सनरी नभए सुरक्षित रूपले बनाउने
                    if 'timeouts' not in state: state['timeouts'] = {}
                    if str(c_half) not in state['timeouts']: state['timeouts'][str(c_half)] = {}
                    
                    state['timeouts'][str(c_half)][team] = state['timeouts'][str(c_half)].get(team, 0) + 1
                    state['timeout_active'] = True; state['timer_running'] = False 
                    state['last_event_msg'] = f"⏳ {team} को टाइमआउट!"
                    state['last_event_icon'] = "KB_time_out.png"
                    st.session_state[f"audio_q_{mid}"] = {"speech": f"Time out, {audio_name(team)}.", "beep": (1000, 0.5, 2, 0.2, 'normal')}
                    save_kabaddi_scores(evt_code, mid, state); st.rerun()
            
            if active_p == 0:
                if st.button("🚨 LONA", type="primary", width="stretch", key=f"lona_{team}"): 
                    state['lona_transition'] = team
                    save_kabaddi_scores(evt_code, mid, state)
                    st.rerun()

            # 🔄 ३. सब्स्टिच्युसन प्यानल
            if is_subs_open:
                st.markdown("<div style='background:#f8fafc; padding:15px; border-radius:10px; border:2px solid #e2e8f0;'>", unsafe_allow_html=True)
                subs_left = 5 - state.get('subs', {}).get(team, 0)
                
                if subs_left > 0:
                    roster = state.get('roster', {}).get(team, {})
                    valid_bench = [b for b in bench_p if cards_dict.get(str(b)) != 'Red']
                    
                    co, ci = st.columns(2)
                    with co:
                        st.markdown("<h4 style='color:#ef4444; font-size:16px; margin-bottom:5px;'>🔴 बाहिर जाने (Court)</h4>", unsafe_allow_html=True)
                        sub_out = st.radio("Out", court_p, format_func=lambda x: f"{x} - {roster.get(str(x), roster.get(int(x), 'Unknown'))}", key=f"rad_out_{team}", label_visibility="collapsed", index=None)
                    with ci:
                        st.markdown("<h4 style='color:#22c55e; font-size:16px; margin-bottom:5px;'>🟢 भित्र आउने (Bench)</h4>", unsafe_allow_html=True)
                        sub_in = st.radio("In", valid_bench, format_func=lambda x: f"{x} - {roster.get(str(x), roster.get(int(x), 'Unknown'))}", key=f"rad_in_{team}", label_visibility="collapsed", index=None)

                    st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)

                    if sub_out and sub_in:
                        out_name = roster.get(str(sub_out), roster.get(int(sub_out), 'Unknown'))
                        in_name = roster.get(str(sub_in), roster.get(int(sub_in), 'Unknown'))
                        
                        if st.button(f"✅ Swap: [ {sub_out} ] {out_name}  ➔  [ {sub_in} ] {in_name}", key=f"do_sub_{team}", use_container_width=True, type="primary"):
                            if sub_out in court_p and sub_in in bench_p:
                                # सुरक्षित रूपमा खेलाडी साट्ने
                                if 'lineup' not in state: state['lineup'] = {}
                                if team not in state['lineup']: state['lineup'][team] = {'court': court_p, 'bench': bench_p}
                                
                                c_idx, b_idx = court_p.index(sub_out), bench_p.index(sub_in)
                                state['lineup'][team]['court'][c_idx] = sub_in
                                state['lineup'][team]['bench'][b_idx] = sub_out
                                
                                if 'subs' not in state: state['subs'] = {}
                                state['subs'][team] = state['subs'].get(team, 0) + 1
                                
                                state['last_event_msg'] = f"🔄 खेलाडी परिवर्तन: {sub_out} Out ➔ {sub_in} In" 
                                state['last_event_icon'] = "KB_substitution.png"
                                st.session_state[f"audio_q_{mid}"] = {"speech": f"Substitution for {audio_name(team)}.", "beep": (800, 0.3, 2, 0.1, 'normal')}
                                st.session_state[f"{state_key}_show_subs_{team}"] = False 
                                save_kabaddi_scores(evt_code, mid, state); st.rerun()
                else: 
                    st.error("🚨 Subs Limit Reached!")
                st.markdown("</div>", unsafe_allow_html=True)

            # 🃏 ४. कार्ड प्यानल
            if is_cards_open:
                st.markdown("<div style='background:#fef2f2; padding:15px; border-radius:10px; border:2px solid #fca5a5;'>", unsafe_allow_html=True)
                
                y_cards = [p for p, c in cards_dict.items() if c == 'Yellow']
                if y_cards:
                    st.markdown("<b style='color:#b45309;'>⏱️ निलम्बन समाप्त भएकालाई भित्र पठाउनुहोस्:</b>", unsafe_allow_html=True)
                    for yp in y_cards:
                        if st.button(f"✅ जर्सी {yp} लाई कोर्टमा फर्काउनुहोस्", key=f"y_clr_{team}_{yp}", use_container_width=True):
                            # १. कार्ड र टाइमर सफा गर्ने
                            state['cards'][team].pop(str(yp), None)
                            if str(yp) in state.get('yc_timers', {}).get(team, {}): state['yc_timers'][team].pop(str(yp))
                            if str(yp) in state.get('yc_announced', {}).get(team, {}): state['yc_announced'][team].pop(str(yp))
                            
                            # 💡 २. जादु: खेलाडीलाई 'आउट' लिस्टबाट हटाउने (ताकि ऊ कोर्टमा फर्कियोस्)
                            if yp in state.get('out_players', {}).get(team, []):
                                state['out_players'][team].remove(yp)
                            # केही गरी स्ट्रिङमा बसेको छ भने पनि हटाउने
                            elif str(yp) in state.get('out_players', {}).get(team, []):
                                state['out_players'][team].remove(str(yp))

                            # ३. म्यासेज र अडियो
                            state['last_event_msg'] = f"🟨 जर्सी {yp} कोर्टमा फर्किए!"
                            state['last_event_icon'] = "KB_substitution.png"
                            st.session_state[f"audio_q_{mid}"] = {"speech": f"Player {spell_num(yp)} returns to court.", "beep": (800, 0.3, 1, 0, 'normal')}
                            
                            save_kabaddi_scores(evt_code, mid, state); st.rerun()
                    st.markdown("<hr style='margin: 10px 0; border-color:#fca5a5;'>", unsafe_allow_html=True)

                roster = state.get('roster', {}).get(team, {})
                active_for_card = court_p + bench_p
                valid_for_card = [p for p in active_for_card if cards_dict.get(str(p)) != 'Red']

                cp1, cp2 = st.columns(2)
                with cp1:
                    st.markdown("<h4 style='color:#334155; font-size:16px; margin-bottom:5px;'>👤 खेलाडी छान्नुहोस्</h4>", unsafe_allow_html=True)
                    sel_player = st.radio("Player", valid_for_card, format_func=lambda x: f"{x} - {roster.get(str(x), roster.get(int(x), 'Unknown'))}", key=f"rad_card_p_{team}", label_visibility="collapsed", index=None)
                with cp2:
                    st.markdown("<h4 style='color:#334155; font-size:16px; margin-bottom:5px;'>🃏 कार्ड छान्नुहोस्</h4>", unsafe_allow_html=True)
                    card_options = {"Green": "🟩 ग्रीन (चेतावनी)", "Yellow": "🟨 पहेँलो (२ मिनेट)", "Red": "🟥 रातो (निष्कासन)"}
                    sel_card = st.radio("Card", list(card_options.keys()), format_func=lambda x: card_options[x], key=f"rad_card_t_{team}", label_visibility="collapsed", index=None)
                
                st.markdown("<hr style='margin: 10px 0; border-color:#fca5a5;'>", unsafe_allow_html=True)

                if sel_player and sel_card:
                    p_name = roster.get(str(sel_player), roster.get(int(sel_player), 'Unknown'))
                    if st.button(f"⚠️ Confirm: [ {sel_player} ] {p_name} लाई {card_options[sel_card]}", key=f"do_card_{team}", use_container_width=True, type="primary"):
                        # सुरक्षित रूपमा डिक्सनरीहरू बनाउने
                        if 'cards' not in state: state['cards'] = {}
                        if team not in state['cards']: state['cards'][team] = {}
                        if 'yc_timers' not in state: state['yc_timers'] = {}
                        if team not in state['yc_timers']: state['yc_timers'][team] = {}
                        if 'out_players' not in state: state['out_players'] = {}
                        if team not in state['out_players']: state['out_players'][team] = []
                        
                        s_cp = str(sel_player)
                        state['cards'][team][s_cp] = sel_card
                        state['last_event_icon'] = "KB_penalty_card.png"
                        
                        import time
                        if sel_card == 'Yellow': 
                            state['yc_timers'][team][s_cp] = time.time()
                            state['last_event_msg'] = f"🟨 जर्सी {sel_player} लाई पहेँलो कार्ड!"
                            st.session_state[f"audio_q_{mid}"] = {"speech": f"Yellow card! Two minutes suspension for jersey {spell_num(sel_player)}, {audio_name(team)}.", "beep": (1200, 0.5, 3, 0.1, 'normal')}
                            if sel_player not in state['out_players'][team]: state['out_players'][team].append(sel_player)
                        elif sel_card == 'Red':
                            state['last_event_msg'] = f"🟥 जर्सी {sel_player} लाई रातो कार्ड!"
                            st.session_state[f"audio_q_{mid}"] = {"speech": f"Red card! Jersey {spell_num(sel_player)}, {audio_name(team)} is out of the match.", "beep": (1200, 0.6, 4, 0.1, 'normal')}
                            if sel_player not in state['out_players'][team]: state['out_players'][team].append(sel_player)
                        else:
                            state['last_event_msg'] = f"🟩 जर्सी {sel_player} लाई ग्रीन कार्ड!"
                            st.session_state[f"audio_q_{mid}"] = {"speech": f"Green card warning for jersey {spell_num(sel_player)}, {audio_name(team)}.", "beep": (1000, 0.3, 2, 0.1, 'normal')}
                            
                        st.session_state[f"{state_key}_show_cards_{team}"] = False
                        save_kabaddi_scores(evt_code, mid, state); st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

            

    c_panel_L, c_panel_R = st.columns(2)
    render_side_panel(left_team, c_panel_L)
    render_side_panel(right_team, c_panel_R)

    # ==========================================
    # 🔊 अन्तिम जादु: स्पिच (Audio) प्ले गर्ने इन्जिन
    # ==========================================
    audio_key = f"audio_q_{mid}"
    if audio_key in st.session_state:
        audio_data = st.session_state.pop(audio_key)
        speech_text = audio_data.get("speech", "")
        
        if speech_text:
            try:
                from gtts import gTTS
                import io
                import base64
                
                # टेक्स्टलाई अडियोमा कन्भर्ट गर्ने
                tts = gTTS(text=speech_text, lang='en', slow=False)
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                fp.seek(0)
                b64 = base64.b64encode(fp.read()).decode()
                
                # अटोमेटिक बजाउने HTML ट्याग
                st.components.v1.html(f"""
                    <audio autoplay>
                        <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                    </audio>
                """, height=0)
            except Exception as e:
                pass