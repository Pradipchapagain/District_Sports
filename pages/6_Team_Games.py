# pages\6_Team_Games.py
import streamlit as st
import pandas as pd
import math
import random
import database as db
import json
import psycopg2.extras

from config import render_header, render_footer
from utils.bracket_generator import generate_team_bracket, update_bracket_flow


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
c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
c.execute("SELECT * FROM matches WHERE event_code=%s ORDER BY match_no", (evt_code,))
saved_matches = c.fetchall()
c.close()
conn.close()

# ==========================================================
# 💡 जादु: हरेकपटक पेज खुल्दा (वा रिफ्रेस हुँदा) 'Bracket Flow' अटो-अपडेट गर्ने
# ==========================================================
if saved_matches:
    try:
        # यसले 'Winner of #1' लाई वास्तविक टिमको नाममा परिवर्तन गर्छ र डाटाबेस अपडेट गर्छ
        update_bracket_flow(saved_matches)
        
        # डाटाबेस अपडेट भएपछि फ्रेस (Fresh) डाटा तान्ने ताकि सबै ट्याबमा नयाँ नाम देखियोस्
        conn = db.get_connection()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        c.execute("SELECT * FROM matches WHERE event_code=%s ORDER BY match_no", (evt_code,))
        saved_matches = c.fetchall()
        c.close()
        conn.close()
    except Exception as e:
        pass

# ==========================================
# 🗂️  TABS MANAGEMENT
# ==========================================
tab1, tab2, tab3 = st.tabs(["📋 १. टाइ-सिट (Bracket)", "🎮 २. लाइभ म्याच कन्ट्रोल", "🏆 ३. नतिजा (Results)"])

