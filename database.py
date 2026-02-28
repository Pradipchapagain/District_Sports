import psycopg2
from psycopg2 import extras
import pandas as pd
import json
import hashlib
import os
import streamlit as st


# ==========================================
# 🔌 १. CONFIGURATION & CONNECTIONS
# ==========================================

# नोट: उत्पादन (Production) मा जाँदा 'Environment Variables' प्रयोग गर्नु राम्रो हुन्छ।

DB_CONFIG = {
    "dbname": "postgres",
    "user": "postgres.uzmquvpwzfzjqwbzivsh",
    "password": "TemporaryPassword123!",
    "host": "aws-0-ap-southeast-1.pooler.supabase.com",
    "port": "6432"
}

def get_connection():

    """Neon Cloud सँग कनेक्सन"""
    conn_url = "postgresql://neondb_owner:npg_d2FTQvBN5jUw@ep-nameless-violet-a1x5ur95-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
   
    # यसले सिधै कनेक्सन फर्काउँछ, कनेक्ट भएन भने स्पष्ट एरर दिन्छ
    conn = psycopg2.connect(conn_url)
    return conn


# ==========================================
# 🔑 २. AUTHENTICATION & SECURITY
# ==========================================

def hash_password(password):
    """पासवर्डलाई SHA-256 मा इन्क्रिप्ट गर्छ।"""
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    """प्रयोगकर्ताको लगइन विवरण जाँच गर्छ।"""
    pwd = hash_password(password)
    conn = get_connection()
    c = conn.cursor(cursor_factory=extras.RealDictCursor)
    c.execute("SELECT * FROM users WHERE username=%s AND password_hash=%s", (username, pwd))
    user = c.fetchone()
    c.close()
    conn.close()
    return user



