import sqlite3
from datetime import datetime

def check_schedule_table(db_path='database.db'):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    print("📋 SCHEDULE TABLE CONTENTS:\n")
    rows = c.execute('SELECT id, display_id, media_id, start_time, end_time FROM schedule ORDER BY start_time ASC').fetchall()

    if not rows:
        print("⚠️ No entries in the schedule table.")
        return

    for row in rows:
        id_, display_id, media_id, start_time, end_time = row
        try:
            start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        except:
            start_dt = f"❌ Invalid format: {start_time}"

        try:
            end_dt = datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S') if end_time else None
        except:
            end_dt = f"❌ Invalid format: {end_time}"

        print(f"🆔 ID: {id_}")
        print(f"🖥️ Display ID: {display_id}")
        print(f"🗂️ Media ID: {media_id}")
        print(f"⏰ Start Time: {start_time} → Parsed: {start_dt}")
        print(f"⏹️ End Time: {end_time} → Parsed: {end_dt}")
        print("-" * 40)

    conn.close()

if __name__ == '__main__':
    check_schedule_table()
