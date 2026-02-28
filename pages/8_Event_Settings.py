import streamlit as st
import database as db
import os
import pandas as pd
from datetime import datetime
from io import BytesIO
import shutil
import zipfile
import time

from config import render_header, render_footer

try:
    import psutil
except ImportError:
    psutil = None

# ==========================================
# 🔒 SECURITY CHECK (ADMIN ONLY)
# ==========================================
st.set_page_config(page_title="System Settings", page_icon="⚙️", layout="wide")

# ------------------------------------------
# हेडर देखाउने
# ------------------------------------------
render_header() # 👈 यो लाइनले सुन्दर ब्यानर बनाउँछ
# ------------------------------------------

if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("🔒 कृपया प्रणाली चलाउन पहिले मुख्य पेज (Main Page) मा गएर लगइन गर्नुहोस्।")
    st.stop()

if st.session_state.user_role != 'admin':
    st.error("🚫 तपाईंलाई यो पेज चलाउने अनुमति छैन। यो एडमिनको लागि मात्र हो।")
    st.stop()
# ------------------------------------------

# ==========================================
# ०. सुरुवाती सेटअप (Folder Creation)
# ==========================================
BACKUP_DIR = "backups"
for folder in [BACKUP_DIR, "reports", "logs"]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ==========================================
# 🏠 UI LAYOUT
# ==========================================
st.title("⚙️ प्रणाली व्यवस्थापन (System Settings)")
st.caption("डाटाबेस ब्याकअप, डाटा रिसेट र एक्सेल रिपोर्ट डाउनलोड गर्ने एडमिन प्यानल।")
st.divider()

# ==========================================
# २. ट्याब संरचना
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "🗑️ डाटा रिसेट (Reset & Clean)", 
    "🗄️ डाटाबेस र ब्याकअप", 
    "📥 निर्यात (Export)",
    "ℹ️ प्रणाली जानकारी"
])

# ==========================================
# सहायक कार्यहरू (Helper Functions - PostgreSQL)
# ==========================================
# 💡 PostgreSQL को लागि database.py कै get_connection प्रयोग गर्ने
def get_all_municipalities():
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT id, name FROM municipalities ORDER BY name", conn)
    conn.close()
    return df

def get_all_events():
    conn = db.get_connection()
    df = pd.read_sql_query("SELECT code, name FROM events ORDER BY name", conn)
    conn.close()
    return df