# ==========================================
# 🏛️ ३. MASTER DATA HELPERS (Palika & Events)
# ==========================================
@st.cache_data(ttl=600)
def get_events():
    """सबै खेलहरूको सूची तान्ने (Caching बिनाको सिधा कोइरी)"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM events ORDER BY name", conn)
    conn.close()
    return df

def update_event_lock(event_code, lock_status):
    """खेलको दर्ता लक वा अनलक गर्ने"""
    conn = get_connection()
    c = conn.cursor()
    status = 1 if lock_status else 0
    c.execute("UPDATE events SET is_locked = %s, updated_at = CURRENT_TIMESTAMP WHERE code = %s", (status, event_code))
    conn.commit()
    c.close()
    conn.close()

@st.cache_data(ttl=600)
def get_municipalities():
    """सबै पालिकाहरूको सूची तान्ने"""
    conn = get_connection()
    df = pd.read_sql_query("SELECT id, name FROM municipalities ORDER BY name", conn)
    conn.close()
    return df

def seed_events(conn):
    """प्रणाली सुरु गर्दा आवश्यक सबै ६६ खेलहरू अटोमेटिक इन्सर्ट गर्छ।"""
    cursor = conn.cursor()
    # (code, name, category, sub_category, event_group, specific_event, gender, type, match_type, max_participants)
    events_data = [
    # --- एथलेटिक्स ट्र्याक (छात्र - Boys Track) ---
    ('BTR100', '100m Race', 'Athletics', 'Track', 'Sprint', '100m', 'Boys', 'Individual', 'Track', 1),
    ('BTR200', '200m Race', 'Athletics', 'Track', 'Sprint', '200m', 'Boys', 'Individual', 'Track', 1),
    ('BTR400', '400m Race', 'Athletics', 'Track', 'Sprint', '400m', 'Boys', 'Individual', 'Track', 1),
    ('BTR800', '800m Race', 'Athletics', 'Track', 'Middle Distance', '800m', 'Boys', 'Individual', 'Track', 1),
    ('BTR1500', '1500m Race', 'Athletics', 'Track', 'Middle Distance', '1500m', 'Boys', 'Individual', 'Track', 1),
    ('BTR3000', '3000m Race', 'Athletics', 'Track', 'Long Distance', '3000m', 'Boys', 'Individual', 'Track', 1),
    ('BTR4X100', '4×100m Relay', 'Athletics', 'Track', 'Relay', '4×100m', 'Boys', 'Team', 'Track', 4),
    ('BTR4X400', '4×400m Relay', 'Athletics', 'Track', 'Relay', '4×400m', 'Boys', 'Team', 'Track', 4),

    # --- एथलेटिक्स ट्र्याक (छात्रा - Girls Track) ---
    ('GTR100', '100m Race', 'Athletics', 'Track', 'Sprint', '100m', 'Girls', 'Individual', 'Track', 1),
    ('GTR200', '200m Race', 'Athletics', 'Track', 'Sprint', '200m', 'Girls', 'Individual', 'Track', 1),
    ('GTR400', '400m Race', 'Athletics', 'Track', 'Sprint', '400m', 'Girls', 'Individual', 'Track', 1),
    ('GTR800', '800m Race', 'Athletics', 'Track', 'Middle Distance', '800m', 'Girls', 'Individual', 'Track', 1),
    ('GTR1500', '1500m Race', 'Athletics', 'Track', 'Middle Distance', '1500m', 'Girls', 'Individual', 'Track', 1),
    ('GTR3000', '3000m Race', 'Athletics', 'Track', 'Long Distance', '3000m', 'Girls', 'Individual', 'Track', 1),
    ('GTR4X100', '4×100m Relay', 'Athletics', 'Track', 'Relay', '4×100m', 'Girls', 'Team', 'Track', 4),
    ('GTR4X400', '4×400m Relay', 'Athletics', 'Track', 'Relay', '4×400m', 'Girls', 'Team', 'Track', 4),

    # --- एथलेटिक्स फिल्ड (छात्र - Boys Field) ---
    ('BFDHJ', 'High Jump', 'Athletics', 'Field', 'Jump', 'High Jump', 'Boys', 'Individual', 'Field', 1),
    ('BFDLJ', 'Long Jump', 'Athletics', 'Field', 'Jump', 'Long Jump', 'Boys', 'Individual', 'Field', 1),
    ('BFDTJ', 'Triple Jump', 'Athletics', 'Field', 'Jump', 'Triple Jump', 'Boys', 'Individual', 'Field', 1),
    ('BFDSP', 'Shot Put', 'Athletics', 'Field', 'Throw', 'Shot Put', 'Boys', 'Individual', 'Field', 1),
    ('BFDJT', 'Javelin Throw', 'Athletics', 'Field', 'Throw', 'Javelin Throw', 'Boys', 'Individual', 'Field', 1),

    # --- एथलेटिक्स फिल्ड (छात्रा - Girls Field) ---
    ('GFDHJ', 'High Jump', 'Athletics', 'Field', 'Jump', 'High Jump', 'Girls', 'Individual', 'Field', 1),
    ('GFDLJ', 'Long Jump', 'Athletics', 'Field', 'Jump', 'Long Jump', 'Girls', 'Individual', 'Field', 1),
    ('GFDTJ', 'Triple Jump', 'Athletics', 'Field', 'Jump', 'Triple Jump', 'Girls', 'Individual', 'Field', 1),
    ('GFDSP', 'Shot Put', 'Athletics', 'Field', 'Throw', 'Shot Put', 'Girls', 'Individual', 'Field', 1),
    ('GFDJT', 'Javelin Throw', 'Athletics', 'Field', 'Throw', 'Javelin Throw', 'Girls', 'Individual', 'Field', 1),

    # --- टिम गेम (Team Games) ---
    ('BVB', 'Volleyball', 'Team Game', 'Volleyball', 'Ball Game', 'Volleyball', 'Boys', 'Team', 'Head_to_Head', 12),
    ('GVB', 'Volleyball', 'Team Game', 'Volleyball', 'Ball Game', 'Volleyball', 'Girls', 'Team', 'Head_to_Head', 12),
    ('BKBD', 'Kabaddi', 'Team Game', 'Kabaddi', 'Contact Sport', 'Kabaddi', 'Boys', 'Team', 'Head_to_Head', 12),
    ('GKBD', 'Kabaddi', 'Team Game', 'Kabaddi', 'Contact Sport', 'Kabaddi', 'Girls', 'Team', 'Head_to_Head', 12),

    # --- मार्शल आर्ट्स: कराते (Karate) ---
    ('BKK', 'Solo Kata', 'Martial Arts', 'Karate', 'Kata', 'Solo Kata', 'Boys', 'Individual', 'Demonstration', 1),
    ('GKK', 'Solo Kata', 'Martial Arts', 'Karate', 'Kata', 'Solo Kata', 'Girls', 'Individual', 'Demonstration', 1),
    ('BKM42', 'Kumite -42kg', 'Martial Arts', 'Karate', 'Kumite', '-42kg', 'Boys', 'Individual', 'Combat', 1),
    ('BKM47', 'Kumite -47kg', 'Martial Arts', 'Karate', 'Kumite', '-47kg', 'Boys', 'Individual', 'Combat', 1),
    ('BKM52', 'Kumite -52kg', 'Martial Arts', 'Karate', 'Kumite', '-52kg', 'Boys', 'Individual', 'Combat', 1),
    ('BKM57', 'Kumite -57kg', 'Martial Arts', 'Karate', 'Kumite', '-57kg', 'Boys', 'Individual', 'Combat', 1),
    ('BKM62', 'Kumite -62kg', 'Martial Arts', 'Karate', 'Kumite', '-62kg', 'Boys', 'Individual', 'Combat', 1),
    ('GKM40', 'Kumite -40kg', 'Martial Arts', 'Karate', 'Kumite', '-40kg', 'Girls', 'Individual', 'Combat', 1),
    ('GKM45', 'Kumite -45kg', 'Martial Arts', 'Karate', 'Kumite', '-45kg', 'Girls', 'Individual', 'Combat', 1),
    ('GKM50', 'Kumite -50kg', 'Martial Arts', 'Karate', 'Kumite', '-50kg', 'Girls', 'Individual', 'Combat', 1),
    ('GKM55', 'Kumite -55kg', 'Martial Arts', 'Karate', 'Kumite', '-55kg', 'Girls', 'Individual', 'Combat', 1),
    ('GKM60', 'Kumite -60kg', 'Martial Arts', 'Karate', 'Kumite', '-60kg', 'Girls', 'Individual', 'Combat', 1),

    # --- मार्शल आर्ट्स: तेक्वान्दो (Taekwondo) ---
    ('BTKPOOM', 'Solo Poomsae', 'Martial Arts', 'Taekwondo', 'Poomsae', 'Solo Poomsae', 'Boys', 'Individual', 'Demonstration', 1),
    ('GTKPOOM', 'Solo Poomsae', 'Martial Arts', 'Taekwondo', 'Poomsae', 'Solo Poomsae', 'Girls', 'Individual', 'Demonstration', 1),
    ('BTW45', 'Kyorugi -45kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-45kg', 'Boys', 'Individual', 'Combat', 1),
    ('BTW48', 'Kyorugi -48kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-48kg', 'Boys', 'Individual', 'Combat', 1),
    ('BTW51', 'Kyorugi -51kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-51kg', 'Boys', 'Individual', 'Combat', 1),
    ('BTW55', 'Kyorugi -55kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-55kg', 'Boys', 'Individual', 'Combat', 1),
    ('BTW59', 'Kyorugi -59kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-59kg', 'Boys', 'Individual', 'Combat', 1),
    ('GTW42', 'Kyorugi -42kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-42kg', 'Girls', 'Individual', 'Combat', 1),
    ('GTW44', 'Kyorugi -44kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-44kg', 'Girls', 'Individual', 'Combat', 1),
    ('GTW46', 'Kyorugi -46kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-46kg', 'Girls', 'Individual', 'Combat', 1),
    ('GTW49', 'Kyorugi -49kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-49kg', 'Girls', 'Individual', 'Combat', 1),
    ('GTW52', 'Kyorugi -52kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-52kg', 'Girls', 'Individual', 'Combat', 1),

    # --- मार्शल आर्ट्स: उसु (Wushu) ---
    ('BWFC', 'Changquan', 'Martial Arts', 'Wushu', 'Taolu', 'Changquan', 'Boys', 'Individual', 'Demonstration', 1),
    ('BWFN', 'Nanquan', 'Martial Arts', 'Wushu', 'Taolu', 'Nanquan', 'Boys', 'Individual', 'Demonstration', 1),
    ('BWFTJ', 'Taiji Quan', 'Martial Arts', 'Wushu', 'Taolu', 'Taiji Quan', 'Boys', 'Individual', 'Demonstration', 1),
    ('GWFC', 'Changquan', 'Martial Arts', 'Wushu', 'Taolu', 'Changquan', 'Girls', 'Individual', 'Demonstration', 1),
    ('GWFN', 'Nanquan', 'Martial Arts', 'Wushu', 'Taolu', 'Nanquan', 'Girls', 'Individual', 'Demonstration', 1),
    ('GWFTJ', 'Taiji Quan', 'Martial Arts', 'Wushu', 'Taolu', 'Taiji Quan', 'Girls', 'Individual', 'Demonstration', 1),
    ('BWSD45', 'Sanda -45kg', 'Martial Arts', 'Wushu', 'Sanda', '-45kg', 'Boys', 'Individual', 'Combat', 1),
    ('BWSD48', 'Sanda -48kg', 'Martial Arts', 'Wushu', 'Sanda', '-48kg', 'Boys', 'Individual', 'Combat', 1),
    ('BWSD51', 'Sanda -51kg', 'Martial Arts', 'Wushu', 'Sanda', '-51kg', 'Boys', 'Individual', 'Combat', 1),
    ('GWSD42', 'Sanda -42kg', 'Martial Arts', 'Wushu', 'Sanda', '-42kg', 'Girls', 'Individual', 'Combat', 1),
    ('GWSD45', 'Sanda -45kg', 'Martial Arts', 'Wushu', 'Sanda', '-45kg', 'Girls', 'Individual', 'Combat', 1),
    ('GWSD48', 'Sanda -48kg', 'Martial Arts', 'Wushu', 'Sanda', '-48kg', 'Girls', 'Individual', 'Combat', 1)
]
    query = """
        INSERT INTO events (code, name, category, sub_category, event_group, specific_event, gender, type, match_type, max_participants) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (code) DO NOTHING
    """
    try:
        cursor.executemany(query, events_data)
        conn.commit()
    finally:
        cursor.close()

# ==========================================
# 📝 ४. PLAYER & TEAM MANAGEMENT
# ==========================================
def add_player(municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, guardian_name, contact_no, photo_path=None):
    """नयाँ खेलाडी दर्ता गर्छ र उत्पन्न भएको ID फर्काउँछ।"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO players (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, guardian_name, contact_no, photo_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, guardian_name, contact_no, photo_path))
        player_id = c.fetchone()[0]
        conn.commit()
        return player_id, "Success"
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        c.close(); conn.close()

