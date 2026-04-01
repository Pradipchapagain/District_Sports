import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
import time  # 💡 यो यहाँ हुनुपर्छ
from config import CONFIG

# ==========================================
# ⚙️ ०. मास्टर फङ्सन (सधैं सबैभन्दा माथि राख्ने)
# ==========================================
def force_clear_state(key_name):
    """डाटाबेसबाट सिधै रेकर्ड डिलिट गर्ने 'मास्टर' फङ्सन (PostgreSQL को लागि)"""
    conn = db.get_connection()
    if conn:
        try:
            c = conn.cursor()
            if key_name == "ALL":
                # तालिका (Schedule) बाहेक अरु सबै उडाउने
                c.execute("DELETE FROM system_states WHERE state_key NOT IN ('master_schedule') AND state_key NOT LIKE 'fixture_%'")
            else:
                # सही टेबल 'system_states', सही कोलम 'state_key', र सही पारामिटर '%s'
                c.execute("DELETE FROM system_states WHERE state_key = %s", (key_name,))
            conn.commit()
        except Exception as e:
            st.error(f"DB Error: {e}")
        finally:
            conn.close()
# ==========================================
# 🛑 १. CONFIGURATION FROM CENTRAL CONFIG
# ==========================================
EXPIRE_TIMES = CONFIG.get('EXPIRE_TIMES', {})

# ==========================================
# ⚙️ १. कन्फिगरेसन र सेक्युरिटी
# ==========================================
st.set_page_config(page_title="Announcer HQ", page_icon="🎙️", layout="wide")

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.switch_page("Home.py")

# ==========================================
# 📺 २. लाइभ टिभी मनिटरिङ (Control Room View)
# ==========================================
st.title("🎙️ उद्घोषक तथा टिभी नियन्त्रण प्यानल")

# --- पहिलो रो: ३ वटा साना टिभी (Volleyball, Kabaddi, Martial Arts) ---
st.markdown("#### 📡 खेल स्कोरबोर्ड मनिटर (Small Screens)")
m_col1, m_col2, m_col3 = st.columns(3)

# 💡 फङ्सन: एउटै फ्रेममा पूरै स्क्रिन अटाउन (No Scroll)
def mini_tv(url, height=250, scale=0.5):
    # scale ले ठूलो पेजलाई सानो विन्डोमा फिट गर्छ
    st.markdown(f"""
        <div style="width:100%; height:{height}px; overflow:hidden; border:2px solid #334155; border-radius:10px;">
            <iframe src="{url}?nav=false" 
                style="width:{int(100/scale)}%; height:{int(height/scale)}px; border:none; 
                transform: scale({scale}); transform-origin: 0 0;">
            </iframe>
        </div>
    """, unsafe_allow_html=True)

with m_col1:
    st.caption("🏐 Volleyball TV")
    # 💡 फाइल 22_VB_Scoreboard.py को लिङ्क
    mini_tv("http://localhost:8501/VB_Scoreboard", height=200, scale=0.4)

with m_col2:
    st.caption("🤼 Kabaddi TV")
    # 💡 फाइल 23_KB_Scoreboard.py को लिङ्क
    mini_tv("http://localhost:8501/KB_Scoreboard", height=200, scale=0.4)

with m_col3:
    st.caption("🥋 Martial Arts TV")
    # 💡 फाइल 21_Mat_Scoreboard.py को लिङ्क
    mini_tv("http://localhost:8501/Mat_Scoreboard", height=200, scale=0.4)

st.write("")

# --- दोस्रो रो: मुख्य लाइभ डिस्प्ले (अलि ठूलो तर साइडमा खुम्चिएको) ---
st.markdown("#### 🖥️ मुख्य लाइभ बोर्ड (Main Live Display)")
c_left, c_main, c_right = st.columns([0.5, 2, 0.5]) # दायाँ-बायाँ खाली राखेर बिचमा खुम्च्याएको

with c_main:
    # मुख्य टिभी अलि ठूलो, scale ०.७५ ताकि प्रस्ट देखियोस्
    mini_tv("http://localhost:8501/Live_Display", height=400, scale=0.7)
    st.markdown("<p style='text-align:center; font-size:12px; color:gray;'>💡 यो विन्डोमा ठ्याक्कै त्यही देखिन्छ जुन रङ्गशालाको मुख्य LED मा छ।</p>", unsafe_allow_html=True)

st.divider()

# ==========================================
# 📑 ३. कन्ट्रोल ट्याबहरू (उद्घाटन, सेड्युल, रिमोट)
# ==========================================
tab_ceremony, tab_schedule, tab_custom, tab_tv_remote = st.tabs([
    "🎊 उद्घाटन/समापन", "📅 खेल तालिका", "✍️ कस्टम सूचना", "🎮 टिभी रिमोट"
])


