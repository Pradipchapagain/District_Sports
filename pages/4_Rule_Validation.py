# pages\4_Rule_Validation.py
import streamlit as st
import pandas as pd
import database as db
from config import render_header, render_footer

# पेज सेटिङ
st.set_page_config(page_title="Rule Validation", page_icon="⚠️", layout="wide")
render_header()

# लगइन चेक
if 'logged_in' not in st.session_state or not st.session_state.logged_in:
    st.error("🔒 कृपया लगइन गर्नुहोस्।")
    st.stop()

st.title("⚠️ नियम उल्लंघन चेक (Rule Validation)")
st.markdown("प्रतियोगितामा दर्ता भएका पालिकाहरूले तोकिएको नियम पालना गरे/नगरेको यहाँबाट एकै क्लिकमा जाँच गर्न सकिन्छ।")
st.divider()

# ==========================================
# 🔍 भ्यालिडेसन सुरु गर्ने बटन
# ==========================================
c1, c2 = st.columns([1, 2])
with c1:
    run_check = st.button("🚀 सम्पूर्ण नियमहरू जाँच गर्नुहोस् (Run Full Validation)", type="primary", width="stretch")
with c2:
    st.info("👈 यो बटन थिचेर डाटाबेसमा रहेका सबै खेलाडी र पालिकाहरूको दर्ता जाँच गर्नुहोस्।")

