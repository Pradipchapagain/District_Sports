import streamlit as st
import pandas as pd
import database as db
import math
import random
import utils.pdf_generator as pdf_gen
import utils.live_state as ls
import utils.result as res

from config import render_header, render_footer, CONFIG

# ==========================================
# 🔒 SECURITY & CONFIG & CSS
# ==========================================
st.set_page_config(page_title="Athletics Operations", page_icon="🏃", layout="wide")

st.markdown("""
<style>
    .stButton>button { border-radius: 8px; font-weight: bold; transition: 0.3s; }
    .stButton>button:hover { transform: scale(1.02); }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { border-radius: 4px 4px 0 0; }
    div[data-testid="stMetricValue"] { font-size: 28px; color: #1f77b4; font-weight: 800; }
    .formal-call-box { padding: 10px; background: #f8f9fa; border-radius: 10px; border-left: 5px solid #ff4b4b; margin-bottom: 20px; }
</style>
""", unsafe_allow_html=True)

render_header() 

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.switch_page("Home.py") 

st.title("🏃 एथलेटिक्स (Track & Field) सञ्चालन")

if 'heats_data' not in st.session_state: st.session_state.heats_data = {}

# ==========================================
# Helper Functions (Athletics Specific)
# ==========================================
def get_athletics_participants(event_code):
    conn = db.get_connection()
    # 💡 PostgreSQL Syntax
    q = """
        SELECT p.id, p.name, p.iemis_id, p.gender, p.class_val as class, p.school_name as school, m.name as municipality, m.id as mun_id
        FROM registrations r
        JOIN players p ON r.player_id = p.id
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE r.event_code = %s
        ORDER BY m.name, p.name
    """
    df = pd.read_sql_query(q, conn, params=(event_code,))
    conn.close()
    return df

def generate_heats(participants_df, lanes_per_heat, seeded_entities=[]):
    players = participants_df.to_dict('records')
    total_players = len(players)
    if total_players == 0: return pd.DataFrame(), 0
    
    num_heats = math.ceil(total_players / lanes_per_heat)
    heats_buckets = {i: [] for i in range(1, num_heats + 1)}
    seed_key = 'name' if 'players_list' in players[0] else 'municipality'
    
    seeded_players = [p for p in players if p.get(seed_key) in seeded_entities]
    regular_players = [p for p in players if p.get(seed_key) not in seeded_entities]
    
    random.shuffle(seeded_players)
    random.shuffle(regular_players)
    
    current_heat = 1
    for p in seeded_players + regular_players:
        heats_buckets[current_heat].append(p)
        current_heat += 1
        if current_heat > num_heats: current_heat = 1
            
    final_rows = []
    for h_num, p_list in heats_buckets.items():
        for i, player in enumerate(p_list):
            player['heat'] = h_num
            player['lane'] = i + 1
            final_rows.append(player)
            
    return pd.DataFrame(final_rows), num_heats

# ==========================================
# SIDEBAR: EVENT SELECTION
# ==========================================
with st.sidebar:
    st.header("🎯 खेल छनौट")
    all_events = db.get_events()
    athletics_events = all_events[all_events['category'] == 'Athletics']
    
    if athletics_events.empty:
        st.error("एथलेटिक्सका इभेन्टहरू भेटिएनन्।")
        st.stop()

    sel_gender = st.radio("१. लिङ्ग (Gender):", ["Boys", "Girls"], horizontal=True)
    gender_filtered = athletics_events[athletics_events['gender'] == sel_gender]
    
    sub_cats = sorted(gender_filtered['sub_category'].unique())
    sel_sub_cat = st.selectbox("२. विधा (Track/Field):", sub_cats)
    sub_filtered = gender_filtered[gender_filtered['sub_category'] == sel_sub_cat]
    
    event_groups = sorted(sub_filtered['event_group'].unique())
    sel_evt_group = st.selectbox("३. समूह (Event Group):", event_groups)
    group_filtered = sub_filtered[sub_filtered['event_group'] == sel_evt_group]
    
    evt_opts = {r['name']: r for _, r in group_filtered.iterrows()}
    
    # 💡 यदि इभेन्ट छ भने मात्र सेलेक्टबक्स देखाउने
    if evt_opts:
        sel_evt_name = st.selectbox("४. इभेन्ट (Event):", list(evt_opts.keys()))
        current_event = evt_opts.get(sel_evt_name)
    else:
        st.warning("⚠️ यो समूहमा कुनै खेल भेटिएन।")
        current_event = None

    # 💡 जादु यहाँ छ: `if current_event:` को सट्टा `is not None` लेख्ने
    if current_event is not None:
        if sel_sub_cat == "Track":
            script_mode = "Relay" if current_event['event_group'] == "Relay" else "Track"
        elif sel_sub_cat == "Field":
            script_mode = "HighJump" if "High Jump" in current_event['name'] else "Field"
    else:
        script_mode = None

