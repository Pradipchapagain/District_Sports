# utils\live_state.py
import json
import logging
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
# 🏆 ४. PODIUM & RESULTS
# ==========================================

def trigger_podium(event_name: str, gold: Dict, silver: Dict, bronze: Any) -> None:
    _save_state("live_podium", {"event_name": event_name, "gold": gold, "silver": silver, "bronze": bronze})

def get_podium() -> Optional[Dict]:
    return _get_state("live_podium")

def trigger_match_result(match_title: str, winner: str, loser: str, score: str) -> None:
    _save_state("live_match_result", {"match_title": match_title, "winner": winner, "loser": loser, "score": score})

def get_match_result() -> Optional[Dict]:
    return _get_state("live_match_result")

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
    """न्यूज हेडलाइनहरू तयार पार्छ (Optionally accepts an existing connection)"""
    import pandas as pd
    headlines = []
    own_conn = False
    if conn is None:
        conn = db.get_connection()
        own_conn = True
    try:
        q = """
            SELECT COALESCE(p.name, t.name) as n, e.name as e 
            FROM results r JOIN events e ON r.event_code = e.code 
            LEFT JOIN players p ON r.player_id = p.id 
            LEFT JOIN teams t ON r.team_id = t.id 
            WHERE r.medal = 'Gold' ORDER BY r.id DESC LIMIT 2
        """
        df = pd.read_sql_query(q, conn)
        for _, r in df.iterrows():
            headlines.append(f"🥇 विनर अलर्ट: {r['n']} ले {r['e']} मा स्वर्ण जित्नुभयो")
    except:
        pass
    finally:
        if own_conn:
            conn.close()
            
    return " | ".join(headlines) if headlines else f"🏆 {CONFIG['EVENT_TITLE_NP']} प्रत्यक्ष प्रसारण"

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