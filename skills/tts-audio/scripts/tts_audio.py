#!/usr/bin/env python3
"""
tts-audio skill — reusable text-to-speech audio generation.

Currently supports mmx-cli / MiniMax speech synthesis.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


SKILL_DIR = Path(__file__).parent.parent
CONFIG_PATH = Path.home() / ".hermes" / "config" / "tts-audio.json"
DEFAULT_CONFIG_PATH = SKILL_DIR / "config.json"


def _load_json(path):
    if not path.exists():
        return {}
    with open(path) as f:
        return json.load(f)


def load_config():
    """Load user config, falling back to the bundled default config."""
    cfg = _load_json(DEFAULT_CONFIG_PATH)
    cfg.update(_load_json(CONFIG_PATH))
    return cfg


def get_provider(provider=None):
    """Resolve the TTS provider from argument, env, or config."""
    if provider:
        return provider
    env_provider = os.environ.get("TTS_PROVIDER")
    if env_provider:
        return env_provider
    return load_config().get("provider", "mmx-cli")


def is_available(provider=None):
    """Return True when the requested TTS provider can be used."""
    resolved = get_provider(provider)
    if resolved != "mmx-cli":
        return False
    return shutil.which("mmx") is not None


def generate_audio(text, output_dir, voice=None, filename=None, provider=None, timeout=None):
    """
    Generate an MP3 audio file.

    Args:
        text: Text to synthesize.
        output_dir: Directory where the audio file should be written.
        voice: Provider voice name. Defaults to config voice.
        filename: Output filename. Defaults to config filename or audio.mp3.
        provider: TTS provider. Currently only mmx-cli is supported.
        timeout: Command timeout in seconds.

    Returns:
        str path to the generated audio file, or None on failure.
    """
    if not text or not str(text).strip():
        return None

    cfg = load_config()
    resolved_provider = get_provider(provider or cfg.get("provider"))
    if resolved_provider != "mmx-cli":
        print(f"[tts-audio] unsupported provider: {resolved_provider}", file=sys.stderr)
        return None

    if not is_available(resolved_provider):
        print("[tts-audio] mmx command not found", file=sys.stderr)
        return None

    voice = voice or cfg.get("voice", "Chinese (Mandarin)_Warm_Girl")
    filename = filename or cfg.get("filename", "audio.mp3")
    timeout = timeout or int(cfg.get("timeout", 60))
    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp_path = f.name

    cmd = [
        "mmx", "speech", "synthesize",
        "--text", text,
        "--voice", voice,
        "--out", tmp_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0 or not os.path.exists(tmp_path):
            if result.stderr:
                print(f"[tts-audio] mmx failed: {result.stderr.strip()}", file=sys.stderr)
            return None

        dest = output_dir / filename
        shutil.copy2(tmp_path, dest)
        return str(dest)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def main():
    """Minimal standalone smoke entrypoint."""
    cfg = load_config()
    provider = get_provider(cfg.get("provider"))
    print("tts-audio skill")
    print(f"Provider: {provider}")
    print(f"Voice: {cfg.get('voice')}")
    print(f"Available: {is_available(provider)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
