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
        "temperature": 0.3  # 🔥 lower = more consistent JSON
    }

    res = requests.post(GROQ_URL, headers=headers, json=payload)

    if res.status_code != 200:
        raise Exception(res.text)

    return res.json()["choices"][0]["message"]["content"]

# =============================
# LOAD / SAVE MASTER
# =============================
def load_master() -> Dict:
    if not os.path.exists(MASTER_FILE):
        return {"characters": {}}

    with open(MASTER_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 🔥 Fix corrupted structure
    if "characters" not in data or not isinstance(data["characters"], dict):
        return {"characters": {}}

    return data


def save_master(data: Dict):
    with open(MASTER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# =============================
# CLEANING / NORMALIZATION
# =============================
BANNED_WORDS = ["angry", "cold", "sad", "worried", "dangerous", "intimidating"]

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    for w in BANNED_WORDS:
        text = text.replace(w, "")
    return text.strip()


def generate_seed(name: str) -> int:
    return abs(hash(name)) % (10**8)


def normalize_character(c: Dict) -> Dict:
    return {
        "gender": c.get("gender", "").lower(),
        "age_range": c.get("age_range", "").lower(),
        "body_build": c.get("body_build", "").lower(),
        "face_shape": c.get("face_shape", "").lower(),
        "hair": clean_text(c.get("hair", "")),
        "eyes": clean_text(c.get("eyes", "")),
        "signature_item": clean_text(c.get("signature_item", "")),
        "default_outfit": clean_text(c.get("clothing", "")),  # renamed
        "seed": generate_seed(c.get("name", "")),
        "model": "anything-v5"
    }

# =============================
# PROMPT GENERATION (FIXED)
# =============================
def build_base_prompt(name, c):
    return (
        f"masterpiece, best quality, anime style, "
        f"{c['gender']}, {name}, {c['age_range']}, "
        f"{c['body_build']} body, {c['face_shape']} face, "
        f"{c['hair']}, {c['eyes']}, "
        f"{c['signature_item']}, consistent character design"
    )


def generate_prompt_file(master: Dict):
    prompts = {}

    for name, c in master["characters"].items():
        prompts[name] = {
            "base_prompt": build_base_prompt(name, c),
            "negative_prompt": "blurry, bad anatomy, extra limbs, deformed face",
            "seed": c["seed"],
            "model": c["model"],
            "default_outfit": c["default_outfit"]
        }

    with open(PROMPT_FILE, "w", encoding="utf-8") as f:
        json.dump(prompts, f, indent=2, ensure_ascii=False)

    print(f"📌 Updated prompts: {PROMPT_FILE}")

# =============================
# LLM PROMPT (STRICT)
# =============================
def build_character_prompt(script: str, existing_names: list) -> str:
    return f"""
Return ONLY valid JSON. No explanation.

FORMAT:
{{
  "characters": [
    {{
      "name": "",
      "gender": "",
      "age_range": "",
      "body_build": "",
      "face_shape": "",
      "eyes": "",
      "hair": "",
      "clothing": "",
      "signature_item": ""
    }}
  ]
}}

RULES:
- Do NOT include emotions in eyes
- Do NOT include aura
- Keep descriptions visual only
- clothing = default outfit (not scene specific)
- Do NOT repeat existing characters: {existing_names}

SCRIPT:
{script}
"""

# =============================
# JSON EXTRACTION
# =============================
def extract_json(text: str) -> Dict:
    text = re.sub(r"<.*?>", "", text, flags=re.DOTALL)
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])

# =============================
# MERGE
# =============================
def merge_characters(master: Dict, new_chars: Dict) -> Dict:
    chars = master["characters"]

    for c in new_chars.get("characters", []):
        name = c.get("name")
        if not name:
            continue

        if name not in chars:
            chars[name] = normalize_character(c)

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

        print(f"\n🚀 Processing Chapter {chapter_num}")

        with open(os.path.join(CHAPTERS_DIR, chapter_file), "r", encoding="utf-8") as f:
            script = f.read()

        existing_names = list(master["characters"].keys())

        prompt = build_character_prompt(script, existing_names)
        response = call_groq(prompt)

        try:
            new_chars = extract_json(response)
        except Exception:
            print("❌ JSON parse failed")
            print(response)
            continue

        master = merge_characters(master, new_chars)
        save_master(master)

        out_file = os.path.join(CHAPTERS_DIR, f"chapter_{chapter_num}_characters.json")
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(new_chars, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved: {out_file}")

    generate_prompt_file(master)

# =============================
# MAIN
# =============================
if __name__ == "__main__":
    if not GROQ_API_KEY:
        raise Exception("Set GROQ_API_KEY")

    process_chapters()
