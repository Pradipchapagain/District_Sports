import sqlite3
import pandas as pd
import os
import json
import hashlib
import database as db

# डाटाबेस फाइलको नाम
DB_FILE = "sports_db.sqlite"

def get_connection():
    """डाटाबेससँग कनेक्सन बनाउने फङ्सन"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    """सबै आवश्यक टेबलहरू बनाउने फङ्सन"""
    conn = get_connection()
    c = conn.cursor()

    # १. पालिकाहरु (MUNICIPALITIES)
    c.execute('''
        CREATE TABLE IF NOT EXISTS municipalities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            logo_path TEXT
        )
    ''')

    # २. खेलहरु (EVENTS)
    c.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,   -- e.g. BTR100
            name TEXT,          -- e.g. 100m Race (Boys)
            category TEXT,      -- Athletics, Martial Arts, Team Game
            sub_category TEXT,  -- Track, Field, Karate, Volleyball
            event_group TEXT,   -- Sprint, Jump, Kata, Kumite 
            specific_event TEXT,-- 100m, Long Jump
            gender TEXT,        -- Boys/Girls
            type TEXT,          -- Team / Individual
            max_participants INTEGER DEFAULT 1
        )
    ''')

    # ३. टिम दर्ता (TEAMS) - टिम गेमको टाइ-सिट बनाउन चाहिने
    c.execute('''
        CREATE TABLE IF NOT EXISTS teams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT,
            municipality_id INTEGER,
            name TEXT,
            FOREIGN KEY (municipality_id) REFERENCES municipalities (id),
            FOREIGN KEY (event_code) REFERENCES events (code)
        )
    ''')

    # ४. खेलाडीको मास्टर प्रोफाइल (PLAYERS) - एक पटक मात्र भरिने
    c.execute('''
        CREATE TABLE IF NOT EXISTS players (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            municipality_id INTEGER,
            iemis_id TEXT,
            name TEXT,
            gender TEXT,
            dob_bs TEXT,
            school_name TEXT,
            class_val TEXT,
            photo_path TEXT,
            FOREIGN KEY (municipality_id) REFERENCES municipalities (id)
        )
    ''')

    # ५. दर्ता (REGISTRATIONS) - कुन खेलाडीले कुन खेल खेल्ने? (One-to-Many)
    c.execute('''
        CREATE TABLE IF NOT EXISTS registrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            event_code TEXT,
            FOREIGN KEY (player_id) REFERENCES players (id),
            FOREIGN KEY (event_code) REFERENCES events (code)
        )
    ''')

    # ६. नतिजा (RESULTS)
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT,
            player_id INTEGER,  -- 👈 यो व्यक्तिगत खेलाडीको लागि
            team_id INTEGER,    -- 👈 यो टिम (भलिबल/कबड्डी) को लागि
            position INTEGER,
            medal TEXT,
            score TEXT
        )
    ''')

    # ७. हिट्स (HEATS)
    c.execute('''
        CREATE TABLE IF NOT EXISTS heats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT,
            round_name TEXT,
            heat_no TEXT,
            lane_no INTEGER,
            team_id INTEGER,
            FOREIGN KEY (team_id) REFERENCES teams (id)
        )
    ''')

    # ८. म्याच र टाइ-सिट (MATCHES / BRACKETS)
    c.execute('''
        CREATE TABLE IF NOT EXISTS matches (
            db_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT,
            match_id INTEGER,          -- Bracket match ID (1, 2, 3...)
            round INTEGER,
            p1_name TEXT,
            p1_id TEXT,                -- Can be ID or "BYE" or None
            p2_name TEXT,
            p2_id TEXT,
            winner_name TEXT,
            winner_id TEXT,
            title TEXT,                -- e.g., "Match 1", "🏆 FINAL"
            is_third_place BOOLEAN DEFAULT 0,
            source_m1 INTEGER,
            source_m2 INTEGER,
            next_match_id INTEGER,
            live_state_json TEXT,      -- लाइभ गेमको स्कोर र अवस्था राख्न
            FOREIGN KEY (event_code) REFERENCES events (code)
        )
    ''')

    # ९. प्रयोगकर्ता लगइन (USERS)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            role TEXT,              -- 'admin' वा 'municipality'
            municipality_id INTEGER,-- यदि 'municipality' हो भने कुन पालिका?
            FOREIGN KEY (municipality_id) REFERENCES municipalities (id)
        )
    ''')

    # १०. अफिसियल विवरण (OFFICIALS)
    c.execute('''
        CREATE TABLE IF NOT EXISTS officials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            municipality_id INTEGER,
            role TEXT,
            name TEXT,
            phone TEXT,
            FOREIGN KEY (municipality_id) REFERENCES municipalities (id)
        )
    ''')

    # Performance Tuning
    c.execute("PRAGMA journal_mode=WAL;")
    
    # --- AUTO SEED EVENTS ---
    seed_events(c)
    
    conn.commit()
    conn.close()
    print("✅ Database tables & Events created successfully!")

# ==========================================
# SEED DATA (All 66 Events)
# ==========================================
def seed_events(cursor):
    """सिस्टम सुरु हुँदा आवश्यक सबै ६६ खेलहरू अटोमेटिक हाल्ने"""
    events_data = [
        # --- ATHLETICS (Track - Boys) ---
        ('BTR100', '100m Race', 'Athletics', 'Track', 'Sprint', '100m', 'Boys', 'Individual', 1),
        ('BTR200', '200m Race', 'Athletics', 'Track', 'Sprint', '200m', 'Boys', 'Individual', 1),
        ('BTR400', '400m Race', 'Athletics', 'Track', 'Sprint', '400m', 'Boys', 'Individual', 1),
        ('BTR800', '800m Race', 'Athletics', 'Track', 'Middle/Long Distance', '800m', 'Boys', 'Individual', 1),
        ('BTR1500', '1500m Race', 'Athletics', 'Track', 'Middle/Long Distance', '1500m', 'Boys', 'Individual', 1),
        ('BTR3000', '3000m Race', 'Athletics', 'Track', 'Middle/Long Distance', '3000m', 'Boys', 'Individual', 1),
        ('BTR4X100', '4×100m Relay', 'Athletics', 'Track', 'Relay', '4×100m', 'Boys', 'Team', 4),
        ('BTR4X400', '4×400m Relay', 'Athletics', 'Track', 'Relay', '4×400m', 'Boys', 'Team', 4),

        # --- ATHLETICS (Track - Girls) ---
        ('GTR100', '100m Race', 'Athletics', 'Track', 'Sprint', '100m', 'Girls', 'Individual', 1),
        ('GTR200', '200m Race', 'Athletics', 'Track', 'Sprint', '200m', 'Girls', 'Individual', 1),
        ('GTR400', '400m Race', 'Athletics', 'Track', 'Sprint', '400m', 'Girls', 'Individual', 1),
        ('GTR800', '800m Race', 'Athletics', 'Track', 'Middle/Long Distance', '800m', 'Girls', 'Individual', 1),
        ('GTR1500', '1500m Race', 'Athletics', 'Track', 'Middle/Long Distance', '1500m', 'Girls', 'Individual', 1),
        ('GTR3000', '3000m Race', 'Athletics', 'Track', 'Middle/Long Distance', '3000m', 'Girls', 'Individual', 1),
        ('GTR4X100', '4×100m Relay', 'Athletics', 'Track', 'Relay', '4×100m', 'Girls', 'Team', 4),
        ('GTR4X400', '4×400m Relay', 'Athletics', 'Track', 'Relay', '4×400m', 'Girls', 'Team', 4),

        # --- ATHLETICS (Field - Boys) ---
        ('BFDHJ', 'High Jump', 'Athletics', 'Field', 'Jump', 'High Jump', 'Boys', 'Individual', 1),
        ('BFDLJ', 'Long Jump', 'Athletics', 'Field', 'Jump', 'Long Jump', 'Boys', 'Individual', 1),
        ('BFDTJ', 'Triple Jump', 'Athletics', 'Field', 'Jump', 'Triple Jump', 'Boys', 'Individual', 1),
        ('BFDSP', 'Shot Put', 'Athletics', 'Field', 'Throw', 'Shot Put', 'Boys', 'Individual', 1),
        ('BFDJT', 'Javelin Throw', 'Athletics', 'Field', 'Throw', 'Javelin Throw', 'Boys', 'Individual', 1),

        # --- ATHLETICS (Field - Girls) ---
        ('GFDHJ', 'High Jump', 'Athletics', 'Field', 'Jump', 'High Jump', 'Girls', 'Individual', 1),
        ('GFDLJ', 'Long Jump', 'Athletics', 'Field', 'Jump', 'Long Jump', 'Girls', 'Individual', 1),
        ('GFDTJ', 'Triple Jump', 'Athletics', 'Field', 'Jump', 'Triple Jump', 'Girls', 'Individual', 1),
        ('GFDSP', 'Shot Put', 'Athletics', 'Field', 'Throw', 'Shot Put', 'Girls', 'Individual', 1),
        ('GFDJT', 'Javelin Throw', 'Athletics', 'Field', 'Throw', 'Javelin Throw', 'Girls', 'Individual', 1),

        # --- TEAM GAMES ---
        ('BVB', 'Volleyball', 'Team Game', 'Volleyball', 'Boys', 'Volleyball', 'Boys', 'Team', 12),
        ('GVB', 'Volleyball', 'Team Game', 'Volleyball', 'Girls', 'Volleyball', 'Girls', 'Team', 12),
        ('BKBD', 'Kabaddi', 'Team Game', 'Kabaddi', 'Boys', 'Kabaddi', 'Boys', 'Team', 12),
        ('GKBD', 'Kabaddi', 'Team Game', 'Kabaddi', 'Girls', 'Kabaddi', 'Girls', 'Team', 12),

        # --- MARTIAL ARTS: KARATE ---
        ('BKK', 'Solo Kata', 'Martial Arts', 'Karate', 'Kata', 'Solo Kata', 'Boys', 'Individual', 1),
        ('GKK', 'Solo Kata', 'Martial Arts', 'Karate', 'Kata', 'Solo Kata', 'Girls', 'Individual', 1),
        ('BKM42', 'Kumite – 42 kg', 'Martial Arts', 'Karate', 'Kumite', '-42 kg', 'Boys', 'Individual', 1),
        ('BKM47', 'Kumite – 47 kg', 'Martial Arts', 'Karate', 'Kumite', '-47 kg', 'Boys', 'Individual', 1),
        ('BKM52', 'Kumite – 52 kg', 'Martial Arts', 'Karate', 'Kumite', '-52 kg', 'Boys', 'Individual', 1),
        ('BKM57', 'Kumite – 57 kg', 'Martial Arts', 'Karate', 'Kumite', '-57 kg', 'Boys', 'Individual', 1),
        ('BKM62', 'Kumite – 62 kg', 'Martial Arts', 'Karate', 'Kumite', '-62 kg', 'Boys', 'Individual', 1),
        ('GKM40', 'Kumite – 40 kg', 'Martial Arts', 'Karate', 'Kumite', '-40 kg', 'Girls', 'Individual', 1),
        ('GKM45', 'Kumite – 45 kg', 'Martial Arts', 'Karate', 'Kumite', '-45 kg', 'Girls', 'Individual', 1),
        ('GKM50', 'Kumite – 50 kg', 'Martial Arts', 'Karate', 'Kumite', '-50 kg', 'Girls', 'Individual', 1),
        ('GKM55', 'Kumite – 55 kg', 'Martial Arts', 'Karate', 'Kumite', '-55 kg', 'Girls', 'Individual', 1),
        ('GKM60', 'Kumite – 60 kg', 'Martial Arts', 'Karate', 'Kumite', '-60 kg', 'Girls', 'Individual', 1),

        # --- MARTIAL ARTS: TAEKWONDO ---
        ('BTKPOOM', 'Solo Poomsae', 'Martial Arts', 'Taekwondo', 'Poomsae', 'Solo Poomsae', 'Boys', 'Individual', 1),
        ('GTKPOOM', 'Solo Poomsae', 'Martial Arts', 'Taekwondo', 'Poomsae', 'Solo Poomsae', 'Girls', 'Individual', 1),
        ('BTW45', 'Kyorugi – 45 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-45 kg', 'Boys', 'Individual', 1),
        ('BTW48', 'Kyorugi – 48 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-48 kg', 'Boys', 'Individual', 1),
        ('BTW51', 'Kyorugi – 51 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-51 kg', 'Boys', 'Individual', 1),
        ('BTW55', 'Kyorugi – 55 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-55 kg', 'Boys', 'Individual', 1),
        ('BTW59', 'Kyorugi – 59 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-59 kg', 'Boys', 'Individual', 1),
        ('GTW42', 'Kyorugi – 42 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-42 kg', 'Girls', 'Individual', 1),
        ('GTW44', 'Kyorugi – 44 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-44 kg', 'Girls', 'Individual', 1),
        ('GTW46', 'Kyorugi – 46 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-46 kg', 'Girls', 'Individual', 1),
        ('GTW49', 'Kyorugi – 49 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-49 kg', 'Girls', 'Individual', 1),
        ('GTW52', 'Kyorugi – 52 kg', 'Martial Arts', 'Taekwondo', 'Kyorugi', '-52 kg', 'Girls', 'Individual', 1),

        # --- MARTIAL ARTS: WUSHU ---
        ('BWFC', 'Changquan', 'Martial Arts', 'Wushu', 'Taolu', 'Changquan', 'Boys', 'Individual', 1),
        ('BWFN', 'Nanquan', 'Martial Arts', 'Wushu', 'Taolu', 'Nanquan', 'Boys', 'Individual', 1),
        ('BWFTJ', 'Taiji Quan', 'Martial Arts', 'Wushu', 'Taolu', 'Taiji Quan', 'Boys', 'Individual', 1),
        ('GWFC', 'Changquan', 'Martial Arts', 'Wushu', 'Taolu', 'Changquan', 'Girls', 'Individual', 1),
        ('GWFN', 'Nanquan', 'Martial Arts', 'Wushu', 'Taolu', 'Nanquan', 'Girls', 'Individual', 1),
        ('GWFTJ', 'Taiji Quan', 'Martial Arts', 'Wushu', 'Taolu', 'Taiji Quan', 'Girls', 'Individual', 1),
        ('BWSD45', 'Sanda – 45 kg', 'Martial Arts', 'Wushu', 'Sanda', '-45 kg', 'Boys', 'Individual', 1),
        ('BWSD48', 'Sanda – 48 kg', 'Martial Arts', 'Wushu', 'Sanda', '-48 kg', 'Boys', 'Individual', 1),
        ('BWSD51', 'Sanda – 51 kg', 'Martial Arts', 'Wushu', 'Sanda', '-51 kg', 'Boys', 'Individual', 1),
        ('GWSD42', 'Sanda – 42 kg', 'Martial Arts', 'Wushu', 'Sanda', '-42 kg', 'Girls', 'Individual', 1),
        ('GWSD45', 'Sanda – 45 kg', 'Martial Arts', 'Wushu', 'Sanda', '-45 kg', 'Girls', 'Individual', 1),
        ('GWSD48', 'Sanda – 48 kg', 'Martial Arts', 'Wushu', 'Sanda', '-48 kg', 'Girls', 'Individual', 1),
    ]

    for ev in events_data:
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO events 
                (code, name, category, sub_category, event_group, specific_event, gender, type, max_participants) 
                VALUES (?,?,?,?,?,?,?,?,?)
            ''', ev)
        except Exception as e:
            print(f"Error seeding event {ev[0]}: {e}")

# ==========================================
# HELPER FUNCTIONS
# ==========================================

def get_municipalities():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM municipalities ORDER BY name", conn)
    conn.close()
    return df

def get_events(category=None):
    conn = get_connection()
    if category:
        query = "SELECT * FROM events WHERE category = ?"
        df = pd.read_sql_query(query, conn, params=(category,))
    else:
        df = pd.read_sql_query("SELECT * FROM events ORDER BY name", conn)
    conn.close()
    return df

def add_municipality(name):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO municipalities (name) VALUES (?)", (name,))
        conn.commit()
    except:
        pass
    finally:
        conn.close()

# --- NEW REGISTRATION FUNCTIONS (PLAYERS + REGISTRATIONS) ---
def add_player(municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, photo_path=None):
    """नयाँ खेलाडी दर्ता गर्ने (Master Profile)"""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO players (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, photo_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val, photo_path))
        player_id = c.lastrowid
        conn.commit()
        return player_id, "Success"
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        conn.close()

def update_player_info(player_id, iemis_id, name, dob_bs, school_name, class_val):
    """खेलाडीको व्यक्तिगत विवरण अपडेट गर्ने"""
    conn = get_connection()
    try:
        # 💡 मुख्य सुधार यहाँ छ: SET class=? को सट्टा SET class_val=? बनाइएको छ।
        conn.execute('''
            UPDATE players 
            SET iemis_id = ?, name = ?, dob_bs = ?, school_name = ?, class_val = ?
            WHERE id = ?
        ''', (iemis_id, name, dob_bs, school_name, class_val, player_id))
        conn.commit()
        return True, "Success"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def update_player_registrations(player_id, event_codes):
    """खेलाडीको इभेन्ट रजिस्ट्रेसन अपडेट गर्ने"""
    conn = get_connection()
    try:
        # १. सुरक्षित पक्ष (Safe side) को लागि: यदि registrations टेबल छैन भने बनाउने
        conn.execute('''CREATE TABLE IF NOT EXISTS registrations (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            player_id INTEGER,
                            event_code TEXT
                        )''')
        
        # २. पुरानो सबै रजिस्ट्रेसन हटाउने (ताकि UI मा 'Uncheck' गरेका इभेन्टहरू डाटाबेसबाट पनि हटिजाउन्)
        conn.execute("DELETE FROM registrations WHERE player_id=?", (player_id,))
        
        # ३. नयाँ छानिएका सबै इभेन्टहरू हाल्ने
        for code in event_codes:
            conn.execute("INSERT INTO registrations (player_id, event_code) VALUES (?, ?)", (player_id, code))
            
        conn.commit()
        return True
    except Exception as e:
        print(f"रजिस्ट्रेसन अपडेटमा त्रुटि: {e}")
        return False
    finally:
        conn.close()

# --- SQUAD/TEAM HELPER (UPDATED) ---
def get_team_members(team_id):
    """
    कुनै टिम (जस्तै भलिबल टिम) मा को-को खेलाडी छन् भनेर तान्ने।
    यसले पहिले टिमको पालिका र इभेन्ट पत्ता लगाउँछ, अनि 'players' र 'registrations' जोडेर लिस्ट तान्छ।
    """
    conn = get_connection()
    # १. टिमको जानकारी (कुन पालिका, कुन इभेन्ट?)
    t_info = conn.execute("SELECT event_code, municipality_id FROM teams WHERE id=?", (team_id,)).fetchone()
    
    if not t_info:
        conn.close()
        return pd.DataFrame()
        
    # २. त्यो पालिकाबाट त्यो इभेन्टमा दर्ता भएका सबै खेलाडीहरू
    q = """
        SELECT p.id, p.name as player_name, p.iemis_id, p.school_name, p.class_val as class, p.gender, p.dob_bs, p.photo_path
        FROM players p
        JOIN registrations r ON p.id = r.player_id
        WHERE p.municipality_id = ? AND r.event_code = ?
    """
    df = pd.read_sql_query(q, conn, params=(t_info['municipality_id'], t_info['event_code']))
    conn.close()
    
    # 'player_name' नभई 'name' आउने भएकोले पछि सजिलोको लागि जर्सी नम्बर राख्ने ठाउँ
    df['jersey'] = "" 
    return df

# --- MATCH RESULT HELPERS ---
def save_match_result(event_code, player_id, position, score, medal):
    """खेलाडीको नतिजा सेभ गर्ने फङ्सन (डाटाबेस संरचना अनुसार)"""
    conn = get_connection()
    try:
        # १. 'rank' को सट्टा 'position' राखिएको छ
        # २. 'score_value' को सट्टा 'score' राखिएको छ
        # ३. एथलेटिक्समा team_id खाली (None) र player_id मा डाटा जान्छ
        conn.execute("""
            INSERT INTO results (event_code, player_id, team_id, position, medal, score)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (event_code, player_id, None, position, medal, score))
        conn.commit()
    except Exception as e:
        print(f"Error saving result: {e}")
    finally:
        conn.close()

