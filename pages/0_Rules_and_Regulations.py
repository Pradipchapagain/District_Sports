import streamlit as st
from config import CONFIG, render_header, render_footer
from datetime import datetime

# १. पेज सेटअप
st.set_page_config(page_title="नियम र सर्तहरू", page_icon="📜", layout="wide", initial_sidebar_state="collapsed")

# २. कस्टम CSS (बुटस्ट्र्याप-जस्तो कार्ड र टाइपोग्राफी)
st.markdown("""
<style>
    /* मुख्य फन्ट र रङ */
    body { font-family: 'Poppins', sans-serif; background-color: #f9fafb; }
    .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    
    /* कार्ड स्टाइल */
    .rule-card {
        background: white;
        border-radius: 20px;
        padding: 1.8rem 1.5rem;
        margin-bottom: 1.8rem;
        box-shadow: 0 10px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.02);
        border: 1px solid #e9ecef;
        transition: transform 0.2s;
    }
    .rule-card:hover { transform: translateY(-3px); box-shadow: 0 20px 30px -10px rgba(0,0,0,0.15); }
    
    .card-header {
        display: flex;
        align-items: center;
        gap: 12px;
        border-bottom: 2px solid #f1f3f5;
        padding-bottom: 0.8rem;
        margin-bottom: 1.2rem;
    }
    .card-header h3 {
        font-size: 1.6rem;
        font-weight: 600;
        margin: 0;
        color: #1E3A8A;
        letter-spacing: -0.02em;
    }
    .card-icon {
        font-size: 2.2rem;
        background: #e9f0ff;
        width: 55px;
        height: 55px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 50%;
        color: #1E3A8A;
    }
    .rule-list {
        list-style: none;
        padding-left: 0;
        margin: 0;
    }
    .rule-list li {
        padding: 0.5rem 0 0.5rem 2rem;
        background: url('data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="%231E88E5" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>') left center no-repeat;
        background-size: 1.2rem;
        margin-bottom: 0.4rem;
        color: #2c3e50;
        font-size: 1rem;
        line-height: 1.6;
    }
    .rule-list strong, .highlight {
        background: #fef9c3;
        color: #92400e;
        padding: 0.1rem 0.4rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.95rem;
    }
    .section-subhead {
        font-size: 1.2rem;
        font-weight: 500;
        color: #1e293b;
        margin: 2rem 0 1rem 0;
        padding-left: 0.5rem;
        border-left: 6px solid #1E88E5;
        background: linear-gradient(to right, #f8fafc, transparent);
        padding: 0.5rem 0 0.5rem 1rem;
        border-radius: 0 30px 30px 0;
    }
    .badge-sport {
        display: inline-block;
        background: #dee2e6;
        padding: 0.3rem 1rem;
        border-radius: 30px;
        font-size: 0.9rem;
        font-weight: 600;
        color: #1e293b;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .badge-sport.vb { background: #dbeafe; color: #1E40AF; }
    .badge-sport.kb { background: #fee2e2; color: #B91C1C; }
    .badge-sport.ma { background: #f1f0ff; color: #5b21b6; }
    .badge-sport.gen { background: #ecfdf5; color: #065f46; }
    
    /* डाउनलोड बटन */
    .download-btn {
        background: #1E3A8A;
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 50px;
        font-size: 1.2rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        transition: 0.2s;
    }
    .download-btn:hover { background: #2563eb; }
    
    /* ट्याब स्टाइल (बेस ओभरराइड) */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background: white;
        border-radius: 30px 30px 0 0;
        padding: 0 25px;
        font-weight: 600;
        color: #4b5563;
        border: 1px solid #e2e8f0;
        border-bottom: none;
        transition: 0.2s;
    }
    .stTabs [aria-selected="true"] {
        background: #1E3A8A !important;
        color: white !important;
        border-color: #1E3A8A;
    }
    hr.divider { margin: 2rem 0; border: 0; border-top: 2px dashed #d1d5db; }
</style>
""", unsafe_allow_html=True)

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

# ५. ट्याब नेभिगेसन (६ वटा)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🌟 सामान्य नियम", "🖥️ दर्ता र प्रविधि", "🏐 भलिबल", "🤼 कबड्डी", "🥋 मार्शल आर्ट्स", "⚖️ विवाद र पदक"])

