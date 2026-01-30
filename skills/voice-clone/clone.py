#!/usr/bin/env python3
"""
Clone a voice using qwen3-tts on fal.ai.
Creates a speaker embedding that can be reused for TTS.
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


def upload_to_fal(file_path: str) -> str:
    """Upload a file to fal.ai storage and return the URL."""
    file_path = Path(file_path)
    content_type = "audio/wav" if file_path.suffix == ".wav" else "audio/mpeg"

    # Get upload URL
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

    # Upload file
    with open(file_path, "rb") as f:
        upload_response = requests.put(
            upload_data["upload_url"],
            data=f,
            headers={"Content-Type": content_type}
        )
        upload_response.raise_for_status()

    return upload_data["file_url"]


def clone_voice(audio_path: str, transcript: str = None, output_dir: str = None) -> dict:
    """
    Clone a voice from an audio sample.

    Args:
        audio_path: Path to audio sample (10-30s of clear speech)
        transcript: Optional transcript of the audio (improves quality)
        output_dir: Directory to save embedding

    Returns:
        Dict with embedding URL and local path
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    print(f"Cloning voice from: {audio_path.name}")

    # Upload audio to fal storage
    print("Uploading audio to fal.ai...")
    audio_url = upload_to_fal(str(audio_path))
    print(f"Uploaded: {audio_url}")

    # Build request
    request_data = {"audio_url": audio_url}
    if transcript:
        request_data["reference_text"] = transcript

    # Call clone API
    print("Cloning voice (this may take a minute)...")
    response = requests.post(
        "https://queue.fal.run/fal-ai/qwen-3-tts/clone-voice/1.7b",
        headers={
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        },
        json=request_data
    )
    response.raise_for_status()

    # Get queue info
    queue_data = response.json()
    request_id = queue_data.get("request_id")
    status_url = queue_data.get("status_url")
    response_url = queue_data.get("response_url")

    if not request_id:
        # Synchronous response
        result = queue_data
    else:
        # Poll for result using provided URLs
        import time

        while True:
            status_response = requests.get(
                status_url,
                headers={"Authorization": f"Key {FAL_KEY}"}
            )
            status_data = status_response.json()
            status = status_data.get("status")

            if status == "COMPLETED":
                # Get result
                result_response = requests.get(
                    response_url,
                    headers={"Authorization": f"Key {FAL_KEY}"}
                )
                result = result_response.json()
                break
            elif status == "FAILED":
                raise RuntimeError(f"Voice cloning failed: {status_data}")
            else:
                print(f"Status: {status}...")
                time.sleep(3)

    # Extract embedding info
    embedding = result.get("speaker_embedding", {})
    embedding_url = embedding.get("url")

    if not embedding_url:
        raise RuntimeError(f"No embedding URL in response: {result}")

    # Download and save embedding locally
    if output_dir is None:
        output_dir = Path(__file__).parent.parent.parent / "assets" / "outputs" / "voice_embeddings"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    embedding_path = output_dir / f"{audio_path.stem}_embedding.safetensors"

    print(f"Downloading embedding...")
    emb_response = requests.get(embedding_url)
    emb_response.raise_for_status()

    with open(embedding_path, "wb") as f:
        f.write(emb_response.content)

    print(f"Voice cloned successfully!")
    print(f"Embedding saved to: {embedding_path}")

    # Save metadata
    metadata = {
        "source_audio": str(audio_path),
        "transcript": transcript,
        "embedding_url": embedding_url,
        "embedding_path": str(embedding_path)
    }
    metadata_path = output_dir / f"{audio_path.stem}_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    return {
        "embedding_url": embedding_url,
        "embedding_path": str(embedding_path),
        "metadata_path": str(metadata_path)
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python clone.py <audio_sample.wav> [--transcript 'text']")
        print("")
        print("Example:")
        print("  python clone.py voice_sample.wav")
        print("  python clone.py voice_sample.wav --transcript '大家好，这是我的声音'")
        sys.exit(1)

    audio_path = sys.argv[1]

    # Parse transcript
    transcript = None
    if "--transcript" in sys.argv:
        idx = sys.argv.index("--transcript")
        if idx + 1 < len(sys.argv):
            transcript = sys.argv[idx + 1]

    result = clone_voice(audio_path, transcript)
    print(f"\nResult: {json.dumps(result, indent=2)}")


if __name__ == "__main__":
    main()
