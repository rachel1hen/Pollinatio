import os
import json
import sys
import re
from typing import Dict
import requests

# =============================
# CONFIG
# =============================
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "qwen/qwen3-32b"

CHAPTERS_DIR = "chapters"
MASTER_FILE = "master_characters.json"
PROMPT_FILE = "character_prompts.json"

# =============================
# INPUT ARG
# =============================
chapter_arg = sys.argv[1] if len(sys.argv) > 1 else ""

# =============================
# GROQ CALL
# =============================
def call_groq(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    response = requests.post(GROQ_URL, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"Groq API Error: {response.text}")

    return response.json()["choices"][0]["message"]["content"]

# =============================
# LOAD / SAVE MASTER
# =============================
def load_master() -> Dict:
    if not os.path.exists(MASTER_FILE):
        return {}
    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_master(data: Dict):
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =============================
# BUILD BASE PROMPT (NO EMOTION)
# =============================
def build_base_prompt(name, c):
    return (
        f"{name}, {c.get('gender','')}, {c.get('age_range','')}, "
        f"{c.get('body_build','')} build, "
        f"{c.get('face_shape','')} face, "
        f"{c.get('eyes','')}, "
        f"{c.get('hair','')}, "
        f"wearing {c.get('clothing','')}, "
        f"colors {c.get('colors','')}, "
        f"{c.get('aura','')}, high detail, cinematic lighting"
    )

# =============================
# GENERATE PROMPTS FILE
# =============================
def generate_prompt_file(master: Dict):
    prompts = {}
    for name, data in master.items():
        prompt = build_base_prompt(name, data)
        prompts[name] = " ".join(prompt.split())

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)

    print(f"📌 Updated prompts: {PROMPT_FILE}")

# =============================
# PROMPT FOR LLM
# =============================
def build_character_prompt(script: str, existing_names: list) -> str:
    return f"""
You are designing consistent characters for cinematic AI visual storytelling.
DO NOT explain.
DO NOT think.
DO NOT include <think> tags.
DO NOT include markdown.
RETURN ONLY VALID JSON.

IMPORTANT:
- Do NOT recreate existing characters
- Existing characters: {existing_names}
- Only generate NEW characters

STRICT RULES:
- Each character must have ONE fixed and unique appearance
- Appearance MUST NOT change across scenes
- No vague descriptions
- Ignore narrator and unknown

Return ONLY valid JSON

Fields:
- name
- gender
- age_range
- height
- body_build
- face_shape
- eyes
- hair
- clothing
- colors
- aura
- signature_item

SCRIPT:
{script}
"""

# =============================
# JSON CLEANER
# =============================
def extract_json(text: str) -> Dict:
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

# =============================
# MERGE LOGIC
# =============================
def merge_characters(master: Dict, new_chars: Dict) -> Dict:
    for name, data in new_chars.items():

        # 🔥 Fix if incoming data is list
        if isinstance(data, list):
            print(f"⚠️ Fixing list for {name}")
            data = data[0] if data else {}

        # 🔥 Fix if master already corrupted
        if name in master and isinstance(master[name], list):
            print(f"⚠️ Fixing existing list for {name}")
            master[name] = master[name][0] if master[name] else {}

        if name not in master:
            master[name] = data

    return master
# =============================
# PROCESS
# =============================
def process_chapters():
    master = load_master()

    chapter_files = sorted(
        [f for f in os.listdir(CHAPTERS_DIR) if f.startswith("chapter_") and f.endswith(".txt")],
        key=lambda x: int(re.search(r"\d+", x).group())
    )

    for chapter_file in chapter_files:
        chapter_num = re.search(r"\d+", chapter_file).group()

        if chapter_arg and chapter_num != str(chapter_arg):
            continue

        file_path = os.path.join(CHAPTERS_DIR, chapter_file)
        output_file = os.path.join(CHAPTERS_DIR, f"chapter_{chapter_num}_characters.json")

        print(f"\n🚀 Processing Chapter {chapter_num}")

        with open(file_path, "r", encoding="utf-8") as f:
            script = f.read()

        existing_names = list(master.keys())

        prompt = build_character_prompt(script, existing_names)
        response = call_groq(prompt)

        try:
            new_chars = extract_json(response)
        except Exception:
            print(f"❌ JSON parse failed for chapter {chapter_num}")
            print(response)
            continue

        master = merge_characters(master, new_chars)
        save_master(master)

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(new_chars, f, indent=2, ensure_ascii=False)

        print(f"✅ New characters saved: {output_file}")

    # 🔥 Always regenerate prompt file after processing
    generate_prompt_file(master)

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    if not GROQ_API_KEY:
        raise Exception("❌ Set GROQ_API_KEY environment variable")

    process_chapters()
