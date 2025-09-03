import sqlite3
import os
import random
from pathlib import Path
import subprocess

DB_PATH = Path("voice.db")

MALE_VOICES = ["Male_1.wav", "Male_2.wav"]
FEMALE_VOICES = ["Female_1.wav", "Female_2.wav", "Female_3.wav", "Female_4.wav"]

def assign_voice(actor_name, gender, existing_voices):
    if actor_name == "Chen Ping" :
        return "Cheng.mp3"
    elif actor_name == "narrator":
        return "Narrator.mp3"
    voice_pool = MALE_VOICES if gender == "male" else FEMALE_VOICES
    available = [v for v in voice_pool if v not in existing_voices]

    return random.choice(available) if available else random.choice(voice_pool)

def update_voice_db(chapter_file):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS voice_assignments (
        actor_name TEXT PRIMARY KEY,
        gender TEXT,
        voice_file TEXT
    )
    """)

    # Track current voices assigned
    cursor.execute("SELECT actor_name, voice_file FROM voice_assignments")
    current = dict(cursor.fetchall())
    used_voices = set(current.values())

    new_assignments = []

    with open(chapter_file, 'r') as f:
        content = f.read()
    all_lines = content.strip().split("\\n")

    for line in all_lines:
        if not line.strip():
            continue
        parts = line.split("\\t")
        if len(parts) < 4:
            continue
        
        actor_name, gender ,mood, text= parts
        if actor_name not in current:
            voice_file = assign_voice(actor_name, gender, used_voices)
            print(f"Assigning voice: {actor_name} -> {voice_file}")
            cursor.execute(
                    "INSERT INTO voice_assignments (actor_name, gender, voice_file) VALUES (?, ?, ?)",
                    (actor_name, gender, voice_file)
            )
            used_voices.add(voice_file)
            new_assignments.append(actor_name)

    conn.commit()
    conn.close()

    return len(new_assignments) > 0

def commit_changes():
    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "voice.db"], check=True)
    subprocess.run(["git", "commit", "-m", "Update voice assignments"], check=True)
    subprocess.run(["git", "push"], check=True)

if __name__ == "__main__":
    chapter_number = os.getenv("CHAPTER_FILE", "1")  # Default if not passed via env
    print(f"🧠 Reading actor info from: {chapter_number}")
    chapter_file = f"LLM_output/chapter_{chapter_number}.txt"
    if update_voice_db(chapter_file):
        print("✅ DB updated, committing to Git...")
        commit_changes()
    else:
        print("ℹ️ No new voice assignments. Nothing to commit.")
