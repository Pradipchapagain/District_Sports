import streamlit as st
import pandas as pd
import database as db  # 💡 यो अब PostgreSQL सँग जोडिएको database.py हुनुपर्छ
import os
from datetime import date

from config import render_header, render_footer, CONFIG
from io import BytesIO
from utils.document_generator import generate_id_cards_docx

# ==========================================
# ⚙️ CONFIG & UTILS
# ==========================================
st.set_page_config(page_title="Player & Official Registration", page_icon="📝", layout="wide")

# ------------------------------------------
render_header() 
# ------------------------------------------

PHOTO_DIR = "assets/players"
if not os.path.exists(PHOTO_DIR): os.makedirs(PHOTO_DIR)

AGE_CUTOFF_BS = CONFIG["AGE_LIMIT_DATE"]

PALETTE = [
    "#E8F8F5", "#EAF2F8", "#FDEDEC", "#FEF9E7", 
    "#F5EEF8", "#E9F7EF", "#F4F6F6", "#FCF3CF", 
    "#D5F5E3", "#E8DAEF"
]

# ==========================================
# 🔒 SECURITY CHECK & AUTO-REDIRECT
# ==========================================
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.switch_page("Home.py") 
# ------------------------------------------

def get_bs_dob(key_prefix, default_date="2064-05-15"):
    try:
        def_y, def_m, def_d = map(int, str(default_date).split('-'))
    except:
        def_y, def_m, def_d = 2064, 5, 15
        
    c_y, c_m, c_d = st.columns(3)
    y_idx = def_y - 2050 if 2050 <= def_y <= 2080 else 14
    y = c_y.selectbox("साल (Year)", range(2050, 2081), index=y_idx, key=f"{key_prefix}_y")
    m = c_m.selectbox("महिना (Month)", range(1, 13), index=def_m-1, key=f"{key_prefix}_m")
    d = c_d.selectbox("गते (Day)", range(1, 33), index=def_d-1, key=f"{key_prefix}_d")
    return f"{y}-{m:02d}-{d:02d}"

# ==========================================
# 🏠 UI LAYOUT & MUNICIPALITY SELECTION
# ==========================================
st.title("📝 पालिका दर्ता डेस्क (Registration Desk)")

if 'flash_success' in st.session_state:
    st.success(st.session_state.flash_success)
    del st.session_state.flash_success 
if 'flash_error' in st.session_state:
    st.error(st.session_state.flash_error)
    del st.session_state.flash_error

municipalities = db.get_municipalities()
events_df = db.get_events()

if municipalities.empty:
    st.error("⚠️ कुनै पनि पालिका भेटिएन।")
    st.stop()

st.markdown("##### 🏛️ कार्यक्षेत्र (Workspace)")
if st.session_state.get('user_role') == 'admin':
    sel_mun_name = st.selectbox("पालिका छान्नुहोस् (Municipality):", municipalities['name'].unique())
    sel_mun_id = int(municipalities[municipalities['name'] == sel_mun_name]['id'].iloc[0])
else:
    sel_mun_id = int(st.session_state.get('municipality_id', 0))
    sel_mun_name = municipalities[municipalities['id'] == sel_mun_id]['name'].iloc[0]
    st.info(f"तपाईं **{sel_mun_name}** को डाटा व्यवस्थापन गर्दै हुनुहुन्छ।")

st.markdown("---")

tab_off, tab_add, tab_edit, tab_view, tab_idcard = st.tabs([
    "👨‍💼 १. अफिसियल विवरण", 
    "➕ २. नयाँ खेलाडी दर्ता", 
    "✏️ ३. सच्याउनु/हटाउनु", 
    "📋 ४. दर्ता सूची",
    "🪪 ५. परिचयपत्र (ID Card)"
])

