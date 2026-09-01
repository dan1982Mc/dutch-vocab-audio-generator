#!/usr/bin/env python3
"""Generate Dutch -> English vocabulary audio using Microsoft Edge TTS.

The vocabulary stays in JSON. This script generates each speech segment with
an appropriate language voice, inserts configurable pauses, and combines all
segments into one MP3 file.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    import edge_tts
except ImportError:
    print("Missing dependency: edge-tts. Run: pip install -r requirements.txt")
    sys.exit(1)

try:
    from pydub import AudioSegment
except ImportError:
    print("Missing dependency: pydub. Run: pip install -r requirements.txt")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG = ROOT / "config.json"
DEFAULT_WORDS = ROOT / "data" / "words.json"
DEFAULT_OUTPUT = ROOT / "output" / "vocabulary.mp3"


DEFAULT_CONFIG_DATA = {
    "dutch_voice": "nl-NL-ColetteNeural",
    "english_voice": "en-US-JennyNeural",
    "dutch_rate": "-5%",
    "english_rate": "-5%",
    "pause_after_dutch_ms": 2000,
    "pause_after_english_ms": 3000,
    "repeat_each_word": 1,
    "include_example_sentence": False,
    "pause_before_example_ms": 1500,
    "pause_after_example_ms": 2500,
    "output_file": "output/vocabulary.mp3",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")


def load_config(path: Path) -> dict[str, Any]:
    config = DEFAULT_CONFIG_DATA.copy()
    if path.exists():
        loaded = load_json(path)
        if not isinstance(loaded, dict):
            raise SystemExit("Config must be a JSON object.")
        config.update(loaded)
    return config


def load_words(path: Path) -> list[dict[str, str]]:
    data = load_json(path)
    if isinstance(data, dict) and "words" in data:
        data = data["words"]
    if not isinstance(data, list):
        raise SystemExit("Vocabulary JSON must be a list, or an object containing a 'words' list.")

    words: list[dict[str, str]] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise SystemExit(f"Word #{index} must be an object.")
        dutch = str(item.get("dutch", "")).strip()
        english = str(item.get("english", "")).strip()
        if not dutch or not english:
            raise SystemExit(f"Word #{index} needs both 'dutch' and 'english'.")
        sentence = str(item.get("sentence_nl", "")).strip()
        words.append({"dutch": dutch, "english": english, "sentence_nl": sentence})
    return words


async def synthesize(text: str, voice: str, rate: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(str(output_path))


async def generate_segment(
    text: str,
    voice: str,
    rate: str,
    target: Path,
) -> None:
    await synthesize(text, voice, rate, target)


def build_lesson(
    words: list[dict[str, str]],
    config: dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pause_after_dutch = int(config["pause_after_dutch_ms"])
    pause_after_english = int(config["pause_after_english_ms"])
    pause_before_example = int(config.get("pause_before_example_ms", 1500))
    pause_after_example = int(config.get("pause_after_example_ms", 2500))
    repeats = max(1, int(config.get("repeat_each_word", 1)))
    include_example = bool(config.get("include_example_sentence", False))

    lesson = AudioSegment.empty()
    dutch_voice = str(config["dutch_voice"])
    english_voice = str(config["english_voice"])
    dutch_rate = str(config.get("dutch_rate", "-5%"))
    english_rate = str(config.get("english_rate", "-5%"))

    with tempfile.TemporaryDirectory(prefix="dutch_vocab_audio_") as temp_dir:
        temp = Path(temp_dir)
        counter = 0

        for word in words:
            for repeat in range(repeats):
                counter += 1
                print(f"[{counter}] {word['dutch']} -> {word['english']}")

                dutch_file = temp / f"{counter:05d}_nl.mp3"
                english_file = temp / f"{counter:05d}_en.mp3"

                asyncio.run(generate_segment(word["dutch"], dutch_voice, dutch_rate, dutch_file))
                asyncio.run(generate_segment(word["english"], english_voice, english_rate, english_file))

                lesson += AudioSegment.from_file(dutch_file, format="mp3")
                lesson += AudioSegment.silent(duration=pause_after_dutch)
                lesson += AudioSegment.from_file(english_file, format="mp3")

                sentence = word.get("sentence_nl", "")
                if include_example and sentence:
                    lesson += AudioSegment.silent(duration=pause_before_example)
                    sentence_file = temp / f"{counter:05d}_sentence.mp3"
                    asyncio.run(generate_segment(sentence, dutch_voice, dutch_rate, sentence_file))
                    lesson += AudioSegment.from_file(sentence_file, format="mp3")
                    lesson += AudioSegment.silent(duration=pause_after_example)
                else:
                    lesson += AudioSegment.silent(duration=pause_after_english)

    print(f"Encoding MP3: {output_path}")
    lesson.export(output_path, format="mp3", bitrate="128k")
    print(f"Done. Duration: {lesson.duration_seconds / 60:.1f} minutes")
    print(f"Output: {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Dutch -> English vocabulary audio.")
    parser.add_argument("--words", type=Path, default=DEFAULT_WORDS, help="Vocabulary JSON file")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Configuration JSON file")
    parser.add_argument("--output", type=Path, default=None, help="Override output MP3 path")
    parser.add_argument("--limit", type=int, default=None, help="Only use the first N words")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    words = load_words(args.words)
    if args.limit is not None:
        if args.limit < 1:
            raise SystemExit("--limit must be at least 1.")
        words = words[: args.limit]
    if not words:
        raise SystemExit("No vocabulary items found.")

    configured_output = Path(str(config.get("output_file", DEFAULT_OUTPUT)))
    output = args.output or configured_output
    if not output.is_absolute():
        output = ROOT / output

    try:
        build_lesson(words, config, output)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    except Exception as exc:
        print(f"Generation failed: {exc}")
        print("Check that edge-tts can reach Microsoft's speech service and that FFmpeg is installed and available on PATH.")
        sys.exit(1)


if __name__ == "__main__":
    main()