# --- BRACKET HELPERS ---
def save_bracket(event_code, bracket_list):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM matches WHERE event_code=?", (event_code,))
    
    for m in bracket_list:
        c.execute("""
            INSERT INTO matches 
            (event_code, match_id, round, p1_name, p1_id, p2_name, p2_id, winner_name, winner_id, title, is_third_place, source_m1, source_m2, next_match_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_code, m['id'], m['round'], 
            m['p1'], str(m['p1_id']) if m.get('p1_id') else None, 
            m['p2'], str(m['p2_id']) if m.get('p2_id') else None,
            m.get('winner'), str(m['winner_id']) if m.get('winner_id') else None,
            m.get('title'), bool(m.get('is_third_place')),
            m.get('source_m1'), m.get('source_m2'), m.get('next_match_id')
        ))
    conn.commit()
    conn.close()

def get_bracket(event_code):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM matches WHERE event_code=? ORDER BY match_id", conn, params=(event_code,))
    conn.close()
    
    if df.empty: return []
        
    matches = []
    for _, row in df.iterrows():
        matches.append({
            'db_id': row['db_id'], 'id': row['match_id'], 'round': row['round'],
            'p1': row['p1_name'], 'p1_id': row['p1_id'], 'p2': row['p2_name'], 'p2_id': row['p2_id'],
            'winner': row['winner_name'], 'winner_id': row['winner_id'], 'title': row['title'],
            'is_third_place': bool(row['is_third_place']), 'source_m1': row['source_m1'],
            'source_m2': row['source_m2'], 'next_match_id': row['next_match_id'], 'live_state_json': row['live_state_json']
        })
    return matches

# --- OFFICIALS HELPERS ---
def add_official(municipality_id, role, name, phone):
    conn = get_connection()
    conn.execute("INSERT INTO officials (municipality_id, role, name, phone) VALUES (?, ?, ?, ?)", 
                 (municipality_id, role, name, phone))
    conn.commit()
    conn.close()

def get_officials(municipality_id):
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM officials WHERE municipality_id=?", conn, params=(municipality_id,))
    conn.close()
    return df

def delete_official(official_id):
    conn = get_connection()
    conn.execute("DELETE FROM officials WHERE id=?", (official_id,))
    conn.commit()
    conn.close()

# --- PLAYER EDIT/DELETE HELPERS ---
def update_player_details(player_id, name, gender, dob_bs, school, class_val):
    conn = get_connection()
    conn.execute("""
        UPDATE players SET name=?, gender=?, dob_bs=?, school_name=?, class_val=? 
        WHERE id=?
    """, (name, gender, dob_bs, school, class_val, player_id))
    conn.commit()
    conn.close()

def delete_player_full(player_id):
    conn = get_connection()
    # पहिले दर्ता (Registrations) मेटाउने
    conn.execute("DELETE FROM registrations WHERE player_id=?", (player_id,))
    # अनि खेलाडी मेटाउने
    conn.execute("DELETE FROM players WHERE id=?", (player_id,))
    conn.commit()
    conn.close()

# ==========================================
# AUTHENTICATION
# ==========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_default_admin():
    conn = get_connection()
    c = conn.cursor()
    pwd = hash_password("admin123")
    try:
        c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)", ("admin", pwd, "admin"))
        conn.commit()
    except: pass
    finally: conn.close()

def authenticate_user(username, password):
    pwd = hash_password(password)
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE username=? AND password_hash=?", (username, pwd)).fetchone()
    conn.close()
    if user: return dict(user)
    return None

# ==========================================
# --- EXCEL IMPORT LOGIC ---
# ==========================================

def import_school_data(excel_file, municipality_id):
    """
    अपडेटेड एक्सेल फाइल पढेर 'players' र 'registrations' टेबलमा डाटा हाल्ने फङ्सन।
    School_Details पाना हटाइएको छ। 'School Name' खेलाडीकै पङ्क्तिबाट लिइन्छ।
    """
    conn = db.get_connection()
    c = conn.cursor()
    
    try:
        events_df = pd.read_sql_query("SELECT code, name, type FROM events", conn)
        event_type_map = {row['code']: row['type'] for _, row in events_df.iterrows()}
        
        total_players_added = 0
        total_registrations = 0

        # Boys र Girls दुवै सिट पढ्ने
        for sheet, gender in [('Boys_Entry', 'Boys'), ('Girls_Entry', 'Girls')]:
            try:
                # Row 4 (Index 3) मा हेडर छ 
                df = pd.read_excel(excel_file, sheet_name=sheet, skiprows=3)
                
                if 'Student Name' not in df.columns: continue
                # 'Student Name' खाली नभएका मात्र लिने
                df = df.dropna(subset=['Student Name'])
                
                for _, row in df.iterrows():
                    player_name = str(row.get('Student Name', '')).strip()
                    iemis = str(row.get('EMIS ID', '')).strip()
                    dob = str(row.get('DOB (YYYY-MM-DD)', '')).strip()
                    school_name = str(row.get('School Name', '')).strip()
                    p_class = str(row.get('Class', '')).strip()
                    
                    if not player_name or player_name == 'nan': continue
                    if not dob or dob == 'nan': dob = "2064-01-01" 
                    if not school_name or school_name == 'nan': school_name = "Unknown School"
                    
                    # A. खेलाडी दर्ता गर्ने
                    c.execute("""
                        INSERT INTO players (municipality_id, iemis_id, name, gender, dob_bs, school_name, class_val)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (municipality_id, iemis, player_name, gender, dob, school_name, p_class))
                    
                    player_id = c.lastrowid
                    total_players_added += 1
                    
                    # B. खेलहरू खोज्ने (जहाँ 1 लेखिएको छ)
                    # सुरुका ५ वटा कोलम बेसिक इन्फो हुन्, त्यसपछिका खेल हुन्
                    selected_events = []
                    for col_name in df.columns[5:]:
                        val = row.get(col_name)
                        if pd.notna(val) and str(val).strip() in ['1', '1.0']:
                            # जेन्डर र नाम मिलेको इभेन्ट तान्ने
                            e_match = events_df[(events_df['name'] == col_name) & (events_df['code'].str.startswith('B' if gender == 'Boys' else 'G'))]
                            if e_match.empty: e_match = events_df[events_df['name'] == col_name] # Fallback
                            
                            if not e_match.empty:
                                e_code = e_match.iloc[0]['code']
                                selected_events.append(e_code)
                                
                                # C. यदि यो टिम गेम हो भने, टिम बनाउने (पालिकाको नामबाट)
                                if event_type_map.get(e_code) == 'Team':
                                    c.execute("SELECT id FROM teams WHERE event_code=? AND municipality_id=?", (e_code, municipality_id))
                                    if not c.fetchone():
                                        # जस्तै: 'Suryodaya Team'
                                        mun_name = conn.execute("SELECT name FROM municipalities WHERE id=?", (municipality_id,)).fetchone()[0]
                                        t_name = f"{mun_name.split(' ')[0]} Team"
                                        c.execute("INSERT INTO teams (event_code, municipality_id, name) VALUES (?, ?, ?)", (e_code, municipality_id, t_name))
                    
                    # D. खेलाडीलाई इभेन्टमा जोड्ने
                    for code in selected_events:
                        c.execute("INSERT INTO registrations (player_id, event_code) VALUES (?, ?)", (player_id, code))
                        total_registrations += 1

            except Exception as e:
                pass # यदि सिट भेटिएन वा फर्म्याट मिलेन भने इग्नोर गर्ने
                
        conn.commit()
        return True, f"सफलतापूर्वक {total_players_added} जना खेलाडी र {total_registrations} वटा इभेन्ट दर्ता भयो!"
        
    except Exception as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()


