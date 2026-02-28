import streamlit as st
import pandas as pd
import math
import random
import database as db
import json
from config import render_header, render_footer

# ==========================================
# ⚙️ PAGE CONFIG & INITIALIZATION
# ==========================================
st.set_page_config(page_title="Team Games Control", page_icon="🏆", layout="wide")

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.switch_page("Home.py")

render_header()

st.title("🏆 टिम गेम सञ्चालन (Team Games Management)")
st.markdown("यहाँबाट भलिबल, कबड्डी जस्ता टिम गेमहरूको टाइसिट निर्माण र म्याच सञ्चालन गर्न सकिन्छ।")
st.divider()

# ==========================================
# 🏀 1. EVENT SELECTION 
# ==========================================
events_df = db.get_events()
team_events = events_df[events_df['category'] == "Team Game"].copy() 

if team_events.empty:
    st.error("⚠️ कुनै पनि 'Team Game' फेला परेन। कृपया इभेन्ट सेटिङ्समा गएर नयाँ इभेन्ट थप्नुहोस्।")
    st.stop()

team_events['display_name'] = team_events['name'] + " (" + team_events['gender'] + ")"

col_sel1, col_sel2 = st.columns([2, 1])
with col_sel1:
    selected_display = st.selectbox("खेल छान्नुहोस् (Select Team Game):", team_events['display_name'].tolist())

current_event = team_events[team_events['display_name'] == selected_display].iloc[0]
evt_code = current_event['code']
evt_name = current_event['name']
sel_gender = current_event['gender']
sub_category = current_event['sub_category']

with col_sel2:
    st.info(f"**Game Mode:** {sub_category}\n\n**Gender:** {sel_gender}")

conn = db.get_connection()
# 💡 PostgreSQL Syntax
saved_matches_df = pd.read_sql_query("SELECT * FROM matches WHERE event_code=%s ORDER BY match_no", conn, params=(evt_code,))
conn.close()

saved_matches = saved_matches_df.to_dict('records') if not saved_matches_df.empty else []

