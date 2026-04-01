# pages\10_Live_Display.py 
import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import time, base64, os, re
from datetime import datetime
from config import CONFIG
from streamlit_autorefresh import st_autorefresh


# ==========================================
# ⚙️ १. कन्फिगरेसन र अल्ट्रा-क्लिन CSS
# ==========================================
st.set_page_config(page_title="LIVE Scoreboard", page_icon="📺", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
        [data-testid="stSidebar"], [data-testid="stSidebarNav"] { display: none !important; width: 0px !important; }
        [data-testid="stHeader"] { display: none !important; height: 0px !important; min-height: 0px !important; }
        .block-container {
            padding-top: 0px !important;
            margin-top: -60px !important;
            padding-bottom: 0px !important;
            padding-left: 0px !important;
            padding-right: 0px !important;
            max-width: 100% !important;
        }
        html, body, [data-testid="stAppViewContainer"], .main {
            background: #0E1117;
            color: white;
            overflow: hidden;
            height: 100vh;
            margin: 0px !important;
            padding: 0px !important;
        }
        footer, #MainMenu {visibility: hidden; display: none !important;}
        
        /* 💡 हेडरको हाइट सकेसम्म घटाइएको छ (पातलो बनाइएको) */
        .header-box { text-align: center; background: linear-gradient(90deg, #0f172a, #1e3a8a, #0f172a); padding: 5px 15px; border-bottom: 3px solid #FFD700; margin-bottom: 5px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
        .ticker-wrap { position: fixed; bottom: 0; left: 0; width: 100%; background: #b91c1c; padding: 10px 0; font-size: 32px; font-weight: 900; z-index: 999; border-top: 3px solid #ffffff; box-shadow: 0 -5px 15px rgba(0,0,0,0.5); }
        .ticker-move { display: inline-block; white-space: nowrap; animation: ticker 30s linear infinite; }
        @keyframes ticker { 0% { transform: translateX(100vw); } 100% { transform: translateX(-100%); } }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 📡 २. डाटा प्रोसेसिङ
# ==========================================
#@st.cache_data(ttl=5)
def fetch_cached_data_v2(): 
    data = {'active_matches': [], 'tally': pd.DataFrame(), 'headlines': "", 'announcement': None, 'podium': None, 'match_result': None, 'active_call': None}
    
    # 💡 सुधार: यदि 'db_mode' सेसनमा छ भने त्यही लिने, नत्र सिधै db.get_connection()
    conn = db.get_connection() 
     
    if not conn:
        st.error("❌ डाटाबेस कनेक्सन हुन सकेन!")
        return data

    try:
        # 💡 महत्वपूर्ण: ls (live_state) फङ्सनहरूमा पनि 'conn' पास गर्नुपर्छ
        data['active_matches'] = ls.get_all_active_matches(conn) # यहाँ conn थप्नुहोस्
        
        q = """
            SELECT m.name as "पालिका", 
                   SUM(CASE WHEN r.medal='Gold' THEN 1 ELSE 0 END) as "Gold", 
                   SUM(CASE WHEN r.medal='Silver' THEN 1 ELSE 0 END) as "Silver", 
                   SUM(CASE WHEN r.medal='Bronze' THEN 1 ELSE 0 END) as "Bronze"
            FROM results r 
            LEFT JOIN players p ON r.player_id = p.id 
            LEFT JOIN teams t ON r.team_id = t.id 
            JOIN municipalities m ON m.id = COALESCE(r.municipality_id, p.municipality_id, t.municipality_id)
            WHERE r.medal IN ('Gold', 'Silver', 'Bronze') 
            GROUP BY m.name 
            ORDER BY "Gold" DESC, "Silver" DESC, "Bronze" DESC 
            LIMIT 10
        """
        data['tally'] = pd.read_sql_query(q, conn)
        data['headlines'] = ls.get_ticker_headlines(conn)
        data['announcement'] = ls.get_announcement(conn) # यहाँ conn थप्नुहोस्
        data['podium'] = ls.get_podium(conn) # यहाँ conn थप्नुहोस्
        data['active_call'] = ls.get_active_call(conn) # यहाँ conn थप्नुहोस्
    except Exception as e:
        print(f"📡 Live Display Error: {e}")
    finally:
        conn.close()
    return data

def play_once(file_name):
    conn = db.get_local_connection()
    try: curr_golds = pd.read_sql_query("SELECT COUNT(*) FROM results WHERE medal='Gold'", conn).iloc[0,0]
    except: curr_golds = 0
    finally: conn.close()
    if 'last_g' not in st.session_state: st.session_state.last_g = curr_golds
    if curr_golds > st.session_state.last_g:
        st.session_state.last_g = curr_golds
        path = os.path.join("sounds", file_name)
        if os.path.exists(path):
            with open(path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
                st.markdown(f'<audio autoplay><source src="data:audio/wav;base64,{b64}"></audio>', unsafe_allow_html=True)

# ==========================================
# 📺 ४. ड्यासबोर्ड रेन्डर
# ==========================================
refresh_count = st_autorefresh(interval=8000, key="live_ref")
d = fetch_cached_data_v2() 
play_once("cheer.wav")

# 📌 ४.१. सधैं माथि देखिने 'प्रोफेसनल हेडर' र तलको टिकर
st.markdown(f"""
<div class='header-box' style='display: flex; justify-content: space-between; align-items: center;'>
    <div style='text-align: left; line-height: 1.2; width: 25%; padding-left: 10px;'>
        <span style='font-size: 14px; color: #cbd5e1;'>आयोजक:</span><br>
        <b style='font-size: 16px; color: #FFD700;'>{CONFIG.get('ORGANIZER_NAME_NP', 'जिल्ला खेलकुद विकास समिति')}</b>
    </div>
    <div style='text-align: center; width: 50%;'>
        <h2 style='margin:0; color:white; text-shadow: 2px 2px 5px #000; font-size: 30px; font-weight: 900;'>🏆 {CONFIG['EVENT_TITLE_NP']}</h2>
    </div>
    <div style='text-align: right; line-height: 1.2; width: 25%; padding-right: 10px;'>
        <span style='font-size: 14px; color: #cbd5e1;'>{CONFIG.get('HOST_ROLE_NP', 'स्थानीय व्यवस्थापन')}:</span><br>
        <b style='font-size: 16px; color: #FFD700;'>{CONFIG.get('HOST_NAME_NP', 'स्थानीय तह')}</b>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<div class='ticker-wrap'><div class='ticker-move'>⚡ {d['headlines']}</div></div>", unsafe_allow_html=True)

col_main, col_gap, col_tally = st.columns([6.8, 0.2, 3])

col_main, col_gap, col_tally = st.columns([6.8, 0.2, 3])

# ------------------------------------------
# 📊 दायाँ भाग: स्थायी पदक तालिका (Top Aligned, Big Font, Total Row)
# ------------------------------------------
with col_tally:
    # 💡 जादु यहाँ छ: उचाइलाई calc(100vh - 190px) बनाइएको छ ताकि तल कुदिरहेको टिकरसँग नजुधोस्!
    tally_html = f"""
    <style>
        .tally-container {{ background: rgba(15, 23, 42, 0.85); border-radius: 10px; padding: 15px; border: 2px solid #334155; height: calc(100vh - 190px); overflow: hidden; box-sizing: border-box; margin-top: 5px; }}
        .tally-table {{ width: 100%; border-collapse: collapse; text-align: center; color: white; margin-top: 10px; }}
        .tally-table th {{ background: #1e293b; color: #FFD700; padding: 12px 5px; font-size: 20px; border-bottom: 3px solid #FFD700; }}
        .tally-table td {{ padding: 10px 5px; font-size: 20px; font-weight: bold; border-bottom: 1px solid #334155; }}
        .tally-table tr:nth-child(even) {{ background: rgba(255,255,255,0.03); }}
        .tally-table tr:nth-child(1) td {{ background: rgba(255, 215, 0, 0.15); color: #FFD700; font-size: 22px; }}
        .total-row td {{ background: #1e3a8a !important; color: white !important; font-size: 22px !important; border-top: 3px solid #FFD700 !important; border-bottom: none !important; padding: 12px 5px !important; }}
    </style>
    <div class='tally-container'>
        <h3 style='text-align:center; color:#FFD700; margin:0; font-size:26px; border-bottom:2px solid #334155; padding-bottom:10px; text-transform:uppercase;'>🥇 पदक तालिका</h3>
    """
    
    tally = d['tally'].copy()
    if not tally.empty:
        col_name = 'name' if 'name' in tally.columns else ('पालिका' if 'पालिका' in tally.columns else tally.columns[0])
        tally[col_name] = tally[col_name].str.replace('Rural Municipality|Municipality|गाउँपालिका|नगरपालिका', '', regex=True, case=False).str.replace(r'\(.*\)', '', regex=True).str.strip()
        
        tally_html += "<table class='tally-table'><tr><th style='text-align:left;'>पालिका</th><th>🥇</th><th>🥈</th><th>🥉</th></tr>"
        
        # सबै पालिकाहरूको लिस्ट प्रिन्ट गर्ने
        for i, row in tally.iterrows():
            tally_html += f"<tr><td style='text-align:left;'>{row[col_name]}</td><td style='color:#fde047;'>{row.get('Gold',0)}</td><td style='color:#cbd5e1;'>{row.get('Silver',0)}</td><td style='color:#fdba74;'>{row.get('Bronze',0)}</td></tr>"
            
        # 💡 जम्मा (Total) क्यालकुलेट गरेर पुछारमा थप्ने
        total_gold = tally['Gold'].sum() if 'Gold' in tally else 0
        total_silver = tally['Silver'].sum() if 'Silver' in tally else 0
        total_bronze = tally['Bronze'].sum() if 'Bronze' in tally else 0
        
        tally_html += f"<tr class='total-row'><td style='text-align:left;'>कुल जम्मा (Total)</td><td style='color:#fde047 !important;'>{total_gold}</td><td style='color:#cbd5e1 !important;'>{total_silver}</td><td style='color:#fdba74 !important;'>{total_bronze}</td></tr>"
        tally_html += "</table>"
    else:
        tally_html += "<p style='text-align:center; margin-top:20px; font-size: 20px;'>हालसम्म कुनै नतिजा अपडेट भएको छैन।</p>"
        
    tally_html += "</div>"
    st.markdown(tally_html, unsafe_allow_html=True)
    
    
# ------------------------------------------
# 🎬 बायाँ भाग: स्वचालित रोटेसन (Auto-Rotation Engine)
# ------------------------------------------
with col_main:
    # 💡 के-के कुरा एक्टिभ छन् भनेर लिस्ट बनाउने (Queue)
    active_views = []
    if d['announcement']: active_views.append('ANNOUNCEMENT')
    if d['active_call']: active_views.append('CALL')
    if d['podium']: active_views.append('PODIUM')
    if d['active_matches']: active_views.append('MATCHES')
    
    # यदि केही पनि छैन भने खाली समयको रोटेसन
    if len(active_views) == 0:
        active_views = ['IDLE_WELCOME', 'IDLE_SPONSOR']
        
    # 💡 जादु यहाँ छ: refresh_count को आधारमा पालैपालो देखाउने
    current_view = active_views[refresh_count % len(active_views)]

    # ==========================================
    # 🔊 १. अनस्टपएबल ब्याकग्राउन्ड अडियो (सबैभन्दा माथि, स्वतन्त्र)
    # ==========================================
    if d['active_call']:
        call_id = d['active_call'].get('timestamp', 'new_call')
        audio_path = os.path.join("sounds", "latest_call.mp3")
        
        if os.path.exists(audio_path):
            with open(audio_path, "rb") as f:
                audio_b64 = base64.b64encode(f.read()).decode()
            
            # अडियोलाई टिभीको मेन ब्राउजर (window.parent) मा पठाउने 
            js_code = f"""
            <script>
                var call_id = "{call_id}";
                // यदि यो नयाँ कल हो भने मात्र बजाउने
                if (window.parent.currentCallId !== call_id) {{
                    window.parent.currentCallId = call_id;
                    
                    // पुरानो बजिरहेको छ भने रोक्ने
                    if (window.parent.callAudio) {{
                        window.parent.callAudio.pause();
                    }}
                    
                    var aud = new Audio("data:audio/mp3;base64,{audio_b64}");
                    window.parent.callAudio = aud;
                    
                    var playCount = 0;
                    aud.onended = function() {{
                        playCount++;
                        // ठ्याक्कै ३ पटक बजाउने (बिचमा २ सेकेन्डको ग्याप राखेर)
                        if (playCount < 3) {{
                            setTimeout(function(){{ aud.play(); }}, 2000); 
                        }}
                    }};
                    aud.play().catch(e => console.log("Audio play blocked by browser:", e));
                }}
            </script>
            """
            import streamlit.components.v1 as components
            components.html(js_code, height=0, width=0)

    # ==========================================
    # 🎬 २. भिजुअल रोटेसन (if/elif को नटुट्ने सिक्वेन्स)
    # ==========================================
    if current_view == 'ANNOUNCEMENT':
        st.markdown(f"""
        <div style="background: linear-gradient(145deg, #f59e0b, #d97706); color: white; padding: 40px; text-align: center; border-radius: 15px; border: 5px solid white; box-shadow: 0 10px 25px rgba(0,0,0,0.5); margin-top: 50px;">
            <h1 style="margin:0; font-size:65px; font-weight:900; text-transform:uppercase; text-shadow: 2px 2px 4px rgba(0,0,0,0.4);">📢 {d['announcement']['title']}</h1>
            <h2 style="margin:20px 0 0 0; font-size:40px; font-weight:bold;">{d['announcement']['subtitle']}</h2>
        </div>
        """, unsafe_allow_html=True)
        
    elif current_view == 'CALL':
        call = d['active_call']
        st.markdown(f"""
        <div style="background-color: {call.get('color_code', '#dc3545')}; color: white; padding: 40px; text-align: center; border-radius: 15px; border: 5px solid white; box-shadow: 0 10px 25px rgba(0,0,0,0.5); margin-top: 50px;">
            <h1 style="margin:0; font-size:70px; font-weight:900; text-transform:uppercase; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);">📢 {call.get('call_type', 'CALL')}</h1>
            <h2 style="margin:15px 0 0 0; font-size:50px; font-weight:bold;">{call.get('event_name', '')} - {call.get('round_name', '')}</h2>
            <h3 style="margin:20px 0 0 0; font-size:30px; color: #f8fafc;">खेलाडीहरूलाई तुरुन्तै कल-रुममा आउन अनुरोध गरिन्छ!</h3>
        </div>
        """, unsafe_allow_html=True)
        # 💡 पुरानो अडियो बजाउने ट्याग यहाँबाट हटाइएको छ किनकि माथि JS ले बजाइसक्छ
        
    elif current_view == 'PODIUM':
        podium = d['podium']
        st.balloons()
        
        st.markdown(f"""
        <h3 style='text-align:center; color:#60a5fa; font-size:26px; margin-bottom:0; margin-top: 5px;'>🎉 नयाँ नतिजा / हार्दिक बधाई ! 🎉</h3>
        <h2 style='text-align:center; color:#FFD700; font-size:45px; text-shadow: 2px 2px 4px #000; margin-top: 5px; margin-bottom: 10px;'>🏆 {podium.get('event_name', 'विजयी खेलाडीहरू')} 🏆</h2>
        """, unsafe_allow_html=True)
        
        g, s, b = podium.get('gold') or {}, podium.get('silver') or {}, podium.get('bronze') or {}
        
        def clean_m(m_name):
            import re
            return re.sub(r'Rural Municipality|Municipality|गाउँपालिका|नगरपालिका|\(.*\)', '', str(m_name), flags=re.IGNORECASE).strip().upper()
            
        g_muni, s_muni, b_muni = clean_m(g.get('municipality', '')), clean_m(s.get('municipality', '')), clean_m(b.get('municipality', ''))
        
        st.markdown(f"""
        <style>
            .podium-wrapper {{ display: flex; flex-direction: column; justify-content: flex-end; margin-bottom: 75px; padding-top: 10px; }}
            .podium-container {{ display: flex; justify-content: center; align-items: flex-end; gap: 15px; padding: 0 10px; z-index: 10; }}
            .pod-box {{ border-radius: 15px 15px 0 0; text-align: center; padding: 15px 10px; box-shadow: 0 -10px 25px rgba(0,0,0,0.5); color: black; width: 32%; position: relative; display: flex; flex-direction: column; justify-content: flex-start; }}
            .pod-gold {{ background: linear-gradient(145deg, #FFF8DC, #FFD700); height: 270px; border: 4px solid #D4AF37; z-index: 3; }}
            .pod-silver {{ background: linear-gradient(145deg, #F8F9FA, #E2E8F0); height: 210px; border: 4px solid #CBD5E1; z-index: 2; }}
            .pod-bronze {{ background: linear-gradient(145deg, #FFF5EE, #CD7F32); height: 160px; border: 4px solid #A0522D; z-index: 1; }}
            .medal-icon {{ font-size: 60px; position: absolute; top: -35px; left: 50%; transform: translateX(-50%); text-shadow: 2px 2px 10px rgba(0,0,0,0.4); }}
            .p-name {{ font-size: 18px; font-weight: 900; margin-top: 30px; margin-bottom: 10px; line-height: 1.2; }}
            .p-muni {{ font-size: 18px; font-weight: 900; color: #1e293b; background: rgba(255,255,255,0.8); padding: 5px 10px; border-radius: 8px; border: 2px dashed #64748b; margin-top: auto; letter-spacing: 1px; }}
            .stage-base {{ width: 95%; height: 30px; background: linear-gradient(180deg, #475569, #0f172a); border-radius: 50% / 15px; border-top: 4px solid #94a3b8; box-shadow: 0 10px 30px rgba(0,0,0,0.9); margin: -5px auto 0 auto; z-index: 1; }}
            .honor-text {{ text-align: center; color: #94a3b8; font-size: 18px; margin-top: 10px; font-style: italic; letter-spacing: 2px; font-weight: bold; }}
        </style>        
        <div class="podium-wrapper">
            <div class="podium-container">
                <div class="pod-box pod-silver"><div class="medal-icon">🥈</div><div class="p-name">{s.get('name', '')}</div><div class="p-muni">🏛️ {s_muni}</div></div>
                <div class="pod-box pod-gold"><div class="medal-icon">🥇</div><div class="p-name" style="font-size:24px; color:#b45309;">{g.get('name', '')}</div><div class="p-muni" style="border-color:#b45309; color:#b45309;">🏛️ {g_muni}</div></div>
                <div class="pod-box pod-bronze"><div class="medal-icon">🥉</div><div class="p-name">{b.get('name', '')}</div><div class="p-muni">🏛️ {b_muni}</div></div>
            </div>
            <div class="stage-base"></div>
            <div class="honor-text">✨ उत्कृष्ट प्रदर्शनका लागि सम्पूर्ण खेलाडीहरूलाई उच्च सम्मान ! ✨</div>
        </div>
        """, unsafe_allow_html=True)
        
    elif current_view == 'MATCHES':
        st.markdown("<h3 style='text-align:center; color:#38bdf8; margin-top:10px;'>🔴 प्रत्यक्ष खेलहरू (Live Action)</h3>", unsafe_allow_html=True)
        matches = d['active_matches'][:4]
        cols = st.columns(2)
        for i, m in enumerate(matches):
            with cols[i % 2]:
                st.markdown(f"""
                <div style='background:linear-gradient(145deg, #1e293b, #0f172a); padding:20px; border-radius:15px; border-top:5px solid #3b82f6; text-align:center; margin-bottom:15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'>
                    <h4 style='color:#94a3b8; margin:0 0 10px 0;'>{m['event_name']}</h4>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div style='width:40%; font-size:20px; font-weight:bold; color:#f8fafc;'>{m['player1'].split('|')[0]}</div>
                        <div style='width:20%; font-size:40px; font-weight:900; color:#FFD700;'>{m['score_a']} - {m['score_b']}</div>
                        <div style='width:40%; font-size:20px; font-weight:bold; color:#f8fafc;'>{m['player2'].split('|')[0]}</div>
                    </div>
                    <p style='color:#64748b; font-size:14px; margin-top:10px;'>{m.get('status', 'Playing...')}</p>
                </div>
                """, unsafe_allow_html=True)
                
    elif current_view == 'IDLE_WELCOME':
        st.markdown(f"""
        <div style='height: 70vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;'>
            <h1 style='font-size: 90px; margin: 0;'>🏟️</h1>
            <h1 style='font-size: 50px; color: #FFD700; text-shadow: 2px 2px 10px rgba(0,0,0,0.8); margin: 20px 0;'>{CONFIG['EVENT_TITLE_NP']}</h1>
            <h2 style='font-size: 30px; color: #cbd5e1; font-weight: 300;'>आयोजक: {CONFIG.get('ORGANIZER_NAME_NP', 'जिल्ला खेलकुद विकास समिति')}</h2>
            <div style='margin-top: 40px; padding: 10px 30px; background: rgba(59, 130, 246, 0.2); border-radius: 50px; border: 1px solid #3b82f6;'>
                <h3 style='color: #60a5fa; margin: 0; font-size: 20px;'>🔴 प्रत्यक्ष प्रसारण भइरहेको छ...</h3>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    elif current_view == 'IDLE_SPONSOR':
        st.markdown("""
        <div style='height: 70vh; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center;'>
            <div style='background:rgba(15, 23, 42, 0.6); width: 80%; padding: 40px; border: 2px dashed #475569; border-radius: 20px; box-shadow: inset 0 0 20px rgba(0,0,0,0.5);'>
                <h1 style='font-size: 70px; margin: 0; color: #94a3b8;'>📸</h1>
                <h2 style='font-size: 35px; color: #e2e8f0; font-weight: bold; margin: 20px 0;'>प्रायोजक तथा सूचना बोर्ड</h2>
                <p style='font-size: 20px; color: #94a3b8;'>(यहाँ प्रतियोगिताका आकर्षक तस्बिर वा प्रायोजकको भिडियो राख्न सकिन्छ)</p>
            </div>
        </div>
        """, unsafe_allow_html=True)