# ==========================================
# TAB 1: OFFICIALS
# ==========================================
with tab_off:
    st.subheader(f"👨‍💼 {sel_mun_name} का अफिसियलहरू")
    
    col_f, col_t = st.columns([1, 1.5])
    with col_f:
        with st.form("official_form", clear_on_submit=True):
            o_role = st.selectbox("पद (Role)", ["Team Manager (टिम म्यानेजर)", "Head Coach (मुख्य प्रशिक्षक)", "Asst. Coach (सहायक प्रशिक्षक)", "Coordinator (संयोजक)"])
            o_name = st.text_input("पूरा नाम (Full Name)")
            o_phone = st.text_input("सम्पर्क नम्बर (Phone)")
            if st.form_submit_button("➕ थप्नुहोस् (Add)", type="primary"):
                if o_name and o_phone:
                    db.add_official(sel_mun_id, o_role, o_name, o_phone)
                    st.session_state.flash_success = "✅ अफिसियल सफलतापूर्वक थपियो!"
                    st.rerun()
                else:
                    st.error("नाम र फोन नम्बर अनिवार्य छ।")
                    
    with col_t:
        off_df = db.get_officials(sel_mun_id)
        if not off_df.empty:
            st.dataframe(off_df[['role', 'name', 'phone']], hide_index=True, use_container_width=True)
            del_id = st.selectbox("हटाउनुपर्ने अफिसियल छान्नुहोस्:", off_df['id'], format_func=lambda x: off_df[off_df['id']==x]['name'].iloc[0])
            if st.button("🗑️ हटाउनुहोस् (Delete)"):
                db.delete_official(del_id)
                st.session_state.flash_success = "✅ अफिसियल विवरण हटाइयो!"
                st.rerun()
        else:
            st.info("कुनै अफिसियल दर्ता गरिएको छैन।")

# ==========================================
# TAB 2: ADD NEW PLAYER (नयाँ दर्ता)
# ==========================================
if 'add_success_msg' not in st.session_state:
    st.session_state.add_success_msg = None

