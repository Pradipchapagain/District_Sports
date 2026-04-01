import streamlit as st
import pandas as pd
import math
import json
import database as db
import re
import utils.bracket_generator as bg  
import utils.pdf_generator as pg      
from config import CONFIG             

def setup_bracket_table():
    """क्लाउडमा ma_brackets टेबल तयार छ कि छैन चेक गर्छ।"""
    conn = db.get_connection()
    c = conn.cursor()
    # नयाँ डेटाबेस लजिकमा JSONB प्रयोग गरिएको छ
    c.execute('''
        CREATE TABLE IF NOT EXISTS ma_brackets (
            event_code VARCHAR(50) PRIMARY KEY REFERENCES events(code) ON DELETE CASCADE, 
            draw_json JSONB, 
            byes_json JSONB, 
            progress_json JSONB
        )
    ''')
    conn.commit()
    c.close()
    conn.close()

def save_bracket(evt_code, draw_data, byes):
    """टाइसिट र ड्र लाई क्लाउडमा सेभ गर्छ (PostgreSQL UPSERT)"""
    conn = db.get_connection()
    c = conn.cursor()
    
    # पहिले पुरानो प्रोग्रेस छ कि हेर्ने
    c.execute("SELECT progress_json FROM ma_brackets WHERE event_code=%s", (evt_code,))
    row = c.fetchone()
    prog = row[0] if row and row[0] else {}
    
    # 💡 PostgreSQL: JSON डाटालाई json.dumps गरेर पठाउनुपर्छ
    c.execute("""
        INSERT INTO ma_brackets (event_code, draw_json, byes_json, progress_json) 
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (event_code) DO UPDATE 
        SET draw_json = EXCLUDED.draw_json, byes_json = EXCLUDED.byes_json
    """, (evt_code, json.dumps(draw_data), json.dumps(byes), json.dumps(prog)))
    
    conn.commit()
    c.close()
    conn.close()

def load_bracket(evt_code):
    """क्लाउडबाट टाइसिट तान्ने"""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT draw_json, byes_json FROM ma_brackets WHERE event_code=%s", (evt_code,))
    row = c.fetchone()
    c.close()
    conn.close()
    
    if row:
        # JSONB बाट सिधै डिक्शनरी आउँछ, तर कहिलेकाहीँ string हुन सक्छ
        d_json = row[0] if isinstance(row[0], dict) else (json.loads(row[0]) if row[0] else None)
        b_json = row[1] if isinstance(row[1], list) else (json.loads(row[1]) if row[1] else None)
        return d_json, b_json
    return None, None

def load_progress_from_db(evt_code):
    """म्याचको अवस्था (Live State) क्लाउडबाट तानेर Session State मा राख्ने"""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT progress_json FROM ma_brackets WHERE event_code=%s", (evt_code,))
    row = c.fetchone()
    c.close()
    conn.close()
    
    if row and row[0]:
        prog = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        for k, v in prog.items():
            if k not in st.session_state: 
                st.session_state[k] = v

def sync_progress_to_db(evt_code):
    """म्याचको नतिजा वा भोटिङलाई क्लाउडमा पठाउने (Background Sync)"""
    prog = {k: st.session_state[k] for k in st.session_state.keys() 
            if f"_{evt_code}_" in k and (k.startswith("winner_") or k.startswith("published_") or k.startswith("votes_") or k.startswith("scores_"))}
    
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("UPDATE ma_brackets SET progress_json=%s WHERE event_code=%s", (json.dumps(prog), evt_code))
    conn.commit()
    c.close()
    conn.close()

def get_standard_byes(total_slots, num_byes):
    """मार्शल आर्ट्सको नियम अनुसार 'Bye' पाउने स्लटहरू निकाल्छ"""
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

