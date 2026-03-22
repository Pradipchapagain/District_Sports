# utils\live_state.py
import json
import logging
import time
from typing import Optional, Any, Dict, List
from datetime import datetime
import database as db
import psycopg2.extras
from config import CONFIG 
import threading
import os

# ==========================================
# 🛑 १. CONFIGURATION FROM CENTRAL CONFIG
# ==========================================
EXPIRE_TIMES = CONFIG.get('EXPIRE_TIMES', {})

# ==========================================
# 🛠️ २. CORE STATE ENGINE (Optimized & Robust)
# ==========================================

def _get_state(key: str, expire_seconds: Optional[int] = None) -> Optional[Any]:
    """स्टेट पढ्ने, समय नाघेको भए हटाउने र JSON डिकोड गर्ने।"""
    
    # यदि प्यारामिटरमा छैन भने CONFIG बाट लिने
    if expire_seconds is None:
        expire_seconds = EXPIRE_TIMES.get(key)

    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT state_data, EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - updated_at)) 
                FROM system_states WHERE state_key = %s
            """, (key,))
            row = cur.fetchone()
            
            if not row:
                return None
            
            data, age_seconds = row
            
            # 🔍 सुधार: 'if not None' प्रयोग गर्दा ० सेकेन्ड एक्सपायरीले पनि काम गर्छ
            if expire_seconds is not None and age_seconds > expire_seconds:
                _clear_state(key)
                return None
            
            if isinstance(data, (dict, list)):
                return data
            return json.loads(data) if data else None
    except Exception as e:
        logging.error(f"Error fetching state '{key}': {e}")
        return None
    finally:
        conn.close()

def _save_state(key: str, data: Any) -> None:
    """PostgreSQL JSONB मा सेभ गर्ने (UPSERT)"""
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO system_states (state_key, state_data, updated_at) 
                VALUES (%s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (state_key) DO UPDATE 
                SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
            """, (key, json.dumps(data, ensure_ascii=False)))
            conn.commit()
    except Exception as e:
        logging.error(f"Error saving state '{key}': {e}")
    finally:
        conn.close()

def _clear_state(key: str) -> None:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM system_states WHERE state_key = %s", (key,))
            conn.commit()
    finally:
        conn.close()

# ==========================================
# 🥋 ३. LIVE SCORE & ANNOUNCEMENTS
# ==========================================

def update_live_match(event_name: str, p_a: str, p_b: str, score_a: Any, score_b: Any, **kwargs) -> None:
    data = {
        "event_name": event_name, "p_a": p_a, "p_b": p_b,
        "score_a": score_a, "score_b": score_b,
        "status": kwargs.get("status", "Playing"),
        "timer": kwargs.get("timer", "00:00"),
        "is_kumite": kwargs.get("is_kumite", False),
        "pen_a": kwargs.get("pen_a", 0),
        "pen_b": kwargs.get("pen_b", 0)
    }
    _save_state("live_match", data)

def get_live_match() -> Optional[Dict]:
    return _get_state("live_match")

def set_announcement(title: str, subtitle: str = "") -> None:
    _save_state("announcement", {"title": title, "subtitle": subtitle})

def get_announcement() -> Optional[Dict]:
    return _get_state("announcement")

# ==========================================
# 🏆 पोडियम (Podium Celebration)
# ==========================================
def trigger_podium(event_name, gold_data=None, silver_data=None, bronze_data=None):
    """लाइभ टिभीमा पोडियम (विजेता) देखाउन डाटा पठाउने"""
    import json
    import database as db
    
    podium_state = {
        "event_name": event_name,
        "gold": gold_data,
        "silver": silver_data,
        "bronze": bronze_data
    }
    
    conn = db.get_connection()
    if conn:
        try:
            c = conn.cursor()
            # 💡 PostgreSQL Upsert
            c.execute("""
                INSERT INTO system_states (state_key, state_data) 
                VALUES ('podium_data', %s)
                ON CONFLICT (state_key) 
                DO UPDATE SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
            """, (json.dumps(podium_state),))
            conn.commit()
        except Exception as e:
            print(f"Podium trigger error: {e}")
        finally:
            conn.close()