# -----------------------------------------------------------------------
# TAB 1: BRACKET GENERATION & VIEW
# -----------------------------------------------------------------------
with tab1:
    # 💡 जादु: दर्ता भएका खेलाडीको आधारमा अटोमेटिक टिम बनाउने
    def auto_generate_teams(event_code):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            c.execute("""
                SELECT DISTINCT p.municipality_id, m.name 
                FROM registrations r
                JOIN players p ON r.player_id = p.id
                JOIN municipalities m ON p.municipality_id = m.id
                WHERE r.event_code = %s
            """, (event_code,))
            active_munis = c.fetchall()
            
            for muni_id, muni_name in active_munis:
                c.execute("SELECT id FROM teams WHERE event_code = %s AND municipality_id = %s", (event_code, muni_id))
                if not c.fetchone():
                    c.execute("INSERT INTO teams (event_code, municipality_id, name) VALUES (%s, %s, %s)", 
                              (event_code, muni_id, f"{muni_name}"))
            conn.commit()
        except Exception as e:
            print(f"Team Auto-gen Error: {e}")
        finally:
            c.close(); conn.close()

    auto_generate_teams(evt_code)

    conn = db.get_connection()
    teams_df = pd.read_sql_query("SELECT t.id, t.name, t.municipality_id FROM teams t WHERE t.event_code=%s", conn, params=(evt_code,))
    conn.close()
    
    if teams_df.empty:
        st.warning("⚠️ यो खेलमा कुनै पनि टिम दर्ता भएका छैनन्। कृपया 'Player Registration' बाट खेलाडी दर्ता गर्नुहोस्।")
    else:
        # ==============================================================
        # 👕 जर्सी नम्बर इन्ट्री (Pre-Match Setup)
        # ==============================================================
        with st.expander("👕 टिमका खेलाडीहरूको जर्सी नम्बर दर्ता गर्नुहोस् (Pre-Match Setup)"):
            st.info("💡 यहाँ भरिएको जर्सी नम्बर 'Live Match Control' मा लाइन-अप बनाउँदा अटोमेटिक तानिन्छ।")
            
            sel_team_name = st.selectbox("जर्सी नम्बर भर्न टिम छान्नुहोस्:", teams_df['name'].tolist(), key="jersey_team_sel")
            
            if sel_team_name:
                conn = db.get_connection()
                c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                c.execute("""
                    SELECT p.id as player_id, p.name as player_name, r.jersey_no 
                    FROM registrations r 
                    JOIN players p ON r.player_id = p.id 
                    JOIN teams t ON p.municipality_id = t.municipality_id
                    WHERE r.event_code = %s AND t.name = %s
                """, (evt_code, sel_team_name))
                team_players = c.fetchall()
                c.close(); conn.close()
                
                if team_players:
                    df_jersey = pd.DataFrame(team_players)
                    if 'jersey_no' not in df_jersey.columns:
                        df_jersey['jersey_no'] = ""
                        
                    config_jersey = {
                        "player_id": None,
                        "player_name": st.column_config.TextColumn("खेलाडीको नाम", disabled=True),
                        "jersey_no": st.column_config.TextColumn("जर्सी नम्बर (Jersey No.)", max_chars=3)
                    }
                    
                    edited_jerseys = st.data_editor(
                        df_jersey, 
                        column_config=config_jersey, 
                        hide_index=True, 
                        width='stretch', 
                        key=f"je_{sel_team_name}"
                    )
                    
                    if st.button(f"💾 {sel_team_name} को जर्सी नम्बर सुरक्षित गर्नुहोस्", type="primary"):
                        conn = db.get_connection()
                        c = conn.cursor()
                        for _, row in edited_jerseys.iterrows():
                            j_no = str(row['jersey_no']).strip() if pd.notna(row['jersey_no']) else None
                            c.execute("UPDATE registrations SET jersey_no = %s WHERE player_id = %s AND event_code = %s", 
                                      (j_no, row['player_id'], evt_code))
                        conn.commit(); c.close(); conn.close()
                        st.success(f"✅ {sel_team_name} का खेलाडीहरूको जर्सी नम्बर सुरक्षित भयो!")
                else:
                    st.warning("यो टिममा खेलाडी दर्ता भएका छैनन्।")
        st.divider()

        # ==============================================================
        # 🔀 टाइ-सिट (Bracket) लजिक
        # ==============================================================
        if not saved_matches:
            st.subheader("🔀 नयाँ टाइ-सिट बनाउनुहोस्")
            seeded = st.multiselect("सिडेड टिमहरू छान्नुहोस् (Seeding):", teams_df['name'].tolist())
            
            if st.button("🎲 टाइ-सिट जेनेरेट गर्नुहोस्", type="primary"):
                # 💡 फिक्स: फङ्सनले True फर्कायो भने मात्र Rerun गर्ने!
                is_success = generate_team_bracket(teams_df, seeded, evt_code)
                if is_success:
                    st.success("✅ टाइ-सिट सफलतापूर्वक तयार भयो!")
                    import time
                    time.sleep(1) # १ सेकेन्ड पर्खिने ताकि सक्सेस मेसेज देखियोस्
                    st.rerun()
        else:
            c_r1, c_r2 = st.columns([1, 4])
            with c_r1:
                if st.button("⚠️ टाइ-सिट रिसेट गर्नुहोस्", type="secondary", width="stretch"):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("DELETE FROM matches WHERE event_code=%s", (evt_code,))
                    conn.commit(); c.close(); conn.close()
                    st.rerun()
            
            with st.expander("🔄 म्याचमा टिम साट्नुहोस् (Exchange Teams)"):
                st.caption("टाइसिट बनिसकेपछि यदि कुनै टिमलाई अर्को म्याचमा सार्नुपरेमा यहाँबाट गर्न सकिन्छ।")
                r1_matches = [m for m in saved_matches if m['title'] == 'Round 1']
                if r1_matches:
                    ex_c1, ex_c2, ex_c3 = st.columns([2, 2, 1])
                    match_a_id = ex_c1.selectbox("पहिलो म्याच छान्नुहोस्:", [m['match_no'] for m in r1_matches], format_func=lambda x: f"Match {x}")
                    match_b_id = ex_c2.selectbox("दोस्रो म्याच छान्नुहोस्:", [m['match_no'] for m in r1_matches if m['match_no'] != match_a_id], format_func=lambda x: f"Match {x}")
                    if ex_c3.button("🔄 साट्नुहोस् (Swap)", type="primary", width="stretch"):
                        m_a = next(m for m in saved_matches if m['match_no'] == match_a_id)
                        m_b = next(m for m in saved_matches if m['match_no'] == match_b_id)
                        
                        conn = db.get_connection()
                        c = conn.cursor()
                        c.execute("UPDATE matches SET p2_name=%s, team2_id=%s, comp2_muni_id=%s WHERE match_no=%s AND event_code=%s", 
                                  (m_b['p2_name'], m_b['team2_id'], m_b['comp2_muni_id'], m_a['match_no'], evt_code))
                        c.execute("UPDATE matches SET p2_name=%s, team2_id=%s, comp2_muni_id=%s WHERE match_no=%s AND event_code=%s", 
                                  (m_a['p2_name'], m_a['team2_id'], m_a['comp2_muni_id'], m_b['match_no'], evt_code))
                        conn.commit(); c.close(); conn.close()
                        st.success("✅ टिम सफलतापूर्वक साटियो!")
                        st.rerun()

            st.divider()
            matches = saved_matches

            # ==============================================================
            # 💡 फिक्स: Tab भित्र Tab राख्न नमिल्ने भएकोले 'Radio' बटनलाई ट्याब जस्तो बनाइएको छ।
            # ==============================================================
            view_mode = st.radio("दृश्य छान्नुहोस् (View Mode):", 
                                 ["📋 सूची (List View)", "🌳 ट्री मोडेल (Tree View)", "📝 लाइन-अप स्लिप (Forms)"], 
                                 horizontal=True, label_visibility="collapsed")
            
            st.markdown("<br>", unsafe_allow_html=True) # अलिकति खाली ठाउँ

            if view_mode == "📋 सूची (List View)":
                st.markdown("### 🏟️ खेल तालिका (Group A & Group B Bracket)")
                
                def get_round_weight(r_name):
                    r_upper = str(r_name).upper()
                    if 'ROUND' in r_upper:
                        import re
                        nums = re.findall(r'\d+', r_upper)
                        return int(nums[0]) if nums else 10
                    if 'QUARTER' in r_upper: return 90
                    if 'SEMI' in r_upper: return 95
                    if 'FINAL STAGE' in r_upper: return 99
                    return 50

                unique_rounds = []
                for m in matches:
                    title_up = str(m.get('title', '')).upper()
                    is_final = title_up == '🏆 FINAL' or title_up == 'FINAL'
                    is_third = 'THIRD' in title_up or '🥉' in title_up or m.get('is_third_place')
                    
                    if is_final or is_third:
                        label = "🏆 Final Stage"
                    else:
                        label = m.get('round_name', 'Round 1')
                        
                    if label not in unique_rounds:
                        unique_rounds.append(label)

                sorted_rounds = sorted(unique_rounds, key=get_round_weight)
                cols = st.columns(len(sorted_rounds))
                
                def build_card_html(m, is_special=False):
                    bg = "#ffffff"
                    title_up = str(m.get('title', '')).upper()
                    if title_up == '🏆 FINAL' or title_up == 'FINAL': bg = "#fef9c3"
                    elif 'THIRD' in title_up or '🥉' in title_up or m.get('is_third_place'): bg = "#ffedd5"
                    elif m.get('status') == 'Completed': bg = "#dcfce7"
                    
                    w_name = m['p1_name'] if m.get('winner_team_id') == m['team1_id'] and m['team1_id'] else (m['p2_name'] if m.get('winner_team_id') else "")
                    special_title = f"<div style='text-align:center; color:#b45309; font-weight:bold; margin-bottom:5px; font-size:13px;'>{m.get('title')}</div>" if is_special else ""
                    
                    return f"<div style='background-color:{bg}; border:1px solid #cbd5e1; border-radius:6px; padding:8px; margin:0; font-size:11px; box-shadow: 1px 1px 4px rgba(0,0,0,0.1); width: 100%; box-sizing: border-box;'>{special_title}<div style='color:#64748b; font-size:9px; font-weight:bold; border-bottom:1px solid #e2e8f0; padding-bottom:2px; margin-bottom:4px;'>Match #{m['match_no']}</div><div title='{m['p1_name']}' style='font-weight:600; color:#1e3a8a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>🔵 {m['p1_name']}</div><div style='color:#94a3b8; font-size:9px; text-align:center; margin:2px 0;'>VS</div><div title='{m['p2_name']}' style='font-weight:600; color:#991b1b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>🔴 {m['p2_name']}</div><div title='{w_name}' style='color:#166534; font-size:11px; font-weight:bold; margin-top:4px; text-align:center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{'🏆 ' + w_name if w_name else ''}</div></div>"

                # 💡 नयाँ फिक्स: सबैभन्दा ठूलो राउण्ड (Round 1) को म्याच गनेर कन्टेनरको 'फिक्स उचाइ' (Fixed Height) निकाल्ने
                import math
                r1_matches = [m for m in matches if m.get('round_name') == 'Round 1' and not (str(m.get('title','')).upper() == '🏆 FINAL' or str(m.get('title','')).upper() == 'FINAL' or 'THIRD' in str(m.get('title','')).upper() or m.get('is_third_place'))]
                max_cards_per_group = math.ceil(len(r1_matches) / 2) if r1_matches else 1
                
                # एउटा कार्डलाई लगभग 110px चाहिन्छ। केही प्याडिङ थपेर हाइट निकाल्ने:
                group_height = max(300, max_cards_per_group * 110 + 60) 
                total_final_height = (group_height * 2) + 20 # Group A + Group B + 20px gap

                for idx, r_label in enumerate(sorted_rounds):
                    with cols[idx]:
                        st.markdown(f"<h4 style='text-align:center; color:#1e293b; border-bottom:2px solid #cbd5e1; padding-bottom:5px; font-size: 14px; white-space: nowrap;'>{r_label}</h4>", unsafe_allow_html=True)
                        
                        if r_label == "🏆 Final Stage":
                            r_matches = [m for m in matches if str(m.get('title','')).upper() == '🏆 FINAL' or str(m.get('title','')).upper() == 'FINAL' or 'THIRD' in str(m.get('title','')).upper() or m.get('is_third_place')]
                            tp_match = next((m for m in r_matches if 'THIRD' in str(m.get('title','')).upper() or m.get('is_third_place')), None)
                            fn_match = next((m for m in r_matches if str(m.get('title','')).upper() == '🏆 FINAL' or str(m.get('title','')).upper() == 'FINAL'), None)
                            
                            # 💡 फाइनल कन्टेनर (Round 1 + Round 2 को जम्मा उचाइ बराबर)
                            html_final = f"<div style='height: {total_final_height}px; display: flex; flex-direction: column; justify-content: center; gap: 40px; box-sizing: border-box; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 8px; padding: 15px;'>"
                            if tp_match: html_final += build_card_html(tp_match, True)
                            if fn_match: html_final += build_card_html(fn_match, True)
                            html_final += "</div>"
                            st.markdown(html_final, unsafe_allow_html=True)
                            
                        else:
                            r_matches = [m for m in matches if m.get('round_name') == r_label and not (str(m.get('title','')).upper() == '🏆 FINAL' or str(m.get('title','')).upper() == 'FINAL' or 'THIRD' in str(m.get('title','')).upper() or m.get('is_third_place'))]
                            r_matches = sorted(r_matches, key=lambda x: x.get('match_no', 0))
                            
                            mid = math.ceil(len(r_matches) / 2)
                            group_a = r_matches[:mid]
                            group_b = r_matches[mid:]
                            
                            # 🔵 Group A (फिक्स उचाइ र सेन्टर)
                            html_a = f"<div style='height: {group_height}px; display: flex; flex-direction: column; justify-content: center; gap: 15px; border: 2px solid #60a5fa; border-radius: 6px; padding: 15px 8px 8px 8px; background: #eff6ff; position: relative; box-sizing: border-box;'>"
                            html_a += "<div style='position:absolute; top:-8px; left:8px; background:#eff6ff; padding:0 4px; color:#1d4ed8; font-size:10px; font-weight:bold; border-radius: 4px;'>Group A</div>"
                            for m in group_a: html_a += build_card_html(m)
                            html_a += "</div>"
                            
                            # 🔴 Group B (फिक्स उचाइ र सेन्टर)
                            html_b = f"<div style='height: {group_height}px; display: flex; flex-direction: column; justify-content: center; gap: 15px; border: 2px solid #f87171; border-radius: 6px; padding: 15px 8px 8px 8px; background: #fef2f2; position: relative; box-sizing: border-box;'>"
                            html_b += "<div style='position:absolute; top:-8px; left:8px; background:#fef2f2; padding:0 4px; color:#b91c1c; font-size:10px; font-weight:bold; border-radius: 4px;'>Group B</div>"
                            for m in group_b: html_b += build_card_html(m)
                            html_b += "</div>"
                                
                            # दुवै ग्रुपलाई एउटै र्यापरमा (२०px को ग्याप)
                            full_col = f"<div style='display: flex; flex-direction: column; gap: 20px; box-sizing: border-box;'>{html_a}{html_b}</div>"
                            st.markdown(full_col, unsafe_allow_html=True)
                            
                            
            elif view_mode == "🌳 ट्री मोडेल (Tree View)":
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
            
            elif view_mode == "📝 लाइन-अप स्लिप (Forms)":
                st.markdown("### 📝 अफिसियल लाइन-अप फारम")
                st.info("यो फारम प्रिन्ट गरेर प्रत्येक म्याच अघि टिम कोच/म्यानेजरलाई भर्न दिनुहोस्।")
                try:
                    from utils.pdf_generator import generate_lineup_sheet_pdf
                    
                    # 💡 फिक्स: CONFIG यहाँ डिफाइन गर्ने ताकि सिस्टमले हेडरमा नाम देखाउन सकोस्
                    CONFIG = {
                        'ORGANIZER_NAME_EN': 'District Sports Development Committee, Ilam',
                        'EVENT_TITLE_EN': '16th District Level President Running Shield - 2082'
                    }
                    
                    evt_info_dict = {
                        'name': evt_name,
                        'gender': sel_gender,
                        'category': 'Team Game',
                        'sub_category': sub_category,
                        'event_group': 'Court/Field'
                    }
                    
                    # अब यहाँ CONFIG पठाउँदा कुनै एरर आउँदैन
                    lineup_pdf = generate_lineup_sheet_pdf(evt_info_dict, CONFIG)
                    
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
        live_matches = saved_matches
        
        st.markdown("""
        <style>
            div[data-testid="stButton"] button {
                white-space: pre-wrap !important; height: auto !important; padding: 10px !important; line-height: 1.5 !important; text-align: left !important;
            }
        </style>
        """, unsafe_allow_html=True)
        
        def short_name(name):
            if not name: return ""
            import re
            clean = re.sub(r'[\u0900-\u097F]+', '', str(name))
            clean = re.sub(r'\(\s*\)', '', clean)
            return clean.strip()
            
        if not st.session_state.get('selected_match'):
            c_pend, c_comp = st.columns([1.5, 1])
            
            # ==========================================================
            # 💡 जादु १: सबै म्याचहरूलाई एकैपटक ३ वटा बाकसमा सही तरिकाले छुट्याउने
            # ==========================================================
            live_now_ms = []
            upcoming_ms = []
            completed_ms = []
            
            for m in live_matches:
                # BYE पाएका टिमहरूलाई नदेखाउने
                if m['p1_name'] == "BYE" or m['p2_name'] == "BYE":
                    continue
                    
                # सुरुमा डाटाबेसको स्टाटस हेर्ने
                db_status = str(m.get('status', '')).strip()
                is_comp = (db_status == 'Completed') or (m.get('winner_team_id') is not None)
                is_live = (db_status == 'In Progress')
                
                # यदि भित्र (live_state) मा डाटा छ भने, त्यसलाई अन्तिम सत्य (Ultimate Truth) मान्ने!
                if m.get('live_state'):
                    try:
                        state = m['live_state'] if isinstance(m['live_state'], dict) else json.loads(m['live_state'])
                        
                        if state.get('status') == 'Completed' or state.get('match_completed') == True:
                            is_comp = True
                            is_live = False
                        elif state.get('match_started') == True or state.get('status') == 'In Progress':
                            is_live = True
                            is_comp = False
                    except: pass
                
                # छुट्याएको आधारमा लिस्टमा हाल्ने
                if is_comp:
                    completed_ms.append(m)
                elif is_live:
                    live_now_ms.append(m)
                else:
                    upcoming_ms.append(m)
            # ==========================================================
            
            with c_pend:
                # 🔴 १. चालु म्याचहरू (Live Now) देखाउने
                if live_now_ms:
                    st.markdown("""
                    <div style='background:#fef2f2; border:2px solid #ef4444; padding:10px; border-radius:8px; margin-bottom:20px;'>
                        <h3 style='color:#dc2626; margin-top:0;'>🔴 चालु म्याचहरू (Live Now)</h3>
                        <p style='margin:0; font-size:14px; color:#b91c1c;'>यी म्याचहरू अहिले चलिरहेका छन्। तलको बटन थिचेर सिधै कोर्टमा जानुहोस्:</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    for m in live_now_ms:
                        btn_txt = f"▶️ Resume Match #{m['match_no']} | {short_name(m['p1_name'])} vs {short_name(m['p2_name'])}"
                        if st.button(btn_txt, key=f"resume_{m['match_no']}", use_container_width=True):
                            st.session_state.selected_match = {
                                'id': m['match_no'], 'round': m['round_name'], 'p1': m['p1_name'], 'p1_id': m['team1_id'], 'p1_muni': m['comp1_muni_id'], 'p2': m['p2_name'], 'p2_id': m['team2_id'], 'p2_muni': m['comp2_muni_id']
                            }
                            st.rerun()
                    st.divider()

                # 🕒 २. आगामी म्याचहरू (Upcoming) देखाउने
                st.markdown("### ⏳ खेल्न बाँकी म्याचहरू (Upcoming)")
                st.caption("*(नोट: जुन म्याचका दुवै टिमहरूको टुङ्गो लागिसकेको छ, ती मात्र यहाँ देखिन्छन्।)*")
                
                if not upcoming_ms and not live_now_ms:
                    st.success("🎉 सबै उपलब्ध खेलहरू सम्पन्न भइसकेका छन्!")
                elif not upcoming_ms:
                    st.info("अहिले खेल्न बाँकी नयाँ म्याचहरू छैनन्।")
                else:
                    def get_r_weight(m):
                        t = str(m.get('title', '')).upper()
                        r = str(m.get('round_name', '')).upper()
                        if 'THIRD' in t or m.get('is_third_place'): return 98
                        if t == '🏆 FINAL' or t == 'FINAL': return 99 
                        import re
                        nums = re.findall(r'\d+', r)
                        return int(nums[0]) if nums else 10
                        
                    upcoming_ms.sort(key=lambda x: (get_r_weight(x), x.get('match_no', 0)))
                    import itertools
                    grouped = itertools.groupby(upcoming_ms, key=get_r_weight)
                    is_first_match = True 
                    
                    for weight, group in grouped:
                        group_list = list(group)
                        r_title = group_list[0].get('round_name', f'Round {weight}')
                        if weight == 98: r_title = "🥉 Third Place Match"
                        elif weight == 99: r_title = "🏆 FINAL MATCH"
                        
                        st.markdown(f"<div style='font-size:16px; font-weight:bold; color:#1e3a8a; border-bottom:2px solid #93c5fd; margin:20px 0 10px 0; padding-bottom:5px;'>{r_title}</div>", unsafe_allow_html=True)
                        
                        if weight >= 98:
                            for m in group_list:
                                btn_txt = f"Match #{m['match_no']}\n🔵 {short_name(m['p1_name'])}\n🔴 {short_name(m['p2_name'])}"
                                if st.button(btn_txt, key=f"mb_{m['match_no']}", use_container_width=True, type="primary"):
                                    st.session_state.selected_match = {
                                        'id': m['match_no'], 'round': m['round_name'], 'p1': m['p1_name'], 'p1_id': m['team1_id'], 'p1_muni': m['comp1_muni_id'], 'p2': m['p2_name'], 'p2_id': m['team2_id'], 'p2_muni': m['comp2_muni_id']
                                    }
                                    st.rerun()
                        else:
                            all_in_round = [x for x in live_matches if get_r_weight(x) == weight]
                            all_ids = sorted([x['match_no'] for x in all_in_round])
                            mid_pt = len(all_ids) // 2
                            pool_a_ids = all_ids[:mid_pt]
                            
                            group_a = [m for m in group_list if m['match_no'] in pool_a_ids]
                            group_b = [m for m in group_list if m['match_no'] not in pool_a_ids]
                            
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if group_a:
                                    with st.container(border=True):
                                        st.markdown("<div style='text-align:center; font-weight:bold; color:#2563eb; margin-bottom:10px; background:#eff6ff; padding:5px; border-radius:5px;'>🔵 Pool A</div>", unsafe_allow_html=True)
                                        for m in group_a:
                                            btn_txt = f"Match #{m['match_no']}\n🔵 {short_name(m['p1_name'])}\n🔴 {short_name(m['p2_name'])}"
                                            if st.button(btn_txt, key=f"mb_{m['match_no']}", use_container_width=True, type="primary" if is_first_match else "secondary"):
                                                st.session_state.selected_match = {
                                                    'id': m['match_no'], 'round': m['round_name'], 'p1': m['p1_name'], 'p1_id': m['team1_id'], 'p1_muni': m['comp1_muni_id'], 'p2': m['p2_name'], 'p2_id': m['team2_id'], 'p2_muni': m['comp2_muni_id']
                                                }
                                                st.rerun()
                                            is_first_match = False
                            with col_b:
                                if group_b:
                                    with st.container(border=True):
                                        st.markdown("<div style='text-align:center; font-weight:bold; color:#dc2626; margin-bottom:10px; background:#fef2f2; padding:5px; border-radius:5px;'>🔴 Pool B</div>", unsafe_allow_html=True)
                                        for m in group_b:
                                            btn_txt = f"Match #{m['match_no']}\n🔵 {short_name(m['p1_name'])}\n🔴 {short_name(m['p2_name'])}"
                                            if st.button(btn_txt, key=f"mb_{m['match_no']}", use_container_width=True, type="secondary"):
                                                st.session_state.selected_match = {
                                                    'id': m['match_no'], 'round': m['round_name'], 'p1': m['p1_name'], 'p1_id': m['team1_id'], 'p1_muni': m['comp1_muni_id'], 'p2': m['p2_name'], 'p2_id': m['team2_id'], 'p2_muni': m['comp2_muni_id']
                                                }
                                                st.rerun()
                            
            with c_comp:
                # ✅ ३. सम्पन्न म्याचहरू देखाउने
                st.markdown("### ✅ सम्पन्न म्याचहरू")
                        
                if not completed_ms:
                    st.info("हालसम्म कुनै म्याच सम्पन्न भएको छैन।")
                else:
                    for m in completed_ms[::-1]: 
                        
                        # १. विजेताको नाम निकाल्ने
                        w_name = m.get('winner_name')
                        if not w_name:
                            if str(m.get('winner_team_id')) == str(m.get('team1_id')) and m.get('team1_id'): 
                                w_name = m['p1_name']
                            elif str(m.get('winner_team_id')) == str(m.get('team2_id')) and m.get('team2_id'): 
                                w_name = m['p2_name']
                            else:
                                if m.get('live_state'):
                                    try:
                                        state = m['live_state'] if isinstance(m['live_state'], dict) else json.loads(m['live_state'])
                                        if 'sets_won' in state:
                                            w_name = max(state['sets_won'], key=state['sets_won'].get)
                                    except: pass
                        if not w_name: w_name = "TBD"
                        
                        # २. स्कोर र थप विवरण निकाल्ने
                        score_txt = "सम्पन्न"
                        extra_details = ""
                        
                        if m.get('live_state'):
                            try:
                                state = m['live_state'] if isinstance(m['live_state'], dict) else json.loads(m['live_state'])
                                
                                if sub_category == "Kabaddi":
                                    if 'score_a' in state and 'score_b' in state:
                                        score_txt = f"{state['score_a']} - {state['score_b']}"
                                    if 'half_1_score' in state:
                                        extra_details = f"<b>पहिलो हाफ:</b> {state['half_1_score']}<br>"
                                
                                elif sub_category == "Volleyball":
                                    p1_n, p2_n = m['p1_name'], m['p2_name']
                                    if 'sets_won' in state and p1_n in state['sets_won'] and p2_n in state['sets_won']:
                                        score_txt = f"{state['sets_won'][p1_n]} - {state['sets_won'][p2_n]}"
                                    
                                    if 'scores' in state:
                                        set_details = []
                                        for s_num, s_data in state['scores'].items():
                                            if s_data.get(p1_n, 0) > 0 or s_data.get(p2_n, 0) > 0:
                                                set_details.append(f"[{s_data.get(p1_n, 0)}-{s_data.get(p2_n, 0)}]")
                                        if set_details:
                                            extra_details = "<b>सेटवाइज स्कोर:</b> " + ", ".join(set_details) + "<br>"
                            except: pass

                        # ३. "अर्को यात्रा" पत्ता लगाउने (Next Match Logic)
                        next_match_txt = "प्रतियोगिता समाप्त (च्याम्पियन)!"
                        
                        if m.get('is_third_place'):
                            next_match_txt = "तेस्रो स्थानको छिनोफानो भयो।"
                        else:
                            current_m_no = m['match_no']
                            nxt_m = next((x for x in live_matches if x.get('source_match1') == current_m_no or x.get('source_match2') == current_m_no), None)
                            
                            if nxt_m:
                                opp_source = nxt_m.get('source_match2') if nxt_m.get('source_match1') == current_m_no else nxt_m.get('source_match1')
                                p1_n = str(nxt_m.get('p1_name', ''))
                                p2_n = str(nxt_m.get('p2_name', ''))
                                
                                opp_name = None
                                if "Winner" not in p1_n and short_name(w_name) not in short_name(p1_n):
                                    opp_name = p1_n
                                elif "Winner" not in p2_n and short_name(w_name) not in short_name(p2_n):
                                    opp_name = p2_n
                                
                                if opp_name:
                                    next_match_txt = f"म्याच #{nxt_m['match_no']} ({nxt_m['round_name']}) मा <b>{short_name(opp_name)}</b> सँग भिड्नेछ।"
                                else:
                                    next_match_txt = f"म्याच #{nxt_m['match_no']} ({nxt_m['round_name']}) मा <b>Winner of #{opp_source}</b> सँग खेल्नेछ।"

                        # ४. UI मा विजेतालाई बोल्ड+ट्रफी र हार्नेलाई फुस्रो (Grey) बनाउने
                        p1_clean = short_name(m['p1_name'])
                        p2_clean = short_name(m['p2_name'])
                        w_clean = short_name(w_name)
                        
                        if w_clean == p1_clean:
                            p1_html = f"<span style='font-weight:bold; color:#1e3a8a;'>🔵 {p1_clean} <span style='color:#059669; font-size:14px; margin-left:5px;'>🏆 ({score_txt})</span></span>"
                            p2_html = f"<span style='color:#94a3b8;'>🔴 {p2_clean}</span>"
                        elif w_clean == p2_clean:
                            p1_html = f"<span style='color:#94a3b8;'>🔵 {p1_clean}</span>"
                            p2_html = f"<span style='font-weight:bold; color:#1e3a8a;'>🔴 {p2_clean} <span style='color:#059669; font-size:14px; margin-left:5px;'>🏆 ({score_txt})</span></span>"
                        else:
                            p1_html = f"🔵 {p1_clean}"
                            p2_html = f"🔴 {p2_clean}"

                        # ५. चिटिक्क परेको कार्ड (Card) देखाउने
                        st.markdown(f"""
                        <div style="background-color:#f8fafc; border-left:4px solid #10b981; padding:10px; margin-bottom:10px; border-radius:5px; box-shadow:0 2px 4px rgba(0,0,0,0.05);">
                            <div style="color:#64748b; font-size:12px; font-weight:bold; margin-bottom:5px;">Match #{m['match_no']} | {m['title']}</div>
                            <div style="font-size:15px; margin:5px 0; line-height: 1.6;">
                                {p1_html} <br>
                                {p2_html}
                            </div>
                            <details style="cursor: pointer; margin-top: 8px; border-top: 1px dashed #cbd5e1; padding-top: 8px;">
                                <summary style="font-size: 12px; color: #2563eb; font-weight: bold; outline: none;">➕ थप विवरण हेर्नुहोस्</summary>
                                <div style="font-size: 12px; color: #475569; margin-top: 5px; background: #eff6ff; padding: 8px; border-radius: 4px;">
                                    {extra_details}<b>⏭️ अर्को यात्रा:</b> {next_match_txt}
                                </div>
                            </details>
                        </div>
                        """, unsafe_allow_html=True)
                        
        else:
            sel_m = st.session_state.selected_match
            
            # 💡 १. म्याच भित्र छिरेको प्रस्ट देखाउन ठूलो हेडर ब्यानर
            st.markdown(f"""
            <div style='background: linear-gradient(135deg, #1e3a8a, #3b82f6); color:white; padding:15px 20px; border-radius:10px; text-align:center; margin-bottom:20px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);'>
                <h2 style='margin:0; color:white; font-size:24px;'>🏟️ Match #{sel_m['id']} : {short_name(sel_m['p1'])} 🆚 {short_name(sel_m['p2'])}</h2>
                <p style='margin:5px 0 0 0; opacity:0.9; font-size:14px;'>{sub_category} | {sel_m['round']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 💡 २. कन्ट्रोल बटनहरू (Back, Edit Lineup, Reset)
            c_back, c_edit, c_reset = st.columns([2, 2, 2])
            
            with c_back:
                if st.button("🔙 म्याच सूचीमा फर्कनुहोस्", type="secondary", use_container_width=True):
                    st.session_state.selected_match = None
                    st.rerun()
                    
            with c_edit:
                s_key = f"{sub_category.lower()}_{evt_code}_{sel_m['id']}"
                can_edit = False
                edit_help = "पहिले तलबाट म्याच लोड हुन दिनुहोस्।"
                
                if s_key in st.session_state:
                    current_state = st.session_state[s_key]
                    if current_state.get('status') == 'Completed':
                        edit_help = "म्याच सम्पन्न भइसकेको छ। अब लाइन-अप सम्पादन गर्न मिल्दैन।"
                    elif current_state.get('match_started') == True:
                        edit_help = "खेल चलिरहेको छ! सेट वा हाफ नसकिउन्जेल लाइन-अप सम्पादन गर्न मिल्दैन।"
                    else:
                        can_edit = True 
                        edit_help = "नयाँ सेट/हाफ सुरु हुनुअघि खेलाडी परिवर्तन गर्न यहाँ थिच्नुहोस्। यसले स्कोर मेटाउँदैन।"

                if st.button("🔄 लाइन-अप सम्पादन (Edit Lineup)", type="primary", use_container_width=True, disabled=not can_edit, help=edit_help):
                    st.session_state[s_key]['setup_complete'] = False 
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("UPDATE matches SET live_state=%s WHERE match_no=%s AND event_code=%s", (json.dumps(st.session_state[s_key]), sel_m['id'], evt_code))
                    conn.commit(); c.close(); conn.close()
                    st.rerun()

            with c_reset:
                # 💡 ३. पूर्ण रिसेट (डाटाबेस, टाइमर र RAM सबै खाली गर्ने)
                if st.button("⚠️ रिसेट म्याच (Reset)", type="primary", use_container_width=True, help="म्याच बिग्रिएमा सबै स्कोर र लाइन-अप मेटाएर सुरुबाट गर्न"):
                    conn = db.get_connection()
                    c = conn.cursor()
                    c.execute("UPDATE matches SET live_state=NULL, status='Pending', winner_team_id=NULL, winner_muni_id=NULL WHERE match_no=%s AND event_code=%s", (sel_m['id'], evt_code))
                    conn.commit(); c.close(); conn.close()
                    
                    # यो म्याचसँग जोडिएका सबै कुरा (टाइमर, साउन्ड, स्टेट) र्यामबाट डिलिट गर्ने
                    keys_to_delete = [k for k in st.session_state.keys() if f"_{sel_m['id']}" in k or k == s_key]
                    for k in keys_to_delete:
                        del st.session_state[k]
                    
                    st.session_state.selected_match = None 
                    st.rerun()
            
            st.divider()
            
            with st.expander(f"🖨️ Match #{sel_m['id']} को लाइन-अप स्लिप (Line-up Sheet) प्रिन्ट गर्नुहोस्", expanded=False):
                st.info(f"यसले {short_name(sel_m['p1'])} र {short_name(sel_m['p2'])} दुवैको नाम र जर्सी नम्बर भरिएको एउटै A4 पाना निकाल्छ। बिचमा ठाडो काटेर दुई टिमलाई दिनुहोस्।")
                
                if st.button("📥 डाउनलोड लाइन-अप स्लिप", type="primary", icon="📄"):
                    import psycopg2.extras
                    conn = db.get_connection()
                    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

                    c.execute("SELECT p.name as player_name, r.jersey_no FROM registrations r JOIN players p ON r.player_id = p.id WHERE r.event_code = %s AND p.municipality_id = %s", (evt_code, sel_m['p1_muni']))
                    t1_p = c.fetchall()

                    c.execute("SELECT p.name as player_name, r.jersey_no FROM registrations r JOIN players p ON r.player_id = p.id WHERE r.event_code = %s AND p.municipality_id = %s", (evt_code, sel_m['p2_muni']))
                    t2_p = c.fetchall()
                    c.close(); conn.close()

                    evt_info_dict = {'name': evt_name, 'gender': sel_gender, 'sub_category': sub_category}
                    
                    # 💡 फिक्स: माथि इम्पोर्ट भएको मास्टर CONFIG चलाउने (हार्डकोडेड हटाइयो)
                    from utils.pdf_generator import generate_prefilled_lineup_pdf
                    pdf_bytes = generate_prefilled_lineup_pdf(evt_info_dict, sel_m, t1_p, t2_p, CONFIG)

                    st.download_button(label="⬇️ यहाँ क्लिक गरेर PDF सेभ गर्नुहोस्", data=pdf_bytes, file_name=f"Match_{sel_m['id']}_{sub_category}_Lineup.pdf", mime="application/pdf")
            
            st.divider()
            
            # म्याचलाई सम्बन्धित गेम-इन्जिन (Engine) मा पठाउने
            if sub_category == "Volleyball":
                import utils.volleyball_match as vb_live
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
            
            if st.button("💾 मेडल ट्यालीमा यो नतिजा पठाउनुहोस् (Push to Results)", type="primary"):
                conn = db.get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM results WHERE event_code=%s", (evt_code,))
                
                w1_muni = final_match['comp1_muni_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['comp2_muni_id']
                w1_team = final_match['team1_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['team2_id']
                c.execute("INSERT INTO results (event_code, municipality_id, team_id, position, medal) VALUES (%s, %s, %s, 1, 'Gold')", (evt_code, w1_muni, w1_team))
                
                w2_muni = final_match['comp2_muni_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['comp1_muni_id']
                w2_team = final_match['team2_id'] if final_match['winner_team_id'] == final_match['team1_id'] else final_match['team1_id']
                c.execute("INSERT INTO results (event_code, municipality_id, team_id, position, medal) VALUES (%s, %s, %s, 2, 'Silver')", (evt_code, w2_muni, w2_team))
                
                w3_muni = ""
                if tp_match and tp_match.get('status') == 'Completed':
                    w3_muni = tp_match['comp1_muni_id'] if tp_match['winner_team_id'] == tp_match['team1_id'] else tp_match['comp2_muni_id']
                    w3_team = tp_match['team1_id'] if tp_match['winner_team_id'] == tp_match['team1_id'] else tp_match['team2_id']
                    c.execute("INSERT INTO results (event_code, municipality_id, team_id, position, medal) VALUES (%s, %s, %s, 3, 'Bronze')", (evt_code, w3_muni, w3_team))
                
                conn.commit()
                c.close()
                conn.close()
                st.success("✅ नतिजा मास्टर मेडल ट्यालीमा सुरक्षित भयो!")
                
                # ==========================================
                # 💡 जादु: लाइभ डिस्प्लेमा पोडियम पठाउने कोड
                # ==========================================
                import utils.live_state as ls
                import psycopg2.extras
                
                # १. इभेन्ट र पालिकाको वास्तविक नाम डाटाबेसबाट तान्ने
                conn2 = db.get_connection()
                c2 = conn2.cursor(cursor_factory=psycopg2.extras.DictCursor)
                
                # इभेन्टको नाम तान्ने (जस्तै: Volleyball (Boys))
                c2.execute("SELECT name, gender FROM events WHERE code=%s", (evt_code,))
                ev_data = c2.fetchone()
                real_event_name = f"{ev_data['name']} ({ev_data['gender']})" if ev_data else "Team Championship"
                
                # पालिकाको नाम तान्ने फङ्सन
                def get_muni_name(m_id):
                    if not m_id: return ""
                    c2.execute("SELECT name FROM municipalities WHERE id=%s", (m_id,))
                    res = c2.fetchone()
                    return res['name'] if res else str(m_id)
                
                m1_name = get_muni_name(w1_muni)
                m2_name = get_muni_name(w2_muni)
                m3_name = get_muni_name(w3_muni)
                
                c2.close()
                conn2.close()

                # २. बल्ल पोडियम ट्रिगर गर्ने
                ls.trigger_podium(
                    event_name=real_event_name, 
                    gold_data={"name": gold_name, "municipality": m1_name},
                    silver_data={"name": silver_name, "municipality": m2_name},
                    bronze_data={"name": bronze_name, "municipality": m3_name}
                )
        else: st.info("फाइनल म्याचको नतिजा आउन बाँकी छ।")
    else: st.warning("कुनै पनि म्याच डाटा उपलब्ध छैन।")

render_footer()