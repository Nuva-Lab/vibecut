"""
Shared Gemini API client for video analysis.
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# Initialize client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

# Default model for video understanding
DEFAULT_MODEL = "gemini-3-pro-preview"


def upload_video(video_path: str, wait_for_ready: bool = True) -> types.File:
    """
    Upload a video file to Gemini File API.

    Args:
        video_path: Path to the video file
        wait_for_ready: Wait for file to finish processing

    Returns:
        Uploaded file object that can be used in generate_content
    """
    import time

    print(f"Uploading {video_path}...")
    uploaded = client.files.upload(file=video_path)
    print(f"Uploaded: {uploaded.name} ({uploaded.state})")

    if wait_for_ready:
        while uploaded.state == types.FileState.PROCESSING:
            print("Waiting for file to process...")
            time.sleep(5)
            uploaded = client.files.get(name=uploaded.name)

        if uploaded.state == types.FileState.FAILED:
            raise RuntimeError(f"File processing failed: {uploaded.name}")

        print(f"File ready: {uploaded.state}")

    return uploaded


def analyze_video(
    video_file: types.File | str,
    prompt: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Analyze video content using Gemini.

    Args:
        video_file: Either an uploaded File object or path to upload
        prompt: Analysis prompt
        model: Model ID to use

    Returns:
        Model response text
    """
    # Upload if path string provided
    if isinstance(video_file, str):
        video_file = upload_video(video_file)

    response = client.models.generate_content(
        model=model,
        contents=[video_file, prompt],
    )
    return response.text


def analyze_video_json(
    video_file: types.File | str,
    prompt: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Analyze video and return structured JSON response.

    Args:
        video_file: Either an uploaded File object or path to upload
        prompt: Analysis prompt (should request JSON output)
        model: Model ID to use

    Returns:
        Parsed JSON response
    """
    import json

    # Upload if path string provided
    if isinstance(video_file, str):
        video_file = upload_video(video_file)

    response = client.models.generate_content(
        model=model,
        contents=[video_file, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )
    return json.loads(response.text)