def clear_podium():
    """टिभीबाट पोडियम हटाउने"""
    import database as db
    conn = db.get_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute("DELETE FROM system_states WHERE state_key = 'podium_data'")
            conn.commit()
        except:
            pass
        finally:
            conn.close()

# ==========================================
# 📡 ५. TICKER & GLOBAL SYNC (Optimized Connections)
# ==========================================

def get_all_active_matches(conn=None) -> List[Dict]:
    """सक्रिय म्याचहरू तान्छ (Optionally accepts an existing connection)"""
    import pandas as pd
    own_conn = False
    if conn is None:
        conn = db.get_connection()
        own_conn = True
    try:
        df = pd.read_sql_query("SELECT * FROM live_match", conn)
        return df.to_dict(orient='records')
    except:
        return []
    finally:
        if own_conn:
            conn.close()

def get_ticker_headlines(conn=None) -> str:
    """न्यूज हेडलाइनहरू तयार पार्छ (नतिजा, लाइभ म्याच, कल, पदक तालिका, सूचना र फाइनल प्रवेश सहित)"""
    import pandas as pd
    import utils.live_state as ls
    from config import CONFIG
    
    headlines = []
    own_conn = False
    if conn is None:
        import database as db
        conn = db.get_connection()
        own_conn = True
        
    try:
        # १. स्वागत र प्रायोजक सन्देश (Welcome Message)
        event_title = CONFIG.get('EVENT_TITLE_NP', 'राष्ट्रपति रनिङ शिल्ड')
        headlines.append(f"🙏 {event_title} प्रत्यक्ष प्रसारणमा यहाँलाई हार्दिक स्वागत छ")
        
        # २. आपतकालीन सूचना (Announcements)
        ann = ls.get_announcement()
        if ann:
            headlines.append(f"📢 सूचना: {ann['title']} - {ann['subtitle']}")
            
        # ३. खेलाडी कल (Call Room)
        call = ls.get_active_call()
        if call:
            headlines.append(f"📣 कल रुम: {call.get('event_name')} ({call.get('round_name')}) का खेलाडीहरूलाई तुरुन्तै सम्पर्क गर्न अनुरोध छ")

        # ४. प्रत्यक्ष खेलहरू (Live Matches)
        live_matches = ls.get_all_active_matches()
        for m in live_matches[:3]: 
            evt_name = str(m.get('event_name', '')).lower()
            p1 = str(m.get('p_a', '')).split('|')[0]
            p2 = str(m.get('p_b', '')).split('|')[0]
            pts_a = m.get('score_a', 0)
            pts_b = m.get('score_b', 0)

            if 'volleyball' in evt_name or 'भलिबल' in evt_name:
                curr_set = m.get('current_set', 1)
                past_sets = m.get('past_sets', []) 
                match_str = f"🏐 लाइभ भलिबल: {p1} VS {p2} | "
                set_strs = [f"Set {i+1} [{s}]" for i, s in enumerate(past_sets)]
                set_strs.append(f"Live Set {curr_set} [{pts_a}-{pts_b}]")
                headlines.append(match_str + ", ".join(set_strs))
            elif 'kabaddi' in evt_name or 'कबडी' in evt_name:
                half = m.get('half', '') 
                half_txt = f"({half})" if half else ""
                headlines.append(f"🤼 लाइभ कबडी {half_txt}: {p1} [{pts_a} अंक] VS {p2} [{pts_b} अंक]")
            elif any(x in evt_name for x in ['karate', 'taekwondo', 'कराते', 'तेक्वान्दो']):
                round_no = m.get('round', '')
                round_txt = f"(Round {round_no})" if round_no else ""
                headlines.append(f"🥋 लाइभ म्याट {round_txt}: 🔴 {p1} [{pts_a}] VS 🔵 {p2} [{pts_b}]")
            else:
                headlines.append(f"🔴 प्रत्यक्ष खेल ({m.get('event_name')}): {p1} [{pts_a}] VS {p2} [{pts_b}]")

        # 💡 ५. फाइनल प्रवेश गरेका खेलाडी/पालिका (Final Qualifiers)
        q_qual = """
            SELECT r.event_code, e.name as event_name, e.gender, m.name as muni_name, COALESCE(p.name, t.name, 'Relay Team') as player_name
            FROM results r 
            JOIN events e ON r.event_code = e.code 
            LEFT JOIN players p ON r.player_id = p.id 
            LEFT JOIN teams t ON r.team_id = t.id 
            JOIN municipalities m ON m.id = COALESCE(r.municipality_id, p.municipality_id, t.municipality_id)
            WHERE r.event_code = (SELECT event_code FROM results WHERE medal='Qualified' ORDER BY id DESC LIMIT 1) 
            AND r.medal = 'Qualified'
        """
        df_qual = pd.read_sql_query(q_qual, conn)
        if not df_qual.empty:
            ev_name = df_qual.iloc[0]['event_name']
            g_label = "Boys" if df_qual.iloc[0]['gender'] in ['Male', 'Boys', 'Boy'] else "Girls"
            
            qual_list = []
            for _, r in df_qual.iterrows():
                muni = r['muni_name'].replace('Rural Municipality', '').replace('Municipality', '').replace('गाउँपालिका', '').replace('नगरपालिका', '').strip()
                p_name = r['player_name']
                # रिले हो भने पालिका मात्र, सिङ्गल हो भने नाम र पालिका दुवै
                if "Relay" in ev_name or p_name == 'Relay Team':
                    if muni not in qual_list: qual_list.append(muni)
                else:
                    qual_list.append(f"{p_name} ({muni})")
            
            # डुप्लिकेट हटाउने र टिकरमा पठाउने
            qual_list = list(dict.fromkeys(qual_list))
            headlines.append(f"🎯 फाइनल प्रवेश ({ev_name} - {g_label}): {', '.join(qual_list)} फाइनल चरणमा प्रवेश गर्न सफल हुनुभएको छ!")

        # ६. पछिल्लो नतिजा (Latest Results - Gold, Silver, Bronze)
        q_results = """
            SELECT r.event_code, e.name as event_name, e.gender, r.medal, m.name as muni_name, COALESCE(p.name, t.name, 'Relay Team') as player_name
            FROM results r 
            JOIN events e ON r.event_code = e.code 
            LEFT JOIN players p ON r.player_id = p.id 
            LEFT JOIN teams t ON r.team_id = t.id 
            JOIN municipalities m ON m.id = COALESCE(r.municipality_id, p.municipality_id, t.municipality_id)
            WHERE r.event_code IN (SELECT event_code FROM results WHERE medal='Gold' ORDER BY id DESC LIMIT 2)
        """
        df_res = pd.read_sql_query(q_results, conn)
        if not df_res.empty:
            events = df_res['event_code'].unique()
            for ev in events:
                ev_data = df_res[df_res['event_code'] == ev]
                ev_name = ev_data.iloc[0]['event_name']
                g_label = "Boys" if ev_data.iloc[0]['gender'] in ['Male', 'Boys', 'Boy'] else "Girls"
                res_str = f"🏆 नतिजा अपडेट ({ev_name} - {g_label}): "
                
                gold_data = ev_data[ev_data['medal'] == 'Gold']
                if not gold_data.empty:
                    muni = gold_data.iloc[0]['muni_name'].replace('Rural Municipality', '').replace('Municipality', '').replace('गाउँपालिका', '').replace('नगरपालिका', '').strip()
                    players = ", ".join(gold_data['player_name'].dropna().unique())
                    res_str += f"🥇 स्वर्ण: {muni} ({players}) "
                    
                silver_data = ev_data[ev_data['medal'] == 'Silver']
                if not silver_data.empty:
                    muni = silver_data.iloc[0]['muni_name'].replace('Rural Municipality', '').replace('Municipality', '').replace('गाउँपालिका', '').replace('नगरपालिका', '').strip()
                    res_str += f"| 🥈 रजत: {muni} "
                    
                bronze_data = ev_data[ev_data['medal'] == 'Bronze']
                if not bronze_data.empty:
                    munis = ", ".join(bronze_data['muni_name'].replace({'Rural Municipality': '', 'Municipality': '', 'गाउँपालिका': '', 'नगरपालिका': ''}, regex=True).str.strip().unique())
                    res_str += f"| 🥉 कास्य: {munis}"
                    
                headlines.append(res_str)

        # ७. पदक तालिकाको अग्रणी पालिका (Leading Municipality)
        q_tally = """
            SELECT m.name as muni_name, SUM(CASE WHEN r.medal='Gold' THEN 1 ELSE 0 END) as golds
            FROM results r JOIN municipalities m ON r.municipality_id = m.id 
            GROUP BY m.name ORDER BY golds DESC LIMIT 1
        """
        df_tally = pd.read_sql_query(q_tally, conn)
        if not df_tally.empty and df_tally.iloc[0]['golds'] > 0:
            lead_muni = df_tally.iloc[0]['muni_name'].replace('Rural Municipality', '').replace('Municipality', '').replace('गाउँपालिका', '').replace('नगरपालिका', '').strip()
            lead_gold = df_tally.iloc[0]['golds']
            headlines.append(f"📊 पदक तालिका अपडेट: {lead_muni} {lead_gold} स्वर्णसहित अग्रस्थानमा!")
            
    except Exception as e:
        print(f"Ticker Error: {e}")
        pass
    finally:
        if own_conn:
            conn.close()
            
    return " &nbsp; ✦ &nbsp; ".join(headlines) if headlines else f"🏆 {CONFIG.get('EVENT_TITLE_NP', 'प्रतियोगिता')} प्रत्यक्ष प्रसारण"


