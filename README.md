# Dutch Vocabulary Audio Generator

A small local Python tool that turns a Dutch-English vocabulary JSON file into MP3 learning lessons.

The intended use is Dutch B2 vocabulary study while walking, commuting, or doing other activities. Dutch and English are spoken by separate voices, and pauses are inserted to support recall.

## Current lesson format

A vocabulary file is automatically split into lessons of **50 words by default**. A smaller final lesson is created when the total is not divisible by 50.

For example:

- 50 words → `lesson_01.mp3`
- 100 words → `lesson_01.mp3`, `lesson_02.mp3`
- 125 words → `lesson_01.mp3`, `lesson_02.mp3`, `lesson_03.mp3` (25 words)

The lesson size can be changed with `words_per_lesson` in `config.json`.

Each lesson follows this structure.

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

### Phase 2 — Recall review

After every block of 5 new words:

1. Dutch word
2. **4 second pause**
3. English translation

This is the active-recall part of the lesson.

### Phase 3 — Final review

After all words in the lesson have been taught:

1. Dutch word
2. **3 second pause**
3. English translation
4. Dutch example sentence

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

For the full learning format, provide:

- `sentence_nl`
- `sentence_en`
- `memory`

The generator will skip optional parts when those fields are empty.

## What each field is for

`dutch` — the exact Dutch word or expression to learn.

`english` — the natural English meaning.

`sentence_nl` — one short, natural B1-B2 Dutch example using the target word.

`sentence_en` — the natural English translation of that complete sentence.

`memory` — a short memory trick or connector. It should create an association, image, sound connection, or memorable situation. It should not simply repeat the definition.

## Installation

Requirements:

- Windows, macOS, or Linux
- Python 3.13.x recommended for the tested setup (including Python 3.13.15)
- Internet connection while generating audio (`edge-tts` uses Microsoft's online speech service)
- FFmpeg installed and available on PATH

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

Use Python to run pip:

```bash
python -m pip install -r requirements.txt
```

The requirements include the Python 3.13 compatibility package `audioop-lts` needed by pydub.

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

## Generate audio

Put your vocabulary into:

`data/words.json`

Then run:

```bash
python generate_audio.py
```

The generator automatically creates one MP3 per lesson of the configured size.

With the default 50-word setting, the files are:

```text
output/lesson_01.mp3
output/lesson_02.mp3
output/lesson_03.mp3
...
```

### Windows shortcut

After the virtual environment and dependencies are installed, you can double-click:

`generate_audio.bat`

The batch file runs the generator using the repository's `.venv` Python environment.

## Useful commands

Generate only the first 5 words for testing. This still uses the normal lesson script, but creates only one small lesson:

```bash
python generate_audio.py --limit 5
```

Use another vocabulary file:

```bash
python generate_audio.py --words data/my_pack.json
```

Use a custom output base name:

```bash
python generate_audio.py --output output/my_lesson.mp3
```

For multiple lessons, the generator adds lesson numbers automatically, for example `my_lesson_01.mp3`, `my_lesson_02.mp3`.

## Lesson configuration

Edit `config.json`.

### Lesson size

```json
"words_per_lesson": 50
```

This controls how many vocabulary items go into each MP3.

### Output naming

```json
"output_dir": "output",
"output_pattern": "lesson_{:02d}.mp3"
```

### Voices

```json
"dutch_voice": "nl-NL-ColetteNeural",
"english_voice": "en-US-JennyNeural"
```

Dutch content uses the Dutch voice and English content uses the English voice.

### Speech speed

```json
"dutch_rate": "-5%",
"english_rate": "-5%"
```

### New-word sequence

The current default pauses are:

```json
"pause_after_dutch_ms": 2500,
"pause_after_english_ms": 1000,
"pause_before_sentence_ms": 1000,
"pause_after_sentence_nl_ms": 1500,
"pause_after_sentence_en_ms": 1500,
"pause_before_memory_ms": 1000,
"pause_after_memory_ms": 2500,
"repeat_word_after_memory": true
```

### Recall review

```json
"review": {
  "words_per_block": 5,
  "pause_after_dutch_ms": 4000,
  "pause_after_english_ms": 1500
}
```

### Repetition

```json
"repetition": {
  "words_per_new_block": 5,
  "review_blocks": 1,
  "final_review": true
}
```

### Example sentences and memory connectors

```json
"include_example_sentence": true,
"include_memory_connector": true
```

## Recommended ChatGPT input for new vocabulary

When preparing new word packs, ask ChatGPT to produce JSON with:

- the exact Dutch word/expression
- a natural English translation
- one short B1-B2 Dutch example sentence
- the English translation of that sentence
- a short visual, sound, or conceptual memory connector

The output should be JSON only so it can be pasted directly into `data/words.json`.

## Important notes

The generator creates Dutch and English speech as separate audio segments and combines them into each MP3. It does not require an OpenAI API key or ChatGPT during audio generation.

An internet connection is required while generating because `edge-tts` uses Microsoft's online speech service. After generation, the MP3 files can be played offline.

There is no overall vocabulary-file word limit imposed by this generator. Large files are split into separate lessons automatically. Generation time and the external speech service are the practical constraints.

Generated MP3 files are excluded from Git so the repository stays small. Keep vocabulary JSON in `data/` and generate audio locally.

## Current status

This is intentionally a simple first version for testing the learning format. The current lesson structure is fixed and can be refined after testing and feedback.
