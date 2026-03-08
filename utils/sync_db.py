import pandas as pd
import database as db
import json
import threading

def pull_cloud_to_local():
    """☁️ → 💻 निओन क्लाउडबाट सम्पूर्ण डाटा लोकल डाटाबेसमा तान्ने"""
    cloud_conn = db.get_cloud_connection()
    local_conn = db.get_local_connection()
    
    if not cloud_conn or not local_conn:
        return False, "क्लाउड वा लोकल कनेक्सन असफल! इन्टरनेट चेक गर्नुहोस्।"
        
    try:
        # तान्नुपर्ने मुख्य टेबलहरू
        tables = ["municipalities", "events", "players", "officials", "teams", "registrations"]
        
        with local_conn.cursor() as local_cur:
            for table in tables:
                # १. क्लाउडबाट डाटा पढ्ने
                df = pd.read_sql_query(f"SELECT * FROM {table}", cloud_conn)
                
                # २. लोकल टेबल खाली गर्ने (संरचना नमेटिने गरी)
                local_cur.execute(f"TRUNCATE {table} RESTART IDENTITY CASCADE")
                
                # ३. क्लाउडको डाटा लोकलमा भर्ने
                if not df.empty:
                    columns = ', '.join(df.columns)
                    placeholders = ', '.join(['%s'] * len(df.columns))
                    insert_query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
                    
                    for _, row in df.iterrows():
                        local_cur.execute(insert_query, tuple(row))
                        
            local_conn.commit()
        return True, f"✅ सम्पूर्ण डाटा सफलतापूर्वक लोकल सर्भरमा सिङ्क भयो!"
        
    except Exception as e:
        local_conn.rollback()
        return False, f"❌ सिङ्क गर्दा त्रुटि: {e}"
    finally:
        cloud_conn.close()
        local_conn.close()

def push_live_score_bg(match_data):
    """ब्याकग्राउन्डमा (बिना कुनै रोकावट) लाइभ स्कोर क्लाउडमा पठाउने जादु"""
    
    def _push_task():
        cloud_conn = db.get_cloud_connection()
        if not cloud_conn:
            return # इन्टरनेट छैन भने चुपचाप बस्ने, एरर नदेखाउने
            
        try:
            c = cloud_conn.cursor()
            # हामी क्लाउडको system_states टेबलमा 'live_mat_score' नाममा यो डाटा सेभ गर्छौँ
            c.execute("""
                INSERT INTO system_states (state_key, state_data, updated_at) 
                VALUES ('live_mat_score', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (state_key) 
                DO UPDATE SET state_data = EXCLUDED.state_data, updated_at = CURRENT_TIMESTAMP
            """, (json.dumps(match_data),))
            cloud_conn.commit()
            c.close()
        except Exception as e:
            print(f"☁️ Cloud Push Error: {e}")
        finally:
            cloud_conn.close()

    # थ्रेडिङ सुरु गर्ने (यसले तपाईंको ल्यापटपको स्क्रिनलाई रोक्दैन)
    thread = threading.Thread(target=_push_task)
    thread.start()