with tab_add:
    st.subheader("१. खेलाडीको लिङ्ग छान्नुहोस्")
    
    if st.session_state.add_success_msg:
        st.success(st.session_state.add_success_msg)
        st.balloons()
        st.session_state.add_success_msg = None 
        
    sel_gender = st.radio("लिङ्ग (Gender):", ["Boys", "Girls"], horizontal=True)

    # 💡 PostgreSQL Syntax: use %s instead of ?
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT r.event_code, p.name 
        FROM registrations r 
        JOIN players p ON r.player_id = p.id 
        WHERE p.municipality_id = %s AND p.gender = %s
    """, (sel_mun_id, sel_gender))
    current_regs_raw = c.fetchall()
    c.close()
    conn.close()
    
    current_regs = pd.DataFrame(current_regs_raw, columns=['event_code', 'name'])
    reg_map = current_regs.groupby('event_code')['name'].apply(list).to_dict() if not current_regs.empty else {}

    st.markdown("---")
    
    with st.form("smart_registration_form", clear_on_submit=True):
        st.subheader("२. व्यक्तिगत विवरण (Personal Details)")
        c1, c2, c3 = st.columns(3)
        with c1:
            p_name = st.text_input("पूरा नाम (Full Name) *")
            iemis = st.text_input("IEMIS ID *")
        with c2:
            st.write(f"**जन्म मिति (वि.सं.) *** *(Cutoff: {AGE_CUTOFF_BS})*")
            dob_bs = get_bs_dob("add_dob", AGE_CUTOFF_BS) 
        with c3:
            school = st.text_input("विद्यालयको नाम (School Name) *")
            p_class = st.text_input("कक्षा (Class)")
            
        # 💡 नयाँ थपिएका फिल्डहरू (Guardian & Contact)
        st.markdown("<br>", unsafe_allow_html=True)
        c4, c5 = st.columns(2)
        with c4:
            guardian_name = st.text_input("अभिभावकको नाम (Guardian Name)")
        with c5:
            contact_no = st.text_input("सम्पर्क नम्बर (Contact No.)")
            
        st.divider()
        st.subheader(f"३. खेल छनौट ({sel_gender} तर्फ)")
        
        gender_events = events_df[(events_df['gender'] == sel_gender) | (events_df['gender'] == 'Both')]
        selected_event_codes = []
        
        color_index = 0
        for cat in gender_events['category'].unique():
            st.markdown(f"### 🏆 {cat}")
            cat_events = gender_events[gender_events['category'] == cat]
            
            for sub_cat in cat_events['sub_category'].unique():
                bg_color = PALETTE[color_index % len(PALETTE)]
                color_index += 1
                st.markdown(f"""<div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; border-left: 5px solid #555; margin-bottom: 10px;"><h5 style="margin:0; color: #333;">🔹 {sub_cat}</h5></div>""", unsafe_allow_html=True)
                
                sub_events = cat_events[cat_events['sub_category'] == sub_cat]
                
                for grp in sub_events['event_group'].unique():
                    st.markdown(f"**{grp}**")
                    h1, h2, h3 = st.columns([2.5, 1, 2.5])
                    h1.caption("इभेन्ट (Event)"); h2.caption("दर्ता संख्या"); h3.caption("दर्ता भएका खेलाडीहरू")
                    
                    grp_events = sub_events[sub_events['event_group'] == grp]
                    for _, row in grp_events.iterrows():
                        e_code = row['code']
                        registered_players = reg_map.get(e_code, [])
                        reg_count = len(registered_players)
                        
                        c_ev, c_cnt, c_list = st.columns([2.5, 1, 2.5])
                        with c_ev:
                            if st.checkbox(row['name'], key=f"add_chk_{e_code}"): selected_event_codes.append(e_code)
                        with c_cnt:
                            st.markdown(f"<span style='color:green;'><b>{reg_count}</b></span>" if reg_count>0 else "<span style='color:gray;'>०</span>", unsafe_allow_html=True)
                        with c_list:
                            if reg_count > 0: st.selectbox("Players", registered_players, key=f"add_dd_{e_code}", label_visibility="collapsed")
                            else: st.caption("-")
                    st.write("")

        st.divider()
        uploaded_photo = st.file_uploader("पासपोर्ट साइज फोटो (Optional)", type=['jpg', 'png'])
        submit_btn = st.form_submit_button("💾 सुरक्षित गर्नुहोस् (Save)", type="primary", use_container_width=True)

        if submit_btn:
            if not p_name or not iemis or not school: 
                st.error("कृपया नाम, IEMIS ID र विद्यालयको नाम अनिवार्य भर्नुहोस्।")
            elif dob_bs < AGE_CUTOFF_BS: 
                st.error(f"⚠️ खेलाडीको जन्म मिति {dob_bs} छ। उमेर हदबन्दी नाघेको कारण दर्ता गर्न मिल्दैन।")
            elif len(selected_event_codes) == 0: 
                st.warning("⚠️ कृपया कम्तिमा एउटा खेल/इभेन्टमा टिक लगाउनुहोस्।")
            else:
                # 💡 Note: We need to update `db.add_player` in database.py to accept guardian_name and contact_no!
                pid, msg = db.add_player(sel_mun_id, iemis, p_name, sel_gender, dob_bs, school, p_class, guardian_name, contact_no, None)
                
                if pid:
                    db.update_player_registrations(pid, selected_event_codes)
                    
                    # 💡 PostgreSQL: Team generation
                    conn = db.get_connection()
                    c = conn.cursor()
                    for e_code in selected_event_codes:
                        if events_df[events_df['code'] == e_code]['type'].iloc[0] == 'Team':
                            c.execute("SELECT id FROM teams WHERE event_code=%s AND municipality_id=%s", (e_code, sel_mun_id))
                            if not c.fetchone():
                                c.execute("INSERT INTO teams (event_code, municipality_id, name) VALUES (%s, %s, %s)", (e_code, sel_mun_id, f"{sel_mun_name.split(' ')[0]} Team"))
                    conn.commit()
                    
                    if uploaded_photo:
                        file_ext = uploaded_photo.name.split('.')[-1]
                        save_path = os.path.join(PHOTO_DIR, f"P_{pid}.{file_ext}")
                        with open(save_path, "wb") as f: f.write(uploaded_photo.getbuffer())
                        c.execute("UPDATE players SET photo_path=%s WHERE id=%s", (save_path, pid))
                        conn.commit()
                        
                    c.close()
                    conn.close()
                    
                    st.session_state.add_success_msg = f"🎉 बधाई छ! '{p_name}' दर्ता भयो। (ID: {pid})"
                    st.rerun()
                else: 
                    st.error(f"❌ Error: {msg}")

