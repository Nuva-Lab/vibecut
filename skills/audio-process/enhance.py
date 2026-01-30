#!/usr/bin/env python3
"""
AI-powered voice enhancement using fal.ai models.
"""
import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment
load_dotenv(Path(__file__).parent.parent.parent / ".env")

FAL_KEY = os.getenv("FAL_KEY")
if not FAL_KEY:
    raise ValueError("FAL_KEY not found in .env")


def upload_audio(file_path: str) -> str:
    """Upload audio to fal.ai storage."""
    file_path = Path(file_path)
    content_type = "audio/wav" if file_path.suffix == ".wav" else "audio/mpeg"

    response = requests.post(
        "https://rest.alpha.fal.ai/storage/upload/initiate",
        headers={"Authorization": f"Key {FAL_KEY}"},
        json={"file_name": file_path.name, "content_type": content_type}
    )
    response.raise_for_status()
    upload_data = response.json()

    with open(file_path, "rb") as f:
        requests.put(
            upload_data["upload_url"],
            data=f,
            headers={"Content-Type": content_type}
        ).raise_for_status()

    return upload_data["file_url"]


def enhance_voice(
    input_path: str,
    output_path: str = None,
    model: str = "deepfilternet3"
) -> str:
    """
    Enhance voice audio using AI models.

    Args:
        input_path: Path to input audio
        output_path: Path for output
        model: Model to use ("deepfilternet3" or "nova-sr")

    Returns:
        Path to enhanced audio
    """
    input_path = Path(input_path)
    if not input_path.exists():
        raise FileNotFoundError(f"Input not found: {input_path}")

    if output_path is None:
        output_path = input_path.parent / f"{input_path.stem}_enhanced{input_path.suffix}"
    else:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Model endpoints
    endpoints = {
        "deepfilternet3": "fal-ai/deepfilternet3",
        "nova-sr": "fal-ai/nova-sr"
    }

    if model not in endpoints:
        raise ValueError(f"Unknown model: {model}. Use: {list(endpoints.keys())}")

    print(f"Enhancing: {input_path.name}")
    print(f"Model: {model}")

    # Upload audio
    print("Uploading audio...")
    audio_url = upload_audio(str(input_path))
    print(f"Uploaded: {audio_url}")

    # Call enhancement API
    print("Processing (AI enhancement)...")
    response = requests.post(
        f"https://queue.fal.run/{endpoints[model]}",
        headers={
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        },
        json={"audio_url": audio_url}
    )
    response.raise_for_status()

    queue_data = response.json()
    request_id = queue_data.get("request_id")
    status_url = queue_data.get("status_url")
    response_url = queue_data.get("response_url")

    if not request_id:
        result = queue_data
    else:
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
                raise RuntimeError(f"Enhancement failed: {status_data}")
            else:
                print(f"Status: {status}...")
                time.sleep(3)

    # Get output audio URL (handle different response formats)
    audio_data = result.get("audio") or result.get("audio_file", {})
    audio_out_url = audio_data.get("url")

    if not audio_out_url:
        raise RuntimeError(f"No audio URL in response: {result}")

    # Download enhanced audio
    print("Downloading enhanced audio...")
    audio_response = requests.get(audio_out_url)
    audio_response.raise_for_status()

    with open(output_path, "wb") as f:
        f.write(audio_response.content)

    print(f"Enhanced audio: {output_path}")
    return str(output_path)


def main():
    if len(sys.argv) < 2:
        print("Usage: python enhance.py <input.wav> [output.wav] [--model deepfilternet3|nova-sr]")
        print("")
        print("Models:")
        print("  deepfilternet3  Remove background noise + upsample to 48kHz (default)")
        print("  nova-sr         Enhance muffled speech to crystal-clear 48kHz")
        print("")
        print("Example:")
        print("  python enhance.py voice.wav voice_enhanced.wav")
        print("  python enhance.py voice.wav --model nova-sr")
        sys.exit(1)

    input_path = sys.argv[1]

    # Parse output path
    output_path = None
    for arg in sys.argv[2:]:
        if not arg.startswith("--") and (arg.endswith(".wav") or arg.endswith(".mp3")):
            output_path = arg
            break

    # Parse model
    model = "deepfilternet3"
    if "--model" in sys.argv:
        idx = sys.argv.index("--model")
        if idx + 1 < len(sys.argv):
            model = sys.argv[idx + 1]

    enhance_voice(input_path, output_path, model)


if __name__ == "__main__":
    main()