def add_player(municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, guardian_name="", contact_no="", photo_path=None):
    """नयाँ खेलाडी दर्ता गर्छ र उत्पन्न भएको ID फर्काउँछ।"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO players (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, guardian_name, contact_no, photo_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id
        """, (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, guardian_name, contact_no, photo_path))
        player_id = c.fetchone()[0]
        conn.commit()
        return player_id, "Success"
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        c.close(); conn.close()
    
def update_player_info(player_id, iemis_id, name, dob_bs, school_name, class_val, guardian_name, contact_no):
    """खेलाडीको व्यक्तिगत विवरण अद्यावधिक गर्छ।"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            UPDATE players SET iemis_id=%s, name=%s, dob_bs=%s, school_name=%s, class_val=%s, guardian_name=%s, contact_no=%s
            WHERE id=%s
        ''', (iemis_id, name, dob_bs, school_name, class_val, guardian_name, contact_no, player_id))
        conn.commit()
        return True, "Success"
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        c.close(); conn.close()

def update_player_registrations(player_id, municipality_id, event_codes):
    """खेलाडीको खेल सूची अपडेट गर्छ। (Cloud SQL Ready)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        # पहिले पुराना सबै दर्ता हटाउने
        c.execute("DELETE FROM registrations WHERE player_id=%s", (player_id,))
        # नयाँ दर्ताहरू थप्ने
        for code in event_codes:
            c.execute("""
                INSERT INTO registrations (player_id, event_code, municipality_id) 
                VALUES (%s, %s, %s)
            """, (player_id, code, municipality_id))
        conn.commit()
        return True
    except Exception as e:
        conn.rollback(); return False
    finally:
        c.close(); conn.close()