def clear_live_state() -> None:
    conn = db.get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                DELETE FROM system_states 
                WHERE state_key NOT IN ('master_schedule') 
                AND state_key NOT LIKE 'fixture_%'
            """)
            conn.commit()
    finally:
        conn.close()


def _save_state(key: str, data: dict) -> None:
    """लोकलमा सेभ गर्ने र इन्टरनेट भए क्लाउडमा पनि पठाउने (Dual-Write)"""
    json_data = json.dumps(data, ensure_ascii=False)
    query = """
        INSERT INTO system_states (state_key, state_data, updated_at) 
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (state_key) DO UPDATE 
        SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
    """
    
    # १. प्राथमिक DB मा सेभ गर्ने (ल्यापटपमा छ भने ल्यापटपमै सेभ हुन्छ, जुन अल्ट्रा-फास्ट हुन्छ)
    primary_conn = db.get_connection()
    if primary_conn:
        try:
            with primary_conn.cursor() as cur:
                cur.execute(query, (key, json_data))
                primary_conn.commit()
        except Exception as e:
            logging.error(f"Primary DB Error: {e}")
        finally:
            primary_conn.close()

    # २. ब्याकग्राउन्डमा क्लाउडमा पठाउने (यदि हामी लोकल मोडमा छौं भने)
    if os.getenv("APP_MODE") == "LOCAL":
        def sync_to_cloud():
            cloud_conn = db.get_cloud_connection()
            if cloud_conn:
                try:
                    with cloud_conn.cursor() as cur:
                        cur.execute(query, (key, json_data))
                        cloud_conn.commit()
                except Exception:
                    pass # इन्टरनेट नभए वा क्लाउड डाउन भए पनि खेल रोकिँदैन
                finally:
                    cloud_conn.close()
        
        # यो कोडले स्कोर अपडेट गर्दा स्क्रिनलाई 'Hang' हुन दिँदैन
        thread = threading.Thread(target=sync_to_cloud)
        thread.daemon = True
        thread.start()

# ==========================================
# 📢 खेलाडी कल (Call Room Announcement)
# ==========================================
def trigger_call(event_name, round_name, call_type, color_code):
    """खेलाडीहरूलाई ट्र्याक वा म्याटमा बोलाउनको लागि लाइभ स्क्रिनमा पठाउने र अटोमेटिक अडियो बनाउने"""
    import json
    import os
    import database as db
    from datetime import datetime
    
    # 💡 gTTS लाइब्रेरी तान्ने (यदि इन्स्टल छैन भने terminal मा: pip install gTTS गर्नुहोला)
    try:
        from gtts import gTTS
    except ImportError:
        gTTS = None
        print("gTTS library is missing. Audio will not be generated.")

    call_data = {
        "event_name": event_name,
        "round_name": round_name,
        "call_type": call_type,
        "color_code": color_code,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # १. पहिले डाटाबेसमा सेभ गर्ने
    conn = db.get_connection()
    if conn:
        try:
            c = conn.cursor()
            # 💡 PostgreSQL Upsert (नयाँ छ भने इन्सर्ट, पुरानो छ भने अपडेट)
            c.execute("""
                INSERT INTO system_states (state_key, state_data) 
                VALUES ('active_call', %s)
                ON CONFLICT (state_key) 
                DO UPDATE SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
            """, (json.dumps(call_data),))
            conn.commit()
        except Exception as e:
            print(f"Call trigger error: {e}")
        finally:
            conn.close()

    # २. 💡 नयाँ थपिएको: डाटाबेसमा सेभ भएपछि अडियो जेनेरेट गर्ने
    if gTTS:
        try:
            # बोल्ने म्यासेज तयार गर्ने (अङ्ग्रेजीमा एकदमै प्रोफेसनल सुनिन्छ)
            # कल टाइपमा FIRST CALL, SECOND CALL जस्ता कुरा हुन्छन्
            announcement_text = f"Attention please! {call_type}. {call_type} for {event_name}, {round_name}. All players, please report to the call room immediately."
            
            # टेक्स्टलाई अडियोमा परिणत गर्ने (slow=False गर्दा नर्मल स्पिडमा बोल्छ)
            tts = gTTS(text=announcement_text, lang='en', slow=False)
            
            # sounds फोल्डर छ कि छैन चेक गर्ने, नभए आफैँ बनाउने
            os.makedirs("sounds", exist_ok=True)
            
            # MP3 फाइल सेभ गर्ने
            tts.save("sounds/latest_call.mp3")
            print("✅ Audio generated successfully!")
        except Exception as e:
            print(f"Audio Generation Error: {e}")

def clear_call():
    """टिभीमा अड्किएको कल म्यासेज हटाएर स्क्रिन सफा गर्ने"""
    import database as db
    conn = db.get_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute("DELETE FROM system_states WHERE state_key = 'active_call'")
            conn.commit()
        except Exception as e:
            pass
        finally:
            conn.close()


def get_active_call():
    """टिभीको लागि एक्टिभ कल तान्ने (६० सेकेन्डपछि स्वतः हट्ने प्रणालीसहित)"""
    import json
    import database as db
    from datetime import datetime
    
    conn = db.get_connection()
    if not conn: return None
    try:
        c = conn.cursor()
        c.execute("SELECT state_data FROM system_states WHERE state_key = 'active_call'")
        row = c.fetchone()
        if row and row[0]:
            call_data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
            
            # 💡 जादु १: घडीको समयअनुसार ६० सेकेन्ड नाघेपछि डाटाबेसबाटै कल उडाइदिने
            if 'timestamp' in call_data:
                call_time = datetime.strptime(call_data['timestamp'], "%Y-%m-%d %H:%M:%S")
                diff_seconds = (datetime.now() - call_time).total_seconds()
                
                if diff_seconds > 60:  # ६० सेकेन्ड (१ मिनेट) पछि
                    clear_call()       # डाटाबेसबाट क्लिन गर्ने
                    return None        
                    
            return call_data
        return None
    except Exception as e:
        print(f"Get Call Error: {e}")
        return None
    finally:
        conn.close()


def get_podium():
    """टिभीमा देखाउनको लागि डाटाबेसबाट पोडियमको नतिजा तान्ने"""
    import json
    import database as db
    
    conn = db.get_connection()
    if not conn: return None
    try:
        c = conn.cursor()
        c.execute("SELECT state_data FROM system_states WHERE state_key = 'podium_data'")
        row = c.fetchone()
        
        if row and row[0]:
            # यदि डाटाबेसले सिधै डिक्सनरी (dict) दियो भने त्यही पठाउने, नत्र JSON बाट रूपान्तरण गर्ने
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None
    except Exception as e:
        print(f"Get podium error: {e}")
        return None
    finally:
        conn.close()

# ==========================================
# 📅 खेल तालिका (Schedule Management)
# ==========================================
def get_db_schedules(day_filter="All"):
    """एनाउन्सर र डिस्प्लेको लागि डाटाबेसबाट खेल तालिका तान्ने"""
    import pandas as pd
    import database as db
    
    conn = db.get_connection()
    if not conn: 
        return pd.DataFrame() # कनेक्सन नभए खाली पठाउने
        
    try:
        # यदि 'Day 1', 'Day 2' जस्तो फिल्टर छ भने त्यही दिनको मात्र तान्ने
        if day_filter and day_filter != "All":
            q = "SELECT * FROM schedules WHERE day = %s ORDER BY time ASC"
            df = pd.read_sql_query(q, conn, params=(day_filter,))
        else:
            # 'All' छ भने सबै दिनको तान्ने
            q = "SELECT * FROM schedules ORDER BY day ASC, time ASC"
            df = pd.read_sql_query(q, conn)
        return df
    except Exception as e:
        # 💡 जादु: यदि 'schedules' टेबल डाटाबेसमा बनिसकेको छैन भने पनि एप क्र्यास हुन नदिने!
        return pd.DataFrame()
    finally:
        conn.close()

# ==========================================
# 📊 म्याच नतिजा (Single Match Result)
# ==========================================
def get_match_result():
    """टिभीमा देखाउनको लागि भर्खरै सकिएको म्याचको नतिजा तान्ने"""
    import json
    import database as db
    
    conn = db.get_connection()
    if not conn: return None
    try:
        c = conn.cursor()
        c.execute("SELECT state_data FROM system_states WHERE state_key = 'match_result'")
        row = c.fetchone()
        
        if row and row[0]:
            return row[0] if isinstance(row[0], dict) else json.loads(row[0])
        return None
    except Exception as e:
        print(f"Get match result error: {e}")
        return None
    finally:
        conn.close()

def clear_match_result():
    """टिभीबाट म्याचको नतिजा हटाउने"""
    import database as db
    conn = db.get_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute("DELETE FROM system_states WHERE state_key = 'match_result'")
            conn.commit()
        except:
            pass
        finally:
            conn.close()

def clear_announcement():
    """टिभीबाट म्यासेज/सूचना पूर्ण रूपमा हटाउने (१००% काम गर्ने तरिका)"""
    import database as db
    conn = db.get_connection()
    if conn:
        try:
            c = conn.cursor()
            # अपडेट गर्नुभन्दा सिधै डिलिट गर्दा कुनै एरर आउँदैन
            c.execute("DELETE FROM live_state WHERE key = 'announcement'")
            conn.commit()
        except Exception as e:
            print(f"Error clearing announcement: {e}")
        finally:
            conn.close()

# ==========================================
# 🏃‍♂️ एथलेटिक्स फिक्चर (Heats & Finals)
# ==========================================
def save_fixture(event_code: str, stage: str, data: list) -> None:
    """एथलेटिक्सको हिट्स वा फाइनलको फिक्चर सेभ गर्ने"""
    # यसले 'fixture_100M_heats' जस्तो युनिक नाम (Key) बनाउँछ
    key = f"fixture_{event_code}_{stage}"
    
    # हामीले माथि नै बनाएको _save_state फङ्सनलाई प्रयोग गर्ने
    _save_state(key, data)

def get_fixture(event_code: str, stage: str):
    """सेभ गरिएको फिक्चर डाटाबेसबाट तान्ने"""
    key = f"fixture_{event_code}_{stage}"
    return _get_state(key)
