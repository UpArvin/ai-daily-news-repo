---
name: tts-audio
version: 0.1.0
description: Text-to-speech audio generation skill for Hermes workflows. Generates MP3 voice summaries from text, currently backed by mmx-cli / MiniMax speech synthesis.
category: productivity
trigger_keywords: []
dependencies:
  - mmx-cli（当前唯一支持的 TTS provider）
---

# TTS Audio Skill

Reusable text-to-speech helper for skills that need audio summaries.

## Interface

```python
from tts_audio import is_available, generate_audio

if is_available("mmx-cli"):
    mp3_path = generate_audio(
        text="今日摘要文本",
        output_dir="/tmp/output",
        voice="Chinese (Mandarin)_Warm_Girl",
        filename="audio.mp3",
    )
```

### `is_available(provider=None) -> bool`

Returns whether the requested TTS provider is available. If `provider` is omitted, it reads `TTS_PROVIDER`, then `~/.hermes/config/tts-audio.json`, then defaults to `mmx-cli`.

### `generate_audio(text, output_dir, voice=None, filename="audio.mp3", provider=None, timeout=None) -> str | None`

Generates an MP3 file and returns its path. Returns `None` on failure.

## Configuration

Default config lives in `config.json`. User overrides may be placed at:

```text
~/.hermes/config/tts-audio.json
```

Current provider support:

- `mmx-cli`: calls `mmx speech synthesize`

TTS does not read or require `MMX_TOKEN_PLAN_KEY` directly. It only requires the local `mmx` command to be installed and already authenticated for speech synthesis.