# ==========================================
# 📊 ५. BULK IMPORT & DATA HANDLING
# ==========================================
def import_school_data(excel_file, municipality_id):
    """एक्सेल फाइलबाट धेरै खेलाडीहरूको डाटा एकैपटक इम्पोर्ट गर्छ।"""
    conn = get_connection()
    c = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        # खेलहरूको सूची र टाइप तान्ने
        c.execute("SELECT code, name, type FROM events")
        events_rows = c.fetchall()
        event_type_map = {row['code']: row['type'] for row in events_rows}
        event_name_map = {row['name']: row['code'] for row in events_rows}
        
        players_cnt, reg_cnt = 0, 0

        for sheet, gender in [('Boys_Entry', 'Boys'), ('Girls_Entry', 'Girls')]:
            try:
                # एक्सेल पढ्ने (skiprows=3 तपाईंको फाइलको फर्म्याट अनुसार)
                df = pd.read_excel(excel_file, sheet_name=sheet, skiprows=3)
                df = df.dropna(subset=['Student Name'])
                
                for _, row in df.iterrows():
                    p_name = str(row.get('Student Name', '')).strip()
                    if not p_name or p_name == 'nan': continue
                    
                    # १. खेलाडी थप्ने
                    c.execute("""
                        INSERT INTO players (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val)
                        VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
                    """, (municipality_id, str(row.get('EMIS ID', '')), p_name, gender, 
                          str(row.get('DOB (YYYY-MM-DD)', '2064-01-01')), 
                          str(row.get('School Name', 'Unknown')), str(row.get('Class', ''))))
                    pid = c.fetchone()['id']
                    players_cnt += 1

                    # २. खेलहरूमा दर्ता गर्ने (कलम ५ बाट सुरु हुने खेलका नामहरू)
                    for col in df.columns[5:]:
                        # यदि कलममा '1' छ भने त्यो खेलमा दर्ता गर्ने
                        if pd.notna(row.get(col)) and str(row.get(col)).strip() in ['1', '1.0']:
                            # नाम मिलेको खेलको कोड पत्ता लगाउने
                            e_code = event_name_map.get(col)
                            if e_code:
                                # खेलको लिङ्ग (Gender) मिलेको हुनुपर्छ
                                if (gender == 'Boys' and e_code.startswith('B')) or (gender == 'Girls' and e_code.startswith('G')):
                                    c.execute("""
                                        INSERT INTO registrations (player_id, event_code, municipality_id) 
                                        VALUES (%s, %s, %s)
                                        ON CONFLICT DO NOTHING
                                    """, (pid, e_code, municipality_id))
                                    reg_cnt += 1
            except Exception as e:
                print(f"Sheet Error: {e}")
                continue
                
        conn.commit()
        return True, f"Successfully imported {players_cnt} players and {reg_cnt} registrations."
    except Exception as e:
        conn.rollback(); return False, str(e)
    finally:
        c.close(); conn.close()

