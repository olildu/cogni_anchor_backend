# stt_whisper.py
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Set OPENAI_API_KEY in .env")

client = OpenAI(api_key=OPENAI_API_KEY)

def transcribe_file(path: str, model: str = "gpt-4o-mini-transcribe", response_format: str = "text") -> str:
    with open(path, "rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format=response_format
        )
    try:
        return transcription.text
    except Exception:
        return str(transcription)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("audio_path")
    p.add_argument("--model", default="gpt-4o-mini-transcribe")
    args = p.parse_args()
    print(transcribe_file(args.audio_path, model=args.model))
