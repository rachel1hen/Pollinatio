import torchaudio as ta
import torch
from zonos.model import Zonos
from zonos.conditioning import make_cond_dict
import os
import tempfile
import asyncio
from pydub import AudioSegment
import subprocess
import uuid
import requests
import sqlite3
from pathlib import Path


device = torch.device("cpu")
model = Zonos.from_pretrained("Zyphra/Zonos-v0.1-transformer", device=device)
AUDIO_DIR = "../audio"
CHAPTERS_DIR = "../LLM_output"
AUDIO_DONE_FILE = "../audio_done.txt"

VOICE_MAPPING = {
    "narrator": "Narrator.mp3",
    "male": "Male_1.wav",
    "female": "Female_5.wav"
}
DB_PATH = Path("../voice.db")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "-1002386494312"
def get_lines_for_chunk(all_lines, chunk_num, total_chunks):
     
     total = len(all_lines)
     base_size = total // total_chunks
     remainder = total % total_chunks

     start = chunk_num * base_size + min(chunk_num, remainder)
     end = start + base_size + (1 if chunk_num < remainder else 0)
     return all_lines[start:end]

async def generate_tts(text, voice, path, mood):
    """Generate TTS for given text chunk."""
    try:
        wav, sampling_rate = ta.load(voice)
        speaker = model.make_speaker_embedding(wav, sampling_rate)
        cond_dict = make_cond_dict(
            text=text,
            speaker=speaker,
            language="en-us",
            # emotion=[0.01, 0.01, 1.00, 0.01, 0.01, 0.01, 0.01, 0.02]
        )
        conditioning = model.prepare_conditioning(cond_dict)
        codes = model.generate(conditioning)
        wavs = model.autoencoder.decode(codes).cpu()
        ta.save(path,  wavs[0], model.autoencoder.sampling_rate)
        
        print(f"✅ Generated TTS for {text[:30]}...")
    except Exception as e:
        print(f"❌ Error generating TTS for {text[:30]}... : {e}")

def create_silence(ms, path):
    silence_path = os.path.join(tempfile.gettempdir(), f"silence_{ms}.mp3")
    if not os.path.exists(silence_path):
        silence = AudioSegment.silent(duration=ms)
        silence.export(silence_path, format="mp3")
    return silence_path

def combine_audio(files, output_file):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for file in files:
            f.write(f"file '{file}'\n")
        list_path = f.name
    subprocess.run(
        ["ffmpeg", "-f", "concat", "-safe", "0", "-i", list_path, "-c", "copy", output_file],
        check=True
    )
    os.unlink(list_path)

def pick_chapter(chapter_arg=None):
    with open(AUDIO_DONE_FILE, "r") as f:
        lines = f.readlines()

    for i, line in enumerate(lines):
        parts = line.strip().split(",")
        if len(parts) < 3:
            continue
        chapter, cleansed, audio_gen = parts
        chapter_num = chapter[:-4].split("_")[1] if "_" in chapter else chapter
        if chapter_arg and chapter_num != str(chapter_arg):
            continue
        if cleansed == "1" and audio_gen == "0":
            return chapter, i, lines
    return None, None, lines

async def process_chapter(chapter_num, index, lines):
    tsv_path = os.path.join(CHAPTERS_DIR, chapter_num)
    chapter_number = chapter_num[:-4].split("_")[1] if "_" in chapter_num else chapter_num
    
    os.makedirs(AUDIO_DIR, exist_ok=True)

    silence_file = create_silence(1000, os.path.join(tempfile.gettempdir(), "silence.mp3"))

    with open(tsv_path, "r", encoding="utf-8") as f:
        content = f.read()
        all_lines = content.strip().split("\\n")

    chunk_num = int(os.getenv("CHUNK_NUM", "0"))
    audio_path = os.path.join(AUDIO_DIR, f"chunk_{chunk_num}.mp3")
    total_chunks = int(os.getenv("TOTAL_CHUNKS", "1"))

    lines_to_process = get_lines_for_chunk(all_lines, chunk_num, total_chunks)

    chunks = []
    idx = 1
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT actor_name, voice_file FROM voice_assignments")
    current = dict(cursor.fetchall())
    conn.close()
    for line in lines_to_process:
        parts = line.split("\\t")
        if len(parts) < 4:
            continue
        actor, gender, mood, text = parts
        if not text:
            continue
        
        #if actor == "narrator":
         #   voice = VOICE_MAPPING["narrator"]
        #elif gender == "male":
        #    voice = VOICE_MAPPING.get(gender, VOICE_MAPPING["male"])
        #elif gender == "female":
        #    voice = VOICE_MAPPING.get(gender, VOICE_MAPPING["female"])
        #else:   
         #   voice = VOICE_MAPPING["narrator"]
            
        if actor == "Chen Ping":
                voice = "Cheng.mp3"

        voice = current.get(actor)
        
        text_parts = text.split("...")
        for j, part in enumerate(text_parts):
            part = part.strip()
            if part:
                out_file = os.path.join(tempfile.gettempdir(), f"{chapter_num}_{idx}_{j}.mp3")
                await generate_tts(part, voice, out_file, mood)
                chunks.append(out_file)
            if j < len(text_parts) - 1:
                chunks.append(silence_file)
        idx += 1

    combine_audio(chunks, audio_path)

    # with open(audio_path, "rb") as f:
    #     requests.post(
    #         f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
    #         data={"chat_id": TELEGRAM_CHAT_ID},
    #         files={"audio": f}
    #     )

    #os.remove(audio_path)

    lines[index] = f"{chapter_num},1,1\n"
    with open(AUDIO_DONE_FILE, "w") as f:
        f.writelines(lines)

def main():
    chapter_arg = os.getenv("CHAPTER_NUM")
    chapter, idx, lines = pick_chapter(chapter_arg)
    if not chapter:
        print("No chapters pending")
        return
    asyncio.run(process_chapter(chapter, idx, lines))

if __name__ == "__main__":
    main()