# ==========================================
# TAB 1: डाटा रिसेट (RESET & CLEAN)
# ==========================================
with tab1:
    st.subheader("🗑️ डाटा रिसेट र सरसफाई")
    st.warning("⚠️ सावधानी: यहाँ गरिने कार्यहरू स्थायी (Permanent) हुनेछन्। कृपया पहिले ब्याकअप लिनुहोला।")

    c_reset_1, c_reset_2 = st.columns(2)

    # --- SECTION A: GAME/EVENT RESET ---
    with c_reset_1:
        with st.container(border=True):
            st.markdown("### 🏟️ खेल नतिजा (Results) रिसेट")
            st.info("यसले खेलको 'नतिजा' र 'म्याच' मात्र मेटाउँछ। खेलाडी दर्ता रहिरहन्छ।")
            
            event_df = get_all_events() 
            event_opts = {"सबै खेलहरू (All Events)": "ALL"}
            for _, r in event_df.iterrows():
                event_opts[f"{r['name']} ({r['code']})"] = r['code']
            
            sel_event_label = st.selectbox("कुन खेलको नतिजा रिसेट गर्ने?", list(event_opts.keys()))
            sel_event_code = event_opts[sel_event_label]
            
            with st.expander(f"⚠️ '{sel_event_label}' रिसेट गर्नुहोस्", expanded=False):
                confirm_game = st.checkbox("हो, म नतिजा मेटाउन चाहन्छु।", key="chk_game_reset")
                if st.button("🔥 नतिजा र सेटिङ मेटाउनुहोस्", type="primary", disabled=not confirm_game):
                    conn = db.get_connection() 
                    c = conn.cursor()
                    try:
                        if sel_event_code == "ALL":
                            c.execute("DELETE FROM results")
                            c.execute("DELETE FROM matches")
                            msg = "सबै खेलको नतिजा र म्याचहरू रिसेट भयो।"
                            
                            if 'heats_data' in st.session_state:
                                st.session_state.heats_data = {}
                        else:
                            # 💡 PostgreSQL को लागि %s प्रयोग गरियो
                            c.execute("DELETE FROM results WHERE event_code = %s", (sel_event_code,))
                            c.execute("DELETE FROM matches WHERE event_code = %s", (sel_event_code,))
                            msg = f"'{sel_event_label}' को नतिजा रिसेट भयो।"
                            
                            if 'heats_data' in st.session_state and sel_event_code in st.session_state.heats_data:
                                del st.session_state.heats_data[sel_event_code]
                        
                        conn.commit()
                        st.success(f"✅ {msg}")
                        
                        import utils.live_state as ls
                        ls.clear_live_state() 
                        
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                        conn.rollback()
                    finally:
                        c.close(); conn.close()

    # --- SECTION B: PARTICIPANT RESET ---
    with c_reset_2:
        with st.container(border=True):
            st.markdown("### 👥 खेलाडी विवरण (Players) रिसेट")
            st.info("यसले पालिकाका सम्पूर्ण खेलाडी दर्ता मेटाउँछ।")
            
            mun_df = get_all_municipalities()
            mun_opts = {"सबै पालिका (All Municipalities)": "ALL"}
            for _, r in mun_df.iterrows():
                mun_opts[f"{r['name']}"] = r['id']
            
            sel_mun_label = st.selectbox("कुन पालिकाका खेलाडी हटाउने?", list(mun_opts.keys()))
            sel_mun_id = mun_opts[sel_mun_label]
            
            with st.expander(f"⚠️ '{sel_mun_label}' का खेलाडी हटाउनुहोस्", expanded=False):
                st.write("पुष्टि गर्नको लागि तल **DELETE** टाइप गर्नुहोस्:")
                user_conf = st.text_input("Confirmation", placeholder="DELETE", key="txt_del_part")
                
                if st.button("🔥 खेलाडी डाटा मेटाउनुहोस्", type="primary", disabled=(user_conf != "DELETE")):
                    conn = db.get_connection()
                    c = conn.cursor()
                    try:
                        c.execute("SELECT COUNT(*) FROM results")
                        res_count = c.fetchone()[0]
                        
                        if res_count > 0:
                            st.error("⛔ **अस्वीकृत:** नतिजा सिस्टममा बाँकी छ। पहिले नतिजा रिसेट गर्नुहोस्।")
                        else:
                            if sel_mun_id == "ALL":
                                c.execute("DELETE FROM registrations")
                                c.execute("DELETE FROM players")
                                c.execute("DELETE FROM teams")
                                msg = "सबै पालिकाका खेलाडीहरू हटाइयो।"
                            else:
                                # 💡 PostgreSQL मा %s
                                c.execute("""
                                    DELETE FROM registrations WHERE player_id IN 
                                    (SELECT id FROM players WHERE municipality_id = %s)
                                """, (sel_mun_id,))
                                c.execute("DELETE FROM players WHERE municipality_id = %s", (sel_mun_id,))
                                c.execute("DELETE FROM teams WHERE municipality_id = %s", (sel_mun_id,))
                                msg = f"'{sel_mun_label}' का खेलाडीहरू हटाइयो।"
                            
                            conn.commit()
                            st.success(f"✅ {msg}")
                            time.sleep(1)
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
                        conn.rollback()
                    finally:
                        c.close(); conn.close()

# ==========================================
# TAB 2: डाटाबेस र ब्याकअप (Cloud Mode)
# ==========================================
with tab2:
    st.subheader("🗄️ डाटाबेस तथ्याङ्क (PostgreSQL Cloud)")
    
    conn = db.get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT COUNT(*) FROM players")
        total_players = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM municipalities")
        total_muns = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM registrations")
        total_regs = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM results")
        total_results = c.fetchone()[0]
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("कुल विद्यार्थी", total_players)
        c2.metric("सहभागी पालिका", total_muns)
        c3.metric("कुल इभेन्ट दर्ता", total_regs)
        c4.metric("क्लाउड नतिजाहरू", total_results)
    except Exception as e:
        st.error(f"Stats Error: {e}")
    finally:
        c.close(); conn.close()
        
    st.divider()
    st.info("ℹ️ **नोट:** तपाईंले हाल 'Cloud PostgreSQL' प्रयोग गरिरहनुभएको छ। क्लाउड डाटाबेसको अटोमेटिक ब्याकअप सर्भरमै हुने भएकोले यहाँबाट फाइल डाउनलोड/अपलोड (SQLite जस्तो) गर्न मिल्दैन। एक्सेल एक्सपोर्ट (Export) ट्याबबाट डाटा निकाल्नुहोस्।")

