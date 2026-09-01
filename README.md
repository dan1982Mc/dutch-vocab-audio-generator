# Dutch Vocabulary Audio Generator

A small local Python tool that turns a Dutch-English vocabulary JSON file into one MP3 lesson.

## What it does

For every vocabulary item it generates:

1. Dutch word — Dutch voice
2. Configurable pause
3. English translation — English voice
4. Configurable pause

The Dutch and English speech are generated as separate segments, so each language uses its own voice. This avoids relying on custom SSML support.

## Requirements

- Windows, macOS, or Linux
- Python 3.10+
- Internet connection while generating audio (edge-tts uses Microsoft's online speech service)
- FFmpeg installed and available on PATH

## Install

Open a terminal in this repository:

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Then:

```bash
pip install -r requirements.txt
```

Install FFmpeg separately and make sure `ffmpeg` works from the terminal:

```bash
ffmpeg -version
```

## Vocabulary format

Edit `data/words.json`:

```json
[
  {
    "dutch": "omringd",
    "english": "surrounded"
  },
  {
    "dutch": "verwaand",
    "english": "arrogant"
  }
]
```

Optional example sentence:

```json
{
  "dutch": "omringd",
  "english": "surrounded",
  "sentence_nl": "Hij stond omringd door vrienden."
}
```

## Generate audio

Default command:

```bash
python generate_audio.py
```

The result is:

`output/vocabulary.mp3`

Generate only the first 10 words for a quick test:

```bash
python generate_audio.py --limit 10
```

Use another word file:

```bash
python generate_audio.py --words data/my_pack.json
```

Use another output filename:

```bash
python generate_audio.py --output output/lesson_01.mp3
```

## Configure the lesson

Edit `config.json`.

Important settings:

- `dutch_voice`: Dutch TTS voice
- `english_voice`: English TTS voice
- `dutch_rate`: Dutch speech speed
- `english_rate`: English speech speed
- `pause_after_dutch_ms`: recall time before English translation
- `pause_after_english_ms`: time before the next word
- `repeat_each_word`: repeat each word N times
- `include_example_sentence`: add an optional Dutch example sentence

A good starting configuration is:

- Dutch: 5% slower than normal
- English: 5% slower than normal
- Dutch → English pause: 2 seconds
- After English: 3 seconds
- Repeat: 1

## Important

The generator requires an internet connection while creating audio. The generated MP3 can then be listened to offline.

Generated audio is ignored by Git so the repository stays small. Keep your vocabulary JSON files in `data/` and generate MP3s locally.

## Future improvements

Possible next steps:

- automatically select new/due/weak words from the vocabulary trainer
- 10/20/30-minute lesson presets
- spaced repetition ordering
- multiple lesson modes (Vocabulary, Recall, Example Sentences)
- automatic word-pack selection
- a simple Windows `.bat` launcher
- optional audio generation directly from the vocabulary trainer
