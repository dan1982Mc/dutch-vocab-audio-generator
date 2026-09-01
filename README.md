# Dutch Vocabulary Audio Generator

A small local Python tool that turns Dutch-English vocabulary JSON files into MP3 learning lessons.

The intended use is Dutch B2 vocabulary study while walking, commuting, or doing other activities. Dutch and English are spoken by separate voices, and pauses are inserted to support recall.

## Part 1: Desktop program window

The current version includes a simple desktop window for selecting vocabulary and starting audio generation.

### Vocabulary files

Put one or more `.json` vocabulary files in:

`data/`

The program lists every JSON file it finds and lets you select multiple files. Their vocabulary is combined in filename order.

### Word range

Choose the first and last word to include:

- Start word: for example `10`
- End word: for example `35`

The numbering applies to the combined vocabulary from the selected JSON files.

### Output filename

Enter the desired MP3 filename in the **Output file** field. The `.mp3` extension is added automatically when omitted.

The file is saved in `output/`. When the selected range creates multiple 25-word lessons, the generator automatically adds `_01`, `_02`, and so on to the requested filename.

Example:

`commute.mp3` → `commute_01.mp3`, `commute_02.mp3`

### Lesson splitting

The selected range is automatically split into lessons of **25 words**.

Examples:

- 10 selected words → `lesson_01.mp3`
- 25 selected words → `lesson_01.mp3`
- 40 selected words → `lesson_01.mp3` (25 words) + `lesson_02.mp3` (15 words)
- 75 selected words → 3 MP3 files (25 + 25 + 25)

The 25-word split is the single standard setting in the current Part 1 version.

### Estimated duration

The program shows an approximate audio duration before generation. The estimate uses the current tested result of about **25.5 minutes for 25 words** and is only an estimate; actual duration depends on the content length.

### Live generation window

When generation starts, a separate progress window shows the generator output as it happens, including lesson number, word being processed, speech segments, completion messages, and errors.

The generator process is run unbuffered so the log should update continuously rather than appearing only after generation finishes.

### Lesson type

Part 1 contains only a placeholder:

`Standard lesson (current format)`

Different lesson types will be implemented later in Part 2. Part 1 does not change the current learning script.

## Current audio lesson format

The current standard lesson follows this structure.

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

### Phase 3 — Final review

After all words in a lesson:

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

The generator skips optional parts when those fields are empty.

## Installation

The tested setup uses **Python 3.13.x**, including Python 3.13.15.

You also need:

- Internet connection while generating audio (`edge-tts` uses Microsoft's online speech service)
- FFmpeg installed and available on PATH

### 1. Download the repository

Use **Code → Download ZIP** on GitHub and extract it, or clone the repository with Git.

### 2. Create the virtual environment

Open Command Prompt in the repository folder and run:

```bat
python -m venv .venv
```

### 3. Activate the environment

```bat
.venv\Scripts\activate
```

You should then see `(.venv)` at the start of the command prompt.

### 4. Install Python dependencies

```bat
python -m pip install -r requirements.txt
```

The requirements include `audioop-lts` for Python 3.13 compatibility with pydub.

### 5. Install FFmpeg

On Windows with WinGet:

```bat
winget install Gyan.FFmpeg
```

Close and reopen Command Prompt after installation, then check:

```bat
ffmpeg -version
```

## Start the program

After the environment and dependencies are installed, simply double-click:

`generate_audio.bat`

The batch file launches the GUI using the repository's `.venv` Python environment **without opening a separate Command Prompt window**.

You do **not** need to activate `.venv` manually when launching with the batch file.

## Using the program

1. Put your vocabulary JSON files in `data/`.
2. Double-click `generate_audio.bat`.
3. Select one or more vocabulary files.
4. Enter the start and end word numbers.
5. Enter an output filename.
6. Confirm the estimated duration.
7. Leave the lesson type as `Standard lesson (current format)` for Part 1.
8. Click **Generate audio**.
9. Watch the live progress window.
10. Find the MP3 files in `output/`.

## Command-line mode

The original command-line generator is still available if needed.

Generate all words using the configured lesson split:

```bat
python generate_audio.py
```

Generate only the first 5 words:

```bat
python generate_audio.py --limit 5
```

Use a specific JSON file:

```bat
python generate_audio.py --words data/my_pack.json
```

Use a custom output base name:

```bat
python generate_audio.py --output output/my_lesson.mp3
```

## Configuration

Edit `config.json` to change voices, speech speed, pauses, repetition, and the standard lesson structure.

The current default voices are:

```json
"dutch_voice": "nl-NL-ColetteNeural",
"english_voice": "en-US-JennyNeural"
```

The current lesson size is:

```json
"words_per_lesson": 25
```

The Part 1 GUI uses this 25-word split when generating selected ranges.

## Important notes

The generator creates Dutch and English speech as separate audio segments and combines them into MP3 files. It does not require an OpenAI API key or ChatGPT during audio generation.

An internet connection is required while generating because `edge-tts` uses Microsoft's online speech service. After generation, the MP3 files can be played offline.

There is no overall vocabulary-file word limit imposed by the generator. Large selections are split into separate 25-word lessons automatically. Generation time and the external speech service are the practical constraints.

Generated MP3 files are excluded from Git so the repository stays small. Keep vocabulary JSON files in `data/` and generate audio locally.

## Current status

**Part 1 is implemented and intended for testing.** It adds the desktop selection interface without changing the existing standard learning script.

**Part 2 is planned:** additional audio lesson types will be added after Part 1 feedback.