# ==========================================
# 🛠️ HELPER FUNCTIONS (Bracket Logic)
# ==========================================
def generate_team_bracket(bracket_df, seeded_teams, event_code):
    teams = bracket_df['name'].tolist()
    # 💡 Municipality ID पनि म्याप गर्ने (For Results)
    team_data_map = {row['name']: {'team_id': row['id'], 'muni_id': row['municipality_id']} for _, row in bracket_df.iterrows()}
    
    non_seeded = [t for t in teams if t not in seeded_teams]
    random.shuffle(non_seeded)
    
    final_order = []
    if len(seeded_teams) >= 1: final_order.append(seeded_teams[0])
    final_order.extend(non_seeded)
    if len(seeded_teams) >= 2: final_order.append(seeded_teams[1])
    
    n = len(final_order)
    power_of_2 = 2 ** math.ceil(math.log2(n)) if n > 0 else 0
    byes_needed = power_of_2 - n
    
    for _ in range(byes_needed): final_order.append("BYE")
        
    matches = []
    match_id = 1
    r1_matches = []
    
    for i in range(0, len(final_order), 2):
        p1, p2 = final_order[i], final_order[i+1]
        t1_info = team_data_map.get(p1, {})
        t2_info = team_data_map.get(p2, {})
        
        m = {
            'match_no': match_id, 'event_code': event_code, 'round_name': 'Round 1', 'title': 'Round 1',
            'p1_name': p1, 'team1_id': t1_info.get('team_id'), 'comp1_muni_id': t1_info.get('muni_id'),
            'p2_name': p2, 'team2_id': t2_info.get('team_id'), 'comp2_muni_id': t2_info.get('muni_id'),
            'status': 'Pending', 'is_third_place': False
        }
        matches.append(m)
        r1_matches.append(match_id)
        match_id += 1
        
    current_round_matches = r1_matches
    current_round = 2
    
    while len(current_round_matches) > 1:
        next_round_temp = []
        is_semi_final = (len(current_round_matches) == 2)
        
        if is_semi_final:
            m1_id, m2_id = current_round_matches[0], current_round_matches[1]
            tp_match = {
                'match_no': match_id, 'event_code': event_code, 'round_name': f"Round {current_round}", 'title': '🥉 Third Place',
                'p1_name': f"Loser of #{m1_id}", 'team1_id': None, 'comp1_muni_id': None,
                'p2_name': f"Loser of #{m2_id}", 'team2_id': None, 'comp2_muni_id': None,
                'status': 'Pending', 'is_third_place': True, 'source_match1': m1_id, 'source_match2': m2_id
            }
            matches.append(tp_match)
            match_id += 1
            
        for i in range(0, len(current_round_matches), 2):
            m1_id = current_round_matches[i]
            m2_id = current_round_matches[i+1] if (i+1) < len(current_round_matches) else None
            
            p1_ph = f"Winner of #{m1_id}"
            p2_ph = f"Winner of #{m2_id}" if m2_id else "BYE"
            r_title = "Quarter-Final" if len(current_round_matches)==8 else "Semi-Final" if len(current_round_matches)==4 else "🏆 FINAL" if len(current_round_matches)==2 else f"Round {current_round}"
            
            m = {
                'match_no': match_id, 'event_code': event_code, 'round_name': f"Round {current_round}", 'title': r_title,
                'p1_name': p1_ph, 'team1_id': None, 'comp1_muni_id': None, 
                'p2_name': p2_ph, 'team2_id': None, 'comp2_muni_id': None,
                'status': 'Pending', 'is_third_place': False, 'source_match1': m1_id, 'source_match2': m2_id
            }
            matches.append(m)
            next_round_temp.append(match_id)
            match_id += 1

        current_round_matches = next_round_temp
        current_round += 1

    conn = db.get_connection()
    c = conn.cursor()
    # 💡 PostgreSQL: Clean up existing matches
    c.execute("DELETE FROM matches WHERE event_code=%s", (event_code,))
    
    for m in matches:
        # 💡 PostgreSQL Logic: Strict Schema Insertion
        c.execute("""
            INSERT INTO matches (event_code, match_no, round_name, title, p1_name, team1_id, comp1_muni_id, p2_name, team2_id, comp2_muni_id, status, is_third_place, source_match1, source_match2)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (m['event_code'], m['match_no'], m['round_name'], m['title'], m['p1_name'], m['team1_id'], m['comp1_muni_id'], m['p2_name'], m['team2_id'], m['comp2_muni_id'], m['status'], m['is_third_place'], m.get('source_match1'), m.get('source_match2')))
        
    conn.commit()
    c.close()
    conn.close()

def update_bracket_flow(matches):
    # 💡 This function handles local state updates, then pushes to DB.
    # Uses `match_no` instead of `match_id` for PostgreSQL Schema.
    match_dict = {m['match_no']: m for m in matches}
    updates_needed = False
    
    for m in matches:
        # Winner Flow
        if "Winner of #" in str(m['p1_name']):
            src_id = int(str(m['p1_name']).split("#")[1])
            if match_dict.get(src_id, {}).get('winner_team_id'): # 💡 Check winner_team_id instead of winner_name
                src_m = match_dict[src_id]
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p1_name'] = src_m['p1_name'] if is_p1_winner else src_m['p2_name']
                m['team1_id'] = src_m['team1_id'] if is_p1_winner else src_m['team2_id']
                m['comp1_muni_id'] = src_m['comp1_muni_id'] if is_p1_winner else src_m['comp2_muni_id']
                updates_needed = True

        if "Winner of #" in str(m['p2_name']):
            src_id = int(str(m['p2_name']).split("#")[1])
            if match_dict.get(src_id, {}).get('winner_team_id'):
                src_m = match_dict[src_id]
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p2_name'] = src_m['p1_name'] if is_p1_winner else src_m['p2_name']
                m['team2_id'] = src_m['team1_id'] if is_p1_winner else src_m['team2_id']
                m['comp2_muni_id'] = src_m['comp1_muni_id'] if is_p1_winner else src_m['comp2_muni_id']
                updates_needed = True
                
        # Loser Flow (For 3rd Place)
        if "Loser of #" in str(m['p1_name']):
            src_id = int(str(m['p1_name']).split("#")[1])
            src_m = match_dict.get(src_id)
            if src_m and src_m.get('winner_team_id'):
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p1_name'] = src_m['p2_name'] if is_p1_winner else src_m['p1_name']
                m['team1_id'] = src_m['team2_id'] if is_p1_winner else src_m['team1_id']
                m['comp1_muni_id'] = src_m['comp2_muni_id'] if is_p1_winner else src_m['comp1_muni_id']
                updates_needed = True
                
        if "Loser of #" in str(m['p2_name']):
            src_id = int(str(m['p2_name']).split("#")[1])
            src_m = match_dict.get(src_id)
            if src_m and src_m.get('winner_team_id'):
                is_p1_winner = src_m['winner_team_id'] == src_m['team1_id']
                m['p2_name'] = src_m['p2_name'] if is_p1_winner else src_m['p1_name']
                m['team2_id'] = src_m['team2_id'] if is_p1_winner else src_m['team1_id']
                m['comp2_muni_id'] = src_m['comp2_muni_id'] if is_p1_winner else src_m['comp1_muni_id']
                updates_needed = True
                
        # BYE Auto-Progression
        if m.get('status', 'Pending') != 'Completed':
            if m['p2_name'] == "BYE" and "Winner" not in str(m['p1_name']) and "Loser" not in str(m['p1_name']):
                m['winner_team_id'], m['winner_muni_id'], m['status'] = m['team1_id'], m['comp1_muni_id'], 'Completed'
                updates_needed = True
            elif m['p1_name'] == "BYE" and "Winner" not in str(m['p2_name']) and "Loser" not in str(m['p2_name']):
                m['winner_team_id'], m['winner_muni_id'], m['status'] = m['team2_id'], m['comp2_muni_id'], 'Completed'
                updates_needed = True

    if updates_needed:
        conn = db.get_connection()
        c = conn.cursor()
        for m in matches:
            c.execute("""
                UPDATE matches SET p1_name=%s, team1_id=%s, comp1_muni_id=%s, 
                                   p2_name=%s, team2_id=%s, comp2_muni_id=%s, 
                                   winner_team_id=%s, winner_muni_id=%s, status=%s 
                WHERE match_no=%s AND event_code=%s
            """, (m['p1_name'], m['team1_id'], m['comp1_muni_id'], 
                  m['p2_name'], m['team2_id'], m['comp2_muni_id'], 
                  m.get('winner_team_id'), m.get('winner_muni_id'), m.get('status'), 
                  m['match_no'], evt_code))
        conn.commit()
        c.close()
        conn.close()
    return matches

# ==========================================
# 🗂️ 2. TABS MANAGEMENT
# ==========================================
tab1, tab2, tab3 = st.tabs(["📋 १. टाइ-सिट (Bracket)", "🎮 २. लाइभ म्याच कन्ट्रोल", "🏆 ३. नतिजा (Results)"])

# -----------------------------------------------------------------------
# TAB 1: BRACKET GENERATION & VIEW
# -----------------------------------------------------------------------
with tab1:
    conn = db.get_connection()
    # 💡 Join to get team and municipality ids
    teams_df = pd.read_sql_query("SELECT t.id, t.name, t.municipality_id FROM teams t WHERE t.event_code=%s", conn, params=(evt_code,))
    conn.close()
    
    if teams_df.empty:
        st.warning("⚠️ यो खेलमा कुनै पनि टिम दर्ता भएका छैनन्। कृपया 'Player Registration' बाट टिम दर्ता गर्नुहोस्।")
    else:
        if not saved_matches:
            st.subheader("🔀 नयाँ टाइ-सिट बनाउनुहोस्")
            seeded = st.multiselect("सिडेड टिमहरू छान्नुहोस् (Seeding):", teams_df['name'].tolist())
            if st.button("🎲 टाइ-सिट जेनेरेट गर्नुहोस्", type="primary"):
                generate_team_bracket(teams_df, seeded, evt_code)
                st.success("✅ टाइ-सिट सफलतापूर्वक तयार भयो!"); st.rerun()
        else:
            c_r1, c_r2 = st.columns([1, 4])
            with c_r1:
                if st.button("⚠️ टाइ-सिट रिसेट गर्नुहोस्", type="secondary", width="stretch"):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM matches WHERE event_code=%s", (evt_code,))
                    conn.commit()
                    c.close()
                    conn.close()
                    st.rerun()
            
            with st.expander("🔄 म्याचमा टिम साट्नुहोस् (Exchange Teams)"):
                st.caption("टाइसिट बनिसकेपछि यदि कुनै टिमलाई अर्को म्याचमा सार्नुपरेमा यहाँबाट गर्न सकिन्छ।")
                r1_matches = [m for m in saved_matches if m['title'] == 'Round 1'] # 💡 Replaced round number check
                if r1_matches:
                    ex_c1, ex_c2, ex_c3 = st.columns([2, 2, 1])
                    match_a_id = ex_c1.selectbox("पहिलो म्याच छान्नुहोस्:", [m['match_no'] for m in r1_matches], format_func=lambda x: f"Match {x}")
                    match_b_id = ex_c2.selectbox("दोस्रो म्याच छान्नुहोस्:", [m['match_no'] for m in r1_matches if m['match_no'] != match_a_id], format_func=lambda x: f"Match {x}")
                    if ex_c3.button("🔄 साट्नुहोस् (Swap)", type="primary", use_container_width=True):
                        m_a = next(m for m in saved_matches if m['match_no'] == match_a_id)
                        m_b = next(m for m in saved_matches if m['match_no'] == match_b_id)
                        
                        conn = db.get_connection()
                        c = conn.cursor()
                        c.execute("UPDATE matches SET p2_name=%s, team2_id=%s, comp2_muni_id=%s WHERE match_no=%s AND event_code=%s", 
                                  (m_b['p2_name'], m_b['team2_id'], m_b['comp2_muni_id'], m_a['match_no'], evt_code))
                        c.execute("UPDATE matches SET p2_name=%s, team2_id=%s, comp2_muni_id=%s WHERE match_no=%s AND event_code=%s", 
                                  (m_a['p2_name'], m_a['team2_id'], m_a['comp2_muni_id'], m_b['match_no'], evt_code))
                        conn.commit()
                        c.close()
                        conn.close()
                        st.success("✅ टिम सफलतापूर्वक साटियो!"); st.rerun()

            st.divider()
            matches = update_bracket_flow(saved_matches)

            view_tab1, view_tab2, view_tab3 = st.tabs(["📋 सूची (List View)", "🌳 ट्री मोडेल (Tree View)", "📝 लाइन-अप स्लिप (Forms)"])
            
            with view_tab1:
                st.markdown("### 🏟️ खेल तालिका (Match List)")
                rounds = sorted(list(set(m['title'] for m in matches)), key=lambda x: 1 if 'Round 1' in x else 2 if 'Quarter' in x else 3 if 'Semi' in x else 4 if 'Third' in x else 5)
                cols = st.columns(len(rounds))
                for idx, r_name in enumerate(rounds):
                    with cols[idx]:
                        st.markdown(f"**{r_name}**")
                        r_matches = [m for m in matches if m['title'] == r_name]
                        for m in r_matches:
                            bg_color = "#fef9c3" if 'FINAL' in m['title'] else "#ffedd5" if 'Third' in m['title'] else "#dcfce7" if m.get('status') == 'Completed' else "#f1f5f9"
                            # 💡 Determine winner name for display
                            w_name = m['p1_name'] if m.get('winner_team_id') == m['team1_id'] and m['team1_id'] else (m['p2_name'] if m.get('winner_team_id') else "")
                            
                            st.markdown(f"""
                            <div style="background-color:{bg_color}; border:1px solid #cbd5e1; border-radius:8px; padding:10px; margin-bottom:10px; font-size:14px; box-shadow: 1px 1px 3px rgba(0,0,0,0.1);">
                                <div style="color:#64748b; font-size:11px;">Match #{m['match_no']}</div>
                                <div>🔵 {m['p1_name']}</div>
                                <div style="color:#94a3b8; font-size:10px; text-align:center;">VS</div>
                                <div>🔴 {m['p2_name']}</div>
                                <div style="color:#166534; font-size:12px; font-weight:bold; margin-top:5px;">{f"🏆 {w_name}" if w_name else ""}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
            with view_tab2:
                st.markdown("### 🌳 टाइसिटको प्रत्यक्ष रूप (Live Bracket Tree)")
                try:
                    from utils.bracket_generator import generate_tree_pdf
                    import base64 
                    
                    mapped_for_pdf = []
                    for m in matches:
                        w_name = m['p1_name'] if m.get('winner_team_id') == m['team1_id'] and m['team1_id'] else (m['p2_name'] if m.get('winner_team_id') else None)
                        mapped_for_pdf.append({
                            'id': m['match_no'], 'round': m['round_name'], 'title': m['title'],
                            'p1': m['p1_name'], 'p2': m['p2_name'], 
                            'winner': w_name, 'is_third_place': m.get('is_third_place'),
                            'source_m1': m.get('source_match1'), 'source_m2': m.get('source_match2')
                        })
                        
                    pdf_buffer = generate_tree_pdf(evt_name, sel_gender, sub_category, mapped_for_pdf)
                    base64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
                    pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="600" type="application/pdf" style="border: 2px solid #cbd5e1; border-radius: 10px;"></iframe>'
                    st.markdown(pdf_display, unsafe_allow_html=True)
                    st.download_button("📥 यो टाइसिट (PDF) डाउनलोड गर्नुहोस्", data=pdf_buffer, file_name=f"{evt_code}_Tree_Bracket.pdf", mime="application/pdf")
                except Exception as e:
                    st.error(f"⚠️ PDF जेनेरेटर लोड हुन सकेन: Error: {e}")
            
            with view_tab3:
                st.markdown("### 📝 अफिसियल लाइन-अप फारम")
                st.info("यो फारम प्रिन्ट गरेर प्रत्येक म्याच अघि टिम कोच/म्यानेजरलाई भर्न दिनुहोस्।")
                try:
                    from utils.pdf_generator import generate_lineup_sheet_pdf
                    lineup_pdf = generate_lineup_sheet_pdf(f"{evt_name} ({sel_gender})")
                    st.download_button(
                        label="🖨️ यहाँ क्लिक गरेर Line-up Slip डाउनलोड/प्रिन्ट गर्नुहोस्",
                        data=lineup_pdf,
                        file_name=f"{evt_code}_Lineup_Slip.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                except Exception as e:
                    st.error(f"⚠️ Line-up PDF जेनेरेटर लोड हुन सकेन: Error: {e}")

# -----------------------------------------------------------------------
# TAB 2: LIVE MATCH CONTROL 
# -----------------------------------------------------------------------
with tab2:
    if not saved_matches:
        st.info("👈 पहिले 'टाइ-सिट' ट्याबबाट खेल तालिका बनाउनुहोस्।")
    else:
        live_matches = update_bracket_flow(saved_matches)
        
        if not st.session_state.get('selected_match'):
            c_pend, c_comp = st.columns([1.2, 1])
            
            with c_pend:
                st.markdown("### 🟢 खेल्न बाँकी म्याचहरू (Pending)")
                ready_ms = [m for m in live_matches 
                            if m['p1_name'] != "BYE" and m['p2_name'] != "BYE" 
                            and m.get('status') != 'Completed'
                            and "Winner" not in str(m['p1_name']) and "Loser" not in str(m['p1_name'])
                            and "Winner" not in str(m['p2_name']) and "Loser" not in str(m['p2_name'])]
                
                if not ready_ms:
                    st.success("🎉 सबै उपलब्ध खेलहरू सम्पन्न भइसकेका छन्!")
                else:
                    for idx, match in enumerate(ready_ms):
                        match_btn_text = f"🎮 Match #{match['match_no']} | {match['title']}\n{match['p1_name']} vs {match['p2_name']}"
                        if st.button(match_btn_text, key=f"mb_{match['match_no']}", use_container_width=True, type="primary" if idx == 0 else "secondary"):
                            st.session_state.selected_match = {
                                'id': match['match_no'], 'round': match['round_name'],
                                'p1': match['p1_name'], 'p1_id': match['team1_id'], 'p1_muni': match['comp1_muni_id'],
                                'p2': match['p2_name'], 'p2_id': match['team2_id'], 'p2_muni': match['comp2_muni_id']
                            }
                            st.rerun()
                            
            with c_comp:
                st.markdown("### ✅ सम्पन्न म्याचहरू (Completed)")
                completed_ms = [m for m in live_matches if m.get('status') == 'Completed' and m['p2_name'] != "BYE" and m['p1_name'] != "BYE"]
                
                if not completed_ms:
                    st.info("हालसम्म कुनै म्याच सम्पन्न भएको छैन।")
                else:
                    for m in completed_ms[::-1]: 
                        w_name = m['p1_name'] if m.get('winner_team_id') == m['team1_id'] and m['team1_id'] else (m['p2_name'] if m.get('winner_team_id') else "TBD")
                        
                        # 💡 Handle JSONB live_state to extract score summary
                        score_txt = "सम्पन्न"
                        if m.get('live_state'):
                            try:
                                state = m['live_state'] if isinstance(m['live_state'], dict) else json.loads(m['live_state'])
                                if 'score_a' in state and 'score_b' in state:
                                    score_txt = f"{state['score_a']} - {state['score_b']}"
                            except: pass
                            
                        st.markdown(f"""
                        <div style="background-color:#f8fafc; border-left:4px solid #10b981; padding:10px; margin-bottom:10px; border-radius:5px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                            <div style="color:#64748b; font-size:12px; font-weight:bold;">Match #{m['match_no']} | {m['title']}</div>
                            <div style="font-size:14px; margin:5px 0;">🔵 {m['p1_name']} <b>vs</b> 🔴 {m['p2_name']}</div>
                            <div style="color:#059669; font-size:14px; font-weight:bold;">🏆 विजेता: {w_name}</div>
                            <div style="color:#475569; font-size:12px; margin-top:2px;">📊 स्कोर: {score_txt}</div>
                        </div>
                        """, unsafe_allow_html=True)
                        
        else:
            sel_m = st.session_state.selected_match
            if st.button("🔙 म्याच सूचीमा फर्कनुहोस्", type="secondary"):
                st.session_state.selected_match = None
                st.rerun()
            st.divider()
            
            if sub_category == "Volleyball":
                import utils.volleyball_match as vb_live
                # Note: vb_live might need minor updates to push team_id and muni_id to the live_state JSONB.
                vb_live.render_match(evt_code, sel_m) 
            elif sub_category == "Kabaddi":
                import utils.kabaddi_match as kb_live
                kb_live.render_match(evt_code, sel_m) 
            else:
                st.warning(f"{sub_category} को लागि लाइभ कन्ट्रोल उपलब्ध छैन।")

# -----------------------------------------------------------------------
# TAB 3: RESULTS (नतिजा)
# -----------------------------------------------------------------------
with tab3:
    st.subheader("🏆 अन्तिम नतिजा (Final Results)")
    if saved_matches:
        final_match = next((m for m in saved_matches if m['title'] == '🏆 FINAL'), None)
        tp_match = next((m for m in saved_matches if m.get('is_third_place') == True), None)
        
        if final_match and final_match.get('status') == 'Completed':
            st.balloons()
            # 💡 PostgreSQL Logic: Fetch names based on winning team ID
            gold_name = final_match['p1_name'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['p2_name']
            silver_name = final_match['p2_name'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['p1_name']
            
            bronze_name = "TBD"
            if tp_match and tp_match.get('status') == 'Completed':
                bronze_name = tp_match['p1_name'] if tp_match['winner_team_id'] == tp_match['team1_id'] else tp_match['p2_name']
            
            st.markdown(f"""
            <div style='background:#fef9c3; padding:20px; border-radius:15px; border:2px solid #eab308; text-align:center;'>
                <h1 style='color:#ca8a04; margin-bottom:5px;'>🥇 प्रथम (Gold)</h1>
                <h2 style='margin-top:0;'>{gold_name}</h2>
            </div><br>
            <div style='display:flex; gap:20px;'>
                <div style='flex:1; background:#f1f5f9; padding:20px; border-radius:15px; border:2px solid #94a3b8; text-align:center;'>
                    <h2 style='color:#64748b; margin-bottom:5px;'>🥈 द्वितीय (Silver)</h2>
                    <h3 style='margin-top:0;'>{silver_name}</h3>
                </div>
                <div style='flex:1; background:#ffedd5; padding:20px; border-radius:15px; border:2px solid #fdba74; text-align:center;'>
                    <h2 style='color:#c2410c; margin-bottom:5px;'>🥉 तृतीय (Bronze)</h2>
                    <h3 style='margin-top:0;'>{bronze_name}</h3>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # 💡 Option to push these to the Master `results` table!
            if st.button("💾 मेडल ट्यालीमा यो नतिजा पठाउनुहोस् (Push to Results)", type="primary"):
                conn = db.get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM results WHERE event_code=%s", (evt_code,))
                
                # Insert Gold
                w1_muni = final_match['comp1_muni_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['comp2_muni_id']
                w1_team = final_match['team1_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['team2_id']
                c.execute("INSERT INTO results (event_code, municipality_id, team_id, position, medal) VALUES (%s, %s, %s, 1, 'Gold')", (evt_code, w1_muni, w1_team))
                
                # Insert Silver
                w2_muni = final_match['comp2_muni_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['comp1_muni_id']
                w2_team = final_match['team2_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['team1_id']
                c.execute("INSERT INTO results (event_code, municipality_id, team_id, position, medal) VALUES (%s, %s, %s, 2, 'Silver')", (evt_code, w2_muni, w2_team))
                
                # Insert Bronze
                if tp_match and tp_match.get('status') == 'Completed':
                    w3_muni = tp_match['comp1_muni_id'] if tp_match['winner_team_id'] == tp_match['team1_id'] else tp_match['comp2_muni_id']
                    w3_team = tp_match['team1_id'] if tp_match['winner_team_id'] == tp_match['team1_id'] else tp_match['team2_id']
                    c.execute("INSERT INTO results (event_code, municipality_id, team_id, position, medal) VALUES (%s, %s, %s, 3, 'Bronze')", (evt_code, w3_muni, w3_team))
                
                conn.commit()
                c.close()
                conn.close()
                st.success("✅ नतिजा मास्टर मेडल ट्यालीमा सुरक्षित भयो!")
                
        else: st.info("फाइनल म्याचको नतिजा आउन बाँकी छ।")
    else: st.warning("कुनै पनि म्याच डाटा उपलब्ध छैन।")

render_footer()