# ==================== 🌟 सामान्य नियम (पुरानो) ====================
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">📋</div>
                <h3>दर्ता सम्बन्धी</h3>
            </div>
            <ul class="rule-list">
                <li><strong>उमेर हद:</strong> जन्म मिति {CONFIG['AGE_LIMIT_DATE']} वा सोभन्दा पछि भएको हुनुपर्ने।</li>
                <li><strong>खेलाडी संख्या:</strong> प्रति पालिका अधिकतम {CONFIG['MAX_PLAYERS_PER_PALIKA']} जना।</li>
                <li><strong>विधा सीमा:</strong> एक खेलाडीले बढीमा २ वटा विधामा मात्र भाग लिन पाउने।</li>
                <li><strong>प्रमाणिकरण:</strong> जन्म दर्ता, पालिकाको सिफारिस, र खेलाडी परिचयपत्र अनिवार्य।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">👕</div>
                <h3>पोशाक र उपकरण</h3>
            </div>
            <ul class="rule-list">
                <li>सबै खेलाडीले आ–आफ्नो पालिकाको एकरूप पोशाक लगाउनु पर्ने।</li>
                <li>जर्सीमा खेलाडीको नाम र नम्बर अनिवार्य (पछाडि ६ इन्च उचाइमा)।</li>
                <li>कप्तानले बायाँ हातको माथिल्लो भागमा आर्मब्यान्ड लगाउनु पर्ने।</li>
                <li>धारिलो गरगहना, घडी, वा अन्य खतरनाक सामग्री निषेध।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">⏱️</div>
                <h3>अनुशासन र आचारसंहिता</h3>
            </div>
            <ul class="rule-list">
                <li>खेल सुरु भएको १५ मिनेटभित्र उपस्थित नभएमा वाकओभर दिइनेछ।</li>
                <li>रेफ्री/अम्पायरको निर्णय अन्तिम हुनेछ। कुनै पनि विवादमा रेफ्रीसँग बहस गर्न पाइने छैन।</li>
                <li>अमर्यादित व्यवहार (अपशब्द, झगडा) गरेमा रातो कार्ड देखाइ खेलबाट निष्कासित गरिनेछ।</li>
                <li>डोपिङ परीक्षणको लागि कुनै पनि समयमा खेलाडीलाई पेश गर्न सकिनेछ।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">📢</div>
                <h3>प्रशिक्षक र अफिसियल</h3>
            </div>
            <ul class="rule-list">
                <li>प्रत्येक टोलीसँग एक प्रशिक्षक र एक टोली व्यवस्थापक हुनु पर्ने।</li>
                <li>प्रशिक्षकले बेन्च क्षेत्रमा मात्र निर्देशन दिन पाउने।</li>
                <li>टोली व्यवस्थापकले दर्ता, फारम, र सम्पर्क विवरणको जिम्मेवारी लिने।</li>
                <li>अफिसियलहरूको निर्णय चुनौती दिन मिल्ने छैन।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== 🖥️ दर्ता र प्रविधि (नयाँ) ====================
