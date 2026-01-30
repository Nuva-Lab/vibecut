#!/usr/bin/env python3
"""
Generate speech using a cloned voice embedding.
"""
import os
import sys
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent.parent / ".env")

FAL_KEY = os.getenv("FAL_KEY")
if not FAL_KEY:
    raise ValueError("FAL_KEY not found in .env")


def upload_embedding(file_path: str) -> str:
    """Upload embedding file to fal.ai storage."""
    file_path = Path(file_path)
    content_type = "application/octet-stream"

    response = requests.post(
        "https://rest.alpha.fal.ai/storage/upload/initiate",
        headers={"Authorization": f"Key {FAL_KEY}"},
        json={
            "file_name": file_path.name,
            "content_type": content_type
        }
    )
    response.raise_for_status()
    upload_data = response.json()

    with open(file_path, "rb") as f:
        upload_response = requests.put(
            upload_data["upload_url"],
            data=f,
            headers={"Content-Type": content_type}
        )
        upload_response.raise_for_status()

    return upload_data["file_url"]


def generate_speech(
    embedding_path: str,
    text: str,
    output_path: str = None,
    reference_text: str = None,
    style_prompt: str = None
) -> str:
    """
    Generate speech using a cloned voice.

    Args:
        embedding_path: Path to .safetensors embedding or URL
        text: Text to speak
        output_path: Optional output path for audio
        reference_text: Optional reference transcript (from cloning)

    Returns:
        Path to generated audio file
    """
    embedding_path = Path(embedding_path) if not embedding_path.startswith("http") else None

    # Get embedding URL
    if embedding_path and embedding_path.exists():
        print(f"Uploading embedding: {embedding_path.name}")
        embedding_url = upload_embedding(str(embedding_path))
    else:
        embedding_url = str(embedding_path) if embedding_path else embedding_path

    print(f"Generating speech for: \"{text[:50]}...\"" if len(text) > 50 else f"Generating speech for: \"{text}\"")

    # Build request
    request_data = {
        "text": text,
        "speaker_voice_embedding_file_url": embedding_url,
        "max_new_tokens": 8192,  # Allow long audio generation (up to ~10 min)
    }
    if reference_text:
        request_data["reference_text"] = reference_text
    if style_prompt:
        request_data["prompt"] = style_prompt  # e.g., "Thoughtful and slow paced"

    # Call TTS API
    response = requests.post(
        "https://queue.fal.run/fal-ai/qwen-3-tts/text-to-speech/1.7b",
        headers={
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        },
        json=request_data
    )
    response.raise_for_status()

    queue_data = response.json()
    request_id = queue_data.get("request_id")
    status_url = queue_data.get("status_url")
    response_url = queue_data.get("response_url")

    if not request_id:
        result = queue_data
    else:
        # Poll for result
        import time

        while True:
            status_response = requests.get(
                status_url,
                headers={"Authorization": f"Key {FAL_KEY}"}
            )
            status_data = status_response.json()
            status = status_data.get("status")

            if status == "COMPLETED":
                result_response = requests.get(
                    response_url,
                    headers={"Authorization": f"Key {FAL_KEY}"}
                )
                result = result_response.json()
                break
            elif status == "FAILED":
                raise RuntimeError(f"TTS failed: {status_data}")
            else:
                print(f"Status: {status}...")
                time.sleep(3)

    # Get audio URL
    audio_data = result.get("audio", {})
    audio_url = audio_data.get("url")

    if not audio_url:
        raise RuntimeError(f"No audio URL in response: {result}")

    # Download audio
    if output_path is None:
        output_dir = Path(__file__).parent.parent.parent / "assets" / "outputs" / "audio"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "generated_speech.wav"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Downloading audio...")
    audio_response = requests.get(audio_url)
    audio_response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(audio_response.content)

    print(f"Audio saved to: {output_path}")
    return str(output_path)


def main():
    if len(sys.argv) < 3:
        print("Usage: python speak.py <embedding.safetensors> \"Text to speak\" [output.wav] [--style \"prompt\"]")
        print("")
        print("Example:")
        print("  python speak.py joyce_embedding.safetensors \"Hello, this is a test\"")
        print("  python speak.py joyce_embedding.safetensors \"大家好\" output.wav")
        print("  python speak.py joyce.safetensors \"Text\" out.wav --style \"Slow and thoughtful\"")
        sys.exit(1)

    embedding_path = sys.argv[1]
    text = sys.argv[2]

    # Parse remaining args
    output_path = None
    style_prompt = None
    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--style" and i + 1 < len(sys.argv):
            style_prompt = sys.argv[i + 1]
            i += 2
        else:
            output_path = sys.argv[i]
            i += 1

    result = generate_speech(embedding_path, text, output_path, style_prompt=style_prompt)
    print(f"\nGenerated: {result}")


if __name__ == "__main__":
    main()