# ------------------------------------------
# १. उद्घाटन/समापन सत्र (Ceremony)
# ------------------------------------------
with tab_ceremony:
    st.subheader("📋 औपचारिक कार्यक्रम कार्यतालिका")
    
    # डाटाबेसबाट 'Ceremony' टाइपको सेड्युल तान्ने
    db_ceremony = ls.get_db_schedules(day_filter="Ceremony")
    
    if db_ceremony.empty:
        st.warning("डाटाबेसमा कुनै उद्घाटन तालिका भेटिएन। कृपया सेड्युल म्यानेजरबाट 'Ceremony' विधामा डाटा भर्नुहोस्।")
        # ब्याकअपको लागि पुरानो हार्डकोडेड लिस्ट देखाउन सकिन्छ, तर डाटाबेस नै राम्रो।
    else:
        for index, item in db_ceremony.iterrows():
            with st.container(border=True):
                c_txt, c_btn = st.columns([4, 1.2])
                c_txt.markdown(f"**⏰ {item['schedule_time']} | {item['title']}**")
                c_txt.caption(item['description'])
                if c_btn.button("📺 Broadcast", key=f"cer_{index}", width="stretch"):
                    ls.set_announcement(f"अहिले भइरहेको कार्यक्रम: {item['title']}", item['description'])
                    st.toast(f"✅ '{item['title']}' टिभीमा पठाइयो!")

# ------------------------------------------
# २. खेल तालिका (Match Schedules)
# ------------------------------------------
with tab_schedule:
    st.subheader("📅 दैनिक खेल तालिका प्रसारण")
    col_sel, col_act = st.columns([1, 2])
    
    day_opt = ["Day 1", "Day 2", "Day 3", "Final Day"]
    selected_day = col_sel.selectbox("दिन छान्नुहोस्:", day_opt)
    
    db_sch = ls.get_db_schedules(day_filter=selected_day)
    
    if db_sch.empty:
        st.info(f"{selected_day} को लागि कुनै खेल तालिका उपलब्ध छैन।")
    else:
        st.dataframe(db_sch[['schedule_time', 'title', 'description']], width="stretch", hide_index=True)
        
        c_show, c_hide = st.columns(2)
        if c_show.button(f"📺 {selected_day} को कार्ड टिभीमा देखाउनुहोस्", type="primary", width="stretch"):
            ls.trigger_schedule_display(selected_day)
            st.success(f"✅ {selected_day} को कार्डहरू टिभीमा कुदिरहेका छन्!")
            
        if c_hide.button("❌ तालिका हटाउनुहोस्", width="stretch"):
            ls.clear_schedule_display()
            st.toast("तालिका हटाइयो।")

# ------------------------------------------
# ३. कस्टम सूचना (Custom Message)
# ------------------------------------------
with tab_custom:
    st.subheader("✍️ तत्काल सूचना पठाउनुहोस्")
    c_title = st.text_input("मुख्य शीर्षक (Title):", placeholder="उदा: खाना खाने समयको जानकारी")
    c_desc = st.text_area("विवरण (Sub-title):", placeholder="थप जानकारी यहाँ लेख्नुहोस्...")
    
    col_c1, col_c2 = st.columns(2)
    if col_c1.button("📢 सूचना पठाउनुहोस्", type="primary", width="stretch"):
        if c_title:
            ls.set_announcement(c_title, c_desc)
            st.success("✅ सूचना टिभीमा पठाइयो!")
        else:
            st.error("शीर्षक अनिवार्य छ!")
            
    if col_c2.button("🧹 सूचना सफा गर्नुहोस्", width="stretch"):
        ls.clear_announcement()
        st.toast("सूचना हटाइयो।")

# --- ४. टिभी रिमोट ट्याब (Compact Buttons) ---
with tab_tv_remote:
    st.caption("⚙️ मास्टर रिमोट स्विचहरू (Direct DB Control):")
    r_col1, r_col2, r_col3, r_col4, r_col5 = st.columns(5)
    
    with r_col1:
        if st.button("🏆 Clear Podium", width="stretch", type="primary"):
            # 💡 यहाँ 'podium' को सट्टा 'podium_data' हुनुपर्छ
            force_clear_state('podium_data')
            st.success("✅ पोडियम हटाइयो!")
            time.sleep(0.5)
            st.rerun()
            
    with r_col2:
        if st.button("📢 Clear Call", width="stretch"):
            force_clear_state('active_call') 
            st.success("✅ कल म्यासेज हटाइयो!")
            time.sleep(0.5)
            st.rerun()
            
    with r_col3:
        if st.button("💬 Clear Msg", width="stretch"):
            force_clear_state('announcement')
            st.success("✅ सूचना हटाइयो!")
            time.sleep(0.5)
            st.rerun()
            
    with r_col4:
        if st.button("📊 Clear Match", width="stretch"):
            force_clear_state('match_result') 
            st.success("✅ म्याच नतिजा हटाइयो!")
            time.sleep(0.5)
            st.rerun()
            
    with r_col5:
        if st.button("🔄 Full Reset", width="stretch"):
            force_clear_state('ALL')
            st.success("✅ टिभी पूर्ण रूपमा रिसेट भयो!")
            time.sleep(0.5)
            st.rerun()