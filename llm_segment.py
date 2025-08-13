import os
import json
import re
import requests

# === CONFIG ===
CHAPTERS_DIR = "chapters"
OUTPUT_DIR = "LLM_output"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GROQ_MODEL = "llama-3.1-70b-versatile"
OPENROUTER_MODEL = "meta-llama/llama-3.1-70b-instruct"

# === PROMPT ===
SYSTEM_PROMPT = """You are given a novel chapter. Your task is to split it into a JSON array where each item has two keys:
- "speaker": either "narrator" or the exact character name speaking (as in the text, e.g., "Chen Ping", "Liu Mei")
- "text": the exact text for that speaker.

Rules:
1. Do not skip or paraphrase any part of the chapter. Every sentence must appear exactly as in the original.
2. Keep punctuation and line breaks intact in the "text" field.
3. If the narrator text contains pronouns like "he said", "she asked", "they replied" that clearly refer to the most recent dialogue speaker, replace the pronoun with that speaker's full name, keeping the rest of the sentence intact.
4. Any non-dialogue description is assigned to the "narrator".
5. If a line contains both dialogue and narration, split it into two JSON entries: one for the character's dialogue, one for the narrator's text.
6. Do not add or invent any content not present in the chapter.

Output only valid JSON (UTF-8), like this:
[
  {"speaker": "narrator", "text": "Liu Mei looked up."},
  {"speaker": "Chen Ping", "text": "Are you alright?"},
  {"speaker": "narrator", "text": "Chen Ping said."}
]
"""

def call_groq(chapter_text):
    """Call GROQ API for segmentation."""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    data = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chapter_text}
        ],
        "temperature": 0
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def call_openrouter(chapter_text):
    """Fallback to OpenRouter."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "LLM Segmenter"
    }
    data = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": chapter_text}
        ],
        "temperature": 0
    }
    r = requests.post(url, headers=headers, json=data, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def parse_llm_output(raw_output):
    """Try to parse the LLM's JSON output."""
    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        # Try to extract JSON from inside text
        match = re.search(r"\{[\s\S]*\}", raw_output)
        if match:
            return json.loads(match.group(0))
        raise

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(OUTPUT_DIR):
      os.makedirs(OUTPUT_DIR)
    if not GROQ_API_KEY:
        return 
    chapter_files = sorted(
        [f for f in os.listdir(CHAPTERS_DIR) if f.startswith("chapter_") and f.endswith(".txt")],
        key=lambda x: int(re.search(r"\d+", x).group())
    )

    for chapter_file in chapter_files:
        chapter_num = re.search(r"\d+", chapter_file).group()
        output_file = os.path.join(OUTPUT_DIR, f"chapter_{chapter_num}.json")

        if os.path.exists(output_file):
            print(f"Skipping chapter {chapter_num} (already processed).",flush=True)
            continue

        print(f"Processing chapter {chapter_num}...",flush=True)

        with open(os.path.join(CHAPTERS_DIR, chapter_file), "r", encoding="utf-8") as f:
            chapter_text = f.read().strip()

        try:
            raw_output = call_groq(chapter_text)
            print(f"output {raw_output}",flush=True)
        except Exception as e:
            print(f"GROQ failed for chapter {chapter_num}: {e}, trying OpenRouter...",flush=True)
            raw_output = call_openrouter(chapter_text)

        try:
            parsed_json = parse_llm_output(raw_output)
            print(f"output1 {parsed_json}",flush=True)
        except Exception as e:
            print(f"Failed to parse LLM output for chapter {chapter_num}: {e}",flush=True)
            continue

        with open(output_file, "w", encoding="utf-8") as f:
            print(f"Printing....",flush=True)
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)

        print(f"Saved {output_file}")

if __name__ == "__main__":
    main()