# ==========================================
# TAB 3: निर्यात (EXPORT)
# ==========================================
with tab3:
    st.subheader("📤 डाटा निर्यात (Export to Excel)")
    st.write("प्रणालीमा दर्ता भएका सम्पूर्ण खेलाडीहरूको विस्तृत विवरण एक्सेलमा डाउनलोड गर्नुहोस्।")
    
    if st.button("📊 सबै खेलाडीको डाटा डाउनलोड गर्नुहोस्", type="primary"):
        conn = db.get_connection()
        # 💡 SQLite को GROUP_CONCAT लाई PostgreSQL को STRING_AGG ले रिप्लेस गरियो
        query = """
            SELECT m.name as "Municipality",
                   p.name as "Student Name", 
                   p.gender as "Gender", 
                   p.class_val as "Class", 
                   p.iemis_id as "EMIS ID",
                   p.school_name as "School Name",
                   STRING_AGG(e.name, ', ') as "Participating Events"
            FROM players p 
            JOIN municipalities m ON p.municipality_id = m.id
            LEFT JOIN registrations r ON p.id = r.player_id
            LEFT JOIN events e ON r.event_code = e.code
            GROUP BY p.id, m.name
            ORDER BY m.name, p.name
        """
        try:
            df = pd.read_sql_query(query, conn)
            
            if df.empty:
                st.warning("No data to export.")
            else:
                bio = BytesIO()
                with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='All_Players')
                
                st.download_button(
                    label="📥 Download Excel File",
                    data=bio.getvalue(),
                    file_name=f"All_Players_Master_List_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.error(f"Export Error: {e}")
        finally:
            conn.close()

# ==========================================
# TAB 4: प्रणाली जानकारी
# ==========================================
with tab4:
    st.subheader("📊 प्रणाली स्वास्थ्य (System Health)")
    
    if psutil:
        col1, col2 = st.columns(2)
        mem = psutil.virtual_memory()
        col1.progress(mem.percent / 100, text=f"RAM Usage: {mem.percent}%")
        disk = psutil.disk_usage('/')
        col2.progress(disk.percent / 100, text=f"Disk Usage: {disk.percent}%")
        
        st.json({
            "CPU Cores": psutil.cpu_count(),
            "Total RAM": f"{mem.total / (1024**3):.2f} GB",
            "Available RAM": f"{mem.available / (1024**3):.2f} GB",
            "Streamlit Version": st.__version__,
            "Database Engine": "PostgreSQL (Neon Cloud)"
        })
    else:
        st.info("psutil मोड्युल इन्स्टल छैन। सिस्टमको मेमोरी हेर्न टर्मिनलमा 'pip install psutil' टाइप गर्नुहोस्।")

    st.markdown("### ℹ️ प्रणालीका मुख्य नियमहरू")
    st.info("""
    * **खेलाडी दर्ता:** एउटै खेलाडीले 'Boys' र 'Girls' दुवै तर्फ खेल्न पाउँदैन। उमेर हदबन्दी २०६४/११/०१ कायम गरिएको छ।
    * **टिम गेम अटोमेसन:** यदि खेलाडीले भलिबल छानेमा, प्रणालीले आफैँ उक्त पालिकाको भलिबल टिम बनाइदिन्छ।
    * **डिलिट नियम:** यदि कुनै खेलको नतिजा (Results) प्रकाशित भइसकेको छ भने खेलाडी वा पालिकालाई डिलिट गर्न मिल्दैन।
    """)

# ------------------------------------------
# पेजको सबैभन्दा तल फुटर देखाउने
# ------------------------------------------
render_footer()