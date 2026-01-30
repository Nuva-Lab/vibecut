"""
Centralized configuration loader with validation.

Provides graceful degradation when optional API keys are missing,
with helpful error messages guiding users to set up required services.
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Find project root and load .env
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")


class ConfigError(Exception):
    """Raised when required configuration is missing."""
    pass


class Config:
    """
    Application configuration with feature flags.

    Attributes:
        google_api_key: Google AI API key for video understanding
        fal_key: fal.ai API key for voice cloning and audio enhancement
        output_dir: Directory for generated outputs
        can_analyze_video: Whether video analysis features are available
        can_clone_voice: Whether voice cloning features are available
        can_enhance_audio: Whether audio enhancement features are available
    """

    def __init__(self):
        # Load from environment
        self.google_api_key: Optional[str] = os.getenv("GOOGLE_API_KEY")
        self.fal_key: Optional[str] = os.getenv("FAL_KEY")
        self.output_dir: Path = Path(os.getenv("OUTPUT_DIR", "./assets/outputs"))

        # Set feature flags based on available keys
        self.can_analyze_video: bool = bool(self.google_api_key)
        self.can_clone_voice: bool = bool(self.fal_key)
        self.can_enhance_audio: bool = bool(self.fal_key)

    def require(self, feature: str) -> None:
        """
        Ensure a required feature is available.

        Args:
            feature: Feature name ('video_analysis', 'voice_cloning', 'audio_enhancement')

        Raises:
            ConfigError: If the required API key is not configured
        """
        FEATURE_REQUIREMENTS = {
            "video_analysis": ("GOOGLE_API_KEY", self.can_analyze_video,
                             "https://aistudio.google.com/app/apikey"),
            "voice_cloning": ("FAL_KEY", self.can_clone_voice,
                            "https://fal.ai/dashboard/keys"),
            "audio_enhancement": ("FAL_KEY", self.can_enhance_audio,
                                "https://fal.ai/dashboard/keys"),
        }

        if feature not in FEATURE_REQUIREMENTS:
            raise ValueError(f"Unknown feature: {feature}")

        key_name, available, signup_url = FEATURE_REQUIREMENTS[feature]

        if not available:
            raise ConfigError(
                f"\n{'='*60}\n"
                f"Feature '{feature}' requires {key_name}\n"
                f"{'='*60}\n\n"
                f"To enable this feature:\n"
                f"  1. Get your API key at: {signup_url}\n"
                f"  2. Add it to your .env file:\n"
                f"     {key_name}=your_key_here\n"
                f"\n"
                f"See .env.example for the full configuration template.\n"
            )

    def check_all(self) -> dict[str, bool]:
        """
        Check which features are available.

        Returns:
            Dictionary mapping feature names to availability status
        """
        return {
            "video_analysis": self.can_analyze_video,
            "voice_cloning": self.can_clone_voice,
            "audio_enhancement": self.can_enhance_audio,
        }

    def print_status(self) -> None:
        """Print configuration status to console."""
        print("\nvibecut Configuration Status")
        print("=" * 40)

        features = self.check_all()
        for feature, available in features.items():
            status = "✓ Ready" if available else "✗ Not configured"
            print(f"  {feature:20} {status}")

        print("=" * 40)

        if not all(features.values()):
            print("\nSome features are not configured.")
            print("See .env.example for setup instructions.")
        print()


# Global config instance - use this in skills
config = Config()


# Convenience functions
def require_video_analysis():
    """Ensure video analysis is available."""
    config.require("video_analysis")


def require_voice_cloning():
    """Ensure voice cloning is available."""
    config.require("voice_cloning")


def require_audio_enhancement():
    """Ensure audio enhancement is available."""
    config.require("audio_enhancement")


if __name__ == "__main__":
    # Print status when run directly
    config.print_status()
