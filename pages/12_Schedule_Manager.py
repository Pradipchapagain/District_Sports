import streamlit as st
import pandas as pd
import database as db
import utils.live_state as ls
from config import render_header, render_footer

# ==========================================
# ⚙️ PAGE CONFIG & SECURITY
# ==========================================
st.set_page_config(page_title="Schedule Manager", page_icon="📅", layout="wide")
render_header()

if 'logged_in' not in st.session_state or st.session_state.user_role != 'admin':
    st.error("🔒 यो पेज चलाउन एडमिन लगइन आवश्यक छ।")
    st.stop()

st.title("📅 खेल तालिका व्यवस्थापन (Schedule Manager)")
st.caption("प्रतियोगिताको दैनिक कार्यतालिका बनाउने, नयाँ सामग्री सिर्जना गर्ने र क्रम मिलाउने प्यानल।")
st.divider()

# ==========================================
# १. नयाँ कार्यतालिका/सामग्री सिर्जना (Create Content)
# ==========================================
with st.expander("➕ नयाँ कार्यक्रम वा सूचना थप्नुहोस् (Create New Entry)", expanded=False):
    # 'Quick Fill' को लागि Session State प्रयोग
    if "form_title" not in st.session_state: st.session_state.form_title = ""
    if "form_desc" not in st.session_state: st.session_state.form_desc = ""

    col_form, col_prev = st.columns([2, 1])
    
    with col_form:
        with st.form("add_schedule_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([1, 1, 1])
            day = c1.selectbox("दिन (Day):", ["Day 1", "Day 2", "Day 3", "Final Day"])
            time_val = c2.text_input("समय (Time):", placeholder="e.g. 10:30 AM")
            order = c3.number_input("क्रम (Order):", min_value=1, step=1, value=1)
            
            title = st.text_input("शीर्षक (Title):", value=st.session_state.form_title, placeholder="नयाँ कार्यक्रम वा सूचनाको शीर्षक...")
            desc = st.text_area("विवरण (Description):", value=st.session_state.form_desc, placeholder="विस्तृत जानकारी यहाँ लेख्नुहोस्...")
            
            # खेलहरूसँग लिंक (Optional)
            event_df = db.get_events()
            event_list = ["None"] + event_df['code'].tolist()
            evt_code = st.selectbox("सम्बन्धित खेल (Link to Event):", event_list)
            
            if st.form_submit_button("💾 डाटाबेसमा सुरक्षित गर्नुहोस्"):
                if title and time_val:
                    conn = db.get_connection()
                    c = conn.cursor()
                    try:
                        c.execute("""
                            INSERT INTO schedules (day_name, schedule_time, title, description, event_code, schedule_order)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (day, time_val, title, desc, None if evt_code=="None" else evt_code, order))
                        conn.commit()
                        st.session_state.form_title = "" # रिसेट
                        st.session_state.form_desc = ""
                        st.success("✅ नयाँ सामग्री तालिकामा सुरक्षित भयो!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        c.close(); conn.close()
                else:
                    st.warning("कृपया शीर्षक र समय अनिवार्य भर्नुहोस्।")

    with col_prev:
        st.markdown("##### 👁️ प्रिभ्यु (Preview)")
        if title:
            st.info(f"**{title}**\n\n{desc}")
        else:
            st.caption("तपाईंले टाइप गरेको कुरा यहाँ देखिनेछ।")
        
        st.markdown("---")
        st.caption("🚀 **छिटो भर्न टेम्प्लेट छान्नुहोस्:**")
        if st.button("अतिथि स्वागत टेम्प्लेट", use_container_width=True):
            st.session_state.form_title = "हार्दिक स्वागतम्"
            st.session_state.form_desc = "प्रमुख अतिथि तथा विशिष्ट अतिथि महानुभावहरूमा हार्दिक स्वागत गर्दछौं।"
            st.rerun()

# ==========================================
# २. तालिका प्रदर्शन र प्रत्यक्ष सम्पादन (Edit Table)
# ==========================================
st.subheader("📋 हालको कार्यतालिका (Master Schedule)")

conn = db.get_connection()
# 💡 PostgreSQL: सबै सेड्युल तान्ने
df_sch = pd.read_sql_query("SELECT * FROM schedules ORDER BY day_name, schedule_order ASC", conn)
conn.close()

if df_sch.empty:
    st.info("अहिलेसम्म कुनै तालिका बनाइएको छैन। माथिको फारम प्रयोग गरी नयाँ सामग्री सिर्जना गर्नुहोस्।")
else:
    # फिल्टरिङ
    days = ["Day 1", "Day 2", "Day 3", "Final Day"]
    available_days = [d for d in days if d in df_sch['day_name'].unique()]
    sel_day = st.segmented_control("दिन फिल्टर गर्नुहोस्:", available_days if available_days else days, default=available_days[0] if available_days else "Day 1")
    
    filtered_df = df_sch[df_sch['day_name'] == sel_day]
    
    # स्मार्ट सम्पादन (Data Editor)
    edited_df = st.data_editor(
        filtered_df,
        column_config={
            "id": None, 
            "day_name": "Day",
            "schedule_order": st.column_config.NumberColumn("Order", width="small"),
            "schedule_time": "Time",
            "title": "Program/Match Title",
            "description": "Details",
            "is_completed": st.column_config.CheckboxColumn("Done?"),
            "event_code": None
        },
        disabled=["id"],
        use_container_width=True,
        hide_index=True,
        key="main_sch_editor"
    )

    c_edit_1, c_edit_2 = st.columns([1, 4])
    
    if c_edit_1.button("💾 परिवर्तनहरू सुरक्षित गर्नुहोस्", type="primary", use_container_width=True):
        conn = db.get_connection()
        c = conn.cursor()
        try:
            for _, row in edited_df.iterrows():
                c.execute("""
                    UPDATE schedules 
                    SET schedule_time=%s, title=%s, description=%s, schedule_order=%s, is_completed=%s
                    WHERE id=%s
                """, (row['schedule_time'], row['title'], row['description'], row['schedule_order'], 1 if row['is_completed'] else 0, row['id']))
            conn.commit()
            st.toast("✅ तालिका सफलतापूर्वक अपडेट भयो!")
            st.rerun()
        except Exception as e:
            st.error(f"Update Error: {e}")
            conn.rollback()
        finally:
            c.close(); conn.close()

    # डिलिट फिचर
    with st.popover("🗑️ आईटम मेटाउनुहोस्"):
        st.write("डिलिट गर्नको लागि आईटमको ID लेख्नुहोस्:")
        del_id = st.number_input("ID:", min_value=1, step=1, key="del_sch_id")
        if st.button("🔥 Confirm Delete", type="primary", use_container_width=True):
            conn = db.get_connection()
            c = conn.cursor()
            c.execute("DELETE FROM schedules WHERE id = %s", (del_id,))
            conn.commit(); c.close(); conn.close()
            st.success(f"ID #{del_id} मेटाइयो।")
            st.rerun()

render_footer()