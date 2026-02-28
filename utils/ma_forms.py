import streamlit as st
import pandas as pd
import math
import json
import database as db
import re
import utils.bracket_generator as bg  
import utils.pdf_generator as pg      
from config import CONFIG             

# ==========================================
# 💾 डाटाबेस सेटिङ (टाइसिट सेभ गर्न)
# ==========================================
def setup_bracket_table():
    conn = db.get_connection()
    c = conn.cursor()
    # 💡 PostgreSQL Syntax
    c.execute('''
        CREATE TABLE IF NOT EXISTS ma_brackets (
            event_code VARCHAR(50) PRIMARY KEY, 
            draw_json TEXT, 
            byes_json TEXT, 
            progress_json TEXT
        )
    ''')
    conn.commit()
    c.close()
    conn.close()

def save_bracket(evt_code, draw_data, byes):
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT progress_json FROM ma_brackets WHERE event_code=%s", (evt_code,))
    row = c.fetchone()
    prog = row[0] if row and row[0] else "{}"
    
    # 💡 PostgreSQL UPSERT
    c.execute("""
        INSERT INTO ma_brackets (event_code, draw_json, byes_json, progress_json) 
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (event_code) DO UPDATE 
        SET draw_json = EXCLUDED.draw_json, byes_json = EXCLUDED.byes_json, progress_json = EXCLUDED.progress_json
    """, (evt_code, json.dumps(draw_data), json.dumps(byes), prog))
    conn.commit()
    c.close()
    conn.close()

def load_bracket(evt_code):
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT draw_json, byes_json FROM ma_brackets WHERE event_code=%s", (evt_code,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row: return json.loads(row[0]), json.loads(row[1])
    return None, None

def load_progress_from_db(evt_code):
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT progress_json FROM ma_brackets WHERE event_code=%s", (evt_code,))
    row = c.fetchone()
    c.close()
    conn.close()
    if row and row[0]:
        prog = json.loads(row[0])
        for k, v in prog.items():
            if k not in st.session_state: st.session_state[k] = v

def sync_progress_to_db(evt_code):
    prog = {k: st.session_state[k] for k in st.session_state.keys() if f"_{evt_code}_" in k and (k.startswith("winner_") or k.startswith("published_") or k.startswith("votes_") or k.startswith("scores_"))}
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE ma_brackets SET progress_json=%s WHERE event_code=%s", (json.dumps(prog), evt_code))
    conn.commit()
    c.close()
    conn.close()

