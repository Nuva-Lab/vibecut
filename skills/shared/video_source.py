"""
Video source abstraction for different input types.

Supports:
- Local files
- HTTP/HTTPS URLs
- Google Drive links

Provides a unified interface for skills to work with video sources
regardless of where they're stored.
"""
import re
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import urllib.request


class SourceType(Enum):
    """Supported video source types."""
    LOCAL = "local"
    URL = "url"
    GOOGLE_DRIVE = "google_drive"


@dataclass
class VideoSource:
    """
    Unified video source reference.

    Provides methods to resolve any video source to a local file path
    and to get references suitable for different APIs (like Gemini).
    """
    uri: str
    source_type: SourceType = field(init=False)
    local_path: Optional[Path] = field(default=None, init=False)
    _temp_file: Optional[Path] = field(default=None, init=False, repr=False)

    def __post_init__(self):
        """Auto-detect source type from URI."""
        if self.uri.startswith("https://drive.google.com") or self.uri.startswith("https://docs.google.com"):
            self.source_type = SourceType.GOOGLE_DRIVE
        elif self.uri.startswith("http://") or self.uri.startswith("https://"):
            self.source_type = SourceType.URL
        else:
            self.source_type = SourceType.LOCAL
            self.local_path = Path(self.uri)

    @classmethod
    def from_uri(cls, uri: str) -> "VideoSource":
        """
        Create a VideoSource from any URI.

        Args:
            uri: Local path, URL, or Google Drive link

        Returns:
            VideoSource instance
        """
        return cls(uri=uri)

    def exists(self) -> bool:
        """Check if the source exists (for local files only)."""
        if self.source_type == SourceType.LOCAL:
            return self.local_path.exists() if self.local_path else False
        # For remote sources, we assume they exist
        return True

    def resolve(self, cache_dir: Optional[Path] = None) -> Path:
        """
        Resolve to local file path, downloading if needed.

        Args:
            cache_dir: Directory to cache downloaded files (default: temp dir)

        Returns:
            Path to local video file
        """
        if self.local_path and self.local_path.exists():
            return self.local_path

        if self.source_type == SourceType.LOCAL:
            if not self.local_path or not self.local_path.exists():
                raise FileNotFoundError(f"Video file not found: {self.uri}")
            return self.local_path

        # Download remote source
        if cache_dir is None:
            cache_dir = Path(tempfile.gettempdir()) / "vibecut-cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        if self.source_type == SourceType.GOOGLE_DRIVE:
            self.local_path = self._download_gdrive(cache_dir)
        elif self.source_type == SourceType.URL:
            self.local_path = self._download_url(cache_dir)

        return self.local_path

    def _download_gdrive(self, cache_dir: Path) -> Path:
        """Download from Google Drive."""
        # Extract file ID from various Google Drive URL formats
        patterns = [
            r"/file/d/([a-zA-Z0-9_-]+)",  # /file/d/ID/view
            r"id=([a-zA-Z0-9_-]+)",       # ?id=ID
            r"/d/([a-zA-Z0-9_-]+)",       # /d/ID/
        ]

        file_id = None
        for pattern in patterns:
            match = re.search(pattern, self.uri)
            if match:
                file_id = match.group(1)
                break

        if not file_id:
            raise ValueError(f"Could not extract file ID from Google Drive URL: {self.uri}")

        # Construct direct download URL
        download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

        # Download (this works for files < 100MB; larger files need confirmation handling)
        output_path = cache_dir / f"gdrive_{file_id}.mp4"
        if not output_path.exists():
            print(f"Downloading from Google Drive: {file_id}...")
            urllib.request.urlretrieve(download_url, output_path)
            print(f"Downloaded to: {output_path}")

        return output_path

    def _download_url(self, cache_dir: Path) -> Path:
        """Download from HTTP/HTTPS URL."""
        # Generate filename from URL
        url_hash = abs(hash(self.uri)) % 10**8
        ext = Path(self.uri).suffix or ".mp4"
        output_path = cache_dir / f"url_{url_hash}{ext}"

        if not output_path.exists():
            print(f"Downloading: {self.uri}...")
            urllib.request.urlretrieve(self.uri, output_path)
            print(f"Downloaded to: {output_path}")

        return output_path

    def gemini_reference(self) -> str:
        """
        Get reference for Gemini API.

        Gemini can process Google Drive and public URLs directly,
        avoiding the need to upload large files.

        Returns:
            URL for remote sources, or uploads local file and returns reference
        """
        # Gemini can fetch from Google Drive and public URLs directly
        if self.source_type in (SourceType.GOOGLE_DRIVE, SourceType.URL):
            return self.uri

        # For local files, we need to upload to Gemini
        # Import here to avoid circular dependencies
        from .gemini_client import upload_video
        local_path = self.resolve()
        uploaded = upload_video(str(local_path))
        return uploaded.name

    def __str__(self) -> str:
        return f"VideoSource({self.source_type.value}: {self.uri})"


def resolve_video(uri: str, cache_dir: Optional[Path] = None) -> Path:
    """
    Convenience function to resolve any video URI to a local path.

    Args:
        uri: Local path, URL, or Google Drive link
        cache_dir: Directory to cache downloaded files

    Returns:
        Path to local video file
    """
    return VideoSource.from_uri(uri).resolve(cache_dir)


if __name__ == "__main__":
    # Test with a local file
    import sys
    if len(sys.argv) > 1:
        source = VideoSource.from_uri(sys.argv[1])
        print(f"Source type: {source.source_type.value}")
        print(f"URI: {source.uri}")
        if source.source_type == SourceType.LOCAL:
            print(f"Exists: {source.exists()}")