# ==========================================
# ⚠️ ६. RULE VALIDATIONS (Rule Engine)
# ==========================================
def check_athletics_violations():
    """एथलेटिक्समा ३ भन्दा बढी व्यक्तिगत खेल खेल्ने खेलाडीहरू खोज्छ।"""
    conn = get_connection()
    # SQL मा '%%Relay%%' को सट्टा '%Relay%' (PostgreSQL syntax)
    q = """
        SELECT p.name as "Player", m.name as "Municipality", STRING_AGG(e.name, ', ') as "Event_List"
        FROM registrations r 
        JOIN players p ON r.player_id = p.id 
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE e.category = 'Athletics' AND e.name NOT LIKE '%Relay%'
        GROUP BY p.id, p.name, m.name 
        HAVING COUNT(r.event_code) > 3
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_duplicate_emis():
    """एउटै EMIS ID प्रयोग गरी फरक-फरक नाम वा पालिकाबाट दर्ता भएका शंकास्पद खेलाडी खोज्छ।"""
    conn = get_connection()
    q = """
        SELECT p.iemis_id as "EMIS_ID", 
               STRING_AGG(DISTINCT p.name, ' / ') as "Names", 
               STRING_AGG(DISTINCT m.name, ' / ') as "Municipalities"
        FROM players p 
        LEFT JOIN municipalities m ON p.municipality_id = m.id
        WHERE p.iemis_id IS NOT NULL AND p.iemis_id NOT IN ('', '0', 'N/A', 'nan')
        GROUP BY p.iemis_id 
        HAVING COUNT(DISTINCT p.id) > 1
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_palika_player_quota(max_limit=88):
    """कोटा (Max 88) भन्दा बढी खेलाडी दर्ता गर्ने पालिकाहरूको सूची दिन्छ।"""
    conn = get_connection()
    q = "SELECT m.name as \"Municipality\", COUNT(p.id) as \"Total_Players\" FROM players p JOIN municipalities m ON p.municipality_id = m.id GROUP BY m.id, m.name HAVING COUNT(p.id) > %s"
    df = pd.read_sql_query(q, conn, params=(max_limit,)); conn.close(); return df

