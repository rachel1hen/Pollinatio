import os
import re
import threading
import json
import logging
import requests
import trafilatura
from flask import Flask, request
import logging
import edge_tts
#from undetected import generate_data
from deepseek_edgetts import generate_tts
import io
import asyncio

app = Flask(__name__)

# Get tokens from environment variables
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
POLLINATIONS_TOKEN = os.environ.get('POLLINATIONS_TOKEN')

# Validate tokens
if not TELEGRAM_TOKEN or not POLLINATIONS_TOKEN:
    raise ValueError("TELEGRAM_TOKEN and POLLINATIONS_TOKEN must be set in environment variables")

# Telegram API endpoints
TELEGRAM_SEND_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TELEGRAM_SEND_AUDIO_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendAudio"


# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StoryBot")

# URL validation regex
#URL_REGEX = re.compile(r'https?://[^\s<>"']+|www\.[^\s<>"']+')
URL_REGEX = re.compile(r"https?://[^\s<>\"']+|www\.[^\s<>\"']+")

def send_telegram_message(chat_id, text):
    """Send text message via Telegram API."""
    payload = {
        "chat_id": chat_id,
        "text": text[:4090] + '...' if len(text) > 4096 else text
    }
    try:
        response = requests.post(TELEGRAM_SEND_MESSAGE_URL, json=payload, timeout=15)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending message: {e}")

def send_telegram_audio(chat_id, audio_data):
    """Send audio file via Telegram API."""
    try:
        files = {'audio': ('audio.ogg', audio_data, 'audio/ogg')}
        data = {'chat_id': chat_id}
        response = requests.post(TELEGRAM_SEND_AUDIO_URL, files=files, data=data, timeout=15)
        response.raise_for_status()
        logger.info(response.headers.get("Content-Type"))
        logger.info(response.text)
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending audio: {e}")

def custom_fetch(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.ok:
            return trafilatura.extract(response.text)
        else:
            logger.error(f"[ERROR] Failed fetch: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Custom fetch failed: {e}")
        return None

def scrape_web_content(url):
    """Scrape main content from URL using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return custom_fetch(url)

        logger.info("Content downloaded")
        content = trafilatura.extract(downloaded)
        logger.info(content)
        return content.strip() if content else None
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return None



def process_url(chat_id, url):
    """Process URL: scrape content, send text and generated audio."""
    content = scrape_web_content(url)
    if not content:
        send_telegram_message(chat_id, "❌ Failed to extract content from URL")
        return
    
    send_telegram_message(chat_id, f"📝 Extracted content:\n\n{content}")
    content = re.sub(r'\n+', ' ', content)
    #json_file_path = generate_data(content)


    prompt = f"""You are a helpful assistant. Read the following story and extract all dialogue and narration into a JSON array.
Each element in the array must follow this format: [actorName, Emotion, textSpoken, gender] 
Rules to follow strictly: 1. Use quotation marks to extract dialogue. 2. Include narration with "actorName" as "narration" and gender as null. 
3. Set Emotion based on cues like “mocked”, “roared”, “angrily”, etc., or null if none. 4. Derive gender from the name, use best judgment if unclear. 
5. Do not skip any part of the story — include every sentence. 6. Output only the JSON array — no explanations, no extra text. 
7. Wrap the entire JSON array inside a markdown code block (triple backticks), specifying json for syntax highlighting. 
Now process this story:\n{content}
"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key =  os.environ.get('API_KEY')
    headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
    }
    payload = {
    "model": "gemma2-9b-it",  # Replace with "gemma-2-9b-it" if that's the exact model identifier
    "messages": [
        {"role": "user", "content": prompt}
    ],
    "temperature": 0.2
}

    response = requests.post(url, headers=headers, json=payload)
    print(response.json()["choices"][0]["message"]["content"])

    json_content = response.json()["choices"][0]["message"]["content"]
    logger.info(f"Extracted JSON content: {json_content}")
    send_telegram_message(chat_id, f"📜 Extracted JSON content:\n```json\n{json_content}\n```")
    audio_data = generate_tts(json_content)

    if not audio_data:
        send_telegram_message(chat_id, "❌ Failed to generate TTS data")
        return
    send_telegram_audio(chat_id, audio_data)
    # if not json_file_path:



@app.route('/webhook', methods=['POST'])
def webhook_handler():
    """Handle incoming Telegram updates."""
    update = request.json

    if 'message' not in update:
        return 'OK', 200

    message = update['message']
    chat_id = message['chat']['id']
    text = message.get('text', '')

    urls = URL_REGEX.findall(text)
    if not urls:
        send_telegram_message(chat_id, "🔍 Please send a valid URL")
        return 'OK', 200

    threading.Thread(target=process_url, args=(chat_id, urls[0])).start()
    return 'OK', 200

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