# ==========================================
# ADVANCED SCHEDULE MANAGEMENT
# ==========================================
def setup_advanced_schedule():
    """सेड्युलको लागि नयाँ डाइनामिक टेबल बनाउने"""
    conn = get_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_code TEXT,
            event_name TEXT,
            phase TEXT,
            schedule_day TEXT,
            schedule_order INTEGER,
            is_completed INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

# ==========================================
# ⚠️ RULE VALIDATION FUNCTIONS (PALIKA WISE)
# ==========================================
import pandas as pd

def check_athletics_violations():
    """एक खेलाडीले ३ भन्दा बढी एथलेटिक्स (रिले बाहेक) खेलेको जाँच"""
    conn = get_connection()
    q = """
        SELECT p.name as Player, m.name as Municipality, p.school_name as School, GROUP_CONCAT(e.name, ', ') as Event_List, '३ भन्दा बढी इभेन्ट' as Issue
        FROM registrations r 
        JOIN players p ON r.player_id = p.id 
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE e.category = 'Athletics' AND e.name NOT LIKE '%Relay%'
        GROUP BY p.id HAVING COUNT(r.event_code) > 3
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_martial_arts_violations():
    """मार्सल आर्ट्समा एकभन्दा बढी तौल समूह खेलेको जाँच"""
    conn = get_connection()
    q = """
        SELECT p.name as Player, m.name as Municipality, e.sub_category as Game, GROUP_CONCAT(e.name, ', ') as Event_List, '१ भन्दा बढी तौल समूह' as Issue
        FROM registrations r 
        JOIN players p ON r.player_id = p.id 
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE e.category = 'Martial Arts' AND e.event_group IN ('Kumite', 'Kyorugi', 'Sanda')
        GROUP BY p.id, e.sub_category HAVING COUNT(r.event_code) > 1
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_team_size_violations():
    """भलिबल, कबड्डी र रिलेमा तोकिएको खेलाडी संख्या जाँच"""
    conn = get_connection()
    q = """
        SELECT t.name as Team_Name, m.name as Municipality, e.name as Event, COUNT(r.player_id) as Player_Count
        FROM teams t
        JOIN events e ON t.event_code = e.code
        LEFT JOIN registrations r ON r.event_code = e.code AND r.player_id IN (SELECT id FROM players WHERE municipality_id = t.municipality_id)
        JOIN municipalities m ON t.municipality_id = m.id
        GROUP BY t.id
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    
    violations = []
    for _, row in df.iterrows():
        c = row['Player_Count']
        ev = row['Event']
        if 'Volleyball' in ev and (c < 6 or c > 9):
            violations.append((row['Team_Name'], row['Municipality'], ev, c, "६ देखि ९ जना हुनुपर्ने"))
        elif 'Kabaddi' in ev and (c < 7 or c > 9):
            violations.append((row['Team_Name'], row['Municipality'], ev, c, "७ देखि ९ जना हुनुपर्ने"))
        elif 'Relay' in ev and (c < 4 or c > 6):
            violations.append((row['Team_Name'], row['Municipality'], ev, c, "४ देखि ६ जना हुनुपर्ने"))
            
    return pd.DataFrame(violations, columns=['Team', 'Municipality', 'Event', 'Count', 'Issue'])

def check_athletics_single_limit_violations():
    """एथलेटिक्सको एउटै खेलमा एउटै पालिकाबाट २ भन्दा बढी खेलाडी जाँच (जिल्ला स्तरमा प्राय: २ जना हुन्छ)"""
    conn = get_connection()
    # यदि तपाईको नियममा पालिकाबाट १ जना मात्र हो भने तल HAVING Player_Count > 1 बनाउनुहोला।
    q = """
        SELECT m.name as Municipality, e.name as Event, COUNT(p.id) as Player_Count
        FROM registrations r 
        JOIN players p ON r.player_id = p.id 
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE e.category = 'Athletics' AND e.name NOT LIKE '%Relay%'
        GROUP BY m.id, e.code HAVING Player_Count > 2
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_martial_arts_forms_violations():
    """मार्सल आर्ट्स (काता/पुम्से) मा एउटै पालिकाबाट १ भन्दा बढी खेलाडी जाँच"""
    conn = get_connection()
    q = """
        SELECT m.name as Municipality, e.name as Event, e.event_group as Group_Name, '१ भन्दा बढी दर्ता' as Issue
        FROM registrations r 
        JOIN players p ON r.player_id = p.id 
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE e.category = 'Martial Arts' AND e.event_group IN ('Kata', 'Poomsae', 'Taolu')
        GROUP BY m.id, e.code HAVING COUNT(p.id) > 1
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_age_limit_violations(limit_date="2064-11-01"):
    """जन्म मिति (Over Age) जाँच"""
    conn = get_connection()
    q = """
        SELECT p.name as Player, p.dob_bs as DOB, m.name as Municipality, 'Over Age' as Issue
        FROM players p
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE p.dob_bs < ?
    """
    df = pd.read_sql_query(q, conn, params=(limit_date,))
    conn.close()
    return df

# ==========================================
# ⚠️ ADDITIONAL RULE VALIDATIONS (PRO LEVEL)
# ==========================================

def check_gender_mismatch():
    """छात्र (Boys) को इभेन्टमा छात्रा (Girls) वा छात्राको इभेन्टमा छात्र दर्ता भएको जाँच"""
    conn = get_connection()
    q = """
        SELECT p.name as Player, p.gender as Player_Gender, e.name as Event, e.gender as Event_Gender, m.name as Municipality, 'Gender Mismatch' as Issue
        FROM registrations r
        JOIN players p ON r.player_id = p.id
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE (p.gender = 'Boys' AND e.gender = 'Girls') 
           OR (p.gender = 'Girls' AND e.gender = 'Boys')
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_duplicate_emis():
    """एउटै EMIS ID दुई फरक नाम, स्कुल वा पालिकाबाट दर्ता भएको जाँच"""
    conn = get_connection()
    q = """
        SELECT 
            p.iemis_id as EMIS_ID, 
            GROUP_CONCAT(p.name, ' / ') as Names, 
            GROUP_CONCAT(p.school_name, ' / ') as Schools, 
            GROUP_CONCAT(m.name, ' / ') as Municipalities,
            'Duplicate EMIS' as Issue
        FROM players p
        LEFT JOIN municipalities m ON p.municipality_id = m.id
        WHERE p.iemis_id IS NOT NULL AND p.iemis_id != '' AND p.iemis_id != '0' AND p.iemis_id != 'N/A'
        GROUP BY p.iemis_id 
        HAVING COUNT(p.id) > 1
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_multiple_team_games():
    """एकै खेलाडीले भलिबल र कबड्डी दुवै (एकभन्दा बढी टिम गेम) खेलेको जाँच"""
    conn = get_connection()
    q = """
        SELECT p.name as Player, m.name as Municipality, GROUP_CONCAT(e.name, ', ') as Team_Games, '१ भन्दा बढी टिम गेम' as Issue
        FROM registrations r
        JOIN players p ON r.player_id = p.id
        JOIN events e ON r.event_code = e.code
        JOIN municipalities m ON p.municipality_id = m.id
        WHERE e.category = 'Team Game' AND e.type = 'Team'
        GROUP BY p.id HAVING COUNT(r.event_code) > 1
    """
    df = pd.read_sql_query(q, conn)
    conn.close()
    return df

def check_palika_player_quota(max_limit=88):
    """एउटा पालिकाबाट तोकिएको अधिकतम खेलाडी संख्या (जस्तै: ८८) नाघेको जाँच"""
    conn = get_connection()
    q = """
        SELECT m.name as Municipality, COUNT(p.id) as Total_Players, 'Quota Exceeded' as Issue
        FROM players p
        JOIN municipalities m ON p.municipality_id = m.id
        GROUP BY m.id HAVING Total_Players > ?
    """
    df = pd.read_sql_query(q, conn, params=(max_limit,))
    conn.close()
    return df

# ==========================================
# 🚨 EMERGENCY / MANUAL RESULT ENTRY
# ==========================================
def save_manual_result(event_code, entity_id, is_team, position, medal, score_str=""):
    """रेफ्रीको कागज हेरेर सिधै नतिजा सेभ गर्ने फङ्सन"""
    conn = get_connection()
    c = conn.cursor()
    
    # पहिले नै त्यो पोजिसनमा कोही छ भने हटाउने (ओभरराइड)
    c.execute("DELETE FROM results WHERE event_code = ? AND position = ?", (event_code, position))
    
    # नयाँ नतिजा हाल्ने
    if is_team:
        c.execute("""
            INSERT INTO results (event_code, team_id, player_id, position, medal, score) 
            VALUES (?, ?, NULL, ?, ?, ?)
        """, (event_code, entity_id, position, medal, score_str))
    else:
        c.execute("""
            INSERT INTO results (event_code, team_id, player_id, position, medal, score) 
            VALUES (?, NULL, ?, ?, ?, ?)
        """, (event_code, entity_id, position, medal, score_str))
        
    conn.commit()
    conn.close()
    return True


# ==========================================
# 🛠️ MANUAL MATCH OVERRIDE (SINGLE MATCH)
# ==========================================
def override_single_match(match_id, winner_name, score=""):
    """कुनै एउटा म्याच (जस्तै: Match #3) को नतिजा म्यानुअल हाल्ने फङ्सन"""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute("""
            UPDATE matches 
            SET winner = ?, score = ?, status = 'Completed' 
            WHERE id = ?
        """, (winner_name, score, match_id))
        conn.commit()
        success = True
    except Exception as e:
        print(f"Error updating match: {e}")
        success = False
        
    conn.close()
    return success

# kata judge pannel ko lagi
def get_live_match(evt_code):
    try:
        conn = get_connection() # यहाँ db.get_connection पर्दैन, सिधै get_connection हुन्छ
        conn.execute('''CREATE TABLE IF NOT EXISTS live_match (
                            event_code TEXT PRIMARY KEY,
                            bout_id TEXT,
                            player1 TEXT,
                            player2 TEXT,
                            p1_muni TEXT,
                            p2_muni TEXT,
                            round_name TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )''')
        cur = conn.cursor()
        cur.execute("SELECT * FROM live_match WHERE event_code=?", (evt_code,))
        row = cur.fetchone()
        conn.close()
        return row
    except Exception as e:
        # यहाँ st.error को सट्टा प्रिन्ट मात्र गर्ने, 
        # ताकी टर्मिनलमा एरर देखियोस् तर एप क्र्यास नहोस्
        print(f"Database Error: {e}")
        return None

# INITIALIZATION
if __name__ == "__main__":
    if os.path.exists(DB_FILE):
        print(f"⚠️ Note: '{DB_FILE}' already exists. Delete it to apply the new schema.")
    create_tables()
    create_default_admin()
else:
    if not os.path.exists(DB_FILE):
        create_tables()
    create_default_admin()