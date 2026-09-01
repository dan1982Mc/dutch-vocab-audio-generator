#!/usr/bin/env python3
"""Generate a Dutch -> English vocabulary learning track."""
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


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")


def load_config(path: Path) -> dict[str, Any]:
    data = load_json(path)
    if not isinstance(data, dict):
        raise SystemExit("Config must be a JSON object.")
    return data


def load_words(path: Path) -> list[dict[str, str]]:
    data = load_json(path)
    if isinstance(data, dict) and "words" in data:
        data = data["words"]
    if not isinstance(data, list):
        raise SystemExit("Vocabulary JSON must be a list or contain a 'words' list.")

    words: list[dict[str, str]] = []
    for index, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise SystemExit(f"Word #{index} must be an object.")
        word = {key: str(item.get(key, "")).strip() for key in (
            "dutch", "english", "sentence_nl", "sentence_en", "memory"
        )}
        if not word["dutch"] or not word["english"]:
            raise SystemExit(f"Word #{index} needs both 'dutch' and 'english'.")
        words.append(word)
    return words


def pause(audio: AudioSegment, milliseconds: int) -> AudioSegment:
    return audio + AudioSegment.silent(duration=max(0, milliseconds))


async def speak(text: str, voice: str, rate: str, path: Path) -> None:
    await edge_tts.Communicate(text, voice=voice, rate=rate).save(str(path))


async def make_segment(text: str, voice: str, rate: str, path: Path) -> AudioSegment:
    await speak(text, voice, rate, path)
    return AudioSegment.from_file(path, format="mp3")


async def build_lesson(words: list[dict[str, str]], config: dict[str, Any], output: Path) -> tuple[float, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    nl_voice = str(config.get("dutch_voice", "nl-NL-ColetteNeural"))
    en_voice = str(config.get("english_voice", "en-US-JennyNeural"))
    nl_rate = str(config.get("dutch_rate", "-5%"))
    en_rate = str(config.get("english_rate", "-5%"))

    lesson_cfg = config.get("lesson", {})
    new_cfg = lesson_cfg.get("new_word", {})
    review_cfg = lesson_cfg.get("review", {})
    final_cfg = lesson_cfg.get("final_review", {})
    rep_cfg = config.get("repetition", {})

    words_per_block = max(1, int(rep_cfg.get("words_per_new_block", 5)))
    review_blocks = max(0, int(rep_cfg.get("review_blocks", 1)))
    final_review = bool(rep_cfg.get("final_review", True))
    include_examples = bool(config.get("include_example_sentence", True))
    include_memory = bool(config.get("include_memory_connector", True))
    repeat_after_memory = bool(new_cfg.get("repeat_word_after_memory", True))

    n_dutch = int(new_cfg.get("pause_after_dutch_ms", 2500))
    n_english = int(new_cfg.get("pause_after_english_ms", 1000))
    n_before_sentence = int(new_cfg.get("pause_before_sentence_ms", 1000))
    n_after_nl_sentence = int(new_cfg.get("pause_after_sentence_nl_ms", 1500))
    n_after_en_sentence = int(new_cfg.get("pause_after_sentence_en_ms", 1500))
    n_before_memory = int(new_cfg.get("pause_before_memory_ms", 1000))
    n_after_memory = int(new_cfg.get("pause_after_memory_ms", 2500))
    r_dutch = int(review_cfg.get("pause_after_dutch_ms", 4000))
    r_english = int(review_cfg.get("pause_after_english_ms", 1500))
    f_dutch = int(final_cfg.get("pause_after_dutch_ms", 3000))
    f_english = int(final_cfg.get("pause_after_english_ms", 1000))
    final_sentence = bool(final_cfg.get("include_example_sentence", True))

    lesson = AudioSegment.empty()
    segment_count = 0

    with tempfile.TemporaryDirectory(prefix="dutch_vocab_audio_") as temp_dir:
        temp = Path(temp_dir)

        async def add_speech(text: str, voice: str, rate: str) -> None:
            nonlocal lesson, segment_count
            segment_count += 1
            segment = await make_segment(text, voice, rate, temp / f"{segment_count:06d}.mp3")
            lesson += segment

        async def teach(word: dict[str, str]) -> None:
            nonlocal lesson
            await add_speech(word["dutch"], nl_voice, nl_rate)
            lesson = pause(lesson, n_dutch)
            await add_speech(word["english"], en_voice, en_rate)
            lesson = pause(lesson, n_english)

            if include_examples and word["sentence_nl"]:
                lesson = pause(lesson, n_before_sentence)
                await add_speech(word["sentence_nl"], nl_voice, nl_rate)
                lesson = pause(lesson, n_after_nl_sentence)
                if word["sentence_en"]:
                    await add_speech(word["sentence_en"], en_voice, en_rate)
                    lesson = pause(lesson, n_after_en_sentence)

            if include_memory and word["memory"]:
                lesson = pause(lesson, n_before_memory)
                await add_speech(word["memory"], en_voice, en_rate)
                lesson = pause(lesson, n_after_memory)

            if repeat_after_memory:
                await add_speech(word["dutch"], nl_voice, nl_rate)
                lesson = pause(lesson, 800)
                await add_speech(word["english"], en_voice, en_rate)
                lesson = pause(lesson, 2500)

        async def recall(word: dict[str, str], dutch_pause: int, english_pause: int) -> None:
            nonlocal lesson
            await add_speech(word["dutch"], nl_voice, nl_rate)
            lesson = pause(lesson, dutch_pause)
            await add_speech(word["english"], en_voice, en_rate)
            lesson = pause(lesson, english_pause)

        # Phase 1 + Phase 2: teach each block, then immediate recall review.
        for start in range(0, len(words), words_per_block):
            block = words[start:start + words_per_block]
            print(f"Teaching words {start + 1}-{start + len(block)}")
            for word in block:
                print(f"  {word['dutch']} -> {word['english']}")
                await teach(word)

            for _ in range(review_blocks):
                print("  Recall review")
                for word in block:
                    await recall(word, r_dutch, r_english)
                lesson = pause(lesson, 1500)

        # Phase 3: final review of all words.
        if final_review:
            print("Final review")
            for word in words:
                await recall(word, f_dutch, f_english)
                if final_sentence and word["sentence_nl"]:
                    await add_speech(word["sentence_nl"], nl_voice, nl_rate)
                    lesson = pause(lesson, 2000)

        lesson.export(output, format="mp3", bitrate="128k")

    return lesson.duration_seconds / 60, segment_count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Dutch -> English vocabulary learning track.")
    parser.add_argument("--words", type=Path, default=DEFAULT_WORDS)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    config = load_config(args.config)
    words = load_words(args.words)
    if args.limit is not None:
        if args.limit < 1:
            raise SystemExit("--limit must be at least 1.")
        words = words[:args.limit]
    if not words:
        raise SystemExit("No vocabulary items found.")

    output = args.output or Path(str(config.get("output_file", "output/vocabulary.mp3")))
    if not output.is_absolute():
        output = ROOT / output

    try:
        duration, count = asyncio.run(build_lesson(words, config, output))
        print(f"Done. Generated {count} speech segments.")
        print(f"Duration: {duration:.1f} minutes")
        print(f"Output: {output}")
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    except Exception as exc:
        print(f"Generation failed: {exc}")
        print("Check Internet access for edge-tts and that FFmpeg is installed and available on PATH.")
        sys.exit(1)


if __name__ == "__main__":
    main()
