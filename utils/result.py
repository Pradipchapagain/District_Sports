import streamlit as st
import database as db
import utils.live_state as ls

def check_and_reset_results(event_code):
    """नतिजा पहिले नै छ कि छैन जाँच्ने र रिसेट गर्ने साझा फङ्सन।"""
    conn = db.get_connection()
    c = conn.cursor()
    
    # 💡 PostgreSQL को लागि ? को सट्टा %s प्रयोग गरिएको
    c.execute("SELECT COUNT(*) FROM results WHERE event_code = %s AND medal != 'Qualified'", (event_code,))
    count = c.fetchone()[0]
    
    if count > 0:
        st.error("⚠️ यस इभेन्टको अन्तिम नतिजा पहिले नै सार्वजनिक भइसकेको छ!")
        st.info("नयाँ नतिजा राख्नको लागि पहिले पुरानो नतिजा रिसेट गर्नुहोस्।")
        if st.button("🔄 नतिजा रिसेट (Reset) गर्नुहोस्", type="primary", key=f"reset_{event_code}"):
            try:
                # 💡 रिसेट गर्दा 'Qualified' डाटालाई सुरक्षित राख्ने
                c.execute("DELETE FROM results WHERE event_code = %s AND medal != 'Qualified'", (event_code,))
                conn.commit()
                st.success("✅ पुरानो नतिजा हटाइयो! अब नयाँ नतिजा प्रविष्ट गर्न सक्नुहुन्छ।")
                st.rerun()
            except Exception as e:
                st.error(f"Error resetting results: {e}")
        
        c.close(); conn.close()
        return True
        
    c.close(); conn.close()
    return False

def display_operator_podium(gold, silver, bronze, score_key, name_key, sub_text_key, is_relay=False):
    """अपरेटरको स्क्रिनमा पोडियम देखाउने साझा फङ्सन"""
    st.markdown("<h2 style='text-align: center;'>🎉 बधाई छ! (Congratulations) 🎉</h2>", unsafe_allow_html=True)
    st.write("") 
    c_s, c_g, c_b = st.columns([1, 1.2, 1])

    def get_html(medal_data, medal_icon, bg_color, border_color, title_color, m_title):
        if not medal_data: return ""
        score = medal_data.get(score_key, '')
        name = medal_data.get(name_key, '')
        sub_text = medal_data.get(sub_text_key, '')
        
        # रिले वा टिम गेमको लागि (HTML List)
        r_list = ""
        if is_relay and 'runner_names' in medal_data:
            lis = "".join([f"<li style='padding:2px 0;'>🏃 {n}</li>" for n in medal_data['runner_names']])
            r_list = f"<ul style='list-style-type:none; padding:0; margin:10px 0 0 0; font-size:15px; color:#444;'>{lis}</ul>"
            sub_text = f"🏛️ {sub_text}" # पालिकाको वा टिमको आइकन
        else:
            sub_text = f"📍 {sub_text}" # व्यक्तिगतको लागि पिन

        return f"""
            <div style='background:{bg_color}; padding:15px; border-radius:10px; border:2px solid {border_color}; text-align:center;'>
                <h1 style='margin:0;'>{medal_icon}</h1>
                <h3 style='color:{title_color}; margin:0;'>{m_title}</h3>
                <h2 style='margin:0;'>{score}</h2>
                <hr style='margin:5px 0;'>
                <h4 style='margin:0;'>{name}</h4>
                <p style='margin:0; font-size:1em; font-weight:bold; color:#333;'>{sub_text}</p>
                {r_list}
            </div>
        """

    with c_g: st.markdown(get_html(gold, '🥇', '#FFF8DC', '#FFD700', '#DAA520', 'GOLD'), unsafe_allow_html=True)
    with c_s: st.markdown(get_html(silver, '🥈', '#F0F8FF', '#C0C0C0', '#708090', 'SILVER'), unsafe_allow_html=True)
    with c_b: st.markdown(get_html(bronze, '🥉', '#FFF5EE', '#CD7F32', '#8B4513', 'BRONZE'), unsafe_allow_html=True)

def trigger_live_tv(evt_name, gender, gold, silver, bronze, type="individual"):
    """लाइभ टिभीमा डाटा पठाउने साझा फङ्सन"""
    def fmt(p_data):
        if not p_data: return None
        if type == "relay" or type == "team":
            # टिम गेम (भलिबल/कबड्डी) को लागि पनि यही काम लाग्छ
            r_str = ", ".join(p_data.get('runner_names', []))
            return {"name": f"👥 {r_str}" if r_str else p_data.get('name', ''), "municipality": p_data.get('municipality', ''), "score": f"{p_data.get('time', p_data.get('score', ''))}"}
        elif type == "track":
            return {"name": p_data.get('name', ''), "municipality": p_data.get('municipality', ''), "score": f"⏱ {p_data.get('time', '')}"}
        else: # field/jump/martial_arts
            return {"name": p_data.get('name', ''), "municipality": p_data.get('municipality', ''), "score": f"{p_data.get('best', p_data.get('score', ''))}"}
            
    ls.trigger_podium(
        event_name=f"{evt_name} - ({gender})",
        gold_data=fmt(gold), silver_data=fmt(silver), bronze_data=fmt(bronze)
    )