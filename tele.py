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
from undetected import generate_data
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

def generate_tts_with_edge_tts(json_file_path):
    """
    Generate TTS audio using Edge TTS for each entry in the JSON file.
    The JSON is a list of [author, emotion, text, gender].
    SSML tags in 'text' are ignored by edge_tts local, so we try to extract prosody info and apply as best as possible.
    Returns: bytes of concatenated audio in ogg_opus format.
    """

    # Helper to extract prosody info from SSML if possible
    def extract_prosody(text):
        # Defaults
        rate = "0%"
        pitch = "0Hz"
        volume = "0%"
        # Try to extract from <prosody ...> tag
        m = re.search(r'<prosody([^>]*)>', text)
        if m:
            attrs = m.group(1)
            rate_m = re.search(r'rate="([^"]+)"', attrs)
            pitch_m = re.search(r'pitch="([^"]+)"', attrs)
            volume_m = re.search(r'volume="([^"]+)"', attrs)
            if rate_m:
                rate = rate_m.group(1)
            if pitch_m:
                pitch = pitch_m.group(1)
            if volume_m:
                volume = volume_m.group(1)
        # Remove all SSML tags for edge_tts local
        safe_text = re.sub(r'<[^>]+>', '', text)
        return safe_text, rate, pitch, volume

    # Map gender to edge_tts voice
    def get_voice(gender):
        # You can expand this mapping as needed
        if gender == "male":
            return "en-US-GuyNeural"
        elif gender == "female":
            return "en-US-JennyNeural"
        else:
            return "en-US-JennyNeural"

    async def synthesize_all(entries):
        audio_bytes = io.BytesIO()
        for entry in entries:
            author, emotion, text, gender = entry
            safe_text, rate, pitch, volume = extract_prosody(text)
            voice = get_voice(gender)
            try:
                communicate = edge_tts.Communicate(
                    text=safe_text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                    volume=volume
                )
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_bytes.write(chunk["data"])
            except Exception as e:
                logger.error(f"Error generating TTS for '{safe_text}': {e}")
        return audio_bytes.getvalue()

    with open(json_file_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    try:
        audio_data = asyncio.run(synthesize_all(data))
        return audio_data
    except Exception as e:
        logger.error(f"Error generating TTS: {e}")
        return None

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
    json_file_path = generate_data(content)
    if not json_file_path:
        send_telegram_message(chat_id, "❌ Failed to generate TTS data")
        return
    audio_data = generate_tts_with_edge_tts(json_file_path)
    send_telegram_audio(chat_id, audio_data)


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