with tab2:
    st.markdown("""
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
        <span class="badge-sport gen">🖥️ डिजिटल प्रणाली</span>
        <span class="badge-sport gen">📊 बल्क दर्ता</span>
        <span class="badge-sport gen">🛡️ डाटा भ्यालिडेसन</span>
    </div>
    """, unsafe_allow_html=True)

    col_r1, col_r2 = st.columns(2)

    with col_r1:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">⌨️</div>
                <h3>दर्ता गर्ने तरिका</h3>
            </div>
            <ul class="rule-list">
                <li><strong>म्यानुअल इन्ट्री:</strong> एउटा एउटा गरी खेलाडीको फोटो र कागजात सहित विवरण भर्न सकिने।</li>
                <li><strong>बल्क एक्सल (Bulk Excel):</strong> धेरै खेलाडी भएमा सिस्टमले दिएको टेम्प्लेटमा डाटा भरेर एकैपटक 'Upload' गर्न सकिने।</li>
                <li><strong>फोटो साइज:</strong> अपलोड गरिने फोटो स्पष्ट र सफा हुनुपर्ने (अधिकतम ५०० KB)।</li>
                <li><strong>विवरण सम्पादन:</strong> दर्ता अवधि नसकिँदासम्म विवरण सच्याउन वा हटाउन सकिने।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with col_r2:
        st.markdown(f"""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">🛡️</div>
                <h3>सिस्टम भ्यालिडेसन चेक</h3>
            </div>
            <p style="color: #64748b; font-size: 0.9rem;">(हाम्रो प्रणालीले स्वचालित रूपमा निम्न कुराहरू चेक गर्छ:)</p>
            <ul class="rule-list">
                <li><strong>उमेर जाँच:</strong> जन्म मिति {CONFIG['AGE_LIMIT_DATE']} भन्दा कम भएमा सिस्टमले दर्ता रोक्नेछ।</li>
                <li><strong>कोटा जाँच:</strong> प्रति पालिका {CONFIG['MAX_PLAYERS_PER_PALIKA']} भन्दा बढी खेलाडी भएमा दर्ता लिइने छैन।</li>
                <li><strong>लिङ्ग जाँच:</strong> खेलको विधा र खेलाडीको लिङ्ग नमिल्दा (जस्तै: महिला विधामा पुरुष) त्रुटि देखाउनेछ।</li>
                <li><strong>डुप्लिकेट जाँच:</strong> एउटै खेलाडीलाई एउटै विधामा दोहोर्याएर दर्ता गर्न मिल्ने छैन।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.warning("⚠️ **ध्यान दिनुहोस्:** एक्सल फाइल अपलोड गर्दा कोलमको नाम र फम्र्याट परिवर्तन नगर्नुहोला, नत्र सिस्टमले डाटा रिजेक्ट गर्न सक्छ।")

# ==================== 🏐 भलिबल (पुरानो) ====================
with tab3:
    st.markdown("""
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
        <span class="badge-sport vb">🏐 FIVB नियम अनुसार</span>
        <span class="badge-sport vb">🇳🇵 राष्ट्रिय संशोधन</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_v1, col_v2 = st.columns(2)
    
    with col_v1:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">🏐</div>
                <h3>खेल संरचना</h3>
            </div>
            <ul class="rule-list">
                <li><strong>सेट:</strong> प्रारम्भिक चरण ३ सेटको (२१ अङ्क), नकआउट चरण ५ सेटको (२५ अङ्क)। निर्णायक सेट १५ अङ्कको।</li>
                <li><strong>टोली:</strong> अधिकतम १२ खेलाडी, ६ जना एक पटकमा मैदानमा।</li>
                <li><strong>लिबेरो:</strong> दुई लिबेरो नियुक्त गर्न सकिने। लिबेरोले विपक्षी आक्रमण रेखाभित्रबाट स्म्याश गर्न पाउने छैन।</li>
                <li><strong>रोटेसन:</strong> सर्भिस प्राप्त गरेपछि अनिवार्य रोटेसन।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">📏</div>
                <h3>कोर्ट र उपकरण</h3>
            </div>
            <ul class="rule-list">
                <li>कोर्ट: १८ मि × ९ मि, आक्रमण रेखा ३ मि।</li>
                <li>नेट उचाइ: पुरुष २.४३ मि, महिला २.२४ मि।</li>
                <li>बल: मिकासा MVA200 वा समकक्ष।</li>
                <li>एन्टेना: नेटको दुबै छेउमा अनिवार्य।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_v2:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">⏸️</div>
                <h3>टाइमआउट र सब्स्टिच्युसन</h3>
            </div>
            <ul class="rule-list">
                <li>प्रति सेट २ टाइमआउट (प्रत्येक ३० सेकेन्ड)।</li>
                <li>अधिकतम ६ सब्स्टिच्युसन प्रति सेट (लिबेरो बाहेक)।</li>
                <li>लिबेरो सब्स्टिच्युसन असीमित तर ब्याक रो मात्र।</li>
                <li>खेलाडी घाइते भएमा विशेष सब्स्टिच्युसन दिइने।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">⚠️</div>
                <h3>फल्ट र पेनाल्टी</h3>
            </div>
            <ul class="rule-list">
                <li>फुट फल्ट (सर्भ गर्दा लाइन नाघेमा)।</li>
                <li>नेट टच (खेलको क्रममा नेट छोएमा)।</li>
                <li>डबल कन्ट्याक्ट (एकै खेलाडीले लगातार दुई पटक बल छोएमा)।</li>
                <li>क्यारी (बललाई समातेर फ्याँकेमा)।</li>
                <li>पेनाल्टी: विपक्षीलाई एक अङ्क दिइने।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== 🤼 कबड्डी (पुरानो) ====================
with tab4:
    st.markdown("""
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
        <span class="badge-sport kb">🤼 अन्तर्राष्ट्रिय कबड्डी संघ</span>
        <span class="badge-sport kb">🇳🇵 राष्ट्रिय नियम</span>
    </div>
    """, unsafe_allow_html=True)
    
    col_k1, col_k2 = st.columns(2)
    
    with col_k1:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">⏱️</div>
                <h3>समय र अङ्क</h3>
            </div>
            <ul class="rule-list">
                <li>दुई हाफ प्रत्येक २० मिनेट, बीचमा ५ मिनेट ब्रेक।</li>
                <li>प्रत्येक टोलीले प्रति हाफ २ टाइमआउट (३० सेकेन्ड) पाउने।</li>
                <li>रेडरले ३० सेकेन्डभित्र रेड सकाउनु पर्ने।</li>
                <li><strong>लोना:</strong> विपक्षीका सबै ७ खेलाडी आउट गरेमा थप २ अङ्क।</li>
                <li>सुपर ट्याकल: ३ वा कम खेलाडी हुँदा रेडरलाई रोकेमा थप १ अङ्क।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">🚶</div>
                <h3>रेडिङ नियम</h3>
            </div>
            <ul class="rule-list">
                <li>रेडरले लगातार 'कबड्डी' भन्नु पर्ने (सास फेर्न पाइँदैन)।</li>
                <li><strong>डू–अर–डाई:</strong> लगातार दुई खाली रेडपछि तेस्रो रेड अनिवार्य अङ्क ल्याउनै पर्ने।</li>
                <li><strong>बोनस लाइन:</strong> रेडरले विपक्षी आधा क्रस गर्दा १ बोनस अङ्क।</li>
                <li>रेडर आधा लाइनपछि मात्र समात्न पाइने।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_k2:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">🟨🟥</div>
                <h3>कार्ड प्रणाली</h3>
            </div>
            <ul class="rule-list">
                <li><strong>पहेँलो कार्ड:</strong> असभ्य व्यवहार, डिफेन्स गर्दा जोर्नी मर्काउने खेल। २ मिनेट सस्पेन्सन।</li>
                <li><strong>रातो कार्ड:</strong> झगडा, जानीबुझी हानी गरेमा। खेलाडी मैदानबाट निष्कासित।</li>
                <li>दुई पहेँलो कार्ड = एक रातो कार्ड।</li>
                <li>कार्ड पाएको खेलाडीको स्थानमा अर्को खेलाडी प्रवेश गर्न सकिने छैन (टोली ६ जनामा सीमित)।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">🔄</div>
                <h3>सब्स्टिच्युसन र पुनरागमन</h3>
            </div>
            <ul class="rule-list">
                <li>प्रारम्भिक ७ खेलाडी दर्ता गर्नु पर्ने।</li>
                <li>बेन्चमा अधिकतम ५ स्थानापन्न खेलाडी।</li>
                <li>आउट भएको खेलाडी अर्को रेडमा फर्किन सक्छ यदि टोलीले अङ्क प्राप्त गर्यो भने।</li>
                <li>सब्स्टिच्युसन रेडको बीचमा मात्र गर्न पाइने।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== 🥋 मार्शल आर्ट्स (पुरानो) ====================
with tab5:
    st.markdown("""
    <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
        <span class="badge-sport ma">🥋 कराते (डब्ल्यूकेएफ)</span>
        <span class="badge-sport ma">🥊 उसु (आइडब्ल्यूयूएफ)</span>
        <span class="badge-sport ma">🥋 तेक्वान्दो (डब्ल्यूटी)</span>
    </div>
    """, unsafe_allow_html=True)
    
    # सब–ट्याब (काता/कुमिते)
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["काता (कराते)", "कुमिते (कराते)", "उसु/तेक्वान्दो"])
    
    with sub_tab1:
        st.markdown("""
        <div class="rule-card">
            <ul class="rule-list">
                <li>प्रत्येक खेलाडीले आफ्नो रोजाइको काता प्रस्तुत गर्ने (टोकुइ/शितेइ)।</li>
                <li>७ जजले अङ्क प्रदान गर्ने (उच्चतम र न्यूनतम हटाइन्छ)।</li>
                <li>निर्णायक चरणमा फरक काता प्रस्तुत गर्नु पर्ने।</li>
                <li>समय सीमा: ३–५ मिनेट।</li>
                <li>झुक्किएर रोकिएमा ०.५ अङ्क कटौती।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with sub_tab2:
        col_km1, col_km2 = st.columns(2)
        with col_km1:
            st.markdown("""
            <div class="rule-card">
                <div class="card-header"><h3>अङ्क प्रणाली</h3></div>
                <ul class="rule-list">
                    <li><strong>इप्पोन (३ अङ्क):</strong> पूर्ण प्रहार (हात, लात) जसले प्रतिद्वन्द्वीलाई ढाल्छ।</li>
                    <li><strong>वाजा–अरी (२ अङ्क):</strong> लात प्रहार, शरीरमा हात प्रहार।</li>
                    <li><strong>युको (१ अङ्क):</strong> चोकुदान जोनमा हात प्रहार।</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
        with col_km2:
            st.markdown("""
            <div class="rule-card">
                <div class="card-header"><h3>प्रतिबन्ध</h3></div>
                <ul class="rule-list">
                    <li>अनुहारमा सीधा प्रहार (नियन्त्रित हुनुपर्छ)।</li>
                    <li>जोर्नी, ढाड, घाँटीमा प्रहार निषेध।</li>
                    <li>समातेर प्रहार गर्न पाइँदैन।</li>
                    <li>पहिलो चेतावनीपछि अङ्क कटौती।</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)
    
    with sub_tab3:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header"><h3>उसु (सान्दा/ताओलु) र तेक्वान्दो</h3></div>
            <ul class="rule-list">
                <li><strong>ताओलु:</strong> निर्धारित फार्मको प्रदर्शन, ५ जजले अङ्क दिने।</li>
                <li><strong>सान्दा:</strong> फुल कन्ट्याक्ट, हात र खुट्टा प्रयोग। हेलमेट, छाती गार्ड, माउथगार्ड अनिवार्य।</li>
                <li><strong>तेक्वान्दो (क्योरुगी):</strong> डब्ल्यूटी नियम, हगु (प्रोटेक्टर) अनिवार्य। इलेक्ट्रोनिक हेलमेट प्रयोग।</li>
                <li>कम्मरभन्दा माथि मात्र प्रहार गर्न पाइने।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== ⚖️ विवाद र पदक (पुरानो) ====================
with tab6:
    col_d1, col_d2 = st.columns(2)
    
    with col_d1:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">⚖️</div>
                <h3>विवाद समाधान</h3>
            </div>
            <ul class="rule-list">
                <li>कुनै पनि विवाद खेल सकिएको ३० मिनेटभित्र लिखित रूपमा पेस गर्नु पर्ने।</li>
                <li>जमानत रकम रु. ५००० राख्नु पर्ने (गलत सावित भए जफत)।</li>
                <li>टेक्निकल कमिटीको निर्णय अन्तिम हुनेछ।</li>
                <li>भिडियो रिभ्यूको लागि प्रति खेल १ पटक अनुरोध गर्न सकिने (यदि सुविधा उपलब्ध छ भने)।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    with col_d2:
        st.markdown("""
        <div class="rule-card">
            <div class="card-header">
                <div class="card-icon">🥇</div>
                <h3>पदक र पुरस्कार</h3>
            </div>
            <ul class="rule-list">
                <li><strong>स्वर्ण:</strong> पदक + प्रमाणपत्र + रु. १०,०००।</li>
                <li><strong>रजत:</strong> पदक + प्रमाणपत्र + रु. ७,०००।</li>
                <li><strong>कास्य:</strong> पदक + प्रमाणपत्र + रु. ५,०००।</li>
                <li>टिम इभेन्टमा विजेताले ट्रफी र नगद पुरस्कार।</li>
                <li>उत्कृष्ट खेलाडी (पुरुष/महिला) ले अतिरिक्त पुरस्कार।</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ==================== डाउनलोड र फुटर ====================
st.divider()
c1, c2 = st.columns([3, 1])
with c1:
    st.info("💡 यो नियम पुस्तिका आधिकारिक हो। सबै टोलीले यसको पूर्ण पालना गर्नु पर्नेछ।")
with c2:
    if st.button("📥 नियम पुस्तिका डाउनलोड (PDF)", use_container_width=True):
        st.warning("PDF फाइल तयार भइरहेको छ। चाँडै उपलब्ध हुनेछ।")

render_footer()