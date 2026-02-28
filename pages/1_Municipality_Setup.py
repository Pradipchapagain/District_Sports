import streamlit as st
import pandas as pd
import os
import database as db  # 💡 यो अब PostgreSQL सँग जोडिएको database.py हुनुपर्छ

from config import render_header, render_footer

# ==========================================
# ⚙️ CONFIG & ASSETS
# ==========================================
st.set_page_config(page_title="Municipality Setup", page_icon="🏛️", layout="wide")

# ------------------------------------------
# हेडर देखाउने
# ------------------------------------------
render_header()
# ------------------------------------------

LOGO_DIR = "assets/logos"
if not os.path.exists(LOGO_DIR):
    os.makedirs(LOGO_DIR)

# इलामका १० पालिकाहरु र तिनीहरूको डिफल्ट युजरनेम
DEFAULT_PALIKAS = [
    {"name": "Ilam Municipality (इलाम नगरपालिका)", "user": "ilam"},
    {"name": "Deumai Municipality (देउमाई नगरपालिका)", "user": "deumai"},
    {"name": "Mai Municipality (माई नगरपालिका)", "user": "mai"},
    {"name": "Suryodaya Municipality (सूर्योदय नगरपालिका)", "user": "suryodaya"},
    {"name": "Phakphokthum Rural Municipality (फाकफोकथुम गाउँपालिका)", "user": "phakphokthum"},
    {"name": "Chulachuli Rural Municipality (चुलाचुली गाउँपालिका)", "user": "chulachuli"},
    {"name": "Mai Jogmai Rural Municipality (माईजोगमाई गाउँपालिका)", "user": "maijogmai"},
    {"name": "Mangsebung Rural Municipality (माङसेबुङ गाउँपालिका)", "user": "mangsebung"},
    {"name": "Rong Rural Municipality (रोङ गाउँपालिका)", "user": "rong"},
    {"name": "Sandakpur Rural Municipality (सन्दकपुर गाउँपालिका)", "user": "sandakpur"}
]

DEFAULT_PASSWORD = "password123"

# ==========================================
# 🔒 SECURITY CHECK & AUTO-REDIRECT
# ==========================================
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.switch_page("Home.py") 
# ------------------------------------------

# ==========================================
# 🏠 UI STRUCTURE
# ==========================================
st.title("🏛️ पालिका सेटअप तथा लगइन व्यवस्थापन")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📋 अटो/म्यानुअल सेटअप", "🔑 पालिका लगइन र पासवर्ड रिसेट", "🖼️ लोगो व्यवस्थापन"])

# ==========================================
# TAB 1: AUTO & MANUAL SETUP
# ==========================================
if 'auto_setup_success_msg' not in st.session_state:
    st.session_state.auto_setup_success_msg = None

with tab1:
    if st.session_state.auto_setup_success_msg:
        st.success(st.session_state.auto_setup_success_msg)
        st.balloons()
        st.session_state.auto_setup_success_msg = None

    col_auto, col_man = st.columns(2)
    
    with col_auto:
        with st.container(border=True):
            st.subheader("⚙️ अटो सेटअप (Auto Load)")
            st.info(f"इलामका १० वटै पालिका अटोमेटिक थप्नुहोस्।\n\n**Default Password:** `{DEFAULT_PASSWORD}` हुनेछ।")
            
            if st.button("📥 लोड गर्नुहोस् (Load All)", type="primary"):
                count = 0
                conn = db.get_connection()
                
                # 💡 PostgreSQL Logic (with RETURNING id)
                for p in DEFAULT_PALIKAS:
                    try:
                        c = conn.cursor()
                        # १. पालिका थप्ने र नयाँ ID तान्ने
                        c.execute("INSERT INTO municipalities (name, logo_path) VALUES (%s, %s) RETURNING id", (p['name'], None))
                        new_mun_id = c.fetchone()[0]
                        
                        # २. युजर खाता थप्ने
                        pwd_hash = db.hash_password(DEFAULT_PASSWORD)
                        c.execute("""
                            INSERT INTO users (username, password_hash, role, municipality_id) 
                            VALUES (%s, %s, 'municipality', %s)
                        """, (p['user'], pwd_hash, new_mun_id))
                        
                        count += 1
                        c.close()
                    except Exception as e:
                        conn.rollback() # यदि डुप्लिकेट भयो भने रोलब्याक गर्ने
                
                conn.commit()
                conn.close()
                
                if count > 0:
                    st.session_state.auto_setup_success_msg = f"✅ {count} वटा नयाँ पालिका र तिनीहरूको लगइन खाता थपियो!"
                    st.rerun() 
                else:
                    st.warning("⚠️ पालिकाहरु पहिले नै दर्ता भइसकेका छन्।")

    with col_man:
        with st.container(border=True):
            st.subheader("✍️ नयाँ म्यानुअल इन्ट्री (Manual Add)")
            st.write("यदि कुनै नयाँ पालिका थप्नुपरेमा:")
            
            with st.form("manual_add_form"):
                m_name = st.text_input("पालिकाको पूरा नाम")
                m_user = st.text_input("लगइन युजरनेम (Username)", placeholder="e.g. jhapamun")
                m_pass = st.text_input("लगइन पासवर्ड (Password)", type="password")
                
                if st.form_submit_button("➕ थप्नुहोस् (Add)"):
                    if not m_name or not m_user or not m_pass:
                        st.error("सबै विवरण भर्नुहोस्।")
                    else:
                        conn = db.get_connection()
                        c = conn.cursor()
                        try:
                            # 💡 PostgreSQL: Use %s instead of ? and RETURNING id
                            c.execute("INSERT INTO municipalities (name) VALUES (%s) RETURNING id", (m_name,))
                            mun_id = c.fetchone()[0]
                            
                            pwd_hash = db.hash_password(m_pass)
                            c.execute("""
                                INSERT INTO users (username, password_hash, role, municipality_id) 
                                VALUES (%s, %s, 'municipality', %s)
                            """, (m_user, pwd_hash, mun_id))
                            
                            conn.commit()
                            st.success("✅ पालिका र लगइन खाता थपियो!")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"Error: युजरनेम वा पालिकाको नाम जुध्यो।")
                        finally:
                            c.close()
                            conn.close()

