# scripts/run_tts.py
import sys
import soundfile as sf
from funasr import AutoModelForTTS

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_tts.py 'Your text here'")
        sys.exit(1)

    text = sys.argv[1]
    print(f"🔊 Generating TTS for: {text}")

    # Load CosyVoice2 model
    model = AutoModelForTTS.from_pretrained("iic/CosyVoice2-200M", trust_remote_code=True)

    # Inference
    wav, sr = model.generate(text, spk="en_default")

    # Save
    sf.write("output.wav", wav, sr)
    print("✅ Saved output.wav")

if __name__ == "__main__":
    main()