def run_tournament(evt_code, current_event, players_df, scoring_panel_func):
    """टाइसिट बनाउने र म्याच खेलाउने मुख्य फङ्सन"""
    setup_bracket_table()
    load_progress_from_db(evt_code)
    
    # डाटा क्लिनिङ र डिस्प्ले नाम बनाउने
    p_names = players_df.get('name', players_df.get('Player_Name', 'Unknown'))
    m_names = players_df.get('school_name', players_df.get('Municipality', ''))
    mun_ids = players_df.get('municipality_id', players_df.get('mun_id', '0'))
    
    players_df['Display_Name'] = p_names + " (" + m_names + ") [ID: " + players_df['id'].astype(str) + "] [M_ID: " + mun_ids.astype(str) + "]"
    registered_players = players_df['Display_Name'].tolist()
    
    num_players = len(registered_players)
    if num_players < 2:
        st.warning("⚠️ यो खेल सुरु गर्न कम्तिमा २ जना खेलाडी दर्ता हुनुपर्छ।")
        return

    # म्याथ लजिक: अर्को पावर अफ २ निकाल्ने
    next_power_of_2 = 2**(math.ceil(math.log(num_players, 2)))
    num_byes = next_power_of_2 - num_players
    
    saved_draw, saved_byes = load_bracket(evt_code)
    bye_slots = saved_byes if saved_byes is not None else get_standard_byes(next_power_of_2, num_byes)

    tab_draw, tab_bouts, tab_results = st.tabs(["📊 १. गोला र टाइसिट (Draw)", "⚔️ २. म्याच सञ्चालन (Bouts)", "🏆 ३. नतिजा (Podium)"])

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
                
                # BYE को लजिक: यदि कोही 'BYE' सँग खेल्दैछ भने ऊ अटोमेटिक जित्छ
                if ("BYE" in [p1, p2]) and ("TBD" not in [p1, p2]):
                    adv_p = p1 if p2 == "BYE" else p2
                    if adv_p != "BYE":
                        st.session_state[f"winner_{evt_code}_{bout_id}"] = adv_p
                        st.session_state[f"published_{evt_code}_{bout_id}"] = True
                        sync_progress_to_db(evt_code)
                        
                bouts_data[r]['bouts'].append({'id': bout_id, 'p1': p1, 'p2': p2, 'r_name': r_name})
                
                def clean_name_for_pdf(n):
                    if not isinstance(n, str) or n in ["BYE", "TBD"]: return n
                    return re.sub(r" \[M_ID: \d+\]", "", n)
                    
                all_matches_for_pdf.append({
                    'id': bout_counter, 'round': r, 'p1': clean_name_for_pdf(p1), 'p2': clean_name_for_pdf(p2),
                    'winner': clean_name_for_pdf(st.session_state.get(f"winner_{evt_code}_{bout_id}")),
                    'title': "🏆 FINAL" if r == total_rounds else ("Semi-Final" if r == total_rounds - 1 else f"Match {bout_counter}"),
                    'is_third_place': False, 'source_m1': src1, 'source_m2': src2
                })
                bout_counter += 1

    # ==========================
    # TAB 1: DRAW (टाइसिट)
    # ==========================
    with tab_draw:
        st.info(f"👥 कुल खेलाडी: {num_players} | 🎯 टाइसिट स्लट: {next_power_of_2} | 🛑 Bye: {num_byes}")
        
        if saved_draw and all_matches_for_pdf:
            tree_pdf = bg.generate_tree_pdf(current_event['name'], current_event.get('gender',''), current_event.get('category',''), all_matches_for_pdf)
            st.download_button("🖨️ Print Visual Bracket Tree (PDF)", data=tree_pdf, file_name=f"Bracket_{evt_code}.pdf", mime="application/pdf", type="primary")
            st.markdown("<hr/>", unsafe_allow_html=True)
            
        c1, c2 = st.columns([1, 1.5])
        with c1:
            st.markdown("#### 📋 ब्ल्याङ्क टाइसिट")
            for i in range(1, next_power_of_2, 2):
                s1 = f"Slot {i}" + (" (BYE)" if i in bye_slots else "")
                s2 = f"Slot {i+1}" + (" (BYE)" if i+1 in bye_slots else "")
                st.markdown(f"<div style='background:#f8fafc; padding:8px; border:1px solid #cbd5e1; border-radius:6px; margin-bottom:6px;'><b>Bout {(i//2)+1}:</b> 🔴 {s1} 🆚 🔵 {s2}</div>", unsafe_allow_html=True)
        
        with c2:
            st.markdown("#### 🎲 गोला नम्बर प्रविष्टि")
            if saved_draw:
                st.success("✅ टाइसिट सुरक्षित भइसकेको छ! अब 'म्याच सञ्चालन' ट्याबमा जानुहोस्।")
                if st.button("⚠️ टाइसिट रिसेट गर्नुहोस्", type="secondary"):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM ma_brackets WHERE event_code=%s", (evt_code,))
                    # पुराना नतिजाहरू पनि हटाउने
                    c.execute("DELETE FROM results WHERE event_code=%s", (evt_code,))
                    conn.commit(); c.close(); conn.close()
                    
                    keys_to_del = [k for k in st.session_state.keys() if f"_{evt_code}_" in k]
                    for k in keys_to_del: del st.session_state[k]
                    st.rerun()
            else:
                # 💡 दर्ता लक छ कि छैन चेक गर्ने
                is_locked = current_event.get('is_locked', 0)
                if not is_locked:
                    st.warning("⚠️ कृपया टाइसिट निकाल्नु अघि 'Event Settings' बाट दर्ता (Registration) बन्द (Lock) गर्नुहोस्!")
                else:
                    with st.form(f"draw_form_{evt_code}"):
                        draw_data = {}
                        cols = st.columns(2)
                        for idx, player in enumerate(registered_players):
                            clean_p = player.split(' [ID:')[0]
                            with cols[idx % 2]: 
                                draw_data[player] = st.number_input(f"{clean_p} को स्लट नं:", min_value=1, max_value=next_power_of_2, step=1)
                        
                        if st.form_submit_button("💾 टाइसिट सेभ गर्नुहोस्", type="primary"):
                            if len(list(draw_data.values())) != len(set(draw_data.values())): 
                                st.error("❌ एउटै स्लट नम्बर दुई जनालाई दिन मिल्दैन!")
                            elif set(draw_data.values()).intersection(set(bye_slots)): 
                                st.error("❌ तपाईंले 'BYE' तोकिएको स्लट छान्नुभयो!")
                            else: 
                                save_bracket(evt_code, draw_data, bye_slots)
                                st.rerun()

    # ==========================
    # TAB 2: BOUTS (म्याच सञ्चालन)
    # ==========================
    with tab_bouts:
        if saved_draw:
            if 'active_bout_data' not in st.session_state: 
                st.session_state.active_bout_data = None
                
            if st.session_state.active_bout_data:
                # 🥊 म्याच भइरहेको अवस्था (Scoring Panel)
                st.markdown("<div style='background:#fff; padding:20px; border-radius:10px; border:2px solid #cbd5e1; box-shadow: 0 10px 20px rgba(0,0,0,0.1);'>", unsafe_allow_html=True)
                
                col1, col2 = st.columns([1, 4])
                with col1:
                    if st.button("⬅️ Back"): 
                        st.session_state.active_bout_data = None
                        st.rerun()
                
                # यहाँ तपाईंको पुरानो scoring_panel_func कल हुन्छ
                scoring_panel_func(evt_code, current_event, players_df, st.session_state.active_bout_data)
                
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # 📋 म्याचहरूको सूची (List View)
                for r, r_data in bouts_data.items():
                    with st.expander(f"📌 {r_data['name']}", expanded=(r==1)):
                        for b in r_data['bouts']:
                            is_comp = st.session_state.get(f"published_{evt_code}_{b['id']}", False)
                            status = "✅ Completed" if is_comp else "⏳ Pending"
                            
                            st.markdown(f"**{b['id']}:** {b['p1']} 🆚 {b['p2']} | *{status}*")
                            
                            if not is_comp and "TBD" not in [b['p1'], b['p2']] and "BYE" not in [b['p1'], b['p2']]:
                                if st.button(f"▶️ Play {b['id']}", key=f"btn_{b['id']}"):
                                    st.session_state.active_bout_data = b
                                    st.rerun()
                            st.markdown("---")

    # ==========================
    # TAB 3: RESULTS (नतिजा र पदक)
    # ==========================
    with tab_results:
        if saved_draw and total_rounds in bouts_data:
            final_bout = bouts_data[total_rounds]['bouts'][0]
            
            # यदि फाइनल सकिएको छ भने
            if st.session_state.get(f"published_{evt_code}_{final_bout['id']}", False):
                g = st.session_state.get(f"winner_{evt_code}_{final_bout['id']}")
                s = final_bout['p2'] if g == final_bout['p1'] else final_bout['p1']
                
                # दुवै सेमिफाइनलिस्टलाई ब्रोन्ज (मार्शल आर्ट्सको नियम)
                b_list = [sf['p2'] if st.session_state.get(f"winner_{evt_code}_{sf['id']}") == sf['p1'] else sf['p1'] for sf in bouts_data.get(total_rounds - 1, {'bouts': []})['bouts']]
                b_list = [b for b in b_list if b and b not in ["TBD", "BYE"]]

                st.success(f"🥇 Gold: {g.split(' [ID:')[0]}")
                st.info(f"🥈 Silver: {s.split(' [ID:')[0]}")
                for b in b_list:
                    st.warning(f"🥉 Bronze: {b.split(' [ID:')[0]}")

                if st.button("💾 Finalize Medal Podium on Cloud", type="primary", width="stretch"):
                    def ext_ids(s_val):
                        if not s_val: return None, None
                        p_match = re.search(r"\[ID:\s*(\d+)\]", s_val)
                        m_match = re.search(r"\[M_ID:\s*(\d+)\]", s_val)
                        return (int(p_match.group(1)) if p_match else None), (int(m_match.group(1)) if m_match else None)
                    
                    conn = db.get_connection()
                    c = conn.cursor()
                    
                    # पुरानो नतिजा हटाउने
                    c.execute("DELETE FROM results WHERE event_code=%s", (evt_code,))
                    
                    # नयाँ नतिजा सेभ गर्ने
                    for p_str, pos, medal in [(g, 1, 'Gold'), (s, 2, 'Silver')] + [(b, 3, 'Bronze') for b in b_list]:
                        pid, mid = ext_ids(p_str)
                        if pid and mid:
                            c.execute("""
                                INSERT INTO results (event_code, municipality_id, player_id, position, medal, score_details) 
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (evt_code, mid, pid, pos, medal, json.dumps({"status": "Finalized"})))
                    
                    # 💡 अडिटरको लागि लग राख्ने (Audit Trail)
                    if 'user_id' in st.session_state:
                        c.execute("INSERT INTO audit_logs (user_id, action, table_name) VALUES (%s, %s, %s)",
                                  (st.session_state.user_id, f"Finalized Result for {evt_code}", "results"))

                    conn.commit()
                    c.close(); conn.close()
                    st.success("✅ Medal tally successfully saved to Neon Cloud!")
                    st.balloons()
            else:
                st.info("⚠️ नतिजा प्रकाशित गर्न कृपया फाइनल म्याच सम्पन्न गर्नुहोस्।")