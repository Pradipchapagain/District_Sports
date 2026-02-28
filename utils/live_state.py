import json
import time
import database as db
import psycopg2

# ==========================================
# 🛠️ Helper Function for Database State
# ==========================================
def _save_state(key, data_dict):
    """कुनै पनि लाइभ स्टेटलाई PostgreSQL को JSONB मा सेभ गर्ने"""
    conn = db.get_connection()
    c = conn.cursor()
    # 💡 PostgreSQL: UPSERT logic (Insert or Update)
    c.execute("""
        INSERT INTO system_states (state_key, state_data, updated_at) 
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (state_key) DO UPDATE 
        SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
    """, (key, json.dumps(data_dict, ensure_ascii=False)))
    conn.commit()
    c.close()
    conn.close()

def _get_state(key, expire_seconds=None):
    """डेटाबेसबाट स्टेट पढ्ने र समय नाघेको छ भने नदेखाउने"""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("SELECT state_data, EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - updated_at)) FROM system_states WHERE state_key = %s", (key,))
    row = c.fetchone()
    c.close()
    conn.close()
    
    if row:
        data, age_seconds = row[0], row[1]
        # यदि एक्स्पायर हुने समय तोकिएको छ र त्यो पार भयो भने None फर्काउने
        if expire_seconds and age_seconds > expire_seconds:
            _clear_state(key)
            return None
        return data if isinstance(data, dict) else json.loads(data)
    return None

def _clear_state(key):
    """म्याच सकिएपछि वा रिसेट गर्दा डेटाबेसबाट हटाउने"""
    conn = db.get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM system_states WHERE state_key = %s", (key,))
    conn.commit()
    c.close()
    conn.close()


# ==========================================
# १. प्रत्यक्ष खेल (Live Match Score) को स्टेट
# ==========================================
def update_live_match(event_name, p_a_name, p_b_name, score_a, score_b, status="Playing", 
                      pen_a=None, pen_b=None, senshu=None, timer=None, is_kumite=False):
    data = {
        "event_name": event_name,
        "p_a": p_a_name,
        "p_b": p_b_name,
        "score_a": score_a,
        "score_b": score_b,
        "status": status,
        "pen_a": pen_a,
        "pen_b": pen_b,
        "senshu": senshu,
        "timer": timer,
        "is_kumite": is_kumite
    }
    _save_state("live_match", data)

def clear_live_match():
    _clear_state("live_match")

def get_live_match():
    # १ घण्टा (3600 सेकेन्ड) भन्दा पुरानो भए नदेखाउने
    return _get_state("live_match", expire_seconds=3600)


# ==========================================
# २. उद्घोषकको सूचना (Announcement) को स्टेट
# ==========================================
def set_announcement(title, subtitle=""):
    _save_state("announcement", {"title": title, "subtitle": subtitle})

def clear_announcement():
    _clear_state("announcement")

def get_announcement():
    # ३० मिनेट (1800 सेकेन्ड) पछि आफैँ हराउने
    return _get_state("announcement", expire_seconds=1800)


# ==========================================
# ३. खेल तालिका (Master Schedule) को स्टेट
# ==========================================
def save_master_schedule(schedule_list):
    _save_state("master_schedule", schedule_list)

def get_master_schedule():
    return _get_state("master_schedule") or []

def trigger_schedule_display(day_name):
    _save_state("trigger_schedule", {"show_day": day_name})

def clear_schedule_display():
    _clear_state("trigger_schedule")

def get_schedule_trigger():
    # ३ मिनेट (180 सेकेन्ड) पछि आफैँ हराउने
    data = _get_state("trigger_schedule", expire_seconds=180)
    return data['show_day'] if data else None


# ==========================================
# ४. लाइभ पोडियम (Auto Celebration Screen)
# ==========================================
def trigger_podium(event_name, gold_data, silver_data, bronze_data):
    data = {
        "event_name": event_name,
        "gold": gold_data,
        "silver": silver_data,
        "bronze": bronze_data
    }
    _save_state("live_podium", data)

def clear_podium():
    _clear_state("live_podium")

def get_podium():
    # ६० सेकेन्ड (१ मिनेट) पछि आफैँ हराउने
    return _get_state("live_podium", expire_seconds=60)


# ==========================================
# ५. सिंगल म्याच नतिजा (Single Match Result)
# ==========================================
def trigger_match_result(match_title, winner, loser, score_summary):
    data = {
        "match_title": match_title,
        "winner": winner,
        "loser": loser,
        "score": score_summary
    }
    _save_state("live_match_result", data)

def clear_match_result():
    _clear_state("live_match_result")

def get_match_result():
    # ४५ सेकेन्ड पछि आफैँ हराउने
    return _get_state("live_match_result", expire_seconds=45)

# ==========================================
# ६. फर्मल कल (Formal Call)
# ==========================================
def trigger_call(event_name, round_name, call_type, color_code):
    data = {
        "event_name": event_name,
        "round_name": round_name,
        "call_type": call_type,
        "color": color_code
    }
    _save_state("formal_call", data)

def clear_call():
    _clear_state("formal_call")

def get_call():
    # २० सेकेन्ड पछि आफैँ हराउने
    return _get_state("formal_call", expire_seconds=20)


# ==========================================
# ८. कराते (Kata) को अन्तिम नतिजा 
# ==========================================
def trigger_kata_result(event_name, bout_id, aka_name, ao_name, votes_list, winner):
    data = {
        "event_name": event_name,
        "bout_id": bout_id,
        "aka_name": aka_name,
        "ao_name": ao_name,
        "votes": votes_list, 
        "winner": winner
    }
    _save_state("kata_result", data)

def clear_kata_result():
    _clear_state("kata_result")

def get_kata_result():
    # ४५ सेकेन्डपछि आफैँ हराउने
    return _get_state("kata_result", expire_seconds=45)

# ==========================================
# 9. उद्घाटन कार्यक्रमको सेडुअल
# ==========================================

def get_db_schedules(day_filter=None):
    """डेटाबेसबाट खेल तालिका तान्ने"""
    conn = db.get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if day_filter:
        c.execute("SELECT * FROM schedules WHERE day_name = %s ORDER BY schedule_order ASC", (day_filter,))
    else:
        c.execute("SELECT * FROM schedules ORDER BY day_name, schedule_order ASC")
    rows = c.fetchall()
    c.close(); conn.close()
    return rows
# ==========================================
# १०. सबै लाइभ स्टेट रिसेट गर्ने (Master Reset)
# ==========================================
def clear_live_state():
    conn = db.get_connection()
    c = conn.cursor()
    # 💡 'master_schedule' र 'fixtures_data' बाहेक सबै अस्थायी स्टेट हटाउने
    c.execute("DELETE FROM system_states WHERE state_key NOT IN ('master_schedule') AND state_key NOT LIKE 'fixture_%'")
    conn.commit()
    c.close()
    conn.close()


# ==========================================
# --- FIXTURE SYNC LOGIC (बहु-प्रयोगकर्ताको लागि) ---
# ==========================================
def save_fixture(event_code, fixture_type, data_list):
    """fixture_type: 'heats' वा 'bracket'"""
    _save_state(f"fixture_{event_code}", {"type": fixture_type, "data": data_list})

def get_fixture(event_code):
    """टिभीले टाइ-सिट पढ्ने।"""
    return _get_state(f"fixture_{event_code}")