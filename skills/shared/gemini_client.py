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


def upload_videos(
    video_paths: list[str],
    wait_for_ready: bool = True,
    parallel: bool = True,
    max_workers: int = 5,
) -> list[types.File]:
    """
    Upload multiple video files to Gemini File API.

    Args:
        video_paths: List of paths to video files
        wait_for_ready: Wait for all files to finish processing
        parallel: Upload in parallel (faster) or sequential
        max_workers: Max parallel uploads (default: 5)

    Returns:
        List of uploaded File objects in same order as input
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    if not video_paths:
        return []

    uploaded_files = [None] * len(video_paths)

    if parallel and len(video_paths) > 1:
        print(f"Uploading {len(video_paths)} files in parallel...")
        with ThreadPoolExecutor(max_workers=min(len(video_paths), max_workers)) as executor:
            futures = {
                executor.submit(client.files.upload, file=path): i
                for i, path in enumerate(video_paths)
            }
            for future in as_completed(futures):
                idx = futures[future]
                uploaded_files[idx] = future.result()
                print(f"  [{idx+1}/{len(video_paths)}] Uploaded: {uploaded_files[idx].name}")
    else:
        print(f"Uploading {len(video_paths)} files sequentially...")
        for i, path in enumerate(video_paths):
            uploaded_files[i] = client.files.upload(file=path)
            print(f"  [{i+1}/{len(video_paths)}] Uploaded: {uploaded_files[i].name}")

    if wait_for_ready:
        print("Waiting for files to process...")
        while True:
            all_ready = True
            for i, f in enumerate(uploaded_files):
                if f.state == types.FileState.PROCESSING:
                    uploaded_files[i] = client.files.get(name=f.name)
                    if uploaded_files[i].state == types.FileState.PROCESSING:
                        all_ready = False
                elif f.state == types.FileState.FAILED:
                    raise RuntimeError(f"File processing failed: {f.name}")

            if all_ready:
                break
            time.sleep(5)

        print(f"All {len(uploaded_files)} files ready")

    return uploaded_files


def analyze_videos_with_context(
    video_files: list[types.File] | list[str],
    prompt: str,
    model: str = DEFAULT_MODEL,
    chunk_metadata: list[dict] = None,
) -> str:
    """
    Analyze multiple videos with global context.

    Useful for: Finding patterns across chunks, understanding full video
    context when individual chunks are too large to upload as single file.

    Args:
        video_files: List of File objects or paths
        prompt: Analysis prompt
        model: Model ID
        chunk_metadata: Optional metadata about each chunk
            [{"chunk_num": 0, "start": 0.0, "end": 180.0, "transcript": "..."}, ...]

    Returns:
        Model response text
    """
    # Upload any paths
    uploaded = []
    for vf in video_files:
        if isinstance(vf, str):
            uploaded.append(upload_video(vf))
        else:
            uploaded.append(vf)

    # Build context-aware prompt
    context_parts = []
    if chunk_metadata:
        context_parts.append("## Video Chunk Context\n\n")
        for i, meta in enumerate(chunk_metadata):
            start = meta.get('start', i * 180)
            end = meta.get('end', start + 180)
            transcript_preview = meta.get('transcript', '')[:200]
            context_parts.append(
                f"**Chunk {meta.get('chunk_num', i)}** "
                f"(time: {start/60:.1f}min - {end/60:.1f}min)\n"
                f"Preview: {transcript_preview}...\n\n"
            )
        context_parts.append("## Analysis Request\n\n")

    full_prompt = "".join(context_parts) + prompt

    # Build contents: [video1, video2, ..., prompt]
    contents = uploaded + [full_prompt]

    response = client.models.generate_content(
        model=model,
        contents=contents,
    )
    return response.text


def analyze_videos_json(
    video_files: list[types.File] | list[str],
    prompt: str,
    model: str = DEFAULT_MODEL,
    chunk_metadata: list[dict] = None,
) -> dict:
    """
    Analyze multiple videos and return structured JSON response.

    Same as analyze_videos_with_context but returns parsed JSON.
    """
    import json
    import re

    # Upload any paths
    uploaded = []
    for vf in video_files:
        if isinstance(vf, str):
            uploaded.append(upload_video(vf))
        else:
            uploaded.append(vf)

    # Build context-aware prompt
    context_parts = []
    if chunk_metadata:
        context_parts.append("## Video Chunk Context\n\n")
        for i, meta in enumerate(chunk_metadata):
            start = meta.get('start', i * 180)
            end = meta.get('end', start + 180)
            transcript_preview = meta.get('transcript', '')[:200]
            context_parts.append(
                f"**Chunk {meta.get('chunk_num', i)}** "
                f"(time: {start/60:.1f}min - {end/60:.1f}min)\n"
                f"Preview: {transcript_preview}...\n\n"
            )
        context_parts.append("## Analysis Request\n\n")

    full_prompt = "".join(context_parts) + prompt

    # Build contents: [video1, video2, ..., prompt]
    contents = uploaded + [full_prompt]

    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    # Parse JSON (handle markdown code blocks)
    text = response.text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        return json.loads(json_match.group(1))
    return json.loads(text)


# ============================================================================
# V2 Pipeline Functions - Speaker Detection, Narrative Ordering, Verification
# ============================================================================

SPEAKER_DETECTION_PROMPT = """
Analyze this video to identify all speakers and detect any "leaked footage" that should be filtered.

