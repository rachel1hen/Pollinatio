import os
import sys
import re
from deep_translator import GoogleTranslator
# from googletrans import Translator

FLAGS_FILE = "audio_done.txt"
CHAPTERS_DIR = "chapters"

def create_tracking_file():
    """Create audio_done.txt if it doesn't exist and populate with chapter file names."""
    if not os.path.exists(FLAGS_FILE):
        with open(FLAGS_FILE, "w", encoding="utf-8") as f:
            for fname in sorted(os.listdir(CHAPTERS_DIR)):
                if fname.startswith("chapter_") and fname.endswith(".txt"):
                    f.write(f"{fname},0,0\n")
        print("Tracking file created.")

def load_flags():
    """Load audio_done.txt into a dict {chapter_filename: {'cleansed': bool, 'audio_gen': bool}}"""
    flags = {}
    if os.path.exists(FLAGS_FILE):
        with open(FLAGS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 3:
                    fname, cleansed, audio_gen = parts
                    flags[fname] = {
                        "cleansed": cleansed == "1",
                        "audio_gen": audio_gen == "1"
                    }
    return flags

def save_flags(flags):
    """Save flags back to audio_done.txt"""
    with open(FLAGS_FILE, "w", encoding="utf-8") as f:
        for fname, status in sorted(flags.items()):
            f.write(f"{fname},{int(status['cleansed'])},{int(status['audio_gen'])}\n")

def remove_invalid_chars(text):
    """Remove invalid characters like �"""
    return text.replace("�", "")

def translate_chinese(text, translator):
    """Translate only Chinese characters"""
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
    matches = chinese_pattern.findall(text)
    for match in set(matches):
        try:
            translated = translator.translate(match)
            # translated = translator.translate(match, src='zh-cn', dest='en').text
            text = text.replace(match, translated)
        except Exception as e:
            print(f"Translation failed for {match}: {e}")
    return text

def cleanse_chapter(file_path):
    """Cleanse a single chapter file"""
    translator = GoogleTranslator(source='zh-CN', target='en') 
    # Translator()
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    content = remove_invalid_chars(content)
    content = translate_chinese(content, translator)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

def main():
    create_tracking_file()  # Ensure the tracking file is created before starting

    chapter_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    flags = load_flags()

    # Make sure all chapter files are in flags dict
    for fname in os.listdir(CHAPTERS_DIR):
        if fname.startswith("chapter_") and fname.endswith(".txt"):
            if fname not in flags:
                flags[fname] = {"cleansed": False, "audio_gen": False}

    if chapter_arg:
        target_file = f"chapter_{chapter_arg}.txt"
        file_path = os.path.join(CHAPTERS_DIR, target_file)
        if os.path.exists(file_path):
            cleanse_chapter(file_path)
            flags[target_file]["cleansed"] = True
            print(f"Cleansed {target_file}")
        else:
            print(f"Chapter {chapter_arg} not found.")
    else:
        for fname, status in flags.items():
            if not status["cleansed"]:
                file_path = os.path.join(CHAPTERS_DIR, fname)
                if os.path.exists(file_path):
                    cleanse_chapter(file_path)
                    flags[fname]["cleansed"] = True
                    print(f"Cleansed {fname}")

    save_flags(flags)

if __name__ == "__main__":
    main()
