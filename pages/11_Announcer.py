import streamlit as st
import utils.live_state as ls
import database as db  # 💡 डाटाबेसबाट तान्न थपिएको
from config import render_header, render_footer

# ... (Security Check Code) ...

st.title("🎙️ उद्घोषक नियन्त्रण कक्ष (Announcer Panel)")

# 💡 अब यहाँ डेटाबेसबाट डाटा तानिन्छ
day_options = ["Day 1", "Day 2", "Day 3"]
selected_day = st.segmented_control("कुन दिनको तालिका हेर्ने?", day_options, default="Day 1")

# ls मा बनाएको फङ्सन प्रयोग गरेर डाटा तान्ने
db_schedule = ls.get_db_schedules(day_filter=selected_day)

c1, c2 = st.columns([1.2, 1])

with c1:
    st.markdown(f"### 📋 {selected_day} को कार्यतालिका")
    if not db_schedule:
        st.info("यो दिनको लागि कुनै तालिका प्रविष्ट गरिएको छैन।")
    else:
        for item in db_schedule:
            with st.container(border=True):
                col_txt, col_btn = st.columns([4, 1.2])
                # Database columns: schedule_time, title, description
                col_txt.markdown(f"**⏰ {item['schedule_time']} | {item['title']}**")
                col_txt.caption(item['description'])
                
                if col_btn.button("📺 Broadcast", key=f"db_btn_{item['id']}", use_container_width=True):
                    ls.set_announcement(item['title'], item['description'])
                    st.toast(f"✅ '{item['title']}' टिभीमा पठाइयो!")