if run_check:
    with st.spinner("नियमहरू जाँच गरिँदैछ... कृपया पर्खनुहोस्..."):
        
        # १. एथ्लेटिक्स (Individual Events)
        st.markdown("### १. एथ्लेटिक्स (Athletics Individual)")
        st.caption("नियम: एक खेलाडीले ३ भन्दा बढी खेल (रिले बाहेक) खेल्न पाउँदैन।")
        v1 = db.check_athletics_violations()
        if v1.empty: st.success("✅ एथ्लेटिक्सका सबै नियम पालना भएका छन्।")
        else:
            st.error(f"❌ {len(v1)} वटा उल्लंघन भेटियो!")
            st.dataframe(v1, width="stretch")
        st.divider()

        # २. मार्सल आर्ट्स (Sparring Weight)
        st.markdown("### २. मार्सल आर्ट्स (Sparring Weight Class)")
        st.caption("नियम: कुमिते, ग्योरोगी वा सान्डामा एक खेलाडीले १ भन्दा बढी तौल समूहमा भाग लिन पाउँदैन।")
        v2 = db.check_martial_arts_violations()
        if v2.empty: st.success("✅ मार्सल आर्ट्सका सबै नियम पालना भएका छन्।")
        else:
            st.error(f"❌ {len(v2)} वटा उल्लंघन भेटियो!")
            st.dataframe(v2, width="stretch")
        st.divider()

        # ३. टिम संख्या (Team Size)
        st.markdown("### ३. टिम खेलाडी संख्या (Team Size)")
        st.caption("नियम: भलिबल (६-९), कबड्डी (७-९), रिले (४-६)")
        v3 = db.check_team_size_violations()
        if v3.empty: st.success("✅ टिम संख्याका सबै नियम पालना भएका छन्।")
        else:
            st.error(f"❌ {len(v3)} वटा उल्लंघन भेटियो!")
            st.dataframe(v3, width="stretch")
        st.divider()

        # ४. एथलेटिक्स एकल दर्ता सीमा
        st.markdown("### ४. एथलेटिक्स एकल दर्ता सीमा (Single Event Limit)")
        st.caption("नियम: एथलेटिक्सको एकल प्रतिष्पर्धामा एउटै पालिकाबाट तोकिएको संख्या भन्दा बढी खेलाडी दर्ता गर्न पाइँदैन।")
        v4 = db.check_athletics_single_limit_violations()
        if v4.empty: st.success("✅ एकल दर्ता सीमाका सबै नियम पालना भएका छन्।")
        else:
            st.error(f"❌ {len(v4)} वटा उल्लंघन भेटियो!")
            st.dataframe(v4, width="stretch")
        st.divider()

        # ५. मार्सल आर्ट्स प्रदर्शन सीमा
        st.markdown("### ५. मार्सल आर्ट्स प्रदर्शन सीमा (Forms Limit)")
        st.caption("नियम: काता, पुम्से र थाउलोमा एउटै पालिकाबाट १ जना भन्दा बढी खेलाडी दर्ता गर्न पाइँदैन।")
        v5 = db.check_martial_arts_forms_violations()
        if v5.empty: st.success("✅ मार्सल आर्ट्स प्रदर्शन तर्फका सबै नियम पालना भएका छन्।")
        else:
            st.error(f"❌ {len(v5)} वटा उल्लंघन भेटियो!")
            st.dataframe(v5, width="stretch")
        st.divider()

        # ६. उमेर हदबन्दी
        limit_date = "2064-11-01" 
        st.markdown("### ६. उमेर हदबन्दी (Age Limit - 18 Years)")
        st.caption(f"नियम: मिति **{limit_date}** भन्दा अगाडि जन्म भएका खेलाडी (Over Age) सहभागी हुन पाउँदैनन्।")
        v6 = db.check_age_limit_violations(limit_date)
        if v6.empty: st.success(f"✅ सबै खेलाडी उमेर हदबन्दी भित्र छन्।")
        else:
            st.error(f"❌ {len(v6)} जना खेलाडी अयोग्य (Over Age) भेटिए!")
            st.dataframe(v6, width="stretch")
        st.divider()

        # ===============================================
        # 🆕 थपिएका प्रोफेसनल नियमहरू (PRO VALIDATIONS)
        # ===============================================
        st.markdown("---")
        st.markdown("## 🛡️ अतिरिक्त प्राविधिक जाँच (Advanced Checks)")

        # ७. जेन्डर म्याच (Gender Mismatch)
        st.markdown("### ७. जेन्डर म्याच (Gender Mismatch)")
        st.caption("नियम: छात्रको खेलमा छात्रा वा छात्राको खेलमा छात्र दर्ता गर्न पाइँदैन। (बल्क अपलोड गर्दा हुने गल्ती)")
        v7 = db.check_gender_mismatch()
        if v7.empty: st.success("✅ कुनै पनि जेन्डर म्याच (Gender Mismatch) गल्ती भेटिएन।")
        else:
            st.error(f"❌ {len(v7)} वटा जेन्डर म्याच गल्ती भेटियो! (कृपया सच्याउनुहोस्)")
            st.dataframe(v7, width="stretch")
        st.divider()

        # ८. दोहोरो EMIS कोड
        st.markdown("### ८. दोहोरो EMIS दर्ता (Duplicate EMIS)")
        st.caption("नियम: एउटै EMIS ID प्रयोग गरेर दुई फरक नाम वा विद्यालयबाट दर्ता गर्न पाइँदैन। (खेलाडी दोहोरिने सम्भावना)")
        v8 = db.check_duplicate_emis()
        if v8.empty: st.success("✅ कुनै पनि दोहोरो EMIS ID दर्ता भेटिएन।")
        else:
            st.error(f"❌ {len(v8)} वटा दोहोरो EMIS ID भेटियो!")
            st.dataframe(v8, width="stretch")
        st.divider()

        # ९. दोहोरो टिम गेम (Config बाट कन्ट्रोल हुने)
        from config import CONFIG
        allow_multiple_teams = CONFIG.get('ALLOW_MULTIPLE_TEAM_GAMES', False)
        
        st.markdown("### ९. दोहोरो टिम गेम (Multiple Team Games)")
        if allow_multiple_teams:
            st.info("ℹ️ वर्तमान सेटिङ अनुसार एक खेलाडीले भलिबल र कबड्डी दुवै खेल्न **पाउँछन्**। (यो जाँच बन्द गरिएको छ)")
            v9 = pd.DataFrame() # खाली 
        else:
            st.caption("नियम: एक खेलाडीले एउटा मात्र टिम गेम (भलिबल वा कबड्डी मध्ये एक) खेल्न पाउँछन्।")
            v9 = db.check_multiple_team_games()
            if v9.empty: st.success("✅ कुनै पनि खेलाडीले २ वटा टिम गेम खेलेका छैनन्।")
            else:
                st.error(f"❌ {len(v9)} जना खेलाडीले १ भन्दा बढी टिम गेम खेलेको भेटियो!")
                st.dataframe(v9, width="stretch")
        st.divider()

        # १०. पालिका खेलाडी कोटा (Palika Quota)
        max_quota = CONFIG.get('MAX_PLAYERS_PER_PALIKA', 88)
        st.markdown(f"### १०. पालिका कुल खेलाडी कोटा (Max {max_quota} Players)")
        st.caption(f"नियम: एउटा पालिकाबाट अधिकतम {max_quota} जना खेलाडी मात्र दर्ता हुन पाउँछन्।")
        v10 = db.check_palika_player_quota(max_quota)
        if v10.empty: st.success(f"✅ सबै पालिकाहरू तोकिएको कोटा ({max_quota} जना) भित्रै छन्।")
        else:
            st.error(f"❌ {len(v10)} वटा पालिकाले कोटाभन्दा बढी खेलाडी दर्ता गरेका छन्!")
            st.dataframe(v10, width="stretch")
        st.divider()
        
        # ===============================================
        # 🏛️ पालिका अनुपालन सारांश (PALIKA COMPLIANCE SUMMARY)
        # ===============================================
        st.header("🏛️ पालिका नियम पालना सारांश (Final Report)")
        
        conn = db.get_connection()
        # 💡 PostgreSQL Query optimization
        active_palikas_df = pd.read_sql_query("""
            SELECT DISTINCT m.name 
            FROM registrations r 
            JOIN players p ON r.player_id = p.id 
            JOIN municipalities m ON p.municipality_id = m.id
            ORDER BY m.name
        """, conn)
        conn.close()
        
        all_participating_palikas = active_palikas_df['name'].tolist()
        palika_violations = {palika: set() for palika in all_participating_palikas}

        # डाटा जम्मा गर्ने
        if not v1.empty:
            for m in v1['Municipality'].unique(): palika_violations.get(m, set()).add("नियम १ (Player Limit)")
        if not v2.empty:
            for m in v2['Municipality'].unique(): palika_violations.get(m, set()).add("नियम २ (Weight Class)")
        if not v3.empty:
            for m in v3['Municipality'].unique(): palika_violations.get(m, set()).add("नियम ३ (Team Size)")
        if not v4.empty:
            for m in v4['Municipality'].unique(): palika_violations.get(m, set()).add("नियम ४ (Athletics Limit)")
        if not v5.empty:
            for m in v5['Municipality'].unique(): palika_violations.get(m, set()).add("नियम ५ (MA Forms)")
        if not v6.empty:
            for m in v6['Municipality'].unique(): palika_violations.get(m, set()).add("नियम ६ (Age Limit)")
        if not v7.empty and 'Municipality' in v7.columns:
            for m in v7['Municipality'].unique(): palika_violations.get(m, set()).add("नियम ७ (Gender Mismatch)")
        if not v8.empty:
            if 'Municipalities' in v8.columns: # Fixed column name based on SQL query
                for m_str in v8['Municipalities'].dropna().unique():
                    for m in str(m_str).split(' / '): 
                        if m.strip() in palika_violations: 
                            palika_violations[m.strip()].add("नियम ८ (Duplicate EMIS)")

        if not v9.empty and 'Municipality' in v9.columns:
            for m in v9['Municipality'].unique(): palika_violations.get(m, set()).add("नियम ९ (Multiple Team Games)")
        if not v10.empty and 'Municipality' in v10.columns:
            for m in v10['Municipality'].unique(): palika_violations.get(m, set()).add("नियम १० (Quota Exceeded)")

        compliant_palikas = []
        non_compliant_palikas = []

        for palika in all_participating_palikas:
            issues = palika_violations.get(palika, set())
            if not issues:
                compliant_palikas.append(palika)
            else:
                rules_broken = ", ".join(sorted(list(issues)))
                non_compliant_palikas.append((palika, rules_broken))

        col_green, col_red = st.columns(2)

        with col_green:
            st.success(f"✅ नियम पालना गर्ने पालिकाहरू ({len(compliant_palikas)})")
            if compliant_palikas:
                clean_list = pd.DataFrame(compliant_palikas, columns=["पालिकाको नाम"])
                st.dataframe(clean_list, width="stretch", hide_index=True)
            else:
                st.info("कुनै पनि पालिका पूर्ण रूपमा नियम पालना गर्ने भेटिएनन्।")

        with col_red:
            st.error(f"❌ नियम उलङ्घन गर्ने पालिकाहरू ({len(non_compliant_palikas)})")
            if non_compliant_palikas:
                df_red = pd.DataFrame(non_compliant_palikas, columns=["पालिकाको नाम", "मिचेका नियमहरू"])
                st.dataframe(df_red, width="stretch", hide_index=True)
            else:
                st.success("बधाई छ! कुनै पनि पालिकाले नियम उलङ्घन गरेका छैनन्।")

render_footer()