# ==========================================
# TAB 2: VIEW CREDENTIALS & RESET PASSWORD
# ==========================================
with tab2:
    c_list, c_reset = st.columns([1.5, 1])
    
    with c_list:
        st.subheader("🔑 पालिकाहरूको लगइन विवरण")
        
        conn = db.get_connection()
        # 💡 PostgreSQL Query
        q = """
            SELECT m.id as "ID", m.name as "पालिकाको नाम", u.username as "Username"
            FROM municipalities m
            LEFT JOIN users u ON m.id = u.municipality_id
            WHERE u.role = 'municipality'
            ORDER BY m.id
        """
        df_cred = pd.read_sql(q, conn)
        conn.close()
        
        if df_cred.empty:
            st.warning("कुनै पनि पालिका दर्ता छैन।")
        else:
            st.dataframe(df_cred, use_container_width=True, hide_index=True)
            st.caption(f"💡 अटो सेटअपबाट बनेका सबैको सुरुवाती पासवर्ड **{DEFAULT_PASSWORD}** हुन्छ।")

    with c_reset:
        st.subheader("🔄 पासवर्ड रिसेट")
        st.info("यदि कुनै पालिकाले पासवर्ड बिर्सियो भने यहाँबाट नयाँ पासवर्ड सेट गरिदिनुहोस्।")
        
        if not df_cred.empty:
            with st.form("reset_pass_form"):
                sel_user = st.selectbox("पालिकाको युजरनेम छान्नुहोस्:", df_cred['Username'].tolist())
                new_pass = st.text_input("नयाँ पासवर्ड (New Password)", value="admin123")
                
                if st.form_submit_button("पासवर्ड रिसेट गर्नुहोस्", type="primary", use_container_width=True):
                    if not new_pass:
                        st.error("पासवर्ड खाली राख्न मिल्दैन।")
                    else:
                        conn = db.get_connection()
                        c = conn.cursor()
                        try:
                            hashed_pass = db.hash_password(new_pass)
                            # 💡 PostgreSQL: Use %s
                            c.execute("UPDATE users SET password_hash = %s WHERE username = %s", (hashed_pass, sel_user))
                            conn.commit()
                            st.success(f"✅ **{sel_user}** को पासवर्ड सफलतापूर्वक परिवर्तन भयो!")
                        except Exception as e:
                            conn.rollback()
                            st.error(f"त्रुटि: {e}")
                        finally:
                            c.close()
                            conn.close()

# ==========================================
# TAB 3: LOGO UPLOAD (Safe for Cloud)
# ==========================================
with tab3:
    st.info("यहाँ अपलोड गरिएको लोगो पछि रिपोर्ट र सर्टिफिकेटमा आउनेछ।")
    
    df = db.get_municipalities() # Make sure database.py has this updated for Postgres
    if df.empty:
        st.error("पहिले पालिका दर्ता गर्नुहोस्।")
    else:
        c1, c2 = st.columns([1, 1])
        
        with c1:
            palika_opts = {row['name']: row['id'] for _, row in df.iterrows()}
            sel_palika_name = st.selectbox("पालिका छान्नुहोस्:", list(palika_opts.keys()))
            sel_palika_id = palika_opts[sel_palika_name]
            
            uploaded_file = st.file_uploader("लोगो छान्नुहोस् (PNG/JPG)", type=['png', 'jpg', 'jpeg'])
            
            if st.button("💾 लोगो सेभ गर्नुहोस्"):
                if uploaded_file:
                    file_ext = uploaded_file.name.split('.')[-1]
                    file_name = f"logo_{sel_palika_id}.{file_ext}"
                    save_path = os.path.join(LOGO_DIR, file_name)
                    
                    # 💡 Note: If deploying to a true cloud (like Heroku/Render), 
                    # saving to a local folder will be lost on restart.
                    # Best practice is to save `uploaded_file.getbuffer()` directly to Postgres as BYTEA or use AWS S3.
                    # For now, we keep the local file logic as you requested.
                    with open(save_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    
                    conn = db.get_connection()
                    c = conn.cursor()
                    # 💡 PostgreSQL: Use %s
                    c.execute("UPDATE municipalities SET logo_path = %s WHERE id = %s", (save_path, sel_palika_id))
                    conn.commit()
                    c.close()
                    conn.close()
                    
                    st.success("✅ लोगो सफलतापूर्वक अपलोड भयो!")
                    st.rerun()
                else:
                    st.error("कृपया फाइल छान्नुहोस्।")

        with c2:
            conn = db.get_connection()
            c = conn.cursor()
            c.execute("SELECT logo_path FROM municipalities WHERE id = %s", (sel_palika_id,))
            cur_logo = c.fetchone()
            c.close()
            conn.close()
            
            st.write("##### हालको लोगो:")
            if cur_logo and cur_logo[0] and os.path.exists(cur_logo[0]):
                st.image(cur_logo[0], width=200, caption=sel_palika_name)
            else:
                st.write("🚫 लोगो छैन (No Logo)")

# ------------------------------------------
# पेजको सबैभन्दा तल फुटर देखाउने
# ------------------------------------------
render_footer()