# ==========================================
# 🏅 ७. OFFICIALS & MATCH RESULTS
# ==========================================
def add_official(municipality_id, role, name, phone):
    """पालिकाको तर्फबाट खटिने अफिसियल/रेफ्रीको विवरण राख्छ।"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT INTO officials (municipality_id, role, name, phone) VALUES (%s, %s, %s, %s)", (municipality_id, role, name, phone))
    conn.commit(); c.close(); conn.close()

def save_match_result(event_code, muni_id, player_id, position, score_dict, medal):
    """खेलको अन्तिम नतिजा (Gold/Silver/Bronze) सेभ गर्छ। (JSON Support सहित)"""
    import json
    conn = get_connection()
    c = conn.cursor()
    try:
        # यदि सोही खेलमा यो खेलाडीको पुरानो नतिजा छ भने हटाउने (Update logic)
        c.execute("DELETE FROM results WHERE event_code = %s AND player_id = %s", (event_code, player_id))
        
        c.execute("""
            INSERT INTO results (event_code, municipality_id, player_id, position, score_details, medal)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (event_code, muni_id, player_id, position, json.dumps(score_dict), medal))
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Result Save Error: {e}")
    finally:
        c.close(); conn.close()

# =========================================================
# ⚙️ ८. SYSTEM SETTINGS & SETUP (The Engine)
# =========================================================


def get_system_setting(key, default_value=None):
    """डाटाबेसबाट सेटिङ तान्ने फङ्सन।"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT value FROM settings WHERE key = %s", (key,))
        row = c.fetchone()
        return row[0] if row else default_value
    except Exception:
        return default_value
    finally:
        c.close(); conn.close()

def seed_admin_user(conn):
    """सुरुमा छिर्न एडमिन युजर बनाउने।"""
    cursor = conn.cursor()
    admin_user = "admin"
    admin_pass = hash_password("admin123") 
    try:
        cursor.execute("SELECT id FROM users WHERE username = %s", (admin_user,))
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO users (username, password_hash, role) 
                VALUES (%s, %s, 'admin')
            """, (admin_user, admin_pass))
            conn.commit()
            print("👤 Default Admin: admin / admin123")
    except Exception as e:
        print(f"❌ Admin seed error: {e}")
    finally:
        cursor.close()

