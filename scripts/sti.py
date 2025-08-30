
import os
import tempfile
#import scipy.io.wavfile
from pydub import AudioSegment
import subprocess
import uuid
import requests

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "-1002386494312"

def combine_audio(files, output_file):
    """Combine mp3 files using ffmpeg concat."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for file in files:
            f.write(f"file '{file}'\n")
        list_path = f.name
    
    cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_file]
    subprocess.run(cmd, check=True)
    os.unlink(list_path)


def main():
    chapter_arg = os.getenv("CHAPTER_NUM")
    audio_path = "chunks"
    output_file = f"chapter_{chapter_arg}.mp3" if chapter_arg else "combined_chapter.mp3"
    

    chunk_files = []
    for i in range(20):  # Based on TOTAL_CHUNKS in workflow
        chunk_path = os.path.join(audio_path, f"chunk-{i}", f"chunk_{i}.mp3")
        if os.path.exists(chunk_path):
            chunk_files.append(chunk_path)

    if not chunk_files:
        print("No chunk files found!")
        return
    
    combine_audio(chunk_files, output_file)
    
    with open(output_file, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={"audio": f}
        )
    os.remove(output_file)


if __name__ == "__main__":
    main()
