# pages\3_Bulk_Upload.py
import streamlit as st
import pandas as pd
import database as db
import utils.excel_handler as eh 
from datetime import datetime

from config import render_header, render_footer

st.set_page_config(page_title="Bulk Upload (Excel)", page_icon="📥", layout="wide")

# ------------------------------------------
render_header() 
# ------------------------------------------

# ==========================================
# 🔒 SECURITY CHECK & AUTO-REDIRECT
# ==========================================
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.switch_page("Home.py") 
# ------------------------------------------

st.title("📥 बल्क दर्ता (Excel Upload)")

municipalities = db.get_municipalities()
if municipalities.empty:
    st.error("⚠️ कुनै पनि पालिका भेटिएन।")
    st.stop()

# --- MUNICIPALITY CONTEXT ---
if st.session_state.get('user_role') == 'admin':
    sel_mun_name = st.selectbox("पालिका छान्नुहोस् (Municipality):", municipalities['name'].unique())
    sel_mun_id = int(municipalities[municipalities['name'] == sel_mun_name]['id'].iloc[0])
else:
    sel_mun_id = int(st.session_state.get('municipality_id', 0))
    sel_mun_name = municipalities[municipalities['id'] == sel_mun_id]['name'].iloc[0]
    st.info(f"तपाईं **{sel_mun_name}** को लागि काम गर्दै हुनुहुन्छ।")

st.markdown("---")
tab_download, tab_import = st.tabs(["📥 १. एक्सेल फारम डाउनलोड गर्ने", "🚀 २. भरेको फारम अपलोड गर्ने"])

# ==========================================
# TAB 1: GENERATE EXCEL
# ==========================================
with tab_download:
    st.subheader("📥 एडभान्स्ड मास्टर टेम्प्लेट (पूर्ण विवरण सहित)")
    st.markdown("""
    विशेषताहरू:
    1. **School Details:** विद्यालयको नाम र अन्य विवरण राख्ने।
    2. **Entry Sheets:** ४ तहको हेडर र भ्यालिडेसन (नियम चेक गर्ने)।
    3. **Summary:** केटा/केटीको एकीकृत रिपोर्ट।
    """)
    
    if st.button("🚀 एक्सेल फारम तयार गर्नुहोस्", type="primary"):
        conn = db.get_connection()
        all_events = pd.read_sql("SELECT * FROM events", conn)
        conn.close()
        
        if all_events.empty:
            st.error("इभेन्टहरू भेटिएनन्।")
        else:
            with st.spinner("एक्सेल फाइल बन्दैछ..."):
                excel_buffer = eh.generate_master_excel(all_events, sel_mun_name)
                
                st.download_button(
                    label="📥 नयाँ एक्सेल फारम डाउनलोड (Complete)",
                    data=excel_buffer.getvalue(),
                    file_name=f"Master_Entry_{sel_mun_name.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ==========================================
# TAB 2: IMPORT FILLED DATA
# ==========================================
if 'upload_key' not in st.session_state:
    st.session_state.upload_key = 0
if 'upload_success_msg' not in st.session_state:
    st.session_state.upload_success_msg = None

with tab_import:
    st.header("🚀 भरेको फारम अपलोड गर्नुहोस्")
    st.info("पालिका वा विद्यालयले पठाएको एक्सेल फाइल यहाँ अपलोड गर्नुहोस्।")
    
    if st.session_state.upload_success_msg:
        st.success(st.session_state.upload_success_msg)
        st.balloons()
        st.session_state.upload_success_msg = None 
    
    conn = db.get_connection()
    mun_df = pd.read_sql_query("SELECT id, name FROM municipalities ORDER BY name", conn)
    conn.close()
    
    mun_dict = {row['name']: row['id'] for _, row in mun_df.iterrows()}
    mun_options = ["-- छान्नुहोस् --"] + list(mun_dict.keys())
    
    # User role अनुसार पालिका लक गर्ने या ड्रपडाउन दिने
    default_idx = 0
    if st.session_state.get('user_role') != 'admin' and sel_mun_name in mun_options:
        default_idx = mun_options.index(sel_mun_name)
        
    sel_upload_mun = st.selectbox(
        "कुन पालिकाको डाटा अपलोड गर्ने हो? छान्नुहोस्: 🔴", 
        mun_options, 
        index=default_idx,
        key="upload_mun_select"
    )
    
    uploaded_file = st.file_uploader(
        "एक्सेल फाइल यहाँ तान्नुहोस् (.xlsx)", 
        type=['xlsx', 'xls'], 
        key=f"bulk_upload_{st.session_state.upload_key}"
    )
    
    if uploaded_file is not None:
        try:
            xls = pd.ExcelFile(uploaded_file)
            sheet_names = xls.sheet_names
            
            st.success(f"📂 फाइल सफलतापूर्वक लोड भयो! (जम्मा सिटहरू: {len(sheet_names)})")
            with st.expander("फाइलमा भएका सिटहरू हेर्नुहोस् (Preview Sheets)"):
                st.write("**भेटिएका खेलका सिटहरू:**")
                st.write(", ".join(sheet_names))
                st.caption("नोट: सिस्टमले माथिका सिटहरूमा भएको डाटा स्वतः पढेर खेलाडी दर्ता गर्नेछ।")
                
        except Exception as e:
            st.error(f"⚠️ फाइल पढ्न सकिएन। कृपया सही ढाँचाको एक्सेल फाइल हाल्नुहोला।")

        st.divider()

        if st.button("🚀 डाटा इम्पोर्ट सुरु गर्नुहोस्", type="primary"):
            if sel_upload_mun == "-- छान्नुहोस् --":
                st.error("❌ कृपया पहिले माथिबाट 'पालिका' छान्नुहोस्!")
            else:
                target_mun_id = int(mun_dict[sel_upload_mun])
                
                with st.spinner("डाटाबेस अपडेट हुँदैछ... कृपया पर्खनुहोस्।"):
                    success, msg = db.import_school_data(uploaded_file, target_mun_id)
                    
                    if success:
                        st.session_state.upload_key += 1
                        st.session_state.upload_success_msg = f"✅ {sel_upload_mun} को डाटा सफलतापूर्वक इम्पोर्ट भयो!"
                        st.rerun()
                    else:
                        st.error(f"❌ त्रुटि: {msg}")

render_footer()