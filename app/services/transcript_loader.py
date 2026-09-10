"""
Pulls a transcript for a given YouTube URL.

Primary path: LangChain's YoutubeLoader (backed by youtube-transcript-api).
Fallback path: yt-dlp, which pulls the same auto-caption tracks directly
and tends to survive YouTube-side blocks/rate limits better.

Both paths normalize to the same output shape: a list of segments with
text + start time, so the rest of the pipeline doesn't care which path
was used.
"""

import re
import subprocess
import json
import tempfile
import os
import sys
from dataclasses import dataclass


@dataclass
class TranscriptSegment:
    text: str
    start: float  # seconds


class TranscriptUnavailableError(Exception):
    pass


def extract_video_id(url: str) -> str:
    patterns = [
        r"(?:v=|\/)([0-9A-Za-z_-]{11}).*",
        r"(?:youtu\.be\/)([0-9A-Za-z_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def _load_via_langchain(url: str) -> list[TranscriptSegment]:
    from langchain_community.document_loaders import YoutubeLoader

    loader = YoutubeLoader.from_youtube_url(url, add_video_info=False)
    docs = loader.load()
    if not docs or not docs[0].page_content.strip():
        raise TranscriptUnavailableError("LangChain loader returned empty transcript")

    # YoutubeLoader (without transcript_format=TIMED) returns one blob of
    # text with no per-line timestamps. Treat it as a single segment;
    # the yt-dlp fallback below is what actually gives us timestamps.
    return [TranscriptSegment(text=docs[0].page_content, start=0.0)]


def _load_via_ytdlp(url: str) -> list[TranscriptSegment]:
    video_id = extract_video_id(url)
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_template = os.path.join(tmp_dir, "%(id)s")
        cmd = [
            sys.executable,
            "-m",
            "yt_dlp",
            "--skip-download",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "en",
            "--sub-format", "json3",
            "-o", out_template,
            url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise TranscriptUnavailableError(f"yt-dlp failed: {result.stderr[:500]}")

        candidates = [
            f for f in os.listdir(tmp_dir)
            if f.startswith(video_id) and f.endswith(".json3")
        ]
        if not candidates:
            raise TranscriptUnavailableError("yt-dlp produced no subtitle file")

        with open(os.path.join(tmp_dir, candidates[0]), "r") as f:
            data = json.load(f)

        segments = []
        for event in data.get("events", []):
            if "segs" not in event:
                continue
            text = "".join(seg.get("utf8", "") for seg in event["segs"]).strip()
            if text:
                start = event.get("tStartMs", 0) / 1000.0
                segments.append(TranscriptSegment(text=text, start=start))

        if not segments:
            raise TranscriptUnavailableError("yt-dlp subtitle file had no usable segments")
        return segments


def get_transcript(url: str) -> list[TranscriptSegment]:
    """Try LangChain's loader first, fall back to yt-dlp on failure."""
    try:
        return _load_via_langchain(url)
    except Exception:
        return _load_via_ytdlp(url)
