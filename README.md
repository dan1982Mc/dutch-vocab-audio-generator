# Dutch Vocabulary Audio Generator

A small local Python tool that turns a Dutch-English vocabulary JSON file into one MP3 learning lesson.

The intended use is Dutch B2 vocabulary study while walking, commuting, or doing other activities. Dutch and English are spoken by separate voices, and pauses are inserted to support recall.

## Current audio lesson

The generator currently follows this structure.

### Phase 1 — New-word teaching

For each new word:

1. **Dutch word** — Dutch voice
2. **2.5 second pause** — think about the meaning
3. **English translation** — English voice
4. Short pause
5. **Dutch example sentence** — Dutch voice
6. **English translation of the sentence** — English voice
7. **Short memory connector** — English voice
8. Pause
9. **Dutch word again** — Dutch voice
10. **English translation again** — English voice

The configuration controls the exact pauses and whether example sentences and memory connectors are included.

### Phase 2 — Recall review

After every block of 5 new words:

1. Dutch word
2. **4 second pause**
3. English translation

This is the active-recall part of the lesson.

### Phase 3 — Final review

After all words have been taught:

1. Dutch word
2. **3 second pause**
3. English translation
4. Dutch example sentence

This gives a second full pass through the vocabulary.

## Vocabulary JSON format

The recommended input contains five fields:

```json
[
  {
    "dutch": "omringd",
    "english": "surrounded",
    "sentence_nl": "Hij stond tijdens het feest omringd door zijn beste vrienden.",
    "sentence_en": "During the party, he was surrounded by his best friends.",
    "memory": "Think around — imagine people standing all around you."
  }
]
```

Required:

- `dutch`
- `english`

Used by the current full lesson:

- `sentence_nl`
- `sentence_en`
- `memory`

For the best result, provide all five fields for every word.

## What each field is for

`dutch` — the exact Dutch word or expression to learn.

`english` — the natural English meaning.

`sentence_nl` — one short, natural B1-B2 Dutch example using the target word.

`sentence_en` — the natural English translation of that complete sentence.

`memory` — a short memory trick or connector. It should create an association, image, sound connection, or memorable situation. It should not simply repeat the definition.

## Requirements

- Windows, macOS, or Linux
- Python 3.10+
- Internet connection while generating audio (`edge-tts` uses Microsoft's online speech service)
- FFmpeg installed and available on PATH

## Installation

### 1. Download the repository

Clone it with Git, or use **Code → Download ZIP** on GitHub and extract it.

### 2. Create a Python virtual environment

Open a terminal in the repository folder:

```bash
python -m venv .venv
```

Activate it.

**Windows:**

```bash
.venv\Scripts\activate
```

**macOS/Linux:**

```bash
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

On Windows with WinGet:

```bash
winget install Gyan.FFmpeg
```

Then open a new terminal and check:

```bash
ffmpeg -version
```

FFmpeg must work from the command line before generating an MP3.

## Generate a lesson

Put your vocabulary into:

`data/words.json`

Then run:

```bash
python generate_audio.py
```

The generated file is:

`output/vocabulary.mp3`

### Windows shortcut

After the virtual environment and dependencies are installed, you can double-click:

`generate_audio.bat`

The batch file runs the generator using the repository's `.venv` Python environment.

## Useful commands

Generate only the first 5 words for testing:

```bash
python generate_audio.py --limit 5
```

Use another vocabulary file:

```bash
python generate_audio.py --words data/my_pack.json
```

Use another output filename:

```bash
python generate_audio.py --output output/lesson_01.mp3
```

## Configure the lesson

Edit `config.json`.

Current default voices:

```json
"dutch_voice": "nl-NL-ColetteNeural",
"english_voice": "en-US-JennyNeural"
```

Current default speeds:

```json
"dutch_rate": "-5%",
"english_rate": "-5%"
```

The most important lesson settings are:

```json
"lesson": {
  "new_word": {
    "pause_after_dutch_ms": 2500,
    "pause_after_english_ms": 1000,
    "pause_before_sentence_ms": 1000,
    "pause_after_sentence_nl_ms": 1500,
    "pause_after_sentence_en_ms": 1500,
    "pause_before_memory_ms": 1000,
    "pause_after_memory_ms": 2500,
    "repeat_word_after_memory": true
  },
  "review": {
    "words_per_block": 5,
    "pause_after_dutch_ms": 4000,
    "pause_after_english_ms": 1500
  },
  "final_review": {
    "pause_after_dutch_ms": 3000,
    "pause_after_english_ms": 1000,
    "include_example_sentence": true
  }
}
```

The current repetition settings are:

```json
"repetition": {
  "words_per_new_block": 5,
  "review_blocks": 1,
  "final_review": true
}
```

And the full lesson currently has both enabled:

```json
"include_example_sentence": true,
"include_memory_connector": true
```

## Recommended ChatGPT input for new vocabulary

When preparing new word packs, ask ChatGPT to produce JSON with:

- exact Dutch word/expression
- natural English translation
- one short B1-B2 Dutch example sentence
- English translation of that sentence
- a short visual/sound/concept memory connector

The output should be JSON only so it can be pasted directly into `data/words.json`.

## Important notes

The generator creates Dutch and English speech as separate audio segments and combines them into one MP3. It does not require an OpenAI API key or ChatGPT during audio generation.

An internet connection is required while generating because `edge-tts` uses Microsoft's online speech service. After generation, the MP3 can be played offline.

Generated MP3 files are excluded from Git so the repository stays small. Keep vocabulary JSON in `data/` and generate audio locally.

## Current status

This is intentionally a simple first version for testing the learning format. The current fixed lesson is the version described above. More advanced modes can be added later after testing and feedback.
