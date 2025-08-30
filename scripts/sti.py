
import os
import tempfile
import scipy.io.wavfile
from pydub import AudioSegment
import subprocess
import uuid
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "-1002386494312"

def main():
    chapter_arg = os.getenv("CHAPTER_NUM")
    audio_path = "chunks"
    with open(audio_path, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={"audio": f}
        )
    #chapter, idx, lines = pick_chapter(chapter_arg)
    #if not chapter:
    #    print("No chapters pending")
    #    return
    #asyncio.run(process_chapter(chapter, idx, lines))

if __name__ == "__main__":
    main()