## TASK 1: Speaker Identification

Identify the MAIN SPEAKER (the person creating content for the audience):
- Who is talking directly to camera / audience?
- How do they introduce themselves? Listen carefully for their name.
- What is their role/background based on what they say?

Also identify OTHER PARTICIPANTS (helpers, camera operators, interviewers):
- Do they speak? What do they say?
- Are they visible on camera?

## TASK 2: Leaked Footage Detection

Find segments that are NOT meant for the final video:
- Behind-the-scenes coordination: "Is that good?", "Let me try again", "Wait, hold on"
- Meta-commentary about recording: "I should note this for editing", "得记一下"
- Q&A setup: Discussion ABOUT the content, not the content itself
- Script iteration: "What if I say it like this...", "觉得好嘛？"

For each leaked segment, note:
- Approximate start/end timestamps (in seconds from chunk start)
- What type of leaked content it is
- Evidence (quote or description)

## OUTPUT FORMAT (JSON)

{
  "main_speaker": {
    "name": "Full Name as they say it (e.g., Xiaoyin Qu, not phonetic like 'Shao Yin')",
    "name_confidence": 0.95,
    "role": "Their stated role/background",
    "visual_description": "Brief description",
    "introduction_quote": "How they introduce themselves"
  },
  "other_participants": [
    {
      "role": "camera_operator",
      "speaks": true,
      "language": "Chinese",
      "visible": false,
      "description": "Helps with script, gives feedback"
    }
  ],
  "leaked_segments": [
    {
      "start_sec": 0,
      "end_sec": 45,
      "type": "coordination",
      "language": "Chinese",
      "evidence": "觉得好嘛？ - Asking for feedback on take"
    }
  ],
  "chunk_analysis": {
    "has_usable_content": true,
    "main_language": "English",
    "quality_notes": "Good lighting, clear audio"
  }
}
"""


def detect_speakers(
    video_files: list[str],
    transcript: str = None,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Identify main speaker vs others, detect leaked footage segments.

    Args:
        video_files: List of video chunk paths (will sample 3 representative chunks)
        transcript: Optional full transcript to help with analysis
        model: Gemini model to use

    Returns:
        {
            "main_speaker": {"name": "...", "role": "...", ...},
            "other_participants": [...],
            "leaked_segments": [{"chunk_num": 0, "start_sec": ..., ...}, ...]
        }
    """
    import json
    import re

    # Sample representative chunks (first, middle, last)
    num_chunks = len(video_files)
    if num_chunks <= 3:
        sample_indices = list(range(num_chunks))
    else:
        sample_indices = [0, num_chunks // 2, num_chunks - 1]

    sample_paths = [video_files[i] for i in sample_indices]

    # Build prompt with transcript context if provided
    prompt = SPEAKER_DETECTION_PROMPT
    if transcript:
        prompt = f"""
## Transcript Context (to help with analysis)

{transcript[:5000]}...

{SPEAKER_DETECTION_PROMPT}
"""

    # Upload and analyze
    print(f"Analyzing {len(sample_paths)} representative chunks for speaker detection...")
    uploaded = upload_videos(sample_paths)

    contents = uploaded + [prompt]
    response = client.models.generate_content(
        model=model,
        contents=contents,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    # Parse response
    text = response.text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        result = json.loads(json_match.group(1))
    else:
        result = json.loads(text)

    # Map chunk indices back to original chunk numbers
    if "leaked_segments" in result:
        for seg in result["leaked_segments"]:
            # The analysis was on sample chunks, map back
            if "chunk_in_sample" in seg:
                seg["chunk_num"] = sample_indices[seg["chunk_in_sample"]]
            elif not "chunk_num" in seg:
                seg["chunk_num"] = 0  # Default to first chunk if not specified

    return result


NARRATIVE_ORDERING_PROMPT = """
You are a video editor for social media. Given these golden segments, propose the best narrative order.

## GOAL
Create a compelling short video (60-120 seconds) that:
1. Grabs attention immediately (hook)
2. Maintains engagement
3. Ends with a memorable takeaway

## SOCIAL MEDIA SHORT STRUCTURE

1. **HOOK (0-15s)**: Most attention-grabbing segment FIRST
   - Strong credibility: "I've raised tens of millions from..."
   - Provocative claim: "VCs are the most hypocritical animals"
   - Clear promise: "crash course on fundraising"
   - The BEST hook often comes from LATER in the original video!

2. **CONTEXT (15-30s)**: Set up problem/topic
   - Why should viewer care?
   - What question are we answering?

3. **BODY (30-60s)**: Key insights
   - 1-3 main points
   - Specific examples or stories

4. **PAYOFF (60-90s)**: Memorable takeaway
   - Actionable advice
   - Quotable conclusion
   - Leave them thinking

## SEGMENTS AVAILABLE

{segments_json}

## OUTPUT FORMAT (JSON)

{{
  "proposed_order": [3, 1, 2],  // Segment IDs in your recommended order
  "rationale": "Why this order works best for social media...",
  "segments": [
    {{
      "position": 1,
      "segment_id": 3,
      "role": "hook",
      "why_here": "Establishes authority immediately"
    }},
    {{
      "position": 2,
      "segment_id": 1,
      "role": "body",
      "why_here": "Provides key insight after hook"
    }}
  ],
  "total_duration_sec": 85,
  "alternatives": [
    {{
      "order": [1, 3, 2],
      "rationale": "Alternative if audience already knows the speaker"
    }}
  ],
  "segments_to_skip": [
    {{
      "segment_id": 4,
      "reason": "Too similar to segment 1, redundant"
    }}
  ]
}}

Be opinionated! The best hook is often NOT the chronologically first segment.
"""


def suggest_narrative_order(
    segments: list[dict],
    style: str = "social_media_short",
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Suggest optimal narrative ordering for segments.

    Args:
        segments: List of segment dicts with id, start_sec, end_sec, topic, score, text
        style: "social_media_short" (default), "mini_documentary", "highlights_reel"
        model: Gemini model to use

    Returns:
        {
            "proposed_order": [segment_ids],
            "rationale": "...",
            "segments": [...],
            "alternatives": [...]
        }
    """
    import json
    import re

    # Format segments for prompt
    segments_json = json.dumps(segments, indent=2, ensure_ascii=False)
    prompt = NARRATIVE_ORDERING_PROMPT.format(segments_json=segments_json)

    # Note: This is text-only analysis, no video upload needed
    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    text = response.text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        return json.loads(json_match.group(1))
    return json.loads(text)


VERIFICATION_PROMPT = """
You are reviewing a final edited video. Check for quality issues.

## EXPECTED STRUCTURE
{expected_structure}

## THINGS TO CHECK

1. **AUDIO CONTINUITY**
   - Any mid-sentence cuts? (words cut off)
   - Jarring audio transitions? (sudden volume changes)
   - Audio sync issues? (voice doesn't match lips)

2. **VISUAL CONTINUITY**
   - Awkward visual jumps? (speaker position changes suddenly)
   - Lighting/color inconsistencies between segments?
   - Any visible splice points?

3. **NARRATIVE FLOW**
   - Does the sequence make logical sense?
   - Are there missing transitions that feel abrupt?
   - Does the hook work as a hook?
   - Does the ending feel complete?

4. **SPEAKER CONSISTENCY**
   - Is it the same speaker throughout?
   - Is the speaker clearly visible?
   - Any frames where speaker is out of focus or off-screen?

## OUTPUT FORMAT (JSON)

{{
  "passed": true,
  "overall_quality": 8,
  "issues": [
    {{
      "timestamp_sec": 25,
      "type": "audio_cut",
      "severity": "minor",
      "description": "Slight audio pop at segment transition"
    }}
  ],
  "suggestions": [
    "Add 0.3s fade between segments 1 and 2",
    "Consider trimming 2 seconds from segment 3 intro"
  ],
  "narrative_assessment": {{
    "hook_effectiveness": 9,
    "flow_smoothness": 7,
    "ending_strength": 8
  }}
}}
"""


def verify_composition(
    video_path: str,
    expected_structure: dict,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Verify final video quality and coherence.

    Args:
        video_path: Path to the composed final video
        expected_structure: Dict describing expected segments, order, duration
        model: Gemini model to use

    Returns:
        {
            "passed": True/False,
            "issues": [...],
            "suggestions": [...],
            "narrative_assessment": {...}
        }
    """
    import json
    import re

    # Format expected structure
    structure_str = json.dumps(expected_structure, indent=2, ensure_ascii=False)
    prompt = VERIFICATION_PROMPT.format(expected_structure=structure_str)

    # Upload video and analyze
    print(f"Uploading {video_path} for verification...")
    uploaded = upload_video(video_path)

    response = client.models.generate_content(
        model=model,
        contents=[uploaded, prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
        ),
    )

    text = response.text
    json_match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
    if json_match:
        return json.loads(json_match.group(1))
    return json.loads(text)
