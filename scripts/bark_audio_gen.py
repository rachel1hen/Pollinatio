import os
import csv
import tempfile
import asyncio
from bark import SAMPLE_RATE, generate_audio
import scipy.io.wavfile
from pydub import AudioSegment
import subprocess


AUDIO_DIR = "audio"
CHAPTERS_DIR = "LLM_output"
AUDIO_DONE_FILE = "audio_done.txt"

VOICE_MAPPING = {
    "narrator": "v2/en_speaker_5",
    "male": "v2/en_speaker_6",
    "female": "v2/en_speaker_9"
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "-1002386494312"

async def generate_tts(text, voice, path):
    """Generate TTS for given text chunk."""
    # audio_array = generate_audio(text, history_prompt=voice)
    try:
        audio_array = await asyncio.to_thread(generate_audio, text, history_prompt=voice)
        wav_path = path.replace(".mp3", ".wav")
    
        # Save .wav file
        scipy.io.wavfile.write(wav_path, SAMPLE_RATE, audio_array)
    
        # Convert to .mp3 using ffmpeg
        # subprocess.run(["ffmpeg", "-y", "-i", wav_path, path], check=True)
        await asyncio.to_thread(
            subprocess.run[
            "ffmpeg", "-y", "-i", wav_path,
            "-af", "afftdn,loudnorm,highpass=f=100,lowpass=f=8000,acompressor",
            path
            ], check=True)
        os.remove(wav_path)
    except Exception as e:
        print(f"❌ Error generating TTS for {text[:30]}... : {e}")


def create_silence(ms, path):
    """Create silence mp3."""
    # silence = AudioSegment.silent(duration=ms)
    # silence.export(path, format="mp3")
    silence_path = os.path.join(tempfile.gettempdir(), f"silence_{ms}.mp3")
    if not os.path.exists(silence_path):
        silence = AudioSegment.silent(duration=ms)
        silence.export(silence_path, format="mp3")
    return silence_path

def combine_audio(files, output_file):
    """Combine mp3 files using ffmpeg concat."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for file in files:
            f.write(f"file '{file}'\n")
        list_path = f.name
    # cmd = ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_file]
    # subprocess.run(cmd, check=True)
    subprocess.run(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_file],
        check=True
    )
    os.unlink(list_path)

def pick_chapter(chapter_arg=None):
    """Return chapter number to process, or None if none left."""
    with open(AUDIO_DONE_FILE, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        parts = line.strip().split(",")
        if len(parts) < 3:  # chapter, cleansed, audio_gen
            continue
        chapter, cleansed, audio_gen = parts
        chapter_num = chapter[:-4].split("_")[1] if "_" in chapter else chapter
        if chapter_arg and chapter_num != str(chapter_arg):
            continue
        if cleansed == "1" and audio_gen == "0":
            return chapter, i, lines
    return None, None, lines

async def process_chapter(chapter_num, index, lines):
    tsv_path = os.path.join(CHAPTERS_DIR, f"{chapter_num}")
    chapter_number = chapter_num[:-4].split("_")[1] if "_" in chapter_num else chapter_num
    audio_path = os.path.join(AUDIO_DIR, f"chapter_{chapter_number}.mp3")
    os.makedirs(AUDIO_DIR, exist_ok=True)

    chunks = []
    silence_file = os.path.join(tempfile.gettempdir(), "silence.mp3")
    create_silence(500, silence_file)

    # tasks = []
    # async with asyncio.TaskGroup() as tg:
    with open(tsv_path, "r", encoding="utf-8") as f:
            content = f.read()
            lines = content.strip().split("\\n")
            indx = 1
            async with asyncio.TaskGroup() as tg:  
                for line in lines:
                    
                    # clean_line = line.encode().decode('unicode_escape')
                    parts = line.split("\\t")
                    actor, gender, mood, text = parts
                    if not text:
                        continue
                    if actor == "narrator":
                        voice = VOICE_MAPPING["narrator"]
                    elif gender == "male":
                        voice = VOICE_MAPPING.get(gender, VOICE_MAPPING["male"])
                    elif gender == "female":
                        voice = VOICE_MAPPING.get(gender, VOICE_MAPPING["female"])
                    else:
                        voice = VOICE_MAPPING["narrator"]
    
                    # Handle "..." splits
                    parts = text.split("...")
                    indx += 1
                    for j, part in enumerate(parts):
                        part = part.strip()
                        if part:
                            out_file = os.path.join(tempfile.gettempdir(), f"{chapter_num}_{indx}_{j}.mp3")
                            # await generate_tts(part, voice, out_file)
                            tg.create_task(generate_tts(part, voice, out_file))
                            # tg.append(asyncio.create_task(generate_tts(part, voice, out_file)))
                            # tasks.append(tg.create_task(generate_tts(part, voice, out_file)))
                            chunks.append(out_file)
                        if j < len(parts) - 1:
                            chunks.append(silence_file)

                
    await asyncio.gather(*tg)
    chunks = [f"{chapter_num}_{i}.mp3" for i in range(len(parts))]
    # Combine into final MP3
    combine_audio(chunks, audio_path)

    # Send to Telegram
    import requests
    with open(audio_path, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={"audio": f}
        )

    # Delete audio after sending
    os.remove(audio_path)

    # Mark audio_done.txt
    with open(AUDIO_DONE_FILE, "r") as f:
        lines = f.readlines()
    lines[index] = f"{chapter_num},1,1\n"
    with open(AUDIO_DONE_FILE, "w") as f:
        f.writelines(lines)

def main():
    chapter_arg = os.getenv("CHAPTER_NUM")  # optional
    chapter, idx, lines = pick_chapter(chapter_arg)
    if not chapter:
        print("No chapters pending")
        return
    asyncio.run(process_chapter(chapter, idx, lines))

if __name__ == "__main__":
    main()
