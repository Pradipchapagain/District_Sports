import streamlit as st
from config import CONFIG, render_header, render_footer
from datetime import datetime

# १. पेज सेटअप
st.set_page_config(page_title="नियम र सर्तहरू", page_icon="📜", layout="wide", initial_sidebar_state="collapsed")

# २. कस्टम CSS (बुटस्ट्र्याप-जस्तो कार्ड र टाइपोग्राफी)
st.markdown("""
<style>
    /* ========== CSS VARIABLES ========== */
    :root {
        --primary: #1E3A8A;
        --primary-light: #2563eb;
        --primary-soft: #e9f0ff;
        --secondary: #059669;
        --accent: #d97706;
        --danger: #B91C1C;
        --dark: #1e293b;
        --light: #f8fafc;
        --border: #e2e8f0;
        --text: #334155;
        --text-light: #64748b;
        --shadow-sm: 0 4px 6px -1px rgba(0,0,0,0.1), 0 2px 4px -2px rgba(0,0,0,0.05);
        --shadow-md: 0 10px 15px -3px rgba(0,0,0,0.1), 0 4px 6px -4px rgba(0,0,0,0.05);
        --shadow-lg: 0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.02);
        --transition: all 0.2s ease;
    }

    /* ========== GLOBAL STYLES ========== */
    body {
        font-family: 'Poppins', 'Segoe UI', sans-serif;
        background: linear-gradient(145deg, #f9fafb 0%, #ffffff 100%);
        color: var(--text);
    }

    .block-container {
        max-width: 1400px;
        margin: 0 auto;
        padding: 1rem 1.5rem;
    }

    /* ========== TYPOGRAPHY ========== */
    h1, h2, h3, h4 {
        font-weight: 600;
        letter-spacing: -0.02em;
        color: var(--dark);
    }

    /* ========== CARD DESIGN ========== */
    .rule-card {
        background: white;
        border-radius: 24px;
        padding: 1.8rem 1.5rem;
        margin-bottom: 2rem;
        box-shadow: var(--shadow-sm);
        border: 1px solid var(--border);
        transition: var(--transition);
        position: relative;
        overflow: hidden;
    }

    .rule-card:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
        border-color: var(--primary-light);
    }

    /* Left border accent (per sport) – apply via inline style */
    .rule-card[vb] { border-left: 6px solid #1E40AF; }
    .rule-card[kb] { border-left: 6px solid #B91C1C; }
    .rule-card[ma] { border-left: 6px solid #5b21b6; }
    .rule-card[gen] { border-left: 6px solid var(--primary); }

    /* Card Header */
    .card-header {
        display: flex;
        align-items: center;
        gap: 14px;
        border-bottom: 2px solid #f1f5f9;
        padding-bottom: 1rem;
        margin-bottom: 1.5rem;
    }

    .card-header h3 {
        font-size: 1.5rem;
        font-weight: 700;
        margin: 0;
        color: var(--dark);
        line-height: 1.3;
    }

    .card-icon {
        font-size: 2.2rem;
        background: var(--primary-soft);
        width: 58px;
        height: 58px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 18px;
        color: var(--primary);
        transition: var(--transition);
    }

    .rule-card:hover .card-icon {
        background: var(--primary);
        color: white;
    }

    /* List Styling */
    .rule-list {
        list-style: none;
        padding-left: 0;
        margin: 0;
    }

    .rule-list li {
        padding: 0.5rem 0 0.5rem 2rem;
        background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="%231E3A8A" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>') left center no-repeat;
        background-size: 1.2rem;
        margin-bottom: 0.5rem;
        color: var(--text);
        font-size: 1rem;
        line-height: 1.6;
    }

    .rule-list strong, .highlight {
        background: #fef9c3;
        color: #92400e;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-block;
        margin: 0.1rem 0;
    }

    /* ========== BADGES ========== */
    .badge-sport {
        display: inline-block;
        background: #f1f5f9;
        padding: 0.4rem 1.2rem;
        border-radius: 40px;
        font-size: 0.85rem;
        font-weight: 600;
        color: var(--dark);
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
        border: 1px solid transparent;
        transition: var(--transition);
        cursor: default;
    }

    .badge-sport:hover {
        transform: scale(1.02);
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }

    .badge-sport.vb { background: #dbeafe; color: #1E40AF; border-color: #1E40AF33; }
    .badge-sport.kb { background: #fee2e2; color: #B91C1C; border-color: #B91C1C33; }
    .badge-sport.ma { background: #f1f0ff; color: #5b21b6; border-color: #5b21b633; }
    .badge-sport.gen { background: #ecfdf5; color: #065f46; border-color: #065f4633; }

    /* ========== TABS IMPROVEMENT ========== */
    .stTabs {
        margin-bottom: 2rem;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background: transparent;
        flex-wrap: nowrap;
        overflow-x: auto;
        overflow-y: hidden;
        scrollbar-width: thin;
        padding-bottom: 0.2rem;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px;
        background: transparent;
        border-radius: 40px 40px 0 0;
        padding: 0 1.5rem;
        font-weight: 600;
        color: var(--text-light);
        border: 1px solid var(--border);
        border-bottom: none;
        transition: var(--transition);
        white-space: nowrap;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--primary);
        border-color: var(--primary-light);
        background: rgba(30, 58, 138, 0.05);
    }

    .stTabs [aria-selected="true"] {
        background: var(--primary) !important;
        color: white !important;
        border-color: var(--primary) !important;
        box-shadow: 0 4px 10px rgba(30, 58, 138, 0.3);
    }

    /* ========== DOWNLOAD BUTTON ========== */
    .download-btn {
        background: var(--primary);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 50px;
        font-size: 1.1rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.6rem;
        cursor: pointer;
        transition: var(--transition);
        box-shadow: var(--shadow-sm);
    }

    .download-btn:hover {
        background: var(--primary-light);
        transform: translateY(-2px);
        box-shadow: var(--shadow-md);
    }

    /* ========== SECTION SUBHEAD ========== */
    .section-subhead {
        font-size: 1.3rem;
        font-weight: 600;
        color: var(--dark);
        margin: 2rem 0 1.2rem 0;
        padding-left: 1rem;
        border-left: 6px solid var(--primary);
        background: linear-gradient(to right, #f1f5f9, transparent);
        padding: 0.7rem 0 0.7rem 1.5rem;
        border-radius: 0 40px 40px 0;
    }

    /* ========== DIVIDER ========== */
    hr.divider {
        margin: 2.5rem 0;
        border: 0;
        border-top: 2px dashed var(--border);
    }

    /* ========== RESPONSIVE TWEAKS ========== */
    @media (max-width: 768px) {
        .block-container {
            padding: 1rem;
        }
        .rule-card {
            padding: 1.2rem 1rem;
        }
        .card-header h3 {
            font-size: 1.3rem;
        }
        .card-icon {
            width: 48px;
            height: 48px;
            font-size: 1.8rem;
        }
        .badge-sport {
            font-size: 0.75rem;
            padding: 0.3rem 0.8rem;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 0 1rem;
            font-size: 0.9rem;
        }
    }

    @media (max-width: 480px) {
        .card-header {
            gap: 8px;
        }
        .card-header h3 {
            font-size: 1.1rem;
        }
    }

    /* ========== INFO/WARNING/SUCCESS BOXES ========== */
    .stAlert {
        border-radius: 16px !important;
        border-left-width: 6px !important;
        box-shadow: var(--shadow-sm);
    }

    /* Streamlit default elements adjustments */
    .stExpander {
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid var(--border);
        margin-bottom: 1.5rem;
    }
</style>""", unsafe_allow_html=True)

# ३. हेडर
render_header()

# ४. मुख्य शीर्षक
st.markdown(f"""
<div style="display: flex; align-items: center; gap: 20px; margin-bottom: 30px;">
    <h1 style="margin:0; color: #0f172a; font-size: 3rem; font-weight: 700;">📜 नियम र सर्तहरू</h1>
    <div style="background: #1E3A8A; color: white; padding: 5px 20px; border-radius: 30px; font-size: 1.2rem;">२०८२ संस्करण</div>
</div>
<p style="font-size: 1.2rem; color: #334155; margin-bottom: 2rem;">
    <span style="background: #f1f5f9; padding: 5px 15px; border-radius: 30px;">🏆 {CONFIG['EVENT_TITLE_NP']}</span> अन्तर्गत सबै विधाका लागि लागु हुने नियमहरू तल उल्लेखित छन्।
</p>
""", unsafe_allow_html=True)


# ५. ट्याब नेभिगेसन (७ वटा)
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "🌟 सामान्य नियम", 
    "🖥️ दर्ता र प्रविधि", 
    "🏐 भलिबल", 
    "🤼 कबड्डी", 
    "🥋 मार्शल आर्ट्स", 
    "🏃‍♂️ एथलेटिक्स", 
    "⚖️ विवाद र पदक"
])

