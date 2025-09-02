from funasr.models import AutoModelForTTS

def main():
    model = AutoModelForTTS.from_pretrained("iic/CosyVoice2-200M", trust_remote_code=True)
    text = "Hello, this is CosyVoice2 running on a Mac M1 self-hosted runner."
    wav_file = "output.wav"

    wav = model.generate(text=text, spk_id=0)
    model.save_wav(wav, wav_file)

if __name__ == "__main__":
    main()