# ==========================================
# 🧮 गणितीय लजिक (BYE क्याल्कुलेसन)
# ==========================================
def get_standard_byes(total_slots, num_byes):
    byes = []
    if num_byes == 0: return byes
    if num_byes >= 1: byes.append(2) 
    if num_byes >= 2: byes.append(total_slots - 1) 
    if num_byes >= 3: byes.append((total_slots // 2)) 
    if num_byes >= 4: byes.append((total_slots // 2) + 1)
    
    current_slot = 4
    while len(byes) < num_byes:
        if current_slot not in byes and current_slot <= total_slots:
            byes.append(current_slot)
        current_slot += 1
    return sorted(byes)

# ==========================================
# 🥋 मुख्य UI (Kata - WKF 2026 Majority Vote)
# ==========================================
def render_panel(evt_code, current_event, players_df):
    """
    नोट: फङ्सनको नाम 'render_panel' राखिएको छ ताकि 7_Martial_Arts.py ले
    यसलाई सिधै कल गर्न सकोस् (ma_forms.render_panel)।
    """
    setup_bracket_table()
    load_progress_from_db(evt_code)
    
    st.markdown(f"<h3 style='color:#1e3a8a; border-bottom:2px solid #1e3a8a; padding-bottom:10px;'>🥋 {current_event['name']} (WKF 2026 Kata Rules)</h3>", unsafe_allow_html=True)
    
    if players_df is None or players_df.empty:
        st.warning("⚠️ यस इभेन्टमा कुनै खेलाडी दर्ता भएका छैनन्।")
        return

    # 💡 पालिका, खेलाडी ID र M_ID सुरक्षित तरिकाले मिलाउने
    p_names = players_df.get('Player_Name', players_df.get('name', 'Unknown'))
    m_names = players_df.get('Municipality', players_df.get('school_name', ''))
    mun_ids = players_df.get('mun_id', players_df.get('municipality_id', '0'))
    
    players_df['Display_Name'] = p_names + " (" + m_names + ") [ID: " + players_df['id'].astype(str) + "] [M_ID: " + mun_ids.astype(str) + "]"
    
    registered_players = players_df['Display_Name'].tolist()
    num_players = len(registered_players)
    
    next_power_of_2 = 2**(math.ceil(math.log(num_players, 2))) if num_players > 1 else 2
    num_byes = next_power_of_2 - num_players
    
    saved_draw, saved_byes = load_bracket(evt_code)
    bye_slots = saved_byes if saved_byes is not None else get_standard_byes(next_power_of_2, num_byes)

    tab_draw, tab_bouts, tab_results = st.tabs([
        "📊 १. गोला र टाइसिट (Draw)", 
        "⚔️ २. म्याच सञ्चालन (Bouts)", 
        "🏆 ३. नतिजा (Podium)"
    ])

    all_matches_for_pdf = []
    bouts_data = {}
    
    if saved_draw:
        def get_player(slot_num):
            if slot_num in bye_slots: return "BYE"
            for p, s in saved_draw.items():
                if s == slot_num: return p
            return "TBD"

        total_rounds = int(math.log2(next_power_of_2))
        bout_counter = 1

        for r in range(1, total_rounds + 1):
            num_bouts = next_power_of_2 // (2**r)
            r_name = "Final" if r == total_rounds else ("Semi-Final" if r == total_rounds - 1 else f"Round {r}")
            bouts_data[r] = {'name': r_name, 'bouts': []}
            
            for i in range(num_bouts):
                bout_id = f"Bout {bout_counter}"
                src1, src2 = None, None
                
                if r == 1: 
                    p1, p2 = get_player(i * 2 + 1), get_player(i * 2 + 2)
                else:
                    prev_bouts = bouts_data[r-1]['bouts']
                    src1 = int(prev_bouts[i*2]['id'].split(' ')[1])
                    src2 = int(prev_bouts[i*2+1]['id'].split(' ')[1])
                    p1 = st.session_state.get(f"winner_{evt_code}_Bout {src1}", "TBD")
                    p2 = st.session_state.get(f"winner_{evt_code}_Bout {src2}", "TBD")
                
                if ("BYE" in [p1, p2]) and ("TBD" not in [p1, p2]):
                    adv_p = p1 if p2 == "BYE" else p2
                    if adv_p != "BYE":
                        st.session_state[f"winner_{evt_code}_{bout_id}"] = adv_p
                        st.session_state[f"published_{evt_code}_{bout_id}"] = True
                        sync_progress_to_db(evt_code)
                        
                bouts_data[r]['bouts'].append({'id': bout_id, 'p1': p1, 'p2': p2, 'r_name': r_name})
                
                # PDF को लागि डाटा
                def clean_name_for_pdf(n):
                    if n in ["BYE", "TBD"]: return n
                    return re.sub(r" \[M_ID: \d+\]", "", n)
                    
                all_matches_for_pdf.append({
                    'id': bout_counter, 'round': r, 'p1': clean_name_for_pdf(p1), 'p2': clean_name_for_pdf(p2),
                    'winner': clean_name_for_pdf(st.session_state.get(f"winner_{evt_code}_{bout_id}")),
                    'title': "🏆 FINAL" if r == total_rounds else ("Semi-Final" if r == total_rounds - 1 else f"Match {bout_counter}"),
                    'is_third_place': False, 'source_m1': src1, 'source_m2': src2
                })
                bout_counter += 1

    # ---------------------------------------------------------
    # 📊 TAB 1: गोला र टाइसिट
    # ---------------------------------------------------------
    with tab_draw:
        st.info(f"👥 **कुल खेलाडी:** {num_players} &nbsp;|&nbsp; 🎯 **टाइसिट स्लट:** {next_power_of_2} &nbsp;|&nbsp; 🛑 **जम्मा 'Bye':** {num_byes}")
        
        if saved_draw and all_matches_for_pdf:
            tree_pdf = bg.generate_tree_pdf(current_event['name'], current_event.get('gender',''), current_event.get('category',''), all_matches_for_pdf)
            st.download_button("🖨️ Print Visual Bracket Tree (PDF)", data=tree_pdf, file_name=f"Bracket_{evt_code}.pdf", mime="application/pdf", type="primary")
            st.markdown("<hr/>", unsafe_allow_html=True)
            
        col1, col2 = st.columns([1, 1.5])
        with col1:
            st.markdown("#### 📋 ब्ल्याङ्क टाइसिट")
            for i in range(1, next_power_of_2, 2):
                s1_text = f"Slot {i}" + (" (BYE)" if i in bye_slots else "")
                s2_text = f"Slot {i+1}" + (" (BYE)" if i+1 in bye_slots else "")
                st.markdown(f"<div style='background-color:#f8fafc; padding:8px; border:1px solid #cbd5e1; border-radius:6px; margin-bottom:6px;'><b>Bout {(i//2)+1}:</b> 🔴 {s1_text} 🆚 🔵 {s2_text}</div>", unsafe_allow_html=True)

        with col2:
            st.markdown("#### 🎲 गोला नम्बर प्रविष्टि")
            if saved_draw:
                st.success("✅ यस इभेन्टको टाइसिट डाटाबेसमा सुरक्षित भइसकेको छ! सीधै 'म्याच सञ्चालन' ट्याबमा जानुहोस्।")
                if st.button("⚠️ टाइसिट रिसेट गर्नुहोस् (Delete Bracket)", type="secondary"):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM ma_brackets WHERE event_code=%s", (evt_code,))
                    conn.commit()
                    c.close()
                    conn.close()
                    keys_to_del = [k for k in st.session_state.keys() if f"_{evt_code}_" in k]
                    for k in keys_to_del: del st.session_state[k]
                    st.rerun()
            else:
                with st.form(f"manual_draw_form_{evt_code}"):
                    st.caption("खेलाडीले तानेको गोला नम्बर हाल्नुहोस्:")
                    draw_data = {}
                    cols = st.columns(2)
                    for idx, player in enumerate(registered_players):
                        clean_p = player.split(' [ID:')[0]
                        with cols[idx % 2]:
                            draw_data[player] = st.number_input(f"{clean_p} को स्लट नं:", min_value=1, max_value=next_power_of_2, step=1, key=f"slot_{evt_code}_{idx}")                    
                    if st.form_submit_button("💾 टाइसिट डाटाबेसमा सेभ गर्नुहोस्", type="primary", use_container_width=True):
                        chosen_slots = list(draw_data.values())
                        if len(chosen_slots) != len(set(chosen_slots)):
                            st.error("❌ एउटै स्लट नम्बर दुई जनालाई दिन मिल्दैन!")
                        elif set(chosen_slots).intersection(set(bye_slots)):
                            st.error("❌ तपाईंले 'BYE' तोकिएको स्लट नम्बर छान्नुभयो!")
                        else:
                            save_bracket(evt_code, draw_data, bye_slots)
                            st.success("🎉 टाइसिट डाटाबेसमा सुरक्षित भयो!")
                            st.rerun()

    # ---------------------------------------------------------
    # ⚔️ TAB 2: म्याच सञ्चालन (Bouts)
    # ---------------------------------------------------------
    with tab_bouts:
        if saved_draw:
            if 'active_bout_data' not in st.session_state: 
                st.session_state.active_bout_data = None

            col_list, col_panel = st.columns([1.3, 1])

            # 👈 COLUMN 1: म्याच सूची
            with col_list:
                for r, r_data in bouts_data.items():
                    r_name = r_data['name']
                    bouts = r_data['bouts']
                    
                    completed_count = sum(1 for b in bouts if st.session_state.get(f"published_{evt_code}_{b['id']}", False))
                    all_completed = (completed_count == len(bouts))
                    is_upcoming = any(b['p1'] == "TBD" or b['p2'] == "TBD" for b in bouts)

                    if all_completed: ui_container = st.expander(f"✅ {r_name} (सम्पन्न)", expanded=False)
                    elif is_upcoming and completed_count == 0: ui_container = st.expander(f"⏳ {r_name} (आगामी)", expanded=False)
                    else: ui_container = st.container() 
                    
                    with ui_container:
                        if not all_completed and not is_upcoming:
                            st.markdown(f"<h3 style='color:#1E88E5; margin:0;'>🟢 {r_name}</h3>", unsafe_allow_html=True)
                            
                            # 🖨️ Score Sheet PDF (PostgreSQL Ready)
                            clean_bouts_for_pdf = []
                            for b in bouts:
                                clean_bouts_for_pdf.append({
                                    'id': b['id'],
                                    'p1': re.sub(r" \[M_ID: \d+\]", "", b['p1']),
                                    'p2': re.sub(r" \[M_ID: \d+\]", "", b['p2'])
                                })
                            score_pdf = pg.generate_judge_score_sheet(current_event['name'], r_name, clean_bouts_for_pdf, current_event['name'], CONFIG)
                            st.download_button(
                                label=f"🖨️ Print Judge Score Sheet ({r_name})",
                                data=score_pdf,
                                file_name=f"JudgeScoreSheet_{evt_code}_R{r}.pdf",
                                mime="application/pdf"
                            )
                            st.markdown("<hr style='margin: 5px 0 15px 0;'/>", unsafe_allow_html=True)

                        for b in bouts:
                            bout_id, p1, p2 = b['id'], b['p1'], b['p2']
                            full_bout_str = f"🔴 {p1.split(' [ID:')[0]} 🆚 🔵 {p2.split(' [ID:')[0]}"
                            
                            is_completed = st.session_state.get(f"published_{evt_code}_{bout_id}", False)
                            is_active = (st.session_state.active_bout_data and st.session_state.active_bout_data['id'] == bout_id)
                            has_tbd = "TBD" in [p1, p2]

                            bg_color = "#f8f9fa" if not is_completed else "#f1f5f9"
                            border_color = "#1E88E5" if is_active else ("#22c55e" if is_completed else "#cbd5e1")
                            opacity_style = "opacity: 0.6;" if is_completed else "opacity: 1;"

                            st.markdown(f"<div style='background-color:{bg_color}; {opacity_style} padding:10px; border-left:5px solid {border_color}; border-radius:5px; margin-bottom:10px;'>", unsafe_allow_html=True)
                            c_info, c_call, c_cast = st.columns([2.5, 1, 1.2])
                            
                            with c_info:
                                if is_completed:
                                    winner_name = st.session_state.get(f"winner_{evt_code}_{bout_id}", "").split(' [ID:')[0]
                                    st.markdown(f"<h5 style='color:#64748b; margin:0;'>{bout_id}: {full_bout_str}</h5>", unsafe_allow_html=True)
                                    st.markdown(f"<span style='color:#22c55e; font-size:13px; font-weight:bold;'>🏆 Winner: {winner_name}</span>", unsafe_allow_html=True)
                                else:
                                    st.markdown(f"<h5 style='color:black; margin:0;'>{bout_id}: {full_bout_str}</h5>", unsafe_allow_html=True)
                                    if "BYE" in full_bout_str: st.caption("⚠️ अटो-पास (BYE)")
                            
                            with c_call:
                                if st.button("📢 Call", key=f"call_{evt_code}_{bout_id}", disabled=is_completed or has_tbd or "BYE" in full_bout_str, use_container_width=True):
                                    import utils.live_state as ls
                                    ls.trigger_call(f"{current_event['name']} {current_event.get('gender', '')}", r_name, "PLAYERS TO MAT", "#d32f2f")
                                    st.toast("खेलाडीलाई बोलाइयो!")
                            
                            with c_cast:
                                btn_label, btn_type = ("🔴 LIVE", "primary") if is_active else ("📡 Broadcast", "secondary")
                                if st.button(btn_label, key=f"cast_{evt_code}_{bout_id}", disabled=is_completed or has_tbd or "BYE" in full_bout_str, type=btn_type, use_container_width=True):
                                    st.session_state.active_bout_data = b
                                    st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)

            # 👉 COLUMN 2: जज प्यानल 
            with col_panel:
                st.markdown("<div style='background-color:#ffffff; padding:20px; border-radius:10px; border:2px solid #cbd5e1; height:100%; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
                
                final_completed = False
                final_bout = None
                if total_rounds in bouts_data and len(bouts_data[total_rounds]['bouts']) > 0:
                    final_bout = bouts_data[total_rounds]['bouts'][0]
                    final_completed = st.session_state.get(f"published_{evt_code}_{final_bout['id']}", False)

                if st.session_state.active_bout_data:
                    st.markdown("<h3 style='text-align:center; color:#1e3a8a; margin-top:0; border-bottom:2px solid #cbd5e1; padding-bottom:10px;'>🧑‍⚖️ म्यानुअल भोटिङ प्यानल</h3>", unsafe_allow_html=True)
                    
                    act_data = st.session_state.active_bout_data
                    bout_id, p1, p2 = act_data['id'], act_data['p1'], act_data['p2']
                    
                    st.markdown(f"<h4 style='color:#d32f2f; text-align:center;'>⚡ लाइभ: {bout_id}</h4>", unsafe_allow_html=True)
                    st.markdown(f"<p style='text-align:center; font-size:18px; font-weight:bold;'>🔴 {p1.split(' [ID:')[0]} <br>VS<br> 🔵 {p2.split(' [ID:')[0]}</p>", unsafe_allow_html=True)

                    voting_state_key = f"voting_open_{evt_code}_{bout_id}"
                    is_voting_open = st.session_state.get(voting_state_key, False)
                                        
                    if not is_voting_open:
                        st.info("⏳ खेलाडी प्रदर्शन गर्दैछन्... प्रदर्शन सकिएपछि भोटिङ खुल्ला गर्नुहोस्।")
                        if st.button("🚦 भोटिङ खुल्ला गर्नुहोस् (Start Voting)", type="primary", use_container_width=True):
                            st.session_state[voting_state_key] = True
                            st.rerun()
                    else:
                        st.success("🟢 भोटिङ खुल्ला छ।")
                        aka_votes, ao_votes = 0, 0
                        
                        for j in range(1, 6):
                            c0, c_aka, c_ao = st.columns([1, 2, 2])
                            with c0: st.markdown(f"**जज {j}**")
                            vote_key = f"vote_{evt_code}_{bout_id}_j{j}"
                            if vote_key not in st.session_state: st.session_state[vote_key] = None
                            
                            is_aka = st.session_state[vote_key] == 'Aka'
                            is_ao = st.session_state[vote_key] == 'Ao'
                            if is_aka: aka_votes += 1
                            if is_ao: ao_votes += 1

                            with c_aka:
                                if st.button("✅ 🔴 AKA" if is_aka else "🔴 AKA", key=f"btn_aka_{vote_key}", use_container_width=True):
                                    st.session_state[vote_key] = 'Aka'; st.rerun()
                            with c_ao:
                                if st.button("✅ 🔵 AO" if is_ao else "🔵 AO", key=f"btn_ao_{vote_key}", use_container_width=True):
                                    st.session_state[vote_key] = 'Ao'; st.rerun()

                        st.markdown(f"<h2 style='text-align:center; background:#f8fafc; padding:10px; border-radius:10px; margin-top:20px;'>📊 🔴 {aka_votes} - 🔵 {ao_votes}</h2>", unsafe_allow_html=True)
                        
                        if (aka_votes + ao_votes) == 5:
                            st.warning("⚠️ ५ वटै भोट प्राप्त भयो। कृपया नतिजा पक्का गर्नुहोस्:")
                            winner = "AKA" if aka_votes > ao_votes else "AO"
                            winning_player = p1 if winner == "AKA" else p2
                            votes_list = [st.session_state.get(f"vote_{evt_code}_{bout_id}_j{j}") for j in range(1, 6)]
                            
                            c_conf, c_reset = st.columns(2)
                            with c_conf:
                                if st.button("✅ पक्का (Confirm)", type="primary", use_container_width=True):
                                    import utils.live_state as ls
                                    ls.trigger_kata_result(current_event['name'], bout_id, p1.split(' [ID:')[0], p2.split(' [ID:')[0], votes_list, winner)
                                    
                                    st.session_state[f"winner_{evt_code}_{bout_id}"] = winning_player
                                    st.session_state[f"published_{evt_code}_{bout_id}"] = True
                                    st.session_state.active_bout_data = None 
                                    st.session_state[voting_state_key] = False 
                                    sync_progress_to_db(evt_code)
                                    st.toast("नतिजा सुरक्षित भयो!"); st.rerun()
                            with c_reset:
                                if st.button("🔄 सच्याउनुहोस्", type="secondary", use_container_width=True):
                                    for j in range(1, 6): st.session_state[f"vote_{evt_code}_{bout_id}_j{j}"] = None
                                    st.rerun()

                elif final_completed and final_bout:
                    st.markdown("<h3 style='text-align:center; color:#b45309; border-bottom:2px solid #fcd34d; padding-bottom:10px;'>🏆 अन्तिम नतिजा (Podium)</h3>", unsafe_allow_html=True)
                    
                    gold_player = st.session_state.get(f"winner_{evt_code}_{final_bout['id']}")
                    silver_player = final_bout['p2'] if gold_player == final_bout['p1'] else final_bout['p1']
                    
                    bronze_players = []
                    semi_finals = bouts_data.get(total_rounds - 1, {'bouts': []})['bouts']
                    for sf in semi_finals:
                        sf_winner = st.session_state.get(f"winner_{evt_code}_{sf['id']}")
                        sf_loser = sf['p2'] if sf_winner == sf['p1'] else sf['p1']
                        if sf_loser and sf_loser not in ["TBD", "BYE"]: bronze_players.append(sf_loser)
                    
                    bronze_text = " / ".join([b.split(' [ID:')[0] for b in bronze_players]) if bronze_players else "N/A"

                    podium_flag = f"podium_published_{evt_code}"
                    if not st.session_state.get(podium_flag, False):
                        def parse_player(p_str):
                            if not p_str or p_str in ["TBD", "BYE"]: return None
                            m = re.search(r"^(.*?)\s*\((.*?)\)", p_str)
                            return {"name": m.group(1).strip(), "municipality": m.group(2).strip(), "score": "Kata"} if m else {"name": p_str.split(" [ID:")[0], "municipality": "", "score": "Kata"}

                        b_data = {"name": bronze_text[:30] + "...", "municipality": "Joint Third", "score": "Kata"} if bronze_players else None
                        import utils.live_state as ls
                        ls.trigger_podium(f"{current_event['name']} {current_event.get('gender', '')}", parse_player(gold_player), parse_player(silver_player), b_data)
                        st.session_state[podium_flag] = True 
                        st.toast("📺 पोडियम अटोमेटिक पठाइयो।")

                    st.markdown(f"""
                        <div style="background: linear-gradient(145deg, #FFF8DC, #FFD700); padding:15px; border-radius:10px; text-align:center; margin-bottom:15px; border:2px solid #D4AF37;">
                            <h1>🥇</h1><h4 style="color:#8B6508; margin:0;">GOLD</h4><h3 style="color:black; margin:0;">{gold_player.split(' [ID:')[0]}</h3>
                        </div>
                        <div style="background: linear-gradient(145deg, #F8F9FA, #E2E8F0); padding:15px; border-radius:10px; text-align:center; margin-bottom:15px; border:2px solid #CBD5E1;">
                            <h1>🥈</h1><h4 style="color:#475569; margin:0;">SILVER</h4><h3 style="color:black; margin:0;">{silver_player.split(' [ID:')[0]}</h3>
                        </div>
                        <div style="background: linear-gradient(145deg, #FFF5EE, #CD7F32); padding:15px; border-radius:10px; text-align:center; border:2px solid #A0522D;">
                            <h1>🥉 🥉</h1><h4 style="color:#8B4513; margin:0;">BRONZE</h4><h4 style="color:black; margin:0;">{bronze_text}</h4>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.info("👈 देब्रे पट्टीबाट कुनै म्याचलाई 'Broadcast' गर्नुहोस्।")
                    st.markdown("<div style='text-align:center; padding:30px 0; color:#94a3b8;'>यहाँ भोटिङ प्यानल खुल्नेछ।</div>", unsafe_allow_html=True)
                
                st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 🏆 TAB 3: अन्तिम नतिजा र डाटाबेस सेभ
    # ---------------------------------------------------------
    with tab_results:
        st.markdown("### 🎉 प्रतियोगिताको अन्तिम नतिजा")
        if saved_draw and 'bouts_data' in locals():
            final_bout = bouts_data[total_rounds]['bouts'][0]
            if st.session_state.get(f"published_{evt_code}_{final_bout['id']}", False):
                gold_player = st.session_state.get(f"winner_{evt_code}_{final_bout['id']}")
                silver_player = final_bout['p2'] if gold_player == final_bout['p1'] else final_bout['p1']
                bronze_players = [st.session_state.get(f"winner_{evt_code}_{sf['id']}") for sf in bouts_data.get(total_rounds - 1, {'bouts': []})['bouts']]
                bronze_players = [sf['p2'] if w == sf['p1'] else sf['p1'] for sf, w in zip(bouts_data.get(total_rounds - 1, {'bouts': []})['bouts'], bronze_players)]
                bronze_players = [b for b in bronze_players if b and b not in ["TBD", "BYE"]]

                c_g, c_s, c_b = st.columns(3)
                c_g.markdown(f"<div style='text-align:center; background:#FFF8DC; padding:15px; border-radius:10px;'><h1>🥇</h1><h3>{gold_player.split(' [ID:')[0]}</h3></div>", unsafe_allow_html=True)
                c_s.markdown(f"<div style='text-align:center; background:#F8F9FA; padding:15px; border-radius:10px;'><h1>🥈</h1><h3>{silver_player.split(' [ID:')[0]}</h3></div>", unsafe_allow_html=True)
                c_b.markdown(f"<div style='text-align:center; background:#FFF5EE; padding:15px; border-radius:10px;'><h1>🥉</h1><h3>{' / '.join([b.split(' [ID:')[0] for b in bronze_players])}</h3></div>", unsafe_allow_html=True)

                st.divider()
                if st.button("💾 पदक विवरण डाटाबेसमा सेभ गर्नुहोस्", type="primary"):
                    # 💡 Extract Both Player ID and Muni ID
                    def ext_ids(s_val):
                        if not s_val: return None, None
                        p_match = re.search(r"\[ID:\s*(\d+)\]", s_val)
                        m_match = re.search(r"\[M_ID:\s*(\d+)\]", s_val)
                        p_id = int(p_match.group(1)) if p_match else None
                        m_id = int(m_match.group(1)) if m_match else None
                        return p_id, m_id
                    
                    g_pid, g_mid = ext_ids(gold_player)
                    s_pid, s_mid = ext_ids(silver_player)
                    b_list = [ext_ids(b) for b in bronze_players]
                    
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM results WHERE event_code=%s", (evt_code,))
                    
                    if g_pid and g_mid: c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal) VALUES (%s, %s, %s, 1, 'Gold')", (evt_code, g_mid, g_pid))
                    if s_pid and s_mid: c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal) VALUES (%s, %s, %s, 2, 'Silver')", (evt_code, s_mid, s_pid))
                    for b_pid, b_mid in b_list:
                        if b_pid and b_mid: c.execute("INSERT INTO results (event_code, municipality_id, player_id, position, medal) VALUES (%s, %s, %s, 3, 'Bronze')", (evt_code, b_mid, b_pid))
                    
                    conn.commit()
                    c.close()
                    conn.close()
                    
                    st.success("✅ पदक सुरक्षित भयो! मेडल ट्याली अपडेट हुनेछ।"); st.balloons()
            else:
                st.info("⏳ प्रतियोगिता सम्पन्न भएको छैन।")