def create_tables():
    """क्लाउडमा सिधै सबै टेबल, अडिट लग र सेटिङहरू सिर्जना गर्छ।"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        sql_commands = [
            # १. आधारभूत टेबलहरू
            "CREATE TABLE IF NOT EXISTS municipalities (id SERIAL PRIMARY KEY, name VARCHAR(255) UNIQUE NOT NULL, logo_path TEXT)",
            "CREATE TABLE IF NOT EXISTS events (code VARCHAR(50) PRIMARY KEY, name VARCHAR(255) NOT NULL, category VARCHAR(100), sub_category VARCHAR(100), event_group VARCHAR(100), specific_event VARCHAR(100), gender VARCHAR(20), type VARCHAR(50), match_type VARCHAR(50), max_participants INTEGER DEFAULT 1, is_locked INTEGER DEFAULT 0, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS users (id SERIAL PRIMARY KEY, username VARCHAR(100) UNIQUE NOT NULL, password_hash TEXT NOT NULL, role VARCHAR(50) DEFAULT 'municipality', municipality_id INTEGER REFERENCES municipalities(id) ON DELETE CASCADE)",
            
            # २. खेलाडी र दर्ता
            "CREATE TABLE IF NOT EXISTS players (id SERIAL PRIMARY KEY, municipality_id INTEGER REFERENCES municipalities(id) ON DELETE CASCADE, iemis_id VARCHAR(50), name VARCHAR(255) NOT NULL, gender VARCHAR(20) NOT NULL, dob_bs VARCHAR(20), school_name VARCHAR(255), class_val VARCHAR(50), guardian_name VARCHAR(255), contact_no VARCHAR(50), photo_path TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS registrations (id SERIAL PRIMARY KEY, player_id INTEGER REFERENCES players(id) ON DELETE CASCADE, event_code VARCHAR(50) REFERENCES events(code) ON DELETE CASCADE, municipality_id INTEGER REFERENCES municipalities(id), UNIQUE(player_id, event_code))",
            "CREATE TABLE IF NOT EXISTS teams (id SERIAL PRIMARY KEY, event_code VARCHAR(50) REFERENCES events(code) ON DELETE CASCADE, municipality_id INTEGER REFERENCES municipalities(id) ON DELETE CASCADE, name VARCHAR(255) NOT NULL)",
            
            # ३. खेल सञ्चालन र नतिजा
            "CREATE TABLE IF NOT EXISTS matches (id SERIAL PRIMARY KEY, event_code VARCHAR(50) REFERENCES events(code) ON DELETE CASCADE, match_no INTEGER NOT NULL, round_name VARCHAR(100), title VARCHAR(255), comp1_muni_id INTEGER REFERENCES municipalities(id), comp2_muni_id INTEGER REFERENCES municipalities(id), winner_muni_id INTEGER REFERENCES municipalities(id), status VARCHAR(50) DEFAULT 'Pending', live_state JSONB DEFAULT '{}'::jsonb, source_match1 INTEGER, source_match2 INTEGER, team1_id INTEGER, team2_id INTEGER, winner_team_id INTEGER)",
            "CREATE TABLE IF NOT EXISTS results (id SERIAL PRIMARY KEY, event_code VARCHAR(50) REFERENCES events(code) ON DELETE CASCADE, municipality_id INTEGER REFERENCES municipalities(id) NOT NULL, player_id INTEGER REFERENCES players(id) NULL, team_id INTEGER REFERENCES teams(id) NULL, position INTEGER NOT NULL, medal VARCHAR(50), score_details JSONB, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            
            # ४. प्रणाली र लाइभ अपडेट
            "CREATE TABLE IF NOT EXISTS system_states (state_key VARCHAR(100) PRIMARY KEY, state_data JSONB, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS settings (key VARCHAR(100) PRIMARY KEY, value TEXT NOT NULL, description TEXT, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)",
            "CREATE TABLE IF NOT EXISTS officials (id SERIAL PRIMARY KEY, municipality_id INTEGER REFERENCES municipalities(id) ON DELETE CASCADE, role VARCHAR(100), name VARCHAR(255) NOT NULL, phone VARCHAR(50))",
            "CREATE TABLE IF NOT EXISTS live_match (id SERIAL PRIMARY KEY, event_code VARCHAR(50), bout_id VARCHAR(50), event_name VARCHAR(255), round_name VARCHAR(100), player1 VARCHAR(255), player2 VARCHAR(255), score_a VARCHAR(50) DEFAULT '0', score_b VARCHAR(50) DEFAULT '0', pen_a INTEGER DEFAULT 0, pen_b INTEGER DEFAULT 0, senshu VARCHAR(10), timer VARCHAR(10) DEFAULT '00:00', voting_open INTEGER DEFAULT 0, j1_vote VARCHAR(10), j2_vote VARCHAR(10), j3_vote VARCHAR(10), j4_vote VARCHAR(10), j5_vote VARCHAR(10))"            "CREATE TABLE IF NOT EXISTS schedules (id SERIAL PRIMARY KEY, day_name VARCHAR(50), schedule_time VARCHAR(100), title VARCHAR(255), description TEXT, event_code VARCHAR(50), is_completed INTEGER DEFAULT 0, schedule_order INTEGER)",
            
            # ५. अडिट लग (अडिटरको लागि सबैभन्दा महत्त्वपूर्ण)
            "CREATE TABLE IF NOT EXISTS audit_logs (id SERIAL PRIMARY KEY, user_id INTEGER REFERENCES users(id), action VARCHAR(255), table_name VARCHAR(100), row_id INTEGER, old_value TEXT, new_value TEXT, ip_address VARCHAR(50), created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
        ]

        # कमान्डहरू रन गर्ने
        for command in sql_commands:
            c.execute(command)
        
        # डिफाल्ट सेटिङहरू थप्ने
        c.execute("""
            INSERT INTO settings (key, value, description) VALUES 
            ('AGE_LIMIT_DATE', '2064-11-01', 'खेलाडीको उमेर हदबन्दी'),
            ('MAX_PLAYERS_PER_PALIKA', '88', 'अधिकतम खेलाडी कोटा'),
            ('ALLOW_MULTIPLE_TEAM_GAMES', 'False', 'बहु-टिम गेम अनुमति')
            ON CONFLICT (key) DO NOTHING
        """)
        
        conn.commit()
        print("✅ Neon Cloud: All Tables & Settings updated successfully!")
        
        # मास्टर डाटा (Admin र Events) सिडिङ गर्ने
        seed_admin_user(conn)
        seed_events(conn)
        
    except Exception as e:
        print(f"❌ Setup Error: {e}")
    finally:
        if 'c' in locals(): c.close()
        if 'conn' in locals(): conn.close()

def create_default_admin():
    """Home.py ले खोजेको एडमिन बनाउने फङ्सन"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        admin_user = "admin"
        # admin123 को ह्यास भ्यालु (तपाईँको सिस्टम अनुसार)
        import hashlib
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest() 
        
        c.execute("SELECT id FROM users WHERE username = %s", (admin_user,))
        if not c.fetchone():
            c.execute("INSERT INTO users (username, password_hash, role) VALUES (%s, %s, 'admin')", (admin_user, admin_pass))
            conn.commit()
            
    except Exception as e:
        print(f"Error checking admin: {e}")
    finally:
        if 'c' in locals(): c.close()
        if 'conn' in locals(): conn.close()