# ==========================================
# TAB 3: EDIT PLAYER (सच्याउने वा हटाउने)
# ==========================================
PALETTE_EDIT = ["#e0f2fe", "#fce7f3", "#fef3c7", "#dcfce7", "#f3e8ff", "#e0e7ff", "#ffedd5"]

if 'edit_success_msg' not in st.session_state:
    st.session_state.edit_success_msg = None

with tab_edit:
    st.header(f"✏️ {sel_mun_name} का खेलाडीको विवरण सच्याउनुहोस् वा हटाउनुहोस्")
    
    if st.session_state.edit_success_msg:
        if "हटाइयो" in st.session_state.edit_success_msg:
            st.error(st.session_state.edit_success_msg)
        else:
            st.success(st.session_state.edit_success_msg)
            st.balloons()
        st.session_state.edit_success_msg = None 
    
    conn = db.get_connection()
    # 💡 PostgreSQL Syntax
    players_df = pd.read_sql_query("SELECT id, name, iemis_id FROM players WHERE municipality_id = %s ORDER BY name", conn, params=(sel_mun_id,))
    
    if players_df.empty:
        st.info(f"'{sel_mun_name}' मा हालसम्म कुनै खेलाडी दर्ता भएका छैनन्।")
        conn.close()
    else:
        player_options = {"-- खेलाडी छान्नुहोस् --": None}
        for _, row in players_df.iterrows():
            player_options[f"{row['name']} ({row['iemis_id']})"] = row['id']
            
        selected_player_label = st.selectbox("सच्याउनुपर्ने वा हटाउनुपर्ने खेलाडी छान्नुहोस्:", list(player_options.keys()), index=0, key="edit_player_select")
        
        if selected_player_label != "-- खेलाडी छान्नुहोस् --":
            edit_player_id = int(player_options[selected_player_label])
            
            c = conn.cursor()
            c.execute("SELECT * FROM players WHERE id=%s", (edit_player_id,))
            cur_p_raw = c.fetchone()
            cur_p = dict(zip([desc[0] for desc in c.description], cur_p_raw)) # Dictionary बनाउने
            
            c.execute("SELECT event_code FROM registrations WHERE player_id=%s", (edit_player_id,))
            old_events = [r[0] for r in c.fetchall()]
            c.close()
            
            all_events = pd.read_sql_query("SELECT * FROM events", conn)
            
            st.markdown(f"**तपाईं अहिले '{cur_p['name']}' को विवरण हेर्दै हुनुहुन्छ:**")
            
            with st.form("edit_player_form", clear_on_submit=True):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_name = st.text_input("पूरा नाम", value=cur_p['name'])
                    new_iemis = st.text_input("IEMIS ID", value=cur_p['iemis_id'])
                with c2:
                    st.write("**जन्म मिति (वि.सं.)**")
                    new_dob = st.text_input("जन्म मिति (YYYY-MM-DD)", value=cur_p['dob_bs']) 
                with c3:
                    new_school = st.text_input("विद्यालय", value=cur_p['school_name'])
                    new_class = st.text_input("कक्षा", value=cur_p.get('class_val', ''))

                c4, c5 = st.columns(2)
                with c4:
                    new_guardian = st.text_input("अभिभावकको नाम", value=cur_p.get('guardian_name', ''))
                with c5:
                    new_contact = st.text_input("सम्पर्क नम्बर", value=cur_p.get('contact_no', ''))

                st.markdown("---")
                st.write("**भाग लिने खेलहरू (Events) सच्याउनुहोस्:**")
                
                edited_event_codes = []
                p_gender = cur_p['gender']
                gender_events = all_events[(all_events['gender'] == p_gender) | (all_events['gender'] == 'Both')]
                
                color_index = 0
                for cat in gender_events['category'].unique():
                    st.markdown(f"### 🏆 {cat}")
                    cat_events = gender_events[gender_events['category'] == cat]
                    
                    for sub_cat in cat_events['sub_category'].unique():
                        bg_color = PALETTE_EDIT[color_index % len(PALETTE_EDIT)]
                        color_index += 1
                        st.markdown(f"""<div style="background-color: {bg_color}; padding: 10px; border-radius: 5px; border-left: 5px solid #555; margin-bottom: 10px;"><h5 style="margin:0; color: #333;">🔹 {sub_cat}</h5></div>""", unsafe_allow_html=True)
                        
                        sub_events = cat_events[cat_events['sub_category'] == sub_cat]
                        for grp in sub_events['event_group'].unique():
                            st.markdown(f"**{grp}**")
                            grp_events = sub_events[sub_events['event_group'] == grp]
                            cols = st.columns(3)
                            for i, (_, row) in enumerate(grp_events.iterrows()):
                                e_code = row['code']
                                is_checked = e_code in old_events 
                                with cols[i % 3]:
                                    if st.checkbox(row['name'], value=is_checked, key=f"edit_chk_{e_code}"):
                                        edited_event_codes.append(e_code)
                            st.write("")

                st.markdown("---")
                submit_update = st.form_submit_button("💾 विवरण अपडेट गर्नुहोस् (Update)", type="primary")
                
                if submit_update:
                    if not new_name or not new_iemis:
                        st.error("नाम र IEMIS अनिवार्य छ।")
                    elif len(edited_event_codes) == 0:
                        st.warning("कम्तिमा एउटा खेल छान्नुहोस्।")
                    else:
                        # 💡 Update player_info needs to support new fields
                        success, msg = db.update_player_info(edit_player_id, new_iemis, new_name, new_dob, new_school, new_class, new_guardian, new_contact)
                        if success:
                            db.update_player_registrations(edit_player_id, edited_event_codes)
                            st.session_state.edit_success_msg = f"✅ '{new_name}' को विवरण सफलतापूर्वक अपडेट भयो!"
                            if 'edit_player_select' in st.session_state: del st.session_state['edit_player_select']
                            st.rerun()
                        else:
                            st.error(f"❌ अपडेट असफल: {msg}")

            # 🗑️ Delete Section
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown("### ⚠️ Danger Zone (खेलाडी हटाउने)")
            with st.expander("🗑️ यो खेलाडीलाई डाटाबेसबाट पूर्ण रूपमा हटाउनुहोस्", expanded=False):
                st.error(f"के तपाईं **{cur_p['name']}** लाई पूर्ण रूपमा हटाउन निश्चित हुनुहुन्छ?")
                del_confirm = st.checkbox("हो, म यो खेलाडी डिलिट गर्न निश्चित छु।", key=f"del_conf_{edit_player_id}")
                
                if st.button("🗑️ खेलाडी डिलिट गर्नुहोस् (Delete)", disabled=not del_confirm, type="primary"):
                    try:
                        db.delete_player_full(edit_player_id) # Function should handle cascade or manual delete
                        st.session_state.edit_success_msg = f"🗑️ खेलाडी '{cur_p['name']}' लाई सफलतापूर्वक हटाइयो!"
                        if 'edit_player_select' in st.session_state: del st.session_state['edit_player_select']
                        st.rerun()
                    except Exception as e:
                        st.error(f"डिलिट गर्दा समस्या आयो: {e}")
        conn.close()

