import os
import re
import threading
import requests
import trafilatura
from flask import Flask, request
import logging
from trafilatura import fetch_url, extract

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
POLLINATIONS_TTS_URL = "https://api.pollinations.ai/tts"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StoryBot")
# URL validation regex
URL_REGEX = re.compile(
    r'https?://(?:[\w-]+\.)+[\w-]+(?:/[\w\-./?%&=]*)?'
)

def send_telegram_message(chat_id, text):
    """Send text message via Telegram API."""
    payload = {
        "chat_id": chat_id,
        "text": text[:4090] + '...' if len(text) > 4096 else text
    }
    try:
        response = requests.post(TELEGRAM_SEND_MESSAGE_URL, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

def send_telegram_audio(chat_id, audio_data):
    """Send audio file via Telegram API."""
    try:
        files = {'audio': ('audio.mp3', audio_data, 'audio/mpeg')}
        data = {'chat_id': chat_id}
        response = requests.post(TELEGRAM_SEND_AUDIO_URL, files=files, data=data)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending audio: {e}")

def custom_fetch(url):
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=10)
    logger.info(response)
    if response.ok:
        return extract(response.text)
    else:
        logger.info(f"[ERROR] Failed fetch: {response.status_code}")
        return None

def scrape_web_content(url):
    """Scrape main content from URL using trafilatura."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return custom_fetch(url)
             
        logger.info(dowloaded)
        content = trafilatura.extract(downloaded)
        logger.info(content)
        return content.strip() if content else None
    except Exception as e:
        print(f"Scraping error: {e}")
        return None

def generate_tts_audio(text, token):
    """Generate TTS audio from text using Pollinations API."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {"text": text[:5000]}  # Truncate long texts
    
    try:
        response = requests.post(POLLINATIONS_TTS_URL, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        print(f"TTS API error: {e}")
        return None

def process_url(chat_id, url):
    """Process URL: scrape content, send text and generated audio."""
    # Scrape content
    content = scrape_web_content(url)
    if not content:
        send_telegram_message(chat_id, "❌ Failed to extract content from URL")
        return

    # Send scraped content
    send_telegram_message(chat_id, f"📝 Extracted content:\n\n{content}")
    
    # Generate and send audio
    audio_data = generate_tts_audio(content, POLLINATIONS_TOKEN)
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
    
    # Find URLs in message
    urls = URL_REGEX.findall(text)
    if not urls:
        send_telegram_message(chat_id, "🔍 Please send a valid URL")
        return 'OK', 200
    
    # Process first URL in background thread
    threading.Thread(target=process_url, args=(chat_id, urls[0])).start()
    return 'OK', 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
