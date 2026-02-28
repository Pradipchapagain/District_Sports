import streamlit as st
import database as db
from config import CONFIG
from streamlit_autorefresh import st_autorefresh
import psycopg2.extras

st.set_page_config(page_title="Judge Tablet - ESS", page_icon="🥋", layout="centered")

JUDGE_PINS = {"जज १ (Judge 1)": "1111", "जज २ (Judge 2)": "2222", "जज ३ (Judge 3)": "3333", "जज ४ (Judge 4)": "4444", "जज ५ (Judge 5)": "5555"}
JUDGE_COLS = {"जज १ (Judge 1)": "j1_vote", "जज २ (Judge 2)": "j2_vote", "जज ३ (Judge 3)": "j3_vote", "जज ४ (Judge 4)": "j4_vote", "जज ५ (Judge 5)": "j5_vote"}

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    .stApp { background: radial-gradient(circle at top, #1e293b 0%, #0f172a 100%); font-family: 'Inter', sans-serif; color: #f8fafc; }
    .master-header { text-align: center; background: rgba(255, 255, 255, 0.03); backdrop-filter: blur(12px); padding: 30px 20px; border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.08); box-shadow: 0 15px 35px rgba(0,0,0,0.4); margin-bottom: 25px; }
    .event-title { font-size: 26px; font-weight: 800; color: #fbbf24; margin: 0; text-transform: uppercase; }
    .match-badge { background: #fbbf24; color: #0f172a; padding: 6px 16px; border-radius: 8px; font-weight: 800; display: inline-block; margin-top: 15px; font-size: 14px; }
    .tatami-container { background: #000; padding: 10px; border-radius: 15px; border: 1px solid #334155; margin-bottom: 30px; }
    .tatami-mat { display: flex; border-radius: 10px; overflow: hidden; }
    .side { flex: 1; padding: 30px 10px; text-align: center; }
    .side.aka { background: #991b1b; border-right: 2px solid rgba(255,255,255,0.1); }
    .side.ao { background: #1e40af; }
    .player-name { font-size: 26px; font-weight: 800; color: #fff; margin-bottom: 4px; }
    .player-muni { font-size: 15px; color: rgba(255,255,255,0.8); font-weight: 600; }
    .belt { margin-top: 15px; font-size: 13px; font-weight: bold; padding: 6px 16px; border-radius: 6px; background: rgba(0,0,0,0.4); color: white; display: inline-block; }
    
    /* 📱 ट्याब्लेटका लागि बटनहरू अझ ठूला बनाइएका छन् */
    .stButton button { height: 160px !important; border-radius: 20px !important; font-size: 40px !important; font-weight: 800 !important; border: 4px solid rgba(255,255,255,0.2) !important; }
    div[data-testid="column"]:nth-child(1) button { background: #dc2626 !important; color: white !important; box-shadow: 0 10px 20px rgba(220, 38, 38, 0.4) !important; }
    div[data-testid="column"]:nth-child(2) button { background: #2563eb !important; color: white !important; box-shadow: 0 10px 20px rgba(37, 99, 235, 0.4) !important; }
    
    button[kind="secondary"] { height: 50px !important; font-size: 18px !important; background: #334155 !important; }
    .vote-success { text-align: center; background: rgba(16, 185, 129, 0.2); border: 2px solid #10b981; color: #34d399; padding: 20px; border-radius: 12px; font-size: 22px; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

def get_live_match():
    """PostgreSQL बाट ताजा म्याच विवरण तान्ने"""
    try:
        conn = db.get_connection()
        c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # 💡 नोट: database.py मा 'updated_at' कोलम हुनुपर्छ
        c.execute("SELECT * FROM live_match ORDER BY id DESC LIMIT 1")
        row = c.fetchone()
        c.close(); conn.close()
        return row
    except: return None

# स्टेट म्यानेजमेन्ट
if 'judge_logged_in' not in st.session_state:
    st.session_state.judge_logged_in = False
    st.session_state.judge_name = None
if 'hidden_bout' not in st.session_state:
    st.session_state.hidden_bout = None

# ==========================================
# 🔐 STEP 1: लगइन प्यानल
# ==========================================
if not st.session_state.judge_logged_in:
    st.markdown(f"<div class='master-header'><div class='event-title'>🏆 {CONFIG.get('EVENT_TITLE_NP', 'Tournament')}</div></div>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align:center; color:#fbbf24; margin-bottom:20px;'>⚖️ निर्णायक (Judge) लगइन</h3>", unsafe_allow_html=True)
    with st.container(border=True):
        j_name = st.selectbox("आफ्नो नाम छान्नुहोस्", list(JUDGE_PINS.keys()), index=None, placeholder="Choose Judge Number")
        pin_in = st.text_input("PIN कोड प्रविष्ट गर्नुहोस्", type="password", max_chars=4)
        
        if st.button("✅ प्रणालीमा प्रवेश गर्नुहोस्", type="primary", use_container_width=True):
            if j_name and JUDGE_PINS.get(j_name) == pin_in:
                st.session_state.judge_logged_in = True
                st.session_state.judge_name = j_name
                st.rerun()
            else: st.error("❌ पिन वा नाम मिलेन!")
    st.stop()

# ==========================================
# 🟢 STEP 2: जज ड्यासबोर्ड (Main Logic)
# ==========================================
live_data = get_live_match()

# यदि यो बाउट जजले 'लुकाइसकेको' छ भने (Next बटन थिचेर)
if live_data and live_data['bout_id'] == st.session_state.hidden_bout:
    live_data = None

# अटो-रिफ्रेस कतिबेला गर्ने?
needs_refresh = False
if not live_data:
    needs_refresh = True
else:
    my_col = JUDGE_COLS[st.session_state.judge_name]
    my_vote = live_data[my_col]
    # यदि भोटिङ बन्द छ वा मैले भोट दिइसकेको छु भने नयाँ म्याचको लागि रिफ्रेस भइरहने
    if not live_data['voting_open'] or my_vote is not None:
        needs_refresh = True

if needs_refresh:
    st_autorefresh(interval=3000, key="judge_sync")

# ------------------------------------------
# UI: वेटिङ वा भोटिङ
# ------------------------------------------
if not live_data:
    st.markdown(f"<div class='master-header'><div class='event-title'>🏆 {CONFIG.get('EVENT_TITLE_NP', 'Tournament')}</div></div>", unsafe_allow_html=True)
    st.markdown("<div style='text-align:center; padding:80px 20px; background:rgba(255,255,255,0.02); border:2px dashed #334155; border-radius:20px;'><h2 style='color:#94a3b8;'>⏳ नयाँ बाउटको प्रतीक्षा गर्दै...</h2><p style='color:#64748b;'>मञ्चबाट अपरेटरले भोटिङ नखुलाएसम्म यो स्क्रिन आफैँ रिफ्रेस भइरहनेछ।</p></div>", unsafe_allow_html=True)
    if st.button("🚪 लगआउट", use_container_width=True):
        st.session_state.judge_logged_in = False; st.rerun()
    st.stop()

# म्याच विवरण (Top Card)
st.markdown(f"""
<div class="master-header">
    <div class="event-title">🏆 {live_data['bout_id']}</div>
    <div><span class="match-badge">{st.session_state.judge_name} प्यानल</span></div>
</div>
""", unsafe_allow_html=True)

# प्लेयर कार्ड
st.markdown(f"""
<div class="tatami-container">
    <div class="tatami-mat">
        <div class="side aka"><div class="player-name">{live_data['player1'] if live_data['player1'] else 'AKA'}</div><div class="belt">🔴 AKA</div></div>
        <div class="side ao"><div class="player-name">{live_data['player2'] if live_data['player2'] else 'AO'}</div><div class="belt">🔵 AO</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

# भोटिङ स्थिति
my_col = JUDGE_COLS[st.session_state.judge_name]
my_vote = live_data[my_col]

if not live_data['voting_open']:
    st.warning("⚠️ भोटिङ अहिले बन्द छ। खेलाडीको प्रदर्शन सकिएपछि मात्र बटनहरू खुल्नेछन्।")
elif my_vote:
    st.markdown(f"<div class='vote-success'>✅ तपाईंको भोट (<b>{my_vote}</b>) सुरक्षित भयो।</div>", unsafe_allow_html=True)
    st.caption("<p style='text-align:center; margin-top:10px;'>अब स्क्रिनमा अन्तिम नतिजाको प्रतीक्षा गर्नुहोस्...</p>", unsafe_allow_html=True)
    if st.button("🔄 अर्को म्याचको लागि तयार हुनुहोस्", use_container_width=True):
        st.session_state.hidden_bout = live_data['bout_id']; st.rerun()
else:
    # 🔴 ठूला भोटिङ बटनहरू
    st.markdown("<h3 style='text-align:center;'>आफ्नो निर्णय दिनुहोस्:</h3>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔴\nAKA", key="btn_aka", use_container_width=True):
            conn = db.get_connection()
            c = conn.cursor()
            # 💡 PostgreSQL: %s र bout_id अनिवार्य प्रयोग गरिएको
            c.execute(f"UPDATE live_match SET {my_col} = %s WHERE bout_id = %s", ('AKA', live_data['bout_id']))
            conn.commit(); c.close(); conn.close()
            st.rerun()
    with c2:
        if st.button("🔵\nAO", key="btn_ao", use_container_width=True):
            conn = db.get_connection()
            c = conn.cursor()
            c.execute(f"UPDATE live_match SET {my_col} = %s WHERE bout_id = %s", ('AO', live_data['bout_id']))
            conn.commit(); c.close(); conn.close()
            st.rerun()

st.write("---")
if st.button("🚪 लगआउट (Exit Panel)", use_container_width=True, kind="secondary"):
    st.session_state.judge_logged_in = False
    st.session_state.judge_name = None
    st.session_state.hidden_bout = None
    st.rerun()