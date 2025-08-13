import os
import json
import re
import requests
import logging
import sys

# === CONFIG ===
CHAPTERS_DIR = "chapters"
OUTPUT_DIR = "LLM_output"
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

GROQ_MODEL = "gemma2-9b-it"
OPENROUTER_MODEL = "meta-llama/llama-3.1-70b-instruct"

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    stream=sys.stdout,  # Ensure logs go to stdout (GitHub Actions captures this)
)

logging.info("Logging started")

# === PROMPT ===
SYSTEM_PROMPT = """
You are given the full text of a novel chapter. 
Your job is to break it into a JSON array, where each element has the following keys:

- "actorname": the full name of the character speaking, or "narrator" for narration.
- "gender": "male", "female", or "unknown" (narrator is "unknown").
- "mood": the emotional tone of the text (e.g., "neutral", "angry", "happy", "sad", "serious", "excited", "worried").
- "text": the exact text from the original, without skipping or changing meaning.

Rules:
1. Do not skip or paraphrase any text. Every sentence must appear exactly as in the original.
2. Preserve punctuation, casing, and line breaks exactly.
3. If narrator text contains pronouns like "he said", "she asked", "they replied" that clearly refer to the most recent dialogue speaker, replace the pronoun with that speaker’s full name, keeping the rest of the sentence unchanged.
4. Non-dialogue description goes under "narrator" with "gender": "unknown" and mood inferred from context.
5. If one paragraph mixes narration and dialogue, split it into multiple JSON objects: one for the character’s dialogue, and one for the narrator part.
6. Output must be valid UTF-8 JSON with no extra commentary, markdown, or formatting.
7. Do not add, reorder, or invent text.

Example:

[
  {"actorname": "narrator", "gender": "unknown", "mood": "neutral", "text": "Liu Mei looked up."},
  {"actorname": "Chen Ping", "gender": "male", "mood": "concerned", "text": "Are you alright?"},
  {"actorname": "narrator", "gender": "unknown", "mood": "neutral", "text": "Chen Ping said."}
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
    logging.info(f"api key  {GROQ_API_KEY}")

    chapter_files = sorted(
        [f for f in os.listdir(CHAPTERS_DIR) if f.startswith("chapter_") and f.endswith(".txt")],
        key=lambda x: int(re.search(r"\d+", x).group())
    )

    for chapter_file in chapter_files:
        chapter_num = re.search(r"\d+", chapter_file).group()
        output_file = os.path.join(OUTPUT_DIR, f"chapter_{chapter_num}.json")
        logging.info(chapter_num)
        if os.path.exists(output_file):
            print(f"Skipping chapter {chapter_num} (already processed).",flush=True)
            continue

        print(f"Processing chapter {chapter_num}...",flush=True)
        logging.info(f"Processing chapter {chapter_num}")

        with open(os.path.join(CHAPTERS_DIR, chapter_file), "r", encoding="utf-8") as f:
            chapter_text = f.read().strip()

        try:
            raw_output = call_groq(chapter_text)
            print(f"output {raw_output}",flush=True)
        except Exception as e:
            print(f"GROQ failed for chapter {chapter_num}: {e}, trying OpenRouter...",flush=True)
            logging.info("GROQ failed")
            raw_output = call_openrouter(chapter_text)

        try:
            parsed_json = parse_llm_output(raw_output)
            print(f"output1 {parsed_json}",flush=True)
            logging.info(parsed_json)
        except Exception as e:
            print(f"Failed to parse LLM output for chapter {chapter_num}: {e}",flush=True)
            logging.info("Failed to parse LLM")
            logging.info(raw_output)
            continue

        with open(output_file, "w", encoding="utf-8") as f:
            print(f"Printing....",flush=True)
            logging.info("Printing....")
            json.dump(parsed_json, f, ensure_ascii=False, indent=2)

        print(f"Saved {output_file}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error in main: {e}")