# ==========================================
# TAB 4: VIEW ALL PLAYERS
# ==========================================
with tab_view:
    st.header(f"📋 {sel_mun_name} का दर्ता भएका खेलाडीहरू")
    
    conn = db.get_connection()
    mun_filter = "" if st.session_state.get('user_role') == 'admin' else f"WHERE p.municipality_id = {sel_mun_id}"
    
    # 💡 PostgreSQL STRING_AGG used instead of GROUP_CONCAT
    q = f"""
        SELECT p.iemis_id as "IEMIS ID", p.name as "Player Name", p.gender as "Gender", 
               p.dob_bs as "D.O.B", p.school_name as "School", p.class_val as "Class",
               p.guardian_name as "Guardian", p.contact_no as "Contact",
               STRING_AGG(e.name, ', ') as "Participating Events"
        FROM players p
        LEFT JOIN registrations r ON p.id = r.player_id
        LEFT JOIN events e ON r.event_code = e.code
        {mun_filter}
        GROUP BY p.id
        ORDER BY p.id DESC
    """
    df_players = pd.read_sql_query(q, conn)
    conn.close()
    
    if df_players.empty:
        st.info("अहिलेसम्म कुनै खेलाडी दर्ता भएका छैनन्।")
    else:
        df_players['Class'] = df_players['Class'].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')
        df_players['IEMIS ID'] = df_players['IEMIS ID'].astype(str).str.replace(r'\.0$', '', regex=True).replace('nan', '')
        
        st.dataframe(df_players, use_container_width=True, hide_index=True)
        st.write(f"कुल खेलाडी संख्या: **{len(df_players)}**")

