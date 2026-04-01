import streamlit as st
import pandas as pd
import database as db
from config import render_header, render_footer
import utils.ma_bracket as ma_bracket
import utils.ma_combat as ma_combat
import utils.ma_combat as ma_forms


# ==========================================
# 📦 नयाँ मोड्युलर फाइलहरू (साझा टाइसिट र ६ वटा गेम प्यानल)
# ==========================================
import utils.ma_bracket as ma_bracket

try:
    import utils.ma_kata as ma_kata
    import utils.ma_kumite as ma_kumite
    import utils.ma_poomsae as ma_poomsae
    import utils.ma_kyorugi as ma_kyorugi
    import utils.ma_taolu as ma_taolu
    import utils.ma_sanda as ma_sanda
except ImportError as e:
    st.error(f"⚠️ मोड्युल लोड हुन सकेन: {e}। कृपया utils फोल्डरमा ६ वटै फाइलहरू (ma_kata.py, ma_kumite.py आदि) बनाउनुहोस्।")

# ==========================================
# 1. कन्फिगरेसन र सुरक्षा
# ==========================================
st.set_page_config(page_title="🥋 मार्शल आर्ट्स", page_icon="🥋", layout="wide")
render_header()

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.switch_page("Home.py")

# ==========================================
# 2. कस्टम सीएसएस (बटनलाई टाइल बनाउन र बल्ने इफेक्ट राख्न)
# ==========================================
st.markdown("""
<style>
    /* बटनहरूको उचाइ र फन्ट मिलाउने */
    button[kind="primary"], button[kind="secondary"] {
        height: 60px !important; 
        border-radius: 10px !important;
        font-size: 16px !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
        margin-top: 5px !important;
    }
    
    /* नछानिएको (Secondary) टाइलको स्टाइल */
    button[kind="secondary"] {
        background-color: #1e293b !important;
        border: 2px solid #334155 !important;
        color: #cbd5e1 !important;
    }
    button[kind="secondary"]:hover {
        border-color: #3b82f6 !important;
        background-color: #27354f !important;
        transform: translateY(-2px);
    }
    
    /* छानिएको (Primary) टाइलको स्टाइल - 🌟 बल्ने इफेक्ट 🌟 */
    button[kind="primary"] {
        background: linear-gradient(135deg, #1d4ed8, #3b82f6) !important;
        border: 2px solid #60a5fa !important;
        box-shadow: 0 0 20px rgba(96, 165, 250, 0.7) !important;
        color: #ffffff !important;
        transform: scale(1.03);
        text-shadow: 1px 1px 5px rgba(0,0,0,0.5);
    }
    
    /* भर्टिकल बार (Divider) */
    .vertical-divider {
        border-left: 3px solid #334155;
        height: 100%;
        min-height: 200px;
        margin: 0 auto;
        width: 3px;
        border-radius: 5px;
    }
    
    /* हेडर टेक्स्ट स्टाइल */
    .grid-header {
        text-align: center;
        font-size: 18px;
        font-weight: bold;
        color: #f1c40f;
        margin-bottom: 5px;
    }
    .row-header {
        display: flex;
        align-items: center;
        height: 70px;
        font-size: 16px;
        font-weight: bold;
        color: #94a3b8;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. मुख्य शीर्षक
# ==========================================
st.title("🥋 मार्शल आर्ट्स (Martial Arts)")
st.markdown("---")

# ==========================================
# 4. डाटाबेसबाट डाइनामिक खेल विधा तान्ने
# ==========================================
@st.cache_data(ttl=60)
def get_dynamic_disciplines():
    conn = db.get_connection()
    # 💡 PostgreSQL Syntax
    query = "SELECT DISTINCT sub_category, event_group FROM events WHERE category='Martial Arts' AND sub_category IS NOT NULL AND event_group IS NOT NULL"
    df = pd.read_sql_query(query, conn)
    conn.close()
    
    disciplines = {}
    form_keywords = ['Kata', 'Poomsae', 'Taolu', 'Form']
    
    for _, row in df.iterrows():
        game = row['sub_category']
        grp = row['event_group']
        
        m_type = "Combat"
        for kw in form_keywords:
            if kw.lower() in grp.lower():
                m_type = "Forms"
                break
                
        disp_key = f"{game}_{grp}" 
        disciplines[disp_key] = {"game": game, "group": grp, "type": m_type}
        
    return disciplines

def get_discipline_icon(grp_name):
    icons = {"Kata": "🥋", "Kumite": "⚔️", "Poomsae": "🧘", "Kyorugi": "🥊", "Taolu": "🎋", "Sanda": "🤼"}
    for key, icon in icons.items():
        if key.lower() in grp_name.lower(): return icon
    return "🥋"

DISCIPLINES = get_dynamic_disciplines()

if not DISCIPLINES:
    st.warning("डाटाबेसमा मार्सल आर्ट्सका कुनै पनि इभेन्टहरू भेटिएनन्।")
    st.stop()

# ==========================================
# 5. स्मार्ट ग्रिड UI (Row/Col Headers + Vertical Bar + Gender)
# ==========================================
if 'ma_discipline' not in st.session_state: st.session_state.ma_discipline = None
if 'ma_gender' not in st.session_state: st.session_state.ma_gender = None

custom_game_order = {"Karate": 1, "Taekwondo": 2, "Wushu": 3}
games = sorted(list(set([d['game'] for d in DISCIPLINES.values()])), key=lambda x: custom_game_order.get(x, 99))
types = ["Forms", "Combat"]
type_labels = {"Forms": "🧘 प्रदर्शन (Forms)", "Combat": "🤼 प्रतिस्पर्धा (Combat)"}

col_main, col_div, col_gen = st.columns([7, 0.2, 2.5])

# ------------------- Main Grid (विधा छान्ने) -------------------
with col_main:
    grid_cols_ratio = [1.8] + [2] * len(games)
    
    head_cols = st.columns(grid_cols_ratio)
    head_cols[0].write("")
    for i, g in enumerate(games):
        head_cols[i+1].markdown(f"<div class='grid-header'>{g}</div>", unsafe_allow_html=True)
        
    for t in types:
        r_cols = st.columns(grid_cols_ratio)
        r_cols[0].markdown(f"<div class='row-header'>{type_labels[t]}</div>", unsafe_allow_html=True)
        
        for i, g in enumerate(games):
            match_key, match_disp = None, None
            for k, v in DISCIPLINES.items():
                if v['game'] == g and v['type'] == t:
                    match_key, match_disp = k, v
                    break
            
            with r_cols[i+1]:
                if match_disp:
                    icon = get_discipline_icon(match_disp['group'])
                    label = f"{icon} {match_disp['group']}"
                    is_sel = (st.session_state.ma_discipline == match_key)
                    btn_type = "primary" if is_sel else "secondary"
                    
                    if st.button(label, key=f"btn_{match_key}", type=btn_type, width="stretch"):
                        st.session_state.ma_discipline = match_key
                        st.session_state.ma_gender = None 
                        st.rerun()
                else:
                    st.markdown("<div style='height:60px; display:flex; align-items:center; justify-content:center; color:#475569;'>-</div>", unsafe_allow_html=True)

# ------------------- Vertical Divider -------------------
with col_div:
    st.markdown("<div class='vertical-divider'></div>", unsafe_allow_html=True)

# ------------------- Gender Selection -------------------
with col_gen:
    st.markdown("<div class='grid-header'>लिङ्ग (Gender)</div>", unsafe_allow_html=True)
    available_genders = []
    
    if st.session_state.ma_discipline in DISCIPLINES:
        d_info = DISCIPLINES[st.session_state.ma_discipline]
        conn = db.get_connection()
        # 💡 PostgreSQL Syntax
        g_df = pd.read_sql_query(
            "SELECT DISTINCT gender FROM events WHERE category='Martial Arts' AND sub_category=%s AND event_group=%s",
            conn, params=(d_info['game'], d_info['group'])
        )
        conn.close()
        available_genders = g_df['gender'].tolist()
    elif st.session_state.ma_discipline:
        st.session_state.ma_discipline = None 
        
    if not available_genders: available_genders = ["Boys", "Girls"]
        
    for gen in available_genders:
        gen_icon = "👨" if "boy" in gen.lower() or "male" in gen.lower() else "👩"
        label = f"{gen_icon} {gen}"
        is_sel = (st.session_state.ma_gender == gen)
        btn_type = "primary" if is_sel else "secondary"
        disabled = st.session_state.ma_discipline is None
        
        if st.button(label, key=f"btn_gen_{gen}", type=btn_type, width="stretch", disabled=disabled):
            st.session_state.ma_gender = gen
            st.rerun()

st.markdown("---")

# ==========================================
# 6. इभेन्ट छान्ने र खेलाडी डेटा तान्ने
# ==========================================
if st.session_state.ma_discipline in DISCIPLINES and st.session_state.ma_gender:
    disp_key = st.session_state.ma_discipline
    game = DISCIPLINES[disp_key]["game"]
    grp = DISCIPLINES[disp_key]["group"]
    mode = DISCIPLINES[disp_key]["type"]
    gender = st.session_state.ma_gender
    
    st.info(f"**इभेन्ट समूह:** {game} {grp} ({gender}) - **{mode} Mode**")
    
    conn = db.get_connection()
    # 💡 PostgreSQL Syntax
    events_df = pd.read_sql_query(
        "SELECT * FROM events WHERE category='Martial Arts' AND sub_category=%s AND event_group=%s AND gender=%s",
        conn, params=(game, grp, gender)
    )
    conn.close()
    
    if events_df.empty:
        st.warning("यस विधा र लिङ्गको लागि कुनै तौल समूह (Weight Category) भेटिएन।")
    else:
        event_options = {row['name']: row for _, row in events_df.iterrows()}
        event_name = st.selectbox("इभेण्टको नाम (Weight Category/Event)", list(event_options.keys()), key="event_selector")
        current_event = event_options[event_name]
        evt_code = current_event['code']
        
        def get_players(event_code):
            conn = db.get_connection()
            # 💡 PostgreSQL: Added 'm.id as mun_id' so we can link players to municipalities for medals
            query = """
                SELECT p.id, p.name as "Player_Name", m.name as "Municipality", m.id as "mun_id", p.iemis_id
                FROM registrations r
                JOIN players p ON r.player_id = p.id
                JOIN municipalities m ON p.municipality_id = m.id
                WHERE r.event_code = %s
                ORDER BY m.name, p.name
            """
            df = pd.read_sql_query(query, conn, params=(event_code,))
            conn.close()
            return df
        
        players_df = get_players(evt_code)
        
        if players_df.empty:
            st.error("यस इभेन्टमा कुनै खेलाडी दर्ता भएका छैनन्।")
        else:
            st.success(f"**{len(players_df)}** जना खेलाडी फेला परे।")
            
            # ==========================================
            # 🎯 7. Routing to Specific Scoring Panels
            # ==========================================
            
            if "Kata" in grp or "Poomsae" in grp or "Taolu" in grp:
                ma_bracket.run_tournament(evt_code, current_event, players_df, ma_forms.render_panel)
            elif "Kumite" in grp or "Kyorugi" in grp or "Sanda" in grp:
                ma_bracket.run_tournament(evt_code, current_event, players_df, ma_combat.render_panel)
            elif "Poomsae" in grp:
                ma_bracket.run_tournament(evt_code, current_event, players_df, ma_poomsae.render_panel)
            elif "Kyorugi" in grp:
                ma_bracket.run_tournament(evt_code, current_event, players_df, ma_kyorugi.render_panel)
            elif "Taolu" in grp:
                ma_bracket.run_tournament(evt_code, current_event, players_df, ma_taolu.render_panel)
            elif "Sanda" in grp:
                ma_bracket.run_tournament(evt_code, current_event, players_df, ma_sanda.render_panel)
            else:
                st.warning(f"यस विधा ({game} - {grp}) को लागि स्कोरिङ प्यानल तयार गरिएको छैन।")

elif st.session_state.ma_discipline:
    st.warning("👆 कृपया माथि दायाँपट्टिबाट लिङ्ग (Gender) छान्नुहोस्।")

# ==========================================
# 8. फुटर
# ==========================================
render_footer()