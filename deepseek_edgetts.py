import asyncio
import os
import tempfile
import subprocess
import json
import edge_tts
from pydub import AudioSegment

VOICE_MAPPING = {
    "narration": "en-GB-LibbyNeural",
    "male": "en-GB-RyanNeural",
    "female": "en-US-AriaNeural"
}

async def generate_audio_chunk(text, voice, output_path):
    """Generate audio for a text chunk using specified voice.
    
    Args:
        text: Text to convert to speech
        voice: Voice model to use
        output_path: Path to save generated MP3
    """
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def create_silence(duration_ms, file_path):
    """Create a silent audio segment.
    
    Args:
        duration_ms: Silence duration in milliseconds
        file_path: Output file path
    """
    silence = AudioSegment.silent(duration=duration_ms)
    silence.export(file_path, format="mp3")

def combine_audio(files, output_file, silence_duration=500):
    """Combine audio files with silence between segments using ffmpeg.
    
    Args:
        files: List of audio files to combine
        output_file: Final output file
        silence_duration: Silence duration between segments (ms)
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as list_file:
        for f in files:
            list_file.write(f"file '{f}'\n")
        list_path = list_file.name
    
    cmd = [
        'ffmpeg',
        '-f', 'concat',
        '-safe', '0',
        '-i', list_path,
        '-c', 'copy',
        output_file
    ]
    subprocess.run(cmd, check=True)
    os.unlink(list_path)

async def generate_audiobook(data, output_filename="output.mp3"):
    """Generate audiobook from structured data.
    
    Args:
        data: List of [speaker, emotion, text, gender]
        output_filename: Output file name
    
    Returns:
        Path to generated audio file
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        audio_files = []
        tasks = []
        
        # Generate silence file
        silence_file = os.path.join(tmpdir, "silence.mp3")
        create_silence(500, silence_file)
        
        for idx, line in enumerate(data):
            speaker, _, text, gender = line
            
            # Skip empty text
            if not text or not text.strip():
                continue
                
            # Determine voice
            if speaker == "narration":
                voice = VOICE_MAPPING["narration"]
            else:
                voice = VOICE_MAPPING.get(gender if gender in VOICE_MAPPING else "male", VOICE_MAPPING["male"])
            
            # Generate audio for line
            output_file = os.path.join(tmpdir, f"line_{idx}.mp3")
            tasks.append(generate_audio_chunk(text, voice, output_file))
            audio_files.append(output_file)
            audio_files.append(silence_file)  # Add silence after each line
        
        # Run all TTS tasks concurrently
        await asyncio.gather(*tasks)
        
        # Combine all audio segments
        if audio_files:
            # Remove last silence
            audio_files = audio_files[:-1]
            combine_audio(audio_files, output_filename)
        else:
            # Create empty file if no audio generated
            open(output_filename, 'wb').close()
            
    return output_filename

def main(data):
    """Synchronous entry point for audiobook generation.
    
    Args:
        data: Input dialogue data
    
    Returns:
        Path to generated audio file
    """
    return asyncio.run(generate_audiobook(data))

def generate_tts(json_path):
    """Generate TTS for a sample dialogue.
    
    This function is just a placeholder and can be removed or modified as needed.
    """
    # input_data = [
    #     ["narration", None, "The golden divine soul clearly hadn't expected Chen Ping to unleash such a rogue.", None],
    #     ["narration", None, "It froze for a moment before roaring in anger,", None],
    #     ["Barbarian Clan ancestor", "angry", "How dare you! I am the ancestor of the Barbarian Clan, how dare a demon like you defile me!", "male"],
    #     ["Red Cloud Demon Lord", "mocking", "Ancestor?", "male"],
    #     ["narration", None, "Red Cloud Demon Lord scoffed, circling the divine soul before suddenly pointing at a crack in its battle armour and laughing loudly,", None]
    # ]
    with open(json_path, "r",encoding="utf-8") as file:
        data = json.load(file)  # Parses the list of lists
    output_file = main(data)
    print(f"Audiobook generated at: {output_file}")
    
# Example usage:
if __name__ == "__main__":
    generate_tts()
    # You can also call main() with your own data
    # data = [["narration", None