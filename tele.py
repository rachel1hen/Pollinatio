import os
import re
import threading
import requests
import trafilatura
from flask import Flask, request
import logging

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

# Pollinations TTS API endpoint
POLLINATIONS_TTS_URL = "https://text.pollinations.ai/models/tts"
HEADERS = {
    "Authorization": f"Bearer {POLLINATIONS_TOKEN}",
    "Content-Type": "application/json"
}

# Logging configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StoryBot")

# URL validation regex
URL_REGEX = re.compile(r'https?://[^\s<>"']+|www\.[^\s<>"']+')

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

def generate_tts_audio(text: str) -> bytes:
    """Generate TTS audio from text using Pollinations.ai (sync version)."""
    if not text:
        raise ValueError("Empty text provided for TTS")

    params = {"text": text, "voice": "en-US-Wavenet-A"}  # You can change the voice
    headers = {"Authorization": f"Bearer {POLLINATIONS_TOKEN}"}

    try:
        response = requests.get(POLLINATIONS_TTS_URL, params=params, headers=headers, timeout=60)
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"TTS API error: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"TTS request failed: {e}")
        return None

def process_url(chat_id, url):
    """Process URL: scrape content, send text and generated audio."""
    content = scrape_web_content(url)
    if not content:
        send_telegram_message(chat_id, "❌ Failed to extract content from URL")
        return

    send_telegram_message(chat_id, f"📝 Extracted content:\n\n{content}")

    audio_data = generate_tts_audio(content)
    if not audio_data and len(content) > 800:
        logger.info("Retrying TTS with shortened content...")
        audio_data = generate_tts_audio(content[:800])

    if audio_data:
        send_telegram_audio(chat_id, audio_data)
    else:
        send_telegram_message(chat_id, "❌ Failed to generate audio")

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