# ==========================================
# TAB 5: ID CARD 
# ==========================================
with tab_idcard:
    st.header("🪪 परिचयपत्र जेनेरेटर (ID Card)")
    st.info("यहाँबाट छानिएको पालिकाका सबै खेलाडीहरूको परिचयपत्र Microsoft Word (.docx) फर्म्याटमा डाउनलोड गर्न सकिन्छ।")
    
    conn = db.get_connection()
    user_role = st.session_state.get('user_role', 'admin') 
    
    if user_role == 'admin':
        mun_df = pd.read_sql_query("SELECT id, name FROM municipalities ORDER BY name", conn)
    else:
        logged_in_mun_id = st.session_state.get('municipality_id', sel_mun_id)
        mun_df = pd.read_sql_query("SELECT id, name FROM municipalities WHERE id = %s", conn, params=(logged_in_mun_id,))
        
    conn.close()
    
    if mun_df.empty:
        st.warning("कुनै पनि पालिका भेटिएन।")
    else:
        mun_dict = {row['name']: row['id'] for _, row in mun_df.iterrows()}
        mun_list = ["-- छान्नुहोस् --"] + list(mun_dict.keys())
        
        default_idx = 1 if user_role != 'admin' and len(mun_dict) == 1 else 0
            
        sel_id_mun_name = st.selectbox("परिचयपत्र प्रिन्ट गर्न पालिका छान्नुहोस्:", mun_list, index=default_idx, key="id_card_mun")
        
        if sel_id_mun_name != "-- छान्नुहोस् --":
            selected_mun_id = int(mun_dict[sel_id_mun_name])
            
            conn = db.get_connection()
            p_df = pd.read_sql_query("SELECT * FROM players WHERE municipality_id = %s", conn, params=(selected_mun_id,))
            conn.close()
            
            if p_df.empty:
                st.warning(f"⚠️ {sel_id_mun_name} मा हालसम्म कुनै पनि खेलाडी दर्ता भएका छैनन्।")
            else:
                st.success(f"✅ {sel_id_mun_name} का जम्मा **{len(p_df)}** जना खेलाडीहरूको परिचयपत्र तयार छ।")
                
                if st.button("🚀 परिचयपत्र (ID Cards) डाउनलोड गर्नुहोस्", type="primary"):
                    with st.spinner("Word File बन्दैछ... कृपया पर्खनुहोस्।"):
                        try:
                            doc = generate_id_cards_docx(sel_id_mun_name, p_df)
                            bio = BytesIO()
                            doc.save(bio)
                            
                            st.download_button(
                                label="📥 यहाँ क्लिक गरेर Word File डाउनलोड गर्नुहोस्",
                                data=bio.getvalue(),
                                file_name=f"ID_Cards_{sel_id_mun_name}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                            )
                            st.balloons()
                        except Exception as e:
                            st.error(f"❌ डकुमेन्ट जेनेरेट गर्दा समस्या आयो: {e}")

render_footer()