def log_action(user_id, action, table_name=None, row_id=None, old_val=None, new_val=None):
    """प्रणालीमा भएका परिवर्तनहरूको अडिट रेकर्ड राख्छ।"""
    conn = get_connection()
    c = conn.cursor()
    try:
        # IP Address पत्ता लगाउने (वैकल्पिक)
        query = """
            INSERT INTO audit_logs (user_id, action, table_name, row_id, old_value, new_value)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        c.execute(query, (user_id, action, table_name, row_id, str(old_val), str(new_val)))
        conn.commit()
    except Exception as e:
        print(f"Logging Error: {e}")
    finally:
        c.close(); conn.close()

@st.cache_data(ttl=600)
def get_audit_logs(limit=100):
    """भर्खरै भएका गतिविधिहरूको सूची तान्ने।"""
    conn = get_connection()
    q = """
        SELECT l.created_at as "Time", u.username as "User", l.action as "Action", 
               l.table_name as "Table", l.old_value as "From", l.new_value as "To"
        FROM audit_logs l
        JOIN users u ON l.user_id = u.id
        ORDER BY l.created_at DESC LIMIT %s
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

# ==========================================
# 🚀 EXECUTION BLOCK
# ==========================================
if __name__ == "__main__":
    create_tables()
    print("🚀 All set! Now run: streamlit run Home.py")