# ==========================================
# MAIN PANEL
# ==========================================
if current_event is not None and script_mode is not None:
    evt_code = current_event['code']
    evt_name = current_event['name']
    evt_gender = current_event['gender']
    
    st.header(f"⚡ {evt_name}")
    p_df = get_athletics_participants(evt_code)
    
    if p_df.empty:
        st.error("⚠️ यो इभेन्टमा कुनै खेलाडी दर्ता छैनन्।")
        st.stop()

    c1, c2, c3 = st.columns([1, 1, 2])
    c1.metric("👥 कुल सहभागी", f"{len(p_df)} जना" if script_mode != "Relay" else f"{p_df['municipality'].nunique()} टिम")
    c2.metric("🏛️ सहभागी पालिका", f"{p_df['municipality'].nunique()} वटा")
    
    with c3:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM results WHERE event_code=%s AND medal='Qualified'", (evt_code,))
        qual_count = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM results WHERE event_code=%s AND medal!='Qualified'", (evt_code,))
        final_count = c.fetchone()[0]
        c.close()
        conn.close()
        
        if final_count > 0:
            st.markdown("<div class='formal-call-box' style='border-left: 5px solid #28a745; background: #e9f7ef;'><b>✅ खेल सम्पन्न भइसकेको छ</b><br><span style='font-size:14px; color:#555;'>नतिजा सार्वजनिक भइसकेकोले अब खेलाडीलाई कल गर्न मिल्दैन।</span></div>", unsafe_allow_html=True)
        else:
            if script_mode in ["Field", "HighJump"]:
                round_name = "Final"
            elif qual_count > 0:
                round_name = "Final"
            else:
                if evt_code in st.session_state.heats_data and 'FINAL' in st.session_state.heats_data[evt_code]['heat'].values:
                    round_name = "Final"
                else:
                    round_name = "Heats"
                    
            display_round = "🏁 फाइनल (Final)" if round_name == "Final" else "🔥 हिट्स (Heats)"
            
            st.markdown(f"<div class='formal-call-box'><b>📢 फर्मल कल ({display_round})</b><br></div>", unsafe_allow_html=True)
            btn1, btn2, btn3 = st.columns(3)
            
            import utils.live_state as ls 
            
            if btn1.button("🟢 पहिलो कल", use_container_width=True): 
                ls.trigger_call(f"{evt_name} - ({evt_gender})", round_name, "FIRST CALL", "#28a745") 
                st.toast(f"📢 {display_round} को लागि पहिलो कल गरियो!", icon="🟢")
                
            if btn2.button("🟡 दोस्रो कल", use_container_width=True): 
                ls.trigger_call(f"{evt_name} - ({evt_gender})", round_name, "SECOND CALL", "#ffc107") 
                st.toast(f"📢 {display_round} को लागि दोस्रो कल गरियो!", icon="🟡")
                
            if btn3.button("🔴 अन्तिम कल", use_container_width=True): 
                ls.trigger_call(f"{evt_name} - ({evt_gender})", round_name, "LAST & FINAL CALL", "#dc3545") 
                st.toast(f"📢 {display_round} को लागि अन्तिम कल! खेलाडी ट्र्याकमा।", icon="🔴")

    
    with st.expander("🏘️ पालिका अनुसार दर्ता भएका खेलाडीहरूको विवरण हेर्नुहोस्", expanded=False):
        cols = st.columns(3) 
        col_idx = 0
        for mun, group in p_df.groupby('municipality'):
            with cols[col_idx % 3]:
                st.markdown(f"**🏛️ {mun}** ({len(group)} जना)")
                st.dataframe(group[['name', 'school']], hide_index=True, use_container_width=True)
            col_idx += 1
    
    st.divider()

    # ========================================================
    # MODE: TRACK (Running)
    # ========================================================       
    if script_mode == "Track":
        is_long_dist = any(x in evt_name for x in ["800", "1500", "3000"])
        comp_mode = st.radio("प्रतियोगिता मोड छान्नुहोस्:", ["🔥 हिट्स र फाइनल", "🏁 सिधै फाइनल"], index=1 if is_long_dist else 0, horizontal=True)
        is_direct_final = (comp_mode == "🏁 सिधै फाइनल")

        if is_long_dist:
            with st.expander("⏱️ लामो दूरीको ल्याप सिट डाउनलोड", expanded=True):
                lap_pdf = pdf_gen.generate_lap_sheet_pdf(current_event, p_df, CONFIG)
                st.download_button("📄 ल्याप सिट डाउनलोड गर्नुहोस्", lap_pdf, f"Laps_{evt_code}.pdf", "application/pdf", type="secondary")
            st.divider()

        if is_direct_final:
            t1, t3 = st.tabs(["📋 स्टार्ट लिस्ट (Start List)", "🏆 अन्तिम नतिजा (Final Result)"])
            t2 = None
        else:
            t1, t2, t3 = st.tabs(["🔥 हिट्स (Heats)", "✅ छनौट (Selection)", "🏁 फाइनल (Final)"])
        
        # --- TAB 1: HEATS ---
        with t1:
            st.markdown("### 🎲 स्टार्ट लिस्ट तयारी")
            unique_municipalities = p_df['municipality'].unique().tolist()
            
            c_seed, c_lane, c_btn = st.columns([2, 1, 1])
            seeded_muns = c_seed.multiselect("सिडेड पालिकाहरू (Priority):", unique_municipalities, help="राम्रा खेलाडीहरूलाई एउटै हिटमा पर्न नदिन छान्नुहोस्।")
            lanes = 8 if is_direct_final else c_lane.slider("लेन संख्या:", 4, 8, 6)
            
            st.write("") 
            if c_btn.button("🎲 जेनेरेट गर्नुहोस्", type="primary", use_container_width=True):
                h_df, cnt = generate_heats(p_df, len(p_df) if is_direct_final else lanes, seeded_muns)
                if is_direct_final: h_df['heat'] = 'FINAL'
                st.session_state.heats_data[evt_code] = h_df
                ls.save_fixture(evt_code, 'heats', h_df.to_dict('records'))
                st.success(f"✅ जम्मा {cnt} वटा हिट्स तयार भयो!")

            if evt_code in st.session_state.heats_data:
                st.divider()
                h_df = st.session_state.heats_data[evt_code]
                
                col_dl, _ = st.columns([1, 2])
                pdf_bytes = pdf_gen.generate_heat_sheet_pdf(current_event, h_df, CONFIG)
                col_dl.download_button("📄 अफिसियल सिट (PDF) डाउनलोड गर्नुहोस्", pdf_bytes, f"StartList_{evt_code}.pdf", "application/pdf")
                
                for h in sorted(h_df['heat'].unique()):
                    with st.container(border=True):
                        st.markdown(f"<h4 style='color:#1f77b4;'>{'🏁 FINAL MATCH' if h=='FINAL' else f'🔥 HEAT {h}'}</h4>", unsafe_allow_html=True)
                        st.dataframe(h_df[h_df['heat']==h].sort_values('lane')[['lane', 'name', 'municipality']], hide_index=True, use_container_width=True)

        # --- TAB 2: SELECTION ---
        if not is_direct_final and t2:
            with t2:
                if evt_code in st.session_state.heats_data:
                    h_df = st.session_state.heats_data[evt_code]
                    st.markdown("### ⏱️ हिट्सको समय प्रविष्टि र छनौट")
                    with st.form(f"sel_{evt_code}"):
                        qual_list = []
                        for h in sorted(h_df['heat'].unique()):
                            st.markdown(f"**🔥 Heat {h}**")
                            hc1, hc2, hc3, hc4 = st.columns([3, 2, 2, 1])
                            hc1.caption("खेलाडी"); hc2.caption("समय (Time)"); hc3.caption("स्थान (Rank)"); hc4.caption("छनौट (Q)")
                            
                            for _, r in h_df[h_df['heat']==h].iterrows():
                                c1, c2, c3, c4 = st.columns([3, 2, 2, 1])
                                c1.write(f"🏃 {r['name']} ({r.get('municipality','')})")
                                t_val = c2.text_input("Time", key=f"t_{r['id']}", label_visibility="collapsed", placeholder="mm:ss.ms")
                                r_val = c3.selectbox("Rank", ["-", "1st", "2nd", "3rd", "4th"], key=f"r_{r['id']}", label_visibility="collapsed")
                                if c4.checkbox("Q", key=f"q_{r['id']}", label_visibility="collapsed"):
                                    # 💡 We need municipality_id for results
                                    qual_list.append({'player_id': r['id'], 'mun_id': r['mun_id'], 'time': t_val})
                            st.divider()
                        
                        if st.form_submit_button("💾 छनौट सुरक्षित गर्नुहोस्", type="primary"):
                            conn = db.get_connection()
                            c = conn.cursor()
                            c.execute("DELETE FROM results WHERE event_code=%s AND medal='Qualified'", (evt_code,))
                            for q in qual_list:
                                import json
                                c.execute("""
                                    INSERT INTO results (event_code, municipality_id, player_id, position, score_details, medal) 
                                    VALUES (%s, %s, %s, 0, %s, 'Qualified')
                                """, (evt_code, q['mun_id'], q['player_id'], json.dumps({"time": q['time']})))
                            conn.commit()
                            c.close()
                            conn.close()
                            st.success("✅ फाइनलका लागि खेलाडीहरू छानिए!")

        # --- TAB 3: FINAL RESULT ---
        with t3:
            st.markdown("### 🏆 अन्तिम नतिजा प्रविष्टि")
            if not res.check_and_reset_results(evt_code):
                target_df = st.session_state.heats_data.get(evt_code, pd.DataFrame()) if is_direct_final else pd.DataFrame()
                
                if not is_direct_final:
                    conn = db.get_connection()
                    q = """
                        SELECT res.player_id as id, res.municipality_id as mun_id, p.name, m.name as municipality 
                        FROM results res 
                        JOIN players p ON res.player_id = p.id 
                        JOIN municipalities m ON res.municipality_id = m.id 
                        WHERE res.event_code = %s AND res.medal = 'Qualified'
                    """
                    target_df = pd.read_sql_query(q, conn, params=(evt_code,))
                    conn.close()

                if not target_df.empty:
                    if st.button("📄 फाइनल सिट डाउनलोड (PDF)", type="secondary"):
                        final_df = target_df.copy()
                        final_df['heat'] = "FINAL"
                        final_df['lane'] = range(1, len(final_df) + 1)
                        st.download_button("📥 डाउनलोड", pdf_gen.generate_heat_sheet_pdf(current_event, final_df, CONFIG), "Final.pdf")
                    
                    with st.form(f"final_{evt_code}"):
                        hc1, hc2, hc3 = st.columns([4, 2, 2])
                        hc1.caption("खेलाडी (Player)"); hc2.caption("समय (Time)"); hc3.caption("स्थान (Rank/Medal)")
                        
                        res_data = []
                        for _, r in target_df.iterrows():
                            c1, c2, c3 = st.columns([4, 2, 2])
                            c1.write(f"🏃 **{r['name']}** <br><span style='font-size:0.8em; color:gray;'>🏛️ {r.get('municipality','')}</span>", unsafe_allow_html=True)
                            ft = c2.text_input("Time", key=f"ft_{r['id']}", label_visibility="collapsed", placeholder="mm:ss.ms")
                            fr = c3.selectbox("Rank", ["-", "🥇 1st (Gold)", "🥈 2nd (Silver)", "🥉 3rd (Bronze)", "Participated"], key=f"fr_{r['id']}", label_visibility="collapsed")
                            
                            if fr != "-":
                                m = "Gold" if "1st" in fr else "Silver" if "2nd" in fr else "Bronze" if "3rd" in fr else "Participated"
                                rank = int(fr.split()[1][0]) if "1st" in fr or "2nd" in fr or "3rd" in fr else 4
                                res_data.append({'player_id': r['id'], 'mun_id': r['mun_id'], 'position': rank, 'time': ft, 'medal': m, 'name': r['name'], 'municipality': r.get('municipality','')})
                        
                        st.divider()
                        if st.form_submit_button("🏆 नतिजा सेभ गर्नुहोस्", type="primary"):
                            if not any(x['medal'] == 'Gold' for x in res_data):
                                st.error("⚠️ कुनै पनि खेलाडीलाई प्रथम (🥇 1st) स्थान तोकिएको छैन! कृपया नतिजा भर्नुहोस्।")
                            else:
                                conn = db.get_connection()
                                c = conn.cursor()
                                for x in res_data: 
                                    # 💡 PostgreSQL Logic: Municipality wins the medal
                                    import json
                                    c.execute("""
                                        INSERT INTO results (event_code, municipality_id, player_id, position, score_details, medal)
                                        VALUES (%s, %s, %s, %s, %s, %s)
                                    """, (evt_code, x['mun_id'], x['player_id'], x['position'], json.dumps({"time": x['time']}), x['medal']))
                                conn.commit()
                                c.close()
                                conn.close()
                                
                                st.success(f"✅ {len(res_data)} जनाको नतिजा सुरक्षित भयो!"); st.balloons()
                                
                                res_data.sort(key=lambda x: x['position'])
                                gold = next((x for x in res_data if x['position']==1), None)
                                silver = next((x for x in res_data if x['position']==2), None)
                                bronze = next((x for x in res_data if x['position']==3), None)
                                
                                res.trigger_live_tv(evt_name, evt_gender, gold, silver, bronze, "track")
                                res.display_operator_podium(gold, silver, bronze, 'time', 'name', 'municipality')

    # ========================================================
    # MODE: RELAY (Team Event - By Municipality)
    # ========================================================
    elif script_mode == "Relay":
        st.info("ℹ️ यो रिले इभेन्ट हो। यसमा सम्बन्धित पालिकाबाट छानिएका खेलाडीहरूको एउटा टिम बन्छ।")
        
        try:
            # 💡 गल्ती यहाँ थियो: participants_df को सट्टा p_df हुनुपर्छ!
            relay_grouped = p_df.groupby(['municipality', 'mun_id']).agg({
                'name': lambda x: ', '.join(x), 
                'id': 'first'
            }).reset_index()
            
            relay_df = pd.DataFrame({
                'id': relay_grouped['id'], 
                'mun_id': relay_grouped['mun_id'], 
                'name': relay_grouped['municipality'], 
                'players_list': relay_grouped['name'], 
                'municipality': relay_grouped['municipality']
            })
        except Exception as e:
            st.error(f"Grouping Error: {e}")
            st.stop()
            
        default_idx = 1 if len(relay_df) <= 8 else 0
        comp_mode = st.radio("प्रतियोगिता मोड छान्नुहोस्:", ["🔥 हिट्स र फाइनल", "🏁 सिधै फाइनल"], index=default_idx, horizontal=True)
        is_direct_final = (comp_mode == "🏁 सिधै फाइनल")
        
        if is_direct_final: 
            t1, t3 = st.tabs(["📋 स्टार्ट लिस्ट", "🏆 नतिजा"])
            t2 = None
        else: 
            t1, t2, t3 = st.tabs(["🔥 हिट्स", "✅ छनौट", "🏁 फाइनल"])
            
        # --------------------------------------------------------
        # १. स्टार्ट लिस्ट र PDF जेनेरेसन
        # --------------------------------------------------------
        with t1:
            st.markdown("### 🎲 रिले स्टार्ट लिस्ट तयारी")
            team_list = relay_df['name'].unique().tolist()
            
            c_seed, c_lane, c_btn = st.columns([2, 1, 1])
            seeded_teams = c_seed.multiselect("सिडेड पालिकाहरू (Priority):", team_list)
            lanes = 8 if is_direct_final else c_lane.slider("लेन संख्या:", 4, 8, 6)
            
            st.write("")
            if c_btn.button("🎲 तयार गर्नुहोस्", type="primary", use_container_width=True):
                h_df, cnt = generate_heats(relay_df, len(relay_df) if is_direct_final else lanes, seeded_teams)
                if is_direct_final: 
                    h_df['heat'] = 'FINAL'
                    
                if 'heats_data' not in st.session_state:
                    st.session_state.heats_data = {}
                    
                st.session_state.heats_data[evt_code] = h_df
                
                try:
                    ls.save_fixture(evt_code, 'heats', h_df.to_dict('records'))
                except Exception as e:
                    pass
                    
                st.success("✅ रिले स्टार्ट लिस्ट तयार भयो!")
                
            if 'heats_data' in st.session_state and evt_code in st.session_state.heats_data:
                st.divider()
                h_df = st.session_state.heats_data[evt_code]
                
                pdf_df = h_df.copy()
                pdf_df['players_list'] = pdf_df['id'].apply(lambda pid: relay_df[relay_df['id']==pid].iloc[0]['players_list'] if not relay_df[relay_df['id']==pid].empty else "")
                
                col_dl, _ = st.columns([1, 2])
                pdf_bytes = pdf_gen.generate_relay_heat_sheet_pdf(current_event, pdf_df, CONFIG)    
                col_dl.download_button("📄 रिले ट्र्याक सिट (PDF) डाउनलोड गर्नुहोस्", pdf_bytes, f"Relay_StartList_{evt_code}.pdf", "application/pdf")
                
                for h in sorted(h_df['heat'].unique()):
                    with st.container(border=True):
                        st.markdown(f"<h4 style='color:#1f77b4;'>{'🏁 FINAL MATCH' if h=='FINAL' else f'🔥 HEAT {h}'}</h4>", unsafe_allow_html=True)
                        disp = h_df[h_df['heat']==h].sort_values(by='lane')[['lane', 'name', 'id']]
                        
                        def get_runners(pid):
                            res = relay_df[relay_df['id']==pid]
                            return res.iloc[0]['players_list'] if not res.empty else ""
                            
                        disp['Runners'] = disp['id'].apply(get_runners)
                        st.dataframe(disp[['lane', 'name', 'Runners']].rename(columns={'name': 'पालिका (Municipality)'}), hide_index=True, use_container_width=True)

        # --------------------------------------------------------
        # २. हिट्स छनौट (यदि सिधै फाइनल होइन भने)
        # --------------------------------------------------------
        if not is_direct_final and t2:
            with t2:
                if 'heats_data' in st.session_state and evt_code in st.session_state.heats_data:
                    h_df = st.session_state.heats_data[evt_code]
                    st.markdown("### ⏱️ रिले हिट्स छनौट")
                    
                    with st.form(f"sel_relay_{evt_code}"):
                        qual_list = []
                        for h in sorted(h_df['heat'].unique()):
                            st.markdown(f"**🔥 Heat {h}**")
                            hc1, hc2, hc3, hc4 = st.columns([4, 2, 2, 1])
                            hc1.caption("टिम (Team)"); hc2.caption("समय"); hc3.caption("स्थान"); hc4.caption("Q")
                            
                            for _, r in h_df[h_df['heat']==h].iterrows():
                                c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
                                c1.write(f"🏛️ **{r['name']}**")
                                t_val = c2.text_input("Time", key=f"rt_{r['id']}", label_visibility="collapsed")
                                r_val = c3.selectbox("Rank", ["-", "1st", "2nd", "3rd", "4th"], key=f"rr_{r['id']}", label_visibility="collapsed")
                                if c4.checkbox("Q", key=f"rq_{r['id']}", label_visibility="collapsed"):
                                    qual_list.append({'mun_id': r['mun_id'], 'time': t_val})
                            st.divider()
                        
                        if st.form_submit_button("💾 छनौट सुरक्षित गर्नुहोस्", type="primary"):
                            conn = db.get_connection()
                            if conn:
                                try:
                                    c = conn.cursor()
                                    c.execute("DELETE FROM results WHERE event_code=%s AND medal='Qualified'", (evt_code,))
                                    for q in qual_list: 
                                        import json
                                        c.execute("INSERT INTO results (event_code, municipality_id, position, score_details, medal) VALUES (%s, %s, 0, %s, 'Qualified')", (evt_code, q['mun_id'], json.dumps({"time": q['time']})))                            
                                    conn.commit()
                                    st.success("✅ पालिकाहरू फाइनलका लागि छानिए!")
                                except Exception as e:
                                    st.error(f"DB Error: {e}")
                                finally:
                                    conn.close()

        # --------------------------------------------------------
        # ३. अन्तिम नतिजा र टिभी डिस्प्ले
        # --------------------------------------------------------
        with t3:
            st.markdown("### 🏆 रिले अन्तिम नतिजा")
            
            already_saved = False
            try:
                already_saved = res.check_and_reset_results(evt_code)
            except:
                pass
                
            if not already_saved:
                target_df = st.session_state.heats_data.get(evt_code, pd.DataFrame()) if is_direct_final else pd.DataFrame()
                
                if not is_direct_final:
                    conn = db.get_connection()
                    if conn:
                        try:
                            # हिट्सबाट छनौट भएका पालिकाहरू तान्ने
                            q = """
                                SELECT res.municipality_id as mun_id, m.name as name 
                                FROM results res 
                                JOIN municipalities m ON res.municipality_id = m.id 
                                WHERE res.event_code = %s AND res.medal = 'Qualified'
                            """
                            target_df = pd.read_sql_query(q, conn, params=(evt_code,))
                        except: pass
                        finally: conn.close()

                if not target_df.empty:
                    st.info("👇 **महत्त्वपूर्ण:** रिले दौडमा सम्बन्धित पालिकाका ४ जना खेलाडी अनिवार्य छान्नुहोस्।")
                    
                    # 💡 नयाँ थपिएको भाग: फाइनल ट्र्याक सिट (PDF) जेनेरेसन
                    with st.expander("📄 फाइनल ट्र्याक सिट (PDF) डाउनलोड", expanded=True):
                        final_pdf_df = target_df.copy()
                        final_pdf_df['heat'] = "FINAL"
                        final_pdf_df['lane'] = range(1, len(final_pdf_df) + 1) # १ देखि लेन असाइन गर्ने
                        final_pdf_df['municipality'] = final_pdf_df['name'] 
                        
                        # सम्बन्धित पालिकाको खेलाडीहरू तान्ने फङ्सन
                        def get_muni_players(m_name):
                            m_players = p_df[p_df['municipality'] == m_name]['name'].tolist()
                            return ", ".join(m_players)
                            
                        final_pdf_df['players_list'] = final_pdf_df['municipality'].apply(get_muni_players)
                        
                        col_fdl, _ = st.columns([1, 2])
                        # त्यही चेकबक्स वाला रिले फङ्सन बोलाउने
                        final_pdf_bytes = pdf_gen.generate_relay_heat_sheet_pdf(current_event, final_pdf_df, CONFIG)
                        col_fdl.download_button("📥 फाइनल रिले सिट डाउनलोड", final_pdf_bytes, f"Relay_Final_{evt_code}.pdf", "application/pdf", type="secondary")
                    
                    with st.form(f"final_relay_{evt_code}"):
                        res_data, val_errors = [], []
                        for _, r in target_df.iterrows():
                            muni_name = r['name']
                            mun_id = r['mun_id']
                            st.markdown(f"#### 🏛️ {muni_name}")
                            c1, c2, c3 = st.columns([4, 2, 2])
                            c1.caption("खेलाडी छान्नुहोस्"); c2.caption("समय"); c3.caption("स्थान (Medal)")
                            
                            # 💡 यहाँ पनि p_df हुनुपर्छ
                            muni_players = p_df[p_df['municipality'] == muni_name]
                            p_opts = {f"{row['name']}": row['id'] for _, row in muni_players.iterrows()}
                            
                            sel_names = c1.multiselect("४ खेलाडी:", options=list(p_opts.keys()), key=f"ms_{mun_id}", max_selections=4, label_visibility="collapsed")
                            ft = c2.text_input("Time", key=f"rft_{mun_id}", placeholder="mm:ss.ms", label_visibility="collapsed")
                            fr = c3.selectbox("Rank", ["-", "🥇 1st", "🥈 2nd", "🥉 3rd", "Participated"], key=f"rfr_{mun_id}", label_visibility="collapsed")
                            
                            if fr != "-":
                                m = "Gold" if "1st" in fr else "Silver" if "2nd" in fr else "Bronze" if "3rd" in fr else "Participated"
                                rank = int(fr.split()[1][0]) if "1st" in fr or "2nd" in fr or "3rd" in fr else 4
                                p_ids = [p_opts[n] for n in sel_names]
                                
                                if rank <= 3 and len(p_ids) != 4: 
                                    val_errors.append(f"❌ {muni_name} को लागि ४ जना खेलाडी छानिएको छैन।")
                                
                                res_data.append({
                                    'p_ids': p_ids, 'mun_id': mun_id, 'position': rank, 
                                    'time': ft, 'medal': m, 'municipality': muni_name, 
                                    'name': 'Relay Team', 'runner_names': sel_names
                                })
                            st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)
                            
                        if st.form_submit_button("🏆 नतिजा सेभ गर्नुहोस्", type="primary"):
                            if val_errors:
                                for err in val_errors: st.error(err)
                            elif not any(x['medal'] == 'Gold' for x in res_data):
                                st.error("⚠️ कुनै पनि टिमलाई प्रथम (🥇 1st) स्थान तोकिएको छैन!")
                            else:
                                conn = db.get_connection()
                                if conn:
                                    try:
                                        c = conn.cursor()
                                        for x in res_data:
                                            if x['p_ids']:
                                                for pid in x['p_ids']: 
                                                    import json
                                                    c.execute("""
                                                        INSERT INTO results (event_code, municipality_id, player_id, position, score_details, medal)
                                                        VALUES (%s, %s, %s, %s, %s, %s)
                                                    """, (evt_code, x['mun_id'], pid, x['position'], json.dumps({"time": x['time']}), x['medal']))
                                        conn.commit()
                                        st.success("✅ रिलेको नतिजा सुरक्षित भयो!"); st.balloons()
                                        
                                        res_data.sort(key=lambda x: x['position'])
                                        gold = next((x for x in res_data if x['position']==1), None)
                                        silver = next((x for x in res_data if x['position']==2), None)
                                        bronze = next((x for x in res_data if x['position']==3), None)
                                        
                                        try:
                                            res.trigger_live_tv(current_event['name'], current_event['gender'], gold, silver, bronze, "relay")
                                            res.display_operator_podium(gold, silver, bronze, 'time', 'name', 'municipality', is_relay=True)
                                        except:
                                            pass
                                    except Exception as e:
                                        st.error(f"DB Error: {e}")
                                    finally:
                                        conn.close()
    # ========================================================
    # MODE: FIELD & HIGH JUMP
    # ========================================================
    elif script_mode in ["Field", "HighJump"]:
        st.info("ℹ️ यो फिल्ड इभेन्ट हो। खेलाडीहरूको अटेम्प्ट स्कोर सिधै भर्नुहोस्।")
        
        if not p_df.empty:
            pdf_func = pdf_gen.generate_high_jump_scoresheet_pdf if script_mode == "HighJump" else pdf_gen.generate_field_scoresheet_pdf
            pdf_data = pdf_func(current_event, p_df, CONFIG)
            st.download_button("📄 स्कोर सिट डाउनलोड गर्नुहोस्", pdf_data, f"{script_mode}_{evt_code}.pdf", "application/pdf", type="secondary")
        st.divider()

        if p_df.empty:
            st.warning("कुनै खेलाडी भेटिएन।")
        else:
            st.markdown("### 🎯 स्कोरकार्ड प्रविष्टि")
            if not res.check_and_reset_results(evt_code):
                with st.form(f"{script_mode}_form_{evt_code}"):
                    if script_mode == "HighJump":
                        h1, h2, h3 = st.columns([3, 1.5, 1.5])
                        h1.caption("खेलाडी (Player)"); h2.caption("Best Height (m)"); h3.caption("Failures") 
                    
                    res_list = []
                    for _, row in p_df.iterrows():
                        if script_mode == "HighJump":
                            c1, c2, c3 = st.columns([3, 1.5, 1.5])
                            c1.write(f"**{row['name']}** <span style='font-size:0.8em; color:gray;'>📍 {row['municipality']}</span>", unsafe_allow_html=True)
                            best_val = c2.number_input("Height", min_value=0.00, max_value=3.00, value=0.00, step=0.01, key=f"hj_h_{row['id']}", label_visibility="collapsed")
                            fails = c3.number_input("Fails", min_value=0, max_value=50, value=0, step=1, key=f"hj_f_{row['id']}", label_visibility="collapsed")
                            res_list.append({'player_id': row['id'], 'mun_id': row['mun_id'], 'best': best_val, 'failures': fails, 'name': row['name'], 'municipality': row['municipality']})
                        else:
                            st.write(f"🏃 **{row['name']}** <span style='font-size:0.8em; color:gray;'>📍 {row['municipality']}</span>", unsafe_allow_html=True)
                            c1, c2, c3 = st.columns(3)
                            a1 = c1.number_input("Attempt 1", 0.00, 100.00, 0.00, step=0.01, key=f"a1_{row['id']}")
                            a2 = c2.number_input("Attempt 2", 0.00, 100.00, 0.00, step=0.01, key=f"a2_{row['id']}")
                            a3 = c3.number_input("Attempt 3", 0.00, 100.00, 0.00, step=0.01, key=f"a3_{row['id']}")
                            best_val = max(a1, a2, a3)
                            if best_val > 0: st.info(f"🏆 Best Score: **{best_val:.2f} m**")
                            res_list.append({'player_id': row['id'], 'mun_id': row['mun_id'], 'best': best_val, 'name': row['name'], 'municipality': row['municipality']})
                        st.markdown("<hr style='margin:10px 0;'>", unsafe_allow_html=True)

                    if st.form_submit_button("🏆 नतिजा सेभ गर्नुहोस्", type="primary"):
                        if script_mode == "HighJump": res_list.sort(key=lambda x: (-x['best'], x['failures']))
                        else: res_list.sort(key=lambda x: x['best'], reverse=True)
                        
                        if len(res_list) == 0 or res_list[0]['best'] <= 0:
                            st.error("⚠️ कुनै पनि खेलाडीको स्कोर भरिएको छैन!")
                        else:
                            saved_count = 0
                            conn = db.get_connection()
                            c = conn.cursor()
                            for idx, item in enumerate(res_list):
                                rank = idx + 1
                                
                                # 💡 यदि स्कोर ० छ भने उसले मेडल पाउँदैन, 'NM' (No Mark) हुन्छ
                                has_valid_score = (item['best'] > 0)
                                
                                # मेडलको लजिक: यदि भ्यालिड स्कोर छ र टप ३ मा पर्छ भने मात्र मेडल, नत्र 'Participated'
                                if rank == 1 and has_valid_score: medal = "Gold"
                                elif rank == 2 and has_valid_score: medal = "Silver"
                                elif rank == 3 and has_valid_score: medal = "Bronze"
                                else: medal = "Participated"
                                
                                import json
                                # 💡 ० स्कोर ल्याउनेलाई "NM" (No Mark) भनेर सेभ गर्ने
                                if script_mode == "HighJump":
                                    display_score = f"{item['best']:.2f}" if has_valid_score else "NM"
                                    score_data = json.dumps({"best_height": display_score, "failures": item.get('failures', 0)})
                                else:
                                    display_score = f"{item['best']:.2f}" if has_valid_score else "NM"
                                    score_data = json.dumps({"best_score": display_score})

                                # सबै जना (स्कोर भए पनि नभए पनि) डाटाबेसमा जाने भए
                                c.execute("""
                                    INSERT INTO results (event_code, municipality_id, player_id, position, score_details, medal)
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (evt_code, item['mun_id'], item['player_id'], rank, score_data, medal))
                                saved_count += 1
                            
                            conn.commit()
                            c.close()
                            conn.close()
                            
                            st.success(f"✅ {saved_count} जनाको नतिजा सुरक्षित भयो!"); st.balloons()

                            gold = res_list[0] if len(res_list) > 0 and res_list[0]['best'] > 0 else None
                            silver = res_list[1] if len(res_list) > 1 and res_list[1]['best'] > 0 else None
                            bronze = res_list[2] if len(res_list) > 2 and res_list[2]['best'] > 0 else None

                            res.trigger_live_tv(evt_name, evt_gender, gold, silver, bronze, "field")
                            res.display_operator_podium(gold, silver, bronze, 'best', 'name', 'municipality')

render_footer()