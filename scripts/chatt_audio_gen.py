import torchaudio as ta
from chatterbox.tts import ChatterboxTTS
import os
import tempfile
import asyncio
import scipy.io.wavfile
from pydub import AudioSegment
import subprocess
import uuid
import requests

model = ChatterboxTTS.from_pretrained(device="cpu")
AUDIO_DIR = "audio"
CHAPTERS_DIR = "LLM_output"
AUDIO_DONE_FILE = "audio_done.txt"

VOICE_MAPPING = {
    "narrator": "sample/Narrator.mp3",
    "male": "sample/Male_1.wav",
    "female": "sample/Female_5.wav"
}

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = "-1002386494312"
AUDIO_PROMPT_PATH = ""
# def get_lines_for_chunk(all_lines, chunk_num, total_chunks):
#     total = len(all_lines)
#     base_size = total // total_chunks
#     remainder = total % total_chunks

#     start = chunk_num * base_size + min(chunk_num, remainder)
#     end = start + base_size + (1 if chunk_num < remainder else 0)
#     return all_lines[start:end]

async def generate_tts(text, voice, path):
    """Generate TTS for given text chunk."""
    try:
    #     audio_array = await asyncio.to_thread(generate_audio, text, history_prompt=voice,text_temp=0.5,
    # waveform_temp=0.5)
    #     wav_path = path.replace(".mp3", ".wav")
    #     scipy.io.wavfile.write(wav_path, SAMPLE_RATE, audio_array)
        
    #     await asyncio.to_thread(
    #         subprocess.run,
    #         [
    #             "ffmpeg", "-y", "-i", wav_path,
    #             "-af", "afftdn,loudnorm,highpass=f=100,lowpass=f=8000,acompressor",
    #             path
    #         ],
    #         check=True
    #     )
    #     os.remove(wav_path)
        wav = model.generate(text, audio_prompt_path=voice)
        ta.save(path, wav, model.sr)
        
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
    audio_path = os.path.join(AUDIO_DIR, f"chapter_{chapter_number}.mp3")
    os.makedirs(AUDIO_DIR, exist_ok=True)

    silence_file = create_silence(500, os.path.join(tempfile.gettempdir(), "silence.mp3"))

    with open(tsv_path, "r", encoding="utf-8") as f:
        content = f.read()
        all_lines = content.strip().split("\\n")

    # chunk_num = int(os.getenv("CHUNK_NUM", "0"))
    # total_chunks = int(os.getenv("TOTAL_CHUNKS", "1"))

    # lines_to_process = get_lines_for_chunk(all_lines, chunk_num, total_chunks)

    chunks = []
    idx = 1

    for line in all_lines:
        parts = line.split("\\t")
        if len(parts) < 4:
            continue
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
            
        if actor == "Chen Ping":
                voice = "sample/Cheng.mp3"

        text_parts = text.split("...")
        for j, part in enumerate(text_parts):
            part = part.strip()
            if part:
                out_file = os.path.join(tempfile.gettempdir(), f"{chapter_num}_{idx}_{j}.mp3")
                await generate_tts(part, voice, out_file)
                chunks.append(out_file)
            if j < len(text_parts) - 1:
                chunks.append(silence_file)
        idx += 1

    combine_audio(chunks, audio_path)

    with open(audio_path, "rb") as f:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio",
            data={"chat_id": TELEGRAM_CHAT_ID},
            files={"audio": f}
        )

    os.remove(audio_path)

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
