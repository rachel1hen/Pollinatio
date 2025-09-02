# scripts/run_tts.py
import sys
from cosyvoice import CosyVoice
import soundfile as sf

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_tts.py 'Your text here'")
        sys.exit(1)

    text = sys.argv[1]
    print(f"Generating TTS for: {text}")

    # Load CosyVoice model (this will download weights if missing)
    model = CosyVoice.from_pretrained("funasr/cosyvoice2-200m")

    # Run inference
    audio, sr = model.inference(text)

    # Save to file
    sf.write("output.wav", audio, sr)
    print("✅ Saved output.wav")

if __name__ == "__main__":
    main()