# ==================== 🌟 सामान्य नियम (General Rules Section) ====================
with tab1:
    # ब्याजहरू (Badges)
    st.markdown("""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;"> 
            <span class="badge-sport gen">📜 राखेप नियमावली</span> 
            <span class="badge-sport gen">🤝 फेयर प्ले (Fair Play)</span> 
            <span class="badge-sport gen">🎓 नियमित विद्यार्थी</span> 
            <span class="badge-sport gen">⏰ समयको पालना</span> 
            <span class="badge-sport gen">🚫 डोपिङ निषेध</span> 
            <span class="badge-sport gen">📞 उजुरी/अपिल</span> 
        </div> 
    """, unsafe_allow_html=True)

    st.info("🌟 सामान्य नियम: यी नियमहरू सबै खेल विधामा समान रूपले लागू हुनेछन्। कुनै खेल-विशेष नियमहरू भएमा उक्त खेलको छुट्टै सेक्सन हेर्नुहोस्।")

    # भ्यालिएबलहरू सेटिङबाट लिने
    age_limit = CONFIG.get('AGE_LIMIT_DATE', '२०६४-११-०१')
    max_players = CONFIG.get('MAX_PLAYERS_PER_PALIKA', '८८')

    # दुईवटा कोलममा विभाजन
    col1, col2 = st.columns(2)

    with col1:
        # ========== सहभागिता र योग्यता ==========
        st.markdown(f"""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">📋</div> <h3>सहभागिता र योग्यता</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>उमेर हद:</strong> जन्म मिति <strong>{age_limit}</strong> वा सोभन्दा पछि भएको हुनुपर्ने।</li> 
                    <li><strong>विद्यार्थी योग्यता:</strong> मान्यता प्राप्त विद्यालयमा <strong>कक्षा ८ देखि १२</strong> सम्म अध्ययनरत नियमित विद्यार्थी।</li> 
                    <li><strong>टोलीको आकार:</strong> प्रति पालिका अधिकतम <strong>{max_players} जना</strong> खेलाडी।</li> 
                    <li><strong>विधा सीमा:</strong> एथलेटिक्समा बढीमा ३ वटा व्यक्तिगत विधा (रिले बाहेक)।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

        # ========== पोशाक र खेल सामग्री ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">👕</div> <h3>पोशाक र खेल सामग्री</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>एकरूपता:</strong> टोली खेलमा सबै खेलाडीको एकै रङ र बुट्टा भएको जर्सी अनिवार्य।</li> 
                    <li><strong>नम्बर:</strong> जर्सीको अगाडि र पछाडि प्रस्ट देखिने नम्बर (१-९९) अनिवार्य।</li> 
                    <li><strong>निषेध:</strong> घडी, सिक्री, औँठी वा अन्य धातुका वस्तु लगाउन पूर्ण निषेध।</li> 
                    <li><strong>जुत्ता:</strong> खेलअनुसारको स्पोर्ट्स जुत्ता अनिवार्य (चप्पल/स्यान्डल निषेध)।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

        # ========== मेडिकल र सुरक्षा ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🏥</div> <h3>मेडिकल र सुरक्षा</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>प्राथमिक उपचार:</strong> प्रत्येक खेल स्थलमा मेडिकल टिम र एम्बुलेन्स उपलब्ध हुनेछ।</li> 
                    <li><strong>डोपिङ:</strong> प्रतिबन्धित औषधि सेवन गरेको पाइएमा तत्काल निष्कासन गरिनेछ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col2:
        # ========== अनुशासन र आचारसंहिता ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">⏱️</div> <h3>अनुशासन र आचारसंहिता</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>वाकओभर:</strong> तोकिएको समयको <strong>१५ मिनेटभित्र</strong> उपस्थित नभए विपक्षी विजयी हुनेछ।</li> 
                    <li><strong>निर्णय:</strong> रेफ्री वा निर्णायकको निर्णय अन्तिम र सर्वमान्य हुनेछ।</li> 
                    <li><strong>मर्यादा:</strong> अभद्र व्यवहार वा हातपात गरेमा टोलीलाई नै रेड कार्ड दिइनेछ।</li> 
                    <li><strong>नशालु पदार्थ:</strong> खेल स्थलमा धूम्रपान र मदिरा पूर्ण रूपमा निषेध छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

        # ========== प्रशिक्षक र टोली व्यवस्थापक ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">📢</div> <h3>प्रशिक्षक र व्यवस्थापक</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>ID कार्ड:</strong> अफिसियल बेन्चमा बस्न आयोजकको परिचयपत्र अनिवार्य छ।</li> 
                    <li><strong>टेक्निकल एरिया:</strong> प्रशिक्षक तोकिएको घेराभित्र मात्र रहनुपर्नेछ।</li> 
                    <li><strong>दाबी-विरोध:</strong> आधिकारिक उजुरी टोली व्यवस्थापकले मात्र गर्न पाउनेछन्।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

        # ========== पुरस्कार र मान्यता ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🏆</div> <h3>पुरस्कार र मान्यता</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>पदक:</strong> प्रथम, द्वितीय र तृतीयलाई स्वर्ण, रजत र कांस्य पदक।</li> 
                    <li><strong>प्रमाणपत्र:</strong> सबै सहभागी खेलाडीलाई डिजिटल वा हार्डकपी प्रमाणपत्र।</li> 
                    <li><strong>विशेष अवार्ड:</strong> उत्कृष्ट खेलाडी र अनुशासित टोली (Fair Play) लाई पुरस्कार।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # विस्तृत खण्ड (Protest)
    with st.expander("⚖️ अपिल र विवाद समाधान (Protest) को विस्तृत प्रक्रिया"):
        st.markdown("""
        **अपिल दर्ता प्रक्रिया:**
        * खेल समाप्त भएको **३० मिनेटभित्र** लिखित रूपमा उजुरी दिनुपर्नेछ।
        * अपिलका लागि **रु. २००० धरौटी** बुझाउनुपर्नेछ (सफल भए फिर्ता हुनेछ)।
        * अपिल समितिले भिडियो फुटेज र प्राविधिक पक्ष हेरेर गर्ने निर्णय अन्तिम हुनेछ।
        """)

    # सारांश सेक्सन
    st.markdown("---")
    summary_text = f"""
        <div style="background-color: #ecfdf5; padding: 15px; border-radius: 10px; border-left: 5px solid #059669;"> 
            <strong>📌 मुख्य सारांश:</strong> 
            <ul style="margin-top: 8px;"> 
                <li><strong>योग्यता:</strong> {age_limit} पछि जन्मिएको, कक्षा ८-१२ को विद्यार्थी।</li> 
                <li><strong>अनुशासन:</strong> १५ मिनेट ढिलो भए वाकओभर, रेफ्रीसँग विवाद निषेध।</li> 
                <li><strong>पोशाक:</strong> अनिवार्य जर्सी नम्बर र स्पोर्ट्स जुत्ता।</li> 
            </ul> 
        </div> 
    """
    st.markdown(summary_text, unsafe_allow_html=True)

# ==================== 🖥️ दर्ता र प्रविधि (Registration & Tech) ====================
with tab2:
    # ब्याजहरू (Badges)
    st.markdown("""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;"> 
            <span class="badge-sport gen">🖥️ डिजिटल प्रणाली</span> 
            <span class="badge-sport gen">📊 बल्क दर्ता</span> 
            <span class="badge-sport gen">🛡️ डाटा भ्यालिडेसन</span> 
            <span class="badge-sport gen">🪪 परिचयपत्र</span> 
            <span class="badge-sport gen">🔒 अटो-लक</span> 
            <span class="badge-sport gen">📅 समय-सीमा</span> 
        </div> 
    """, unsafe_allow_html=True)

    # पहिलो रो: दर्ता प्रक्रिया र स्वचालित जाँच
    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">⌨️</div> <h3>दर्ता प्रक्रिया र नियमहरू</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>EMIS अनिवार्य:</strong> प्रत्येक खेलाडीको <strong>IEMIS ID</strong> अनिवार्य छ। यसबाट व्यक्तिगत विवरण स्वतः भरिनेछ।</li> 
                    <li><strong>फोटो मापदण्ड:</strong> स्पष्ट मुखाकृति देखिने, अधिकतम <strong>५०० KB</strong> सम्मको फोटो आवश्यक।</li> 
                    <li><strong>बल्क एक्सेल:</strong> धेरै खेलाडी भएमा सिस्टमको टेम्प्लेट प्रयोग गरी 'Bulk Upload' गर्न सकिने।</li> 
                    <li><strong>फाइल नाम:</strong> फोटोको नाम खेलाडीको EMIS ID सँग मिल्नुपर्नेछ (जस्तै: 12345.jpg)।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_r2:
        # CONFIG बाट डाटा लिँदै (यदि उपलब्ध नभए डिफल्ट मान प्रयोग हुने)
        age_limit = CONFIG.get('AGE_LIMIT_DATE', '२०६४-११-०१')
        max_players = CONFIG.get('MAX_PLAYERS_PER_PALIKA', '८८')
        
        st.markdown(f"""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🛡️</div> <h3>सिस्टम भ्यालिडेसन (स्वचालित जाँच)</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>उमेर जाँच:</strong> जन्म मिति <strong>{age_limit}</strong> भन्दा पछिको हुनुपर्ने।</li> 
                    <li><strong>कोटा जाँच:</strong> प्रति पालिका अधिकतम <strong>{max_players} जना</strong> मात्र दर्ता गर्न मिल्ने।</li> 
                    <li><strong>दोहोरो दर्ता:</strong> एउटै EMIS ID बाट फरक विधा वा दोहोर्याएर दर्ता गर्न मिल्दैन।</li> 
                    <li><strong>लिङ्ग जाँच:</strong> खेलको विधा र खेलाडीको लिङ्ग नमिल्दा सिस्टमले त्रुटि देखाउनेछ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # दोस्रो रो: एक्सेल टेम्प्लेट र समय-सीमा
    col_r3, col_r4 = st.columns(2)

    with col_r3:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">📊</div> <h3>एक्सेल बल्क अपलोड निर्देशिका</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>टेम्प्लेट:</strong> सिस्टमबाटै डाउनलोड गरिएको सक्कल टेम्प्लेट मात्र प्रयोग गर्नुहोस्।</li> 
                    <li><strong>अनिवार्य स्तम्भ:</strong> Name, IEMIS ID, DOB (YYYY-MM-DD), Gender, Event Code।</li> 
                    <li><strong>जिप फाइल:</strong> सबै फोटोहरूलाई एउटा जिप (ZIP) फाइलमा राखेर अपलोड गर्नुहोस्।</li> 
                    <li><strong>त्रुटि रिपोर्ट:</strong> अपलोड असफल भएमा सिस्टमले त्रुटि भएको पङ्क्ति संकेत गर्नेछ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_r4:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">⏰</div> <h3>दर्ता अवधि र अटो-लक</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>समय-सीमा:</strong> तोकिएको अन्तिम मितिपछि सिस्टम स्वतः 'Lock' हुनेछ।</li> 
                    <li><strong>इभेन्ट लक:</strong> प्राविधिक समितिले खेल सुरु हुनुअघि डाटा 'Frozen' गर्नेछ।</li> 
                    <li><strong>परिचयपत्र (ID Card):</strong> दर्ता लक भएपछि <strong>QR कोडसहितको</strong> परिचयपत्र स्वतः डाउनलोड गर्न मिल्नेछ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # तेस्रो रो: प्राविधिक नियम र सुरक्षा
    col_r5, col_r6 = st.columns(2)

    with col_r5:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">⚙️</div> <h3>खेलगत प्राविधिक नियमहरू</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>एथलेटिक्स सीमा:</strong> एक खेलाडीले अधिकतम <strong>३ व्यक्तिगत विधा</strong> (रिले बाहेक) मा मात्र भाग लिन पाउने।</li> 
                    <li><strong>बहु-टिम खेल:</strong> भलिबल र कबड्डी दुवैमा एउटै खेलाडी राख्ने सुविधा सेटिङमा निर्भर हुनेछ।</li> 
                    <li><strong>टोली व्यवस्थापन:</strong> सामूहिक खेलका लागि कप्तान र खेलाडीको सूची अनिवार्य तोक्नुपर्नेछ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_r6:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🔐</div> <h3>डाटा सुरक्षा र पहुँच</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>एक्सेस कन्ट्रोल:</strong> पालिका, जिल्ला र एडमिनका लागि छुट्टाछुट्टै लगइन अधिकार।</li> 
                    <li><strong>अडिट ट्रेल:</strong> प्रत्येक दर्ता र परिवर्तनको समय र कर्ताको रेकर्ड सुरक्षित रहन्छ।</li> 
                    <li><strong>ब्याकअप:</strong> डाटा हराउन नदिन दैनिक स्वचालित ब्याकअपको व्यवस्था।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # हेल्प डेस्क र अन्तिम सन्देश
    st.warning("""
        🚨 **ध्यान दिनुहोस्:**
        1. एक्सेल फाइलको हेडर (Header) र फर्म्याटमा कुनै परिवर्तन नगर्नुहोला।
        2. फोटोहरू जिप गर्दा फोल्डर भित्र फोल्डर नबनाई सिधै फाइलहरू जिप गर्नुहोस्।
        3. प्राविधिक समस्या आएमा तत्काल **Help Desk** मा सम्पर्क गर्नुहोस्।
    """)

    st.success("✅ **सुन्निश्चित गर्नुहोस्:** सबै डाटा अपलोड भएपछि 'समीक्षा' पृष्ठबाट कुल संख्या र फोटो स्थिति जाँच गर्नुहोस्।")

# ==================== 🏐 भलिबल (Volleyball Section) ====================
with tab3:
    # ब्याजहरू (Badges)
    st.markdown("""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;"> 
            <span class="badge-sport vb">🇳🇵 राष्ट्रिय खेल (२०७४)</span> 
            <span class="badge-sport vb">🌐 FIVB २०२५-२०२८ नियम</span> 
            <span class="badge-sport vb">📏 कोर्ट: १८मि × ९मि</span> 
            <span class="badge-sport vb">🛡️ लिबेरो</span> 
            <span class="badge-sport vb">🟨🟥 कार्ड प्रणाली</span> 
        </div> 
    """, unsafe_allow_html=True)

    st.info("🏐 भलिबल (Volleyball): नेपालको राष्ट्रिय खेल। तल उल्लेखित नियमहरू FIVB (२०२५-२०२८) का आधिकारिक नियममा आधारित छन्।")

    # पहिलो रो: कोर्ट र म्याच ढाँचा
    col_v1, col_v2 = st.columns(2)

    with col_v1:
        # ========== कोर्ट र प्राविधिक मापदण्ड ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">📏</div> <h3>कोर्ट र प्राविधिक मापदण्ड</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>मैदानको नाप:</strong> १८ मिटर लम्बाइ × ९ मिटर चौडाइ।</li> 
                    <li><strong>नेटको उचाइ:</strong> 
                        <ul> 
                            <li>पुरुष (Men): २.४३ मि.</li> 
                            <li>महिला (Women): २.२४ मि.</li> 
                            <li>सिटिङ भलिबल: पुरुष १.१५ मि., महिला १.०५ मि.</li> 
                        </ul> 
                    </li> 
                    <li><strong>एन्टेना:</strong> १.८० मि. लामो (८० सेमि नेटभन्दा माथि)। यो बलको वैध क्रसिङ स्पेस हो।</li> 
                    <li><strong>क्षेत्र विभाजन:</strong> अट्याक लाइन (Front Zone) सेन्टर लाइनदेखि ३ मि. मा हुन्छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

        # ========== लिबेरो (Libero) विस्तृत ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🛡️</div> <h3>लिबेरो (Libero) का नियम</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>पोशाक:</strong> अन्य खेलाडीभन्दा फरक रङको जर्सी अनिवार्य।</li> 
                    <li><strong>प्रतिबन्ध:</strong> सर्भिस गर्न, ब्लक गर्न, र कप्तान बन्न पाइँदैन।</li> 
                    <li><strong>अट्याक:</strong> नेटभन्दा माथिबाट अट्याक हिट गर्न पाइँदैन।</li> 
                    <li><strong>प्रतिस्थापन:</strong> ब्याक रो खेलाडीसँग विना सिट्टी असीमित साटफेर गर्न सकिन्छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_v2:
        # ========== म्याच ढाँचा र अङ्क प्रणाली ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">⏱️</div> <h3>म्याच ढाँचा र अङ्क प्रणाली</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>सेट:</strong> 'बेस्ट अफ ५' सेट। पहिलो ४ सेट २५ अङ्कका, ५ औं सेट १५ अङ्कको।</li> 
                    <li><strong>अग्रता:</strong> सेट जित्न कम्तीमा २ अङ्कको अग्रता (जस्तै: १६-१४) अनिवार्य छ।</li> 
                    <li><strong>रोटेसन:</strong> सर्भिस अधिकार पाएपछि घडीको सुई दिशा (Clockwise) मा सर्ने।</li> 
                    <li><strong>हिट्स:</strong> ब्लक बाहेक अधिकतम ३ पटक छुन पाइन्छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

        # ========== FIVB नयाँ नियम २०२५-२०२८ ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🆕</div> <h3>FIVB नयाँ नियम (२०२५-२०२८)</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>सर्भिस पोजिसन:</strong> सर्भिस गर्ने टोलीका खेलाडी कोर्टभित्र जहाँ पनि बस्न पाउँछन् (रोटेसनल अर्डर अनिवार्य छैन)।</li> 
                    <li><strong>स्क्रिनिङ:</strong> सर्भिस गर्दा हात उठाएर विपक्षीको दृष्टि छेक्न पाइँदैन।</li> 
                    <li><strong>बल फिर्ता:</strong> फ्री-जोनमा पुगेको बल ३ हिटभित्र बाहिरी भागबाटै फिर्ता ल्याउन पाइन्छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # दोस्रो रो: फल्ट र कार्ड प्रणाली
    col_v3, col_v4 = st.columns(2)

    with col_v3:
        # ========== मुख्य फल्टहरू ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">⚠️</div> <h3>मुख्य फल्टहरू (Faults)</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>डबल कन्ट्याक्ट:</strong> एकै खेलाडीले लगातार दुई पटक बल छोएमा।</li> 
                    <li><strong>नेट फल्ट:</strong> खेलको दौरान नेटको कुनै भाग छोएमा।</li> 
                    <li><strong>फुट फल्ट:</strong> सर्भिस गर्दा अन्तिम रेखा कुल्चिएमा।</li> 
                    <li><strong>फोर हिट्स:</strong> टोलीले ३ पटकभन्दा बढी बल छोएमा।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_v4:
        # ========== अनुशासन र कार्ड प्रणाली ==========
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🟥</div> <h3>अनुशासन र कार्ड प्रणाली</h3> </div> 
                <ul class="rule-list"> 
                    <li>🟨 <strong>पहेँलो:</strong> औपचारिक चेतावनी (अङ्क काटिँदैन)।</li> 
                    <li>🟥 <strong>रातो:</strong> पेनाल्टी (विपक्षीलाई १ अङ्क र सर्भिस)।</li> 
                    <li>🟨+🟥 <strong>एकै हातमा:</strong> निष्कासन (सेटभरि बाहिर)।</li> 
                    <li>🟨 🟥 <strong>अलग हातमा:</strong> अयोग्यता (पूरै म्याचबाट बाहिर)।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # बिस्तारित खण्डहरू (Expanders)
    with st.expander("🇳🇵 नेपालमा भलिबलको इतिहास र राष्ट्रिय खेल"):
        st.markdown("""
        * **इतिहास:** नेपालमा वि.सं. १९९९ देखि भलिबल खेल्न थालिएको मानिन्छ।
        * **NVA:** नेपाल भलिबल संघको स्थापना वि.सं. २०३० मा भएको हो।
        * **राष्ट्रिय खेल:** २०७४ साल जेठ ८ गते भलिबललाई नेपालको **राष्ट्रिय खेल** घोषणा गरियो।
        """)

    with st.expander("🪑 सिटिङ भलिबल (Sitting Volleyball) का नियम"):
        st.markdown("""
        * **कोर्ट:** १०×६ मिटर (सानो आकार)।
        * **नियम:** प्रहार गर्दा खेलाडीको नितम्ब (Buttocks) भुइँमा टाँसिएको हुनुपर्छ।
        * **विशेष:** विपक्षीको सर्भिसलाई सिधै ब्लक गर्न पाइन्छ।
        """)

    # सारांश
    st.markdown("---")
    st.markdown("""
        <div style="background-color: #dbeafe; padding: 15px; border-radius: 10px; border-left: 5px solid #1E40AF;"> 
            <strong>📌 भलिबल मुख्य सारांश:</strong> 
            <ul style="margin-top: 8px;"> 
                <li><strong>म्याच:</strong> बेस्ट अफ ५, २५ अङ्कको सेट (निर्णायक १५ अङ्क)।</li> 
                <li><strong>लिबेरो:</strong> रक्षात्मक विशेषज्ञ, फरक जर्सी, सर्भिस/ब्लक निषेध।</li> 
                <li><strong>नयाँ नियम:</strong> सर्भिस गर्दा टोलीको पोजिसन स्वतन्त्र रहने।</li> 
            </ul> 
        </div> 
    """, unsafe_allow_html=True)

# ==================== 🤼 कबड्डी (Kabaddi Section) ====================
with tab4:
    # ब्याजहरू (Badges)
    st.markdown("""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;"> 
            <span class="badge-sport kb">🤼 विश्व कबड्डी महासंघ (IKF)</span> 
            <span class="badge-sport kb">⏱️ ३० सेकेन्ड रेड</span> 
            <span class="badge-sport kb">📏 पुरुष: १३×१० मि | महिला: १२×८ मि</span> 
            <span class="badge-sport kb">🟨🟥 कार्ड प्रणाली</span> 
            <span class="badge-sport kb">📹 भिडियो रिभ्यु (PKL)</span> 
        </div> 
    """, unsafe_allow_html=True)

    st.info("🤼 कबड्डी (Kabaddi): यो एक शारीरिक स्फूर्ति, रणनीति र टिम सहकार्यको खेल हो। तल उल्लेखित नियमहरू अन्तर्राष्ट्रिय कबड्डी महासंघ (IKF) द्वारा मान्यता प्राप्त आधिकारिक नियमहरू हुन्।")

    # पहिलो रो: मैदान र समय संरचना
    col_k1, col_k2 = st.columns(2)

    with col_k1:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">📏</div> <h3>मैदान र खेलाडी संरचना</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>मैदानको नाप (Court Size):</strong> 
                        <ul> 
                            <li><strong>पुरुष:</strong> १३ × १० मिटर</li> 
                            <li><strong>महिला:</strong> १२ × ८ मिटर</li> 
                        </ul> 
                    </li> 
                    <li><strong>खेलाडी सङ्ख्या:</strong> टोलीमा १२ जना (मैदानमा ७ जना, ५ जना अतिरिक्त)।</li> 
                    <li><strong>बाउन्ड्री र लबी:</strong> 'स्ट्रगल' (तानातान) सुरु भएपछि मात्र 'लबी' एरिया प्रयोग गर्न पाइन्छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_k2:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">⏱️</div> <h3>समय र टाइमआउट</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>खेलको अवधि:</strong> पुरुष (२०-२० मिनेट), महिला (१५-१५ मिनेट)।</li> 
                    <li><strong>रेडको समय:</strong> एउटा रेड अधिकतम <strong>३० सेकेन्ड</strong>को हुन्छ।</li> 
                    <li><strong>टाइमआउट:</strong> प्रति हाफ ३० सेकेन्डका <strong>२ वटा</strong> टाइमआउट।</li> 
                    <li><strong>विश्राम:</strong> दुई हाफको बीचमा ५ मिनेटको ग्याप।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # दोस्रो रो: रेडिङ र डिफेन्डिङ
    col_k3, col_k4 = st.columns(2)

    with col_k3:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🏃</div> <h3>रेडिङ (आक्रमण) नियमहरू</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>क्यान्ट (Cant):</strong> रेडरले निरन्तर "कबड्डी-कबड्डी" भन्नुपर्छ।</li> 
                    <li><strong>बोनस अंक:</strong> ६ वा ७ डिफेन्डर हुँदा बोनस लाइन पार गरेमा १ अंक।</li> 
                    <li><strong>डु-अर-डाइ (Do-or-Die):</strong> लगातार २ खाली रेडपछि तेस्रोमा अंक अनिवार्य।</li> 
                    <li><strong>अंक प्राप्ति:</strong> छोए जति खेलाडी बराबर अंक र उनीहरू आउट।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_k4:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🛡️</div> <h3>डिफेन्स र विशेष अंक</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>सुपर ट्याकल:</strong> ३ वा कम डिफेन्डरले रेडर समातेमा <strong>२ अंक</strong>।</li> 
                    <li><strong>लोना (All-Out):</strong> विपक्षी सबै आउट गरेमा थप <strong>२ अंक</strong>।</li> 
                    <li><strong>पुनर्जीवन (Revival):</strong> आफ्नो टिमले अंक पाउँदा आउट भएका खेलाडी क्रमैसँग फर्कन्छन्।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # तेस्रो रो: सब्स्टिच्युसन र कार्ड
    col_k5, col_k6 = st.columns(2)

    with col_k5:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🔄</div> <h3>सब्स्टिच्युसन र फाउल</h3> </div> 
                <ul class="rule-list"> 
                    <li><strong>सब्स्टिच्युसन:</strong> ५ जना अतिरिक्त मध्येबाट परिवर्तन गर्न पाइने।</li> 
                    <li><strong>निषेध:</strong> कपाल, कपडा वा घाँटीमा समात्न पाइँदैन।</li> 
                    <li><strong>प्राविधिक अंक:</strong> नियम तोडेमा विपक्षीलाई १ अंक दिइन्छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    with col_k6:
        st.markdown("""
            <div class="rule-card"> 
                <div class="card-header"> <div class="card-icon">🟨🟥</div> <h3>कार्ड र अनुशासन</h3> </div> 
                <ul class="rule-list"> 
                    <li>🟩 <strong>हरियो:</strong> सामान्य चेतावनी।</li> 
                    <li>🟨 <strong>पहेँलो:</strong> २ मिनेट निलम्बन (एक खेलाडी कम हुन्छ)।</li> 
                    <li>🟥 <strong>रातो:</strong> पूरै म्याचबाट निष्कासन।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)

    # चौथो रो: अफिसियल र भिडियो रिभ्यु
    with st.expander("👥 अफिसियल (Officials) र भिडियो रिभ्यु सम्बन्धी विस्तृत जानकारी"):
        st.markdown("""
        **📋 अधिकारीहरूको संरचना:**
        * १ रेफ्री, २ अम्पायर, १ स्कोरर, र २ सहायक स्कोरर।
        
        **📹 भिडियो रिभ्यु (Video Review):**
        * निर्णयमा शंका लागेमा टोलीले रिभ्यु माग्न सक्छन्। 
        * सफल भएमा रिभ्यु कायम रहन्छ, असफल भएमा गुम्छ।
        """)

    # पाँचौँ: बराबरी
    st.markdown("""
        <div class="rule-card" style="border-left: 5px solid #B91C1C; margin-top: 20px;"> 
            <div class="card-header"> <div class="card-icon">🏆</div> <h3>विजेता र बराबरी</h3> </div> 
            <ul class="rule-list"> 
                <li><strong>बराबरी भएमा:</strong> ५-५ मिनेटको अतिरिक्त समय थपिन्छ।</li> 
                <li><strong>गोल्डन रेड:</strong> अतिरिक्त समयमा पनि बराबरी भएमा प्रयोग गरिन्छ।</li> 
            </ul> 
        </div> 
    """, unsafe_allow_html=True)

    # सारांश
    st.markdown("---")
    st.markdown("""
        <div style="background-color: #fee2e2; padding: 15px; border-radius: 10px; border-left: 5px solid #B91C1C;"> 
            <strong>📌 कबड्डी मुख्य सारांश:</strong> 
            <ul style="margin-top: 8px;"> 
                <li><strong>संरचना:</strong> ७ खेलाडी, ३० सेकेन्ड रेड, क्यान्ट अनिवार्य।</li> 
                <li><strong>अंक:</strong> टच, बोनस, सुपर ट्याकल (२ अंक), लोना (२ अंक)।</li> 
                <li><strong>अनुशासन:</strong> पहेँलो कार्डले २ मिनेट टिमलाई घाटा पुग्छ।</li> 
            </ul> 
        </div> 
    """, unsafe_allow_html=True)

# ==================== 🥋 मार्शल आर्ट्स (Karate, Taekwondo, Wushu) ====================
with tab5:
    st.markdown("""
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;"> 
            <span class="badge-sport ma">🥋 WKF २०२६ अद्यावधिक</span> 
            <span class="badge-sport ma">⚖️ बहुमत निर्णय (Kata)</span> 
            <span class="badge-sport ma">⏱️ समान ३ मिनेट (Kumite)</span> 
            <span class="badge-sport ma">🛡️ एकीकृत पेनाल्टी</span> 
        </div> 
    """, unsafe_allow_html=True)

    # उप-ट्याबहरू (Sub-tabs)
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["🥋 कराँते (Karate)", "🥋 तेक्वान्दो (Taekwondo)", "🥋 उसु (Wushu)"])

    # ---------- १. कराँते (WKF 2026 Rules) ----------
    with sub_tab1:
        st.markdown("<h3 style='color:#1e293b; border-bottom:2px solid #e2e8f0; padding-bottom:10px;'>विश्व कराते महासंघ (WKF) २०२६ आधिकारिक नियम</h3>", unsafe_allow_html=True)
        
        col_kr1, col_kr2 = st.columns(2)

        # ================== काता (KATA) ==================
        with col_kr1:
            st.markdown("""
                <div class="rule-card" style="border-left: 5px solid #0f172a;"> 
                    <div class="card-header"> <div class="card-icon">🧘‍♂️</div> <h3>काता (Kata) नियम</h3> </div> 
                    <ul class="rule-list"> 
                        <li><strong>क्षेत्र:</strong> ८m × ८m म्याट।</li> 
                        <li><strong>मूल्याङ्कन (२०२६):</strong> अंक प्रणाली खारेज। अब <strong>'बहुमत भोटिङ' (Majority Vote)</strong> बाट विजेता छानिन्छ।</li> 
                        <li><strong>नाटकीयता प्रतिबन्ध:</strong> भुइँमा खुट्टा बजार्ने (Stomping), गी (Gi) मा हिर्काउने वा अस्वाभाविक सास फेर्ने कार्य निषेध।</li> 
                        <li><strong>पोशाक:</strong> करातोगीलाई स्टार्च गरेर कडा बनाउन पाइँदैन। <strong>स्पोर्ट ग्लास</strong> लगाउन अनुमति छ।</li> 
                    </ul> 
                </div> 
            """, unsafe_allow_html=True)

        # ================== कुमिते (KUMITE) ==================
        with col_kr2:
            st.markdown("""
                <div class="rule-card" style="border-left: 5px solid #dc2626;"> 
                    <div class="card-header"> <div class="card-icon">🤼‍♂️</div> <h3>कुमिते (Kumite) नियम</h3> </div> 
                    <ul class="rule-list"> 
                        <li><strong>अङ्क प्रणाली:</strong> 
                            <ul> 
                                <li><strong>इप्पोन (३ अंक):</strong> टाउको/घाँटीमा किक वा फालेर प्रहार।</li> 
                                <li><strong>वाजा-अरी (२ अंक):</strong> शरीर (पेट/छाती) मा किक।</li> 
                                <li><strong>युको (१ अंक):</strong> टाउको/शरीरमा पन्च।</li> 
                            </ul> 
                        </li> 
                        <li><strong>खेल अवधि:</strong> सिनियर पुरुष र महिला दुवैलाई <strong>३ मिनेट</strong> समान।</li> 
                        <li><strong>पेनाल्टी (एकीकृत):</strong> C1/C2 खारेज। अब सबै फउल एउटै शृङ्खलामा: <strong>चुई (१–३) → हान्सोकु-चुई → हान्सोकु (आउट)</strong>।</li> 
                        <li><strong>सुरक्षा:</strong> लडेको विपक्षीलाई <strong>किक हान्न पूर्ण प्रतिबन्ध</strong> (हातको प्रविधि मात्र मान्य)।</li> 
                    </ul> 
                </div> 
            """, unsafe_allow_html=True)

        # विस्तृत व्याख्या (Expandable Section)
        with st.expander("📘 WKF २०२६ नियम परिवर्तनको विस्तृत विश्लेषण (पुरानो बनाम नयाँ)"):
            st.markdown("""
            ### १. पेनाल्टी प्रणालीको एकीकरण
            विगतमा C1 र C2 फउल छुट्टाछुट्टै गनिन्थे। २०२६ देखि सबै गल्तीहरूलाई एउटै बास्केटमा राखिएको छ। यसले खेलाडीलाई रणनीतिक रूपमा फउल गर्नबाट रोक्छ।
            
            ### २. लैङ्गिक समानता
            महिला खेलाडीहरूको खेल अवधि २ मिनेटबाट बढाएर ३ मिनेट (पुरुष सरह) पुर्‍याइएको छ। 
            
            ### ३. कातामा शुद्धता
            अंक दिनुको साटो जजहरूले सिधै नीलो वा रातो झण्डा उठाएर विजेता रोज्नेछन् (Majority Vote)।
            """)

            # तुलना तालिका
            st.markdown("""
            | प्राविधिक मापदण्ड | पुरानो नियम | २०२६ नयाँ नियम |
            | :--- | :--- | :--- |
            | **पेनाल्टी वर्ग** | C1 र C2 (छुट्टाछुट्टै) | एकीकृत प्रणाली (C1/C2 खारेज) |
            | **काता मूल्याङ्कन** | ५.० – १०.० अंक | बहुमत भोटिङ (Majority Vote) |
            | **महिला खेल समय** | २ मिनेट | ३ मिनेट |
            | **लडेको विपक्षी** | किक हान्न पाइन्थ्यो | किक पूर्ण निषेध (फउल) |
            | **चस्मा** | निषेध | प्रेस्क्रिप्सन स्पोर्ट ग्लास अनुमति |
            """)

    # ------------------ २. तेक्वान्दो (WT Rules - 2026 Update) ------------------
    with sub_tab2:
        st.markdown("<h3 style='color:#1e293b; border-bottom:2px solid #e2e8f0; padding-bottom:10px;'>विश्व तेक्वान्दो (WT) नियम - २०२६ अद्यावधिक</h3>", unsafe_allow_html=True)
        
        # ब्याजहरू (Badges)
        st.markdown("""
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;"> 
                <span class="badge-sport ma">⚡ ग्योरोगी (स्पारिङ)</span> 
                <span class="badge-sport ma">🧘 पुम्से (फर्म)</span> 
                <span class="badge-sport ma">🔄 टर्निङ किक ४/६ अङ्क</span> 
                <span class="badge-sport ma">⏱️ प्यासिभ पेनाल्टी (१० सेकेन्ड)</span> 
                <span class="badge-sport ma">🛡️ ५ गाम्जोममा DQ</span> 
            </div> 
        """, unsafe_allow_html=True)

        col_tk1, col_tk2 = st.columns(2)

        # ================== पुम्से (POOMSAE) ==================
        with col_tk1:
            st.markdown("""
                <div class="rule-card" style="border-left: 5px solid #0f172a;"> 
                    <div class="card-header"> <div class="card-icon">🧘‍♀️</div> <h3>पुम्से (Poomsae) - परम्परा र फ्रिस्टाइल</h3> </div> 
                    <ul class="rule-list"> 
                        <li><strong>मूल्याङ्कन (कुल १०.०):</strong> शुद्धता (४.०) र प्रस्तुतीकरण (६.०)।</li> 
                        <li><strong>नयाँ फ्रिस्टाइल नियम (२०२६):</strong> 
                            <ul> 
                                <li><strong>एक्रोब्याटिक्स:</strong> अधिकतम ३ वटा मात्र। थप भएमा ०.३ कटौती।</li> 
                                <li><strong>८०% घुँडा नियम:</strong> हावामा किक हान्दा घुँडा पूर्ण तन्किएको हुनुपर्ने।</li> 
                                <li><strong>अनिवार्य स्टान्स:</strong> टाइगर, ब्याक र क्रेन स्टान्स मध्ये एक छुटेमा ०.३ कटौती।</li> 
                            </ul> 
                        </li> 
                        <li><strong>समय:</strong> रिकग्नाइज्ड ३०-९० सेकेन्ड, फ्रिस्टाइल ९०-१०० सेकेन्ड।</li> 
                        <li><strong>निषेध:</strong> सङ्गीतमा मानव आवाज/गीत भएमा सिधै अयोग्य (DSQ)।</li> 
                    </ul> 
                </div> 
            """, unsafe_allow_html=True)

        # ================== ग्योरोगी (KYORUGI) ==================
        with col_tk2:
            st.markdown("""
                <div class="rule-card" style="border-left: 5px solid #dc2626;"> 
                    <div class="card-header"> <div class="card-icon">🥷</div> <h3>ग्योरोगी (Kyorugi) - स्पारिङ</h3> </div> 
                    <ul class="rule-list"> 
                        <li><strong>नयाँ अङ्क प्रणाली (२०२६):</strong> 
                            <ul> 
                                <li><strong>१/२ अङ्क:</strong> चेस्टमा मुक्का (१) वा सामान्य किक (२)।</li> 
                                <li><strong>३ अङ्क:</strong> टाउकोमा सामान्य किक।</li> 
                                <li><strong>४ अङ्क:</strong> चेस्टमा टर्निङ/स्पिनिङ किक (दोब्बर अंक)।</li> 
                                <li><strong>६ अङ्क:</strong> टाउकोमा टर्निङ/स्पिनिङ किक (दोब्बर अंक)।</li> 
                            </ul> 
                        </li> 
                        <li><strong>पेनाल्टी (Gam-jeom):</strong> अब <strong>५ गाम्जोम</strong> पुगेपछि खेलाडी अयोग्य (DQ) हुने।</li> 
                        <li><strong>पावर प्ले (२०२६):</strong> प्यासिभ पेनाल्टीपछि १० सेकेन्डसम्म विपक्षीले पाउने अंक <strong>दोब्बर</strong> हुनेछ।</li> 
                        <li><strong>ढाँचा:</strong> बेस्ट अफ ३ राउन्ड (प्रति राउन्ड २ मिनेट)।</li> 
                    </ul> 
                </div> 
            """, unsafe_allow_html=True)

        # रणनीतिक परिवर्तनहरू (Expander)
        with st.expander("🔍 ग्योरोगीका थप रणनीतिक नियम र परिवर्तनहरू (२०२६)"):
            st.markdown("""
            **१. भिडियो रिभ्यु (IVR) परिमार्जन:**
            अब प्रशिक्षकले टाउकोको किकका लागि रिभ्यु माग्न पाउने छैनन्। केवल सेन्टर रेफ्रीले आवश्यक ठानेमा मात्र भिडियो हेरिनेछ।
            
            **२. रेफ्री संख्या:**
            निर्णय प्रक्रिया छिटो बनाउन अब म्याटमा ३ जना मात्र रेफ्री (१ सेन्टर + २ जज) रहनेछन्।
            
            **३. सुपेरियोरिटी (बराबरी भएमा):**
            राउन्ड बराबरी भएमा: १. बढी टाउको प्रहार गर्ने २. बढी टर्निङ किक गर्ने ३. बढी आक्रामक देखिएको आधारमा विजेता छानिनेछ।
            """)

        # अङ्क तुलना तालिका
        st.markdown("""
            <div style="background: white; padding: 1.5rem; border-radius: 20px; margin-top: 1rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);"> 
                <h4 style="margin-top:0; color:#1e293b;">⚖️ पुरानो बनाम नयाँ (२०२६) अङ्क प्रणाली तुलना</h4> 
                <table style="width:100%; border-collapse: collapse;"> 
                    <tr style="background:#f8fafc;"> 
                        <th style="padding:10px; text-align:left;">प्रहार प्रकार</th> 
                        <th style="padding:10px; text-align:center;">पुरानो अङ्क</th> 
                        <th style="padding:10px; text-align:center;">२०२६ अङ्क</th> 
                    </tr> 
                    <tr style="border-bottom:1px solid #e2e8f0;"> 
                        <td style="padding:10px;">चेस्टमा मुक्का / किक</td> 
                        <td style="padding:10px; text-align:center;">१ / २</td> 
                        <td style="padding:10px; text-align:center; background:#fef9c3; font-weight:600;">१ / २</td> 
                    </tr> 
                    <tr style="border-bottom:1px solid #e2e8f0;"> 
                        <td style="padding:10px;">टाउकोमा सामान्य किक</td> 
                        <td style="padding:10px; text-align:center;">३</td> 
                        <td style="padding:10px; text-align:center; background:#fef9c3; font-weight:600;">३</td> 
                    </tr> 
                    <tr style="border-bottom:1px solid #e2e8f0;"> 
                        <td style="padding:10px;">चेस्टमा टर्निङ किक</td> 
                        <td style="padding:10px; text-align:center;">४</td> 
                        <td style="padding:10px; text-align:center; background:#fee2e2; font-weight:700; color:#B91C1C;">४</td> 
                    </tr> 
                    <tr> 
                        <td style="padding:10px;">टाउकोमा टर्निङ किक</td> 
                        <td style="padding:10px; text-align:center;">५</td> 
                        <td style="padding:10px; text-align:center; background:#fee2e2; font-weight:700; color:#B91C1C;">६ (दोब्बर)</td> 
                    </tr> 
                </table> 
            </div> 
        """, unsafe_allow_html=True)

        # सारांश
        st.markdown("""
            <div style="background-color: #f1f0ff; padding: 15px; border-radius: 10px; border-left: 5px solid #5b21b6; margin-top: 20px;"> 
                <strong>📌 तेक्वान्दो मुख्य सारांश (२०२६):</strong> 
                <ul style="margin-top: 8px;"> 
                    <li><strong>पुम्से:</strong> फ्रिस्टाइलमा एक्रोब्याटिक्स सीमा (३) र ८०% घुँडा तन्काउनुपर्ने नियम कडा पारिएको।</li> 
                    <li><strong>ग्योरोगी:</strong> ५ गाम्जोममा DQ, टर्निङ किकको अंक ६ पुर्‍याइएको, र पावर प्ले (डबल पोइन्ट) को सुरुवात।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)
        
    # ------------------ ३. उसु (Wushu - IWUF Rules 2025/2026) ------------------
    with sub_tab3:
        st.markdown("<h3 style='color:#1e293b; border-bottom:2px solid #e2e8f0; padding-bottom:10px;'>अन्तर्राष्ट्रिय उसु महासंघ (IWUF) नियम - २०२५/२०२६ अद्यावधिक</h3>", unsafe_allow_html=True)
        
        # ब्याजहरू (Badges)
        st.markdown("""
            <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;"> 
                <span class="badge-sport ma">🥊 सान्डा (फुल कन्ट्याक्ट)</span> 
                <span class="badge-sport ma">🗡️ थाउलो (कला प्रदर्शन)</span> 
                <span class="badge-sport ma">📊 १०-अङ्क प्रणाली (A/B/C)</span> 
                <span class="badge-sport ma">⚖️ नन्दु (कठिनाई) २.० अङ्क</span> 
                <span class="badge-sport ma">🛡️ हेडगियर अनिवार्य</span> 
            </div> 
        """, unsafe_allow_html=True)

        col_wu1, col_wu2 = st.columns(2)

        # ================== सान्डा (SANDA) ==================
        with col_wu1:
            st.markdown("""
                <div class="rule-card" style="border-left: 5px solid #dc2626;"> 
                    <div class="card-header"> <div class="card-icon">🥊</div> <h3>सान्डा (Sanda) - फुल कन्ट्याक्ट फाइट</h3> </div> 
                    <ul class="rule-list"> 
                        <li><strong>क्षेत्र (Leitai):</strong> ८m × ८m डोरीविहीन प्लेटफर्म, भुइँबाट ८० से.मी. अग्लो।</li> 
                        <li><strong>अङ्क प्रणाली:</strong> 
                            <ul> 
                                <li><strong>२ अङ्क:</strong> विपक्षीलाई प्लेटफर्मबाट खसाल्दा, थ्रोइङ (आफू उभिँदा), टाउको/धडमा शक्तिशाली किक।</li> 
                                <li><strong>१ अङ्क:</strong> टाउको/धडमा पन्च, तिघ्रामा किक, विपक्षी ८ सेकेन्ड निष्क्रिय भएमा।</li> 
                            </ul> 
                        </li> 
                        <li><strong>अवधि:</strong> ३ राउन्ड × २ मिनेट (बिचमा १ मिनेट विश्राम)।</li> 
                        <li><strong>जित:</strong> ३ मध्ये २ राउन्ड जितेमा, नकआउट भएमा वा १२ अङ्कको अन्तर (Absolute Victory) भएमा।</li> 
                    </ul> 
                </div> 
            """, unsafe_allow_html=True)

            with st.expander("🔍 सान्डाका विस्तृत नियम (तौल समूह र पेनाल्टी)"):
                st.markdown("""
                **तौल समूह:** * पुरुष: ४८ केजी देखि ९०+ केजी सम्म (११ वर्ग)। 
                * महिला: ४८ केजी देखि ७५ केजी सम्म (७ वर्ग)।
                
                **पेनाल्टी:** * **Admonition (१ अङ्क कटौती):** समय खेर फाल्नु वा पन्च नखोल्नु।
                * **Warning (२ अङ्क कटौती):** प्रतिबन्धित क्षेत्र (घाँटी, कम्मर मुनि) मा प्रहार गर्नु।
                * ३ पटक 'Warning' पाएमा खेलाडी अयोग्य (DQ) हुनेछ।
                """)

        # ================== थाउलो (TAOLU) ==================
        with col_wu2:
            st.markdown("""
                <div class="rule-card" style="border-left: 5px solid #0f172a;"> 
                    <div class="card-header"> <div class="card-icon">🗡️</div> <h3>थाउलो (Taolu) - कलात्मक प्रदर्शन</h3> </div> 
                    <ul class="rule-list"> 
                        <li><strong>मूल्याङ्कन (१०.० अङ्क):</strong> 
                            <ul> 
                                <li><strong>समूह A (५.०):</strong> चालको गुणस्तर (Quality) - सन्तुलन गुमे ०.१, लडे ०.३ कटौती।</li> 
                                <li><strong>समूह B (३.०):</strong> समग्र प्रदर्शन (Overall) - शक्ति, लय र संगीत तालमेल।</li> 
                                <li><strong>समूह C (२.०):</strong> कठिनाई (Nandu) - जम्प र कम्बिनेसन।</li> 
                            </ul> 
                        </li> 
                        <li><strong>समय:</strong> १ मिनेट २० सेकेन्ड (चाङ्क्वान), ३-४ मिनेट (ताइची)।</li> 
                        <li><strong>नन्दु:</strong> एउटै जम्प २ पटक भन्दा बढी गर्न नपाइने।</li> 
                    </ul> 
                </div> 
            """, unsafe_allow_html=True)

            with st.expander("🔍 थाउलोका विस्तृत नियम (Nandu र शैली)"):
                st.markdown("""
                **नन्दु ग्रेड (Nandu Grades):**
                * ग्रेड A (०.२०): ३६०° जम्प।
                * ग्रेड B (०.३०): ५४०° जम्प।
                * ग्रेड C (०.४०): ७२०° जम्प।
                
                **शैलीहरू:** चाङ्क्वान (गति), नान्क्वान (शक्ति), ताइचीक्वान (सन्तुलन)। 
                **हतियार:** जियान्सु (तरवार), दाओसु (ब्रोडस्वोर्ड), गुन्शु (लट्ठी) आदि।
                """)

        # मूल्याङ्कन तालिका
        st.markdown("""
            <div style="background: white; padding: 1.5rem; border-radius: 20px; margin-top: 1rem; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);"> 
                <h4 style="margin-top:0; color:#1e293b;">📊 थाउलो मूल्याङ्कन संरचना (१० अङ्क)</h4> 
                <table style="width:100%; border-collapse: collapse;"> 
                    <tr style="background:#f8fafc;"> 
                        <th style="padding:10px; text-align:left;">समूह</th> 
                        <th style="padding:10px; text-align:center;">अङ्कभार</th> 
                        <th style="padding:10px; text-align:left;">मूल्याङ्कन विषय</th> 
                    </tr> 
                    <tr style="border-bottom:1px solid #e2e8f0;"> 
                        <td style="padding:10px;">A</td> 
                        <td style="padding:10px; text-align:center;">५.०</td> 
                        <td style="padding:10px;">चालको गुणस्तर (त्रुटि कटौती)</td> 
                    </tr> 
                    <tr style="border-bottom:1px solid #e2e8f0;"> 
                        <td style="padding:10px;">B</td> 
                        <td style="padding:10px; text-align:center;">३.०</td> 
                        <td style="padding:10px;">समग्र प्रदर्शन (शक्ति, लय, सङ्गीत)</td> 
                    </tr> 
                    <tr> 
                        <td style="padding:10px;">C</td> 
                        <td style="padding:10px; text-align:center;">२.०</td> 
                        <td style="padding:10px;">नन्दु (कठिनाई प्रविधि + जडान)</td> 
                    </tr> 
                </table> 
            </div> 
        """, unsafe_allow_html=True)

        # सारांश
        st.markdown("""
            <div style="background-color: #f1f0ff; padding: 15px; border-radius: 10px; border-left: 5px solid #5b21b6; margin-top: 20px;"> 
                <strong>📌 उसु मुख्य सारांश (IWUF २०२५/२६):</strong> 
                <ul style="margin-top: 8px;"> 
                    <li><strong>सान्डा:</strong> लेइताई प्लेटफर्म, थ्रोइङ र किकको मुख्य अंक, ३ राउन्डमा २ जित।</li> 
                    <li><strong>थाउलो:</strong> १०-अङ्क प्रणाली, नन्दु (जम्प) को महत्वपूर्ण भूमिका, समय सीमा पालना अनिवार्य।</li> 
                    <li><strong>सुरक्षा:</strong> दुवै विधामा आधिकारिक सुरक्षा उपकरण र हेडगियर अनिवार्य गरिएको छ।</li> 
                </ul> 
            </div> 
        """, unsafe_allow_html=True)
    
# ==================== 🏃‍♂️ एथलेटिक्स (अपडेटेड) ====================
with tab6:
    # ब्याजहरू
    st.markdown("""
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
        <span class="badge-sport gen">🏃‍♂️ ट्र्याक (Track)</span>
        <span class="badge-sport gen">🤾‍♂️ फिल्ड (Field)</span>
        <span class="badge-sport gen">⏱️ फोटो फिनिस / टाइमिङ</span>
        <span class="badge-sport gen">👟 स्पाइक्स नियम</span>
        <span class="badge-sport gen">📋 हिट्स / फाइनल</span>
        <span class="badge-sport gen">🔔 ल्याप काउन्ट / बेल</span>
    </div>
    """, unsafe_allow_html=True)

    st.info("🏃‍♂️ **एथलेटिक्स (Athletics):** दौड (स्प्रिन्ट, मध्यदूरी, रिले) र फिल्ड इभेन्ट (जम्प, थ्रो) का अन्तर्राष्ट्रिय नियमहरू यहाँ समावेश गरिएका छन्। सबै नियम **World Athletics** द्वारा मान्यता प्राप्त छन्।")

    # दुई स्तम्भ
    col_a1, col_a2 = st.columns(2)

    with col_a1:
        # ========== स्प्रिन्ट (छोटो दूरी) ==========
        st.markdown("""
        <div class="rule-card" style="border-left: 5px solid #2563eb;">
            <div class="card-header">
                <div class="card-icon">⚡</div>
                <h3>छोटो दूरी (Sprint: 100m, 200m, 400m)</h3>
            </div>
            <ul class="rule-list">
                <li><strong>तयारी (Preparation):</strong> खेलाडीहरूलाई <strong>स्टार्टिङ ब्लक</strong>मा उभ्याइन्छ। आदेश क्रम: <code>'On your marks' → 'Set' → पिस्टल</code>। बन्दुक चल्नुअघि दौडिएमा <strong>False Start</strong> मानी सिधै आउट गरिन्छ।</li>
                <li><strong>लेन प्रयोग (Lane Discipline):</strong> सुरुदेखि अन्त्यसम्म <strong>आफ्नै लेन</strong>मा दौडनुपर्छ। लेन बाहिर निस्किएमा वा अर्को खेलाडीलाई अवरोध गरेमा अयोग्य (DQ) हुन्छ।</li>
                <li><strong>समाप्ति (Finish):</strong> जसको <strong>धड (Torso)</strong> सबैभन्दा पहिले फिनिस लाइन छुन्छ, ऊ विजेता हुन्छ (हात वा टाउकोले छोएर हुँदैन)। समय मापन इलेक्ट्रोनिक टाइमिङ वा फोटो-फिनिसबाट गरिन्छ।</li>
                <li><strong>चरणहरू (Heats → Semifinals → Finals):</strong> धेरै खेलाडी भएमा प्रतियोगितालाई हिट्समा विभाजन गरिन्छ। प्रत्येक हिटबाट पहिलो-दोस्रो स्थान वा <strong>छिटो समय (q)</strong> भएका खेलाडीहरू अर्को चरणमा पुग्छन्। <strong>Q = स्थानबाट छनोट, q = समयबाट छनोट</strong>।</li>
                <li><strong>बोलाउने प्रणाली (Calling System):</strong>
                    <ul>
                        <li><strong>First Call:</strong> प्रतियोगिता सुरु हुनु १५–२० मिनेटअगाडि घोषणा।</li>
                        <li><strong>Second Call:</strong> करिब १० मिनेटअगाडि पुनः घोषणा।</li>
                        <li><strong>Final Call:</strong> करिब ५ मिनेटअगाडि अन्तिम घोषणा; रिपोर्टिङ एरिया बन्द हुन्छ। ढिलो आएका खेलाडीलाई सहभागी गराइँदैन।</li>
                    </ul>
                </li>
                <li><strong>चेस्ट नम्बर (Bib Number):</strong> प्रत्येक खेलाडीलाई चेस्ट नम्बर दिइन्छ, जुन छाती र पछाडि स्पष्ट देखिने गरी लगाउनुपर्छ। यो नै खेलाडीको पहिचान हो।</li>
                <li><strong>लेन नम्बर (Lane Assignment):</strong> ड्र वा सिडिङअनुसार लेन निर्धारण हुन्छ। घोषणा गर्दा: <em>“हिट १, लेन ३ — चेस्ट नम्बर ४५”</em> जस्ता सूचना दिइन्छ।</li>
                <li><strong>अन्य नियम:</strong> धक्का, अवरोध, वा अनुचित लाभ लिन पाइँदैन। जुत्ता र उपकरण नियमअनुसार हुनुपर्छ।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # ========== मध्य दूरी (८००m, १५००m, ३०००m) ==========
        st.markdown("""
        <div class="rule-card" style="border-left: 5px solid #059669;">
            <div class="card-header">
                <div class="card-icon">🏃‍♂️</div>
                <h3>मध्य दूरी (800m, 1500m, 3000m) र ल्याप काउन्ट</h3>
            </div>
            <p style="font-size: 0.95rem; color: #475569; margin-bottom: 5px;"><strong>🏟️ २०० मिटर ट्र्याकका लागि विशेष गणना:</strong></p>
            <ul class="rule-list">
                <li><strong>८०० मिटर:</strong> २०० मि. ट्र्याकमा <strong>४ ल्याप</strong> (४ पटक घुम्नुपर्ने)। सुरुमा स्ट्यागर्ड स्टार्ट; पहिलो १०० मि. आ–आफ्नै लेनमा, त्यसपछि <strong>ब्रेक लाइन</strong> काटेर भित्री लेन प्रयोग गर्न पाइन्छ।</li>
                <li><strong>१५०० मिटर:</strong> २०० मि. ट्र्याकमा <strong>७ ल्याप + १०० मि.</strong> (७ पटक पूरा घुम्ती + थप १०० मि.)। कमन कर्भ्ड स्टार्ट; सुरुदेखि नै कमन ट्र्याक प्रयोग गरिन्छ।</li>
                <li><strong>३००० मिटर:</strong> २०० मि. ट्र्याकमा <strong>१५ ल्याप</strong> (१५ पटक पूरा घुम्ती)।</li>
                <li><strong>ल्याप काउन्टिङ प्रणाली:</strong> अन्तिम ल्याप सुरु हुँदा <strong>घण्टी (Bell)</strong> बजाइन्छ। ल्याप गन्ने जिम्मा अफिसियलको भए पनि, खेलाडी आफैँले ल्याप गलत बुझेर दौड छोडेमा स्वतः आउट हुन्छ।</li>
                <li><strong>सुरु (Start):</strong> ८०० मि.मा स्ट्यागर्ड स्टार्ट (Split start); १५००/३००० मि.मा कमन कर्भ्ड स्टार्ट लाइन। आदेश: ‘On your marks’ → ‘Set’ → पिस्टल।</li>
                <li><strong>धक्का/अवरोध निषेध:</strong> कमन ट्र्याकमा दौड्दा पनि अरूलाई धक्का दिन वा अवरोध गर्न पाइँदैन।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # ========== रिले दौड (विस्तृत) ==========
        with st.expander("🔄 रिले दौड (Relay: 4x100m र 4x400m) का विस्तृत नियमहरू"):
            st.markdown("""
            **📌 टिम संरचना:** प्रत्येक टिममा ४ खेलाडी, सबैले बराबर दूरी दौड्ने र **ब्याटन (Baton)** एक अर्कालाई पास गर्ने।

            ---
            **🏃 ४x१०० मिटर रिले (4x100m):**
            * प्रत्येक खेलाडीले १०० मि. दौडन्छ। सुरुदेखि अन्त्यसम्म **आफ्नै लेनमा मात्र** दौडनुपर्छ।
            * **एक्सचेन्ज जोन (Exchange Zone):** २० मिटर लामो (अर्को लेग सुरु हुने स्थानभन्दा १० मि. अगाडि र १० मि. पछाडि)। यही क्षेत्रभित्र मात्र ब्याटन पास गर्नुपर्छ।
            * ब्याटन झरेमा वा जोनबाहिर पास गरेमा टिम आउट हुन्छ। पास गर्दा प्रायः इन्कमिङ रनरले आवाज दिन्छ र आउटगोइङ रनरले हात पछाडि फैलाएर ब्याटन लिन्छ।

            **🏃 ४x४०० मिटर रिले (4x400m):**
            * प्रत्येक खेलाडीले ४०० मि. (एक ल्याप) दौडन्छ।
            * **पहिलो खेलाडी:** आ–आफ्नै लेनमा स्ट्यागर्ड स्टार्टबाट दौडन्छ।
            * **ब्याटन पास:** पहिलो ब्याटन ह्यान्डओभरपछि दोस्रो खेलाडीले ब्रेक लाइन काटेपछि मात्र भित्री लेन (कमन ट्र्याक) प्रयोग गर्न पाउँछ।
            * एक्सचेन्ज जोन २० मि. नै हुन्छ। ब्याटन पास गर्दा धक्कामुक्की गर्न पाइँदैन।

            **📊 २०० मि. ट्र्याकमा एक्सचेन्ज जोनको अवस्थिति:** ट्र्याक छोटो भएकाले आधा घुम्तीमा पास हुन सक्छ। तर जोनको लम्बाइ २० मि. नै रहन्छ।

            **🔹 ब्याटन विशेषता:**
            * लम्बाइ २८–३० सेमी, तौल करिब ५० ग्राम।
            * दौडभरि हातमै राख्नुपर्छ। फिनिस लाइन ब्याटनसहित पार गरेपछि मात्र दौड पूरा हुन्छ।
            """)

    with col_a2:
        # ========== जम्पिङ इभेन्ट्स ==========
        st.markdown("""
        <div class="rule-card" style="border-left: 5px solid #d97706;">
            <div class="card-header">
                <div class="card-icon">🦘</div>
                <h3>जम्पिङ (Jumps: High, Long, Triple)</h3>
            </div>
            <ul class="rule-list">
                <li><strong>हाइ जम्प (High Jump):</strong> <strong>एक खुट्टाले मात्र</strong> टेक-अफ गर्नुपर्छ। बार (Crossbar) खसेमा प्रयास अमान्य। बराबरी (Tie) भएमा <strong>Count-back नियम</strong>:
                    <ol style="margin-top: 5px; margin-bottom: 5px;">
                        <li>कम प्रयासमा सफल भएको खेलाडी अगाडि।</li>
                        <li>त्यसपछि कम असफल प्रयास भएको खेलाडी अगाडि।</li>
                        <li>यदि अझै बराबरी भए <strong>Jump-off</strong> (बार घटाएर एक–एक प्रयास)।</li>
                    </ol>
                </li>
                <li><strong>लङ जम्प (Long Jump):</strong> <strong>टेक-अफ बोर्ड</strong> (२० सेमी चौडा) भित्रबाट जम्प गर्नुपर्छ। रनवे कम्तीमा ४० मि. लामो हुन्छ। बालुवामा शरीरले छोएको सबैभन्दा पछिल्लो डोबबाट बोर्डको नजिकको किनारासम्म दूरी नापिन्छ। (साधारणतः ३ प्रयास; ठूला प्रतियोगितामा ६ प्रयास।)</li>
                <li><strong>ट्रिपल जम्प (Triple Jump):</strong> अनिवार्य क्रम: <strong>Hop (उही खुट्टा) → Step (अर्को खुट्टा) → Jump (बालुवामा)</strong> हुनुपर्छ। उदाहरण: दायाँ खुट्टाबाट हप गरे दायाँमै ल्यान्ड, त्यसपछि स्टेपमा बायाँ खुट्टा, अन्तिम जम्प दुवै खुट्टाले बालुवामा। यो क्रम बिग्रेमा फाउल हुन्छ।</li>
                <li><strong>मापन विधि:</strong> टेक-अफ बोर्डको नजिकको किनाराबाट बालुवामा शरीरको कुनै पनि भागले बनाएको सबैभन्दा नजिकको चिन्हसम्म सिधा नापिन्छ।</li>
                <li><strong>प्रयास:</strong> सामान्यतया ३ प्रयास, उत्कृष्ट दूरी/उचाइको आधारमा विजेता। फाउल भएको प्रयास गणना हुँदैन।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # ========== थ्रोइङ इभेन्ट्स ==========
        st.markdown("""
        <div class="rule-card" style="border-left: 5px solid #7c3aed;">
            <div class="card-header">
                <div class="card-icon">🎯</div>
                <h3>थ्रोइङ (Throws: Shot Put, Javelin)</h3>
            </div>
            <ul class="rule-list">
                <li><strong>सटपुट (Shot Put):</strong> (पुरुष: ७.२६ केजी, महिला: ४ केजी)। सटलाई <strong>काँध (Shoulder) नजिक राखेर Push (पुस)</strong> गर्नुपर्छ, फ्याँक्न (Throw) पाइँदैन। सर्कल (व्यास २.१३५ मि.) भित्रबाट फ्याँक्नुपर्छ; अगाडि <strong>स्टप बोर्ड</strong> हुन्छ, जसलाई नाघ्न पाइँदैन।</li>
                <li><strong>ज्याभलिन थ्रो (Javelin Throw):</strong> (पुरुष: ८०० ग्राम, २.६–२.७ मि. लामो; महिला: ६०० ग्राम, २.२–२.३ मि.)। <strong>ग्रिपबाट समातेर काँधमाथिबाट फ्याँक्नुपर्छ। भालाको चुच्चो (Tip)</strong> पहिले जमिनमा पर्नुपर्छ। रनवे (३०–३६ मि.) भित्र दौडेर फ्याँक्ने, <strong>आर्क लाइन</strong> नाघ्न पाइँदैन।</li>
                <li><strong>सेक्टर (Sector):</strong> Shot Put: ३४.९२° कोण; Javelin: २८.९६° कोण। फ्याँकिएको वस्तु यही सेक्टरभित्र मात्र मान्य हुन्छ।</li>
                <li><strong>प्रयास र मापन:</strong> साधारणतः ३ प्रयास (अन्तर्राष्ट्रियमा ६)। वस्तुले छोएको सबैभन्दा नजिकको बिन्दुबाट सर्कल/आर्कको भित्री किनारासम्म नापिन्छ। सबैभन्दा राम्रो दूरी आधारमा विजेता; बराबरी भए दोस्रो उत्कृष्ट प्रयास हेरिन्छ।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

        # ========== फाउल र मापन सम्बन्धी विस्तृत जानकारी ==========
        with st.expander("⚠️ फाउल (Foul) र मापन (Measurement) सम्बन्धी विस्तृत जानकारी"):
            st.markdown("""
            **🚫 फाउल हुने अवस्थाहरू:**
            * **टेक-अफ बोर्ड/रेखा कुल्चिएमा वा नाघेमा** (Long Jump, Triple Jump, Javelin, Shot Put)।
            * **सटपुटलाई पुस नगरी क्रिकेट बल जस्तो थ्रो गरेमा।**
            * **ज्याभलिनको चुच्चो (Tip) नभई पछाडिको भाग पहिले जमिनमा परेमा।**
            * **फ्याँकेको वस्तु सेक्टर लाइनबाहिर परेमा।**
            * **रेफ्रीको आदेशअघि नै सुरु गरेमा वा तोकिएको समयभित्र प्रयास नगरेमा।**
            * **ट्रिपल जम्पमा Hop-Step-Jump को क्रम बिग्रेमा।**
            * **दौडमा लेन नाघेमा वा अरूलाई अवरोध गरेमा।**
            
            **📏 मापन विधि:**
            * **जम्प (Long/Triple):** टेक-अफ बोर्डको नजिकको किनाराबाट बालुवामा शरीरले छोएको सबैभन्दा नजिकको चिन्हसम्म (कुनै पनि भाग — हात, लुगा, कपाल — ले बनाएको डोब)।
            * **थ्रो (Shot/Javelin):** वस्तुले छोएको सबैभन्दा नजिकको बिन्दुबाट सर्कल/आर्कको भित्री किनारासम्म सिधा रेखा।
            * सबै मापन सेन्टिमिटर वा मिटरमा हुन्छ।
            """)

    # ========== तल थप सारांश ==========
    st.markdown("---")
    st.markdown("""
    <div style="background-color: #f0f9ff; padding: 15px; border-radius: 10px; border-left: 5px solid #0284c7;">
        <strong>📌 मुख्य सारांश:</strong>
        <ul style="margin-top: 8px;">
            <li><strong>ट्र्याक:</strong> स्प्रिन्ट (लेन अनिवार्य, फल्स स्टार्टमा आउट, हिट्स/फाइनल, Q/q, कलिङ सिस्टम), मध्यदूरी (ल्याप काउन्ट, बेल, २००मि ट्र्याकमा ८००=४ल्याप, १५००=७.५ल्याप, ३०००=१५ल्याप), रिले (२०मि एक्सचेन्ज जोन, ब्याटन अनिवार्य)।</li>
            <li><strong>फिल्ड:</strong> हाइजम्प (काउन्ट-ब्याक), लङजम्प (बोर्ड, बालुवा), ट्रिपलजम्प (हप-स्टेप-जम्प), सटपुट (पुस, सर्कल), ज्याभलिन (टिप पहिले, आर्क लाइन)।</li>
            <li><strong>प्रयास:</strong> सामान्यतः ३ प्रयास (ठूला प्रतियोगितामा ६), उत्कृष्ट प्रदर्शनको आधारमा विजेता।</li>
            <li><strong>बोलाउने प्रणाली:</strong> फर्स्ट/सेकेण्ड/फाइनल कल — ढिलो आए अयोग्य।</li>
            <li><strong>चेस्ट नम्बर:</strong> अनिवार्य, स्पष्ट देखिने।</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

# ==================== ⚖️ विवाद र पदक (विस्तृत र व्यावसायिक नियम) ====================
with tab7:
    st.markdown("""
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
        <span class="badge-sport gen">⚖️ ज्युरी अफ अपिल (Jury of Appeal)</span>
        <span class="badge-sport gen">🏅 पदक तालिका (Medal Tally)</span>
        <span class="badge-sport gen">🏆 च्याम्पियनसिप ट्रफी</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.markdown("""
        <div class="rule-card" style="border-left: 5px solid #ea580c;">
            <div class="card-header">
                <div class="card-icon">⚖️</div>
                <h3>दावी-विरोध र विवाद समाधान</h3>
            </div>
            <ul class="rule-list">
                <li><strong>अपील गर्ने अधिकार:</strong> खेलमा विवाद भएमा खेलाडी वा दर्शकले होइन, सम्बन्धित पालिकाको <strong>आधिकारिक टिम व्यवस्थापक (Team Manager)</strong> ले मात्र अपील गर्न पाउनेछन्।</li>
                <li><strong>समय सीमा:</strong> खेलको नतिजा घोषणा भएको <strong>३० मिनेटभित्र</strong> लिखित रूपमा (तोकिएको फाराममा) उजुरी पेस गरिसक्नुपर्नेछ।</li>
                <li><strong>धरौटी रकम:</strong> प्रत्येक उजुरी दर्ता गर्दा <strong>रु. ५,०००/- (पाँच हजार)</strong> धरौटी राख्नुपर्नेछ। दावी सही ठहरिएमा रकम फिर्ता हुनेछ, गलत ठहरिएमा जफत हुनेछ।</li>
                <li><strong>अन्तिम निर्णय:</strong> प्राविधिक समिति वा 'ज्युरी अफ अपिल' को निर्णय नै सर्वमान्य र अन्तिम हुनेछ। भिडियो रिभ्यु (उपलब्ध भएमा) ज्युरीको तजबिजमा मात्र हेरिनेछ।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_d2:
        st.markdown(f"""
        <div class="rule-card" style="border-left: 5px solid #fbbf24;">
            <div class="card-header">
                <div class="card-icon">🏆</div>
                <h3>पदक, पुरस्कार र च्याम्पियनसिप</h3>
            </div>
            <ul class="rule-list">
                <li><strong>व्यक्तिगत पदक:</strong> प्रथमलाई स्वर्ण (Gold), द्वितीयलाई रजत (Silver) र तृतीयलाई कांस्य (Bronze) पदक तथा प्रमाणपत्र प्रदान गरिनेछ। मार्शल आर्ट्समा दुई जनालाई कांस्य दिइनेछ।</li>
                <li><strong>च्याम्पियनसिप ट्रफी (Team Champion):</strong> प्रतियोगिताको अन्त्यमा सबैभन्दा बढी <strong>स्वर्ण पदक</strong> जित्ने पालिकालाई 'समग्र च्याम्पियन ट्रफी' प्रदान गरिनेछ। स्वर्ण बराबर भएमा रजत, र रजत पनि बराबर भएमा कांस्य पदक गनिनेछ।</li>
                <li><strong>उत्कृष्ट खेलाडी:</strong> प्रतियोगिताभरिको प्रदर्शनको आधारमा एक छात्र र एक छात्रालाई 'सर्वोत्कृष्ट खेलाडी' को ट्रफी प्रदान गरिनेछ।</li>
                <li><strong>नगद पुरस्कार:</strong> आयोजकको पूर्व निर्णयअनुसार स्वर्ण, रजत र कांस्य विजेताहरूलाई तोकिएको नगद पुरस्कार (जस्तै: १० हजार, ७ हजार, ५ हजार) प्रदान गर्न सकिनेछ।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== डाउनलोड र फुटर ====================
st.divider()
c1, c2 = st.columns([3, 1])
with c1:
    st.info("💡 **आधिकारिक दस्तावेज:** यो नियम पुस्तिका (Rulebook) आधिकारिक हो। राष्ट्रपति रनिङ शिल्डमा सहभागी सबै पालिका र टोलीले यसको पूर्ण रूपमा पालना गर्नुपर्नेछ।")
with c2:
    if st.button("📥 नियम पुस्तिका डाउनलोड (PDF)", type="primary", use_container_width=True):
        st.toast("PDF फाइल तयार भइरहेको छ। चाँडै उपलब्ध हुनेछ!", icon="⏳")

# यदि render_footer() भन्ने छुट्टै फङ्सन छ भने कल गर्ने:
if 'render_footer' in globals():
    render_footer()