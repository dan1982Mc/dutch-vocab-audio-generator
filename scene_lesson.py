#!/usr/bin/env python3
"""Three-voice Scene & Dialogue lesson generator."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import edge_tts
from pydub import AudioSegment


def pause(audio: AudioSegment, ms: int) -> AudioSegment:
    return audio + AudioSegment.silent(duration=max(0, int(ms)))


async def speech(text: str, voice: str, rate: str, path: Path) -> AudioSegment:
    await edge_tts.Communicate(text, voice=voice, rate=rate).save(str(path))
    return AudioSegment.from_file(path, format="mp3")


def required(value: Any, field: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise SystemExit(f"Scene lesson JSON needs a non-empty '{field}'.")
    return value


def load_lesson(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc}")
    if not isinstance(data, dict) or not isinstance(data.get("lesson"), dict):
        raise SystemExit("Scene lesson JSON must contain a 'lesson' object.")
    lesson = data["lesson"]
    if not isinstance(lesson.get("speakers"), dict):
        raise SystemExit("Scene lesson JSON needs a 'speakers' object.")
    if not isinstance(lesson.get("scenes"), list) or not lesson["scenes"]:
        raise SystemExit("Scene lesson JSON needs at least one scene.")
    if not isinstance(lesson.get("fast_replay"), list):
        raise SystemExit("Scene lesson JSON needs a 'fast_replay' list.")
    if not isinstance(lesson.get("shadow_practice"), list):
        raise SystemExit("Scene lesson JSON needs a 'shadow_practice' list.")
    for role in ("male", "female", "coach"):
        spec = lesson["speakers"].get(role)
        if not isinstance(spec, dict):
            raise SystemExit(f"speakers.{role} must be an object.")
        required(spec.get("voice"), f"speakers.{role}.voice")
    return lesson


async def build(lesson: dict[str, Any], output: Path) -> tuple[float, int]:
    output.parent.mkdir(parents=True, exist_ok=True)
    voices = {r: str(lesson["speakers"][r]["voice"]) for r in ("male", "female", "coach")}
    rates = {r: str(lesson["speakers"][r].get("rate", "-5%")) for r in ("male", "female", "coach")}
    audio = AudioSegment.empty()
    count = 0

    with tempfile.TemporaryDirectory(prefix="dutch_scene_audio_") as temp_dir:
        temp = Path(temp_dir)

        async def add(text: str, role: str) -> None:
            nonlocal audio, count
            count += 1
            audio += await speech(text, voices[role], rates[role], temp / f"{count:06d}.mp3")

        for scene in lesson["scenes"]:
            number = scene.get("scene_number", "")
            title = str(scene.get("title", "")).strip()
            print(f"  Scene {number}: {title}")
            await add(f"Scene {number}. {title}", "coach")
            audio = pause(audio, 800)
            for line in scene.get("dialogue", []):
                role = line.get("speaker")
                if role not in ("male", "female"):
                    raise SystemExit(f"Invalid dialogue speaker in scene {number}: {role}")
                await add(required(line.get("text"), "dialogue.text"), role)
                audio = pause(audio, 500)
            audio = pause(audio, 1000)
            for item in scene.get("coach", []):
                term = required(item.get("term"), "coach.term")
                explanation = item.get("explanation") or {}
                await add(term, "coach")
                audio = pause(audio, 600)
                await add(required(explanation.get("nl"), f"coach explanation.nl for {term}"), "coach")
                audio = pause(audio, 500)
                await add(required(explanation.get("nl_example"), f"coach explanation.nl_example for {term}"), "coach")
                audio = pause(audio, 500)
                await add(required(explanation.get("en_meaning"), f"coach explanation.en_meaning for {term}"), "coach")
                audio = pause(audio, 700)
                for use in item.get("additional_uses", []):
                    await add(required(use.get("nl"), f"additional use for {term}"), "coach")
                    audio = pause(audio, 350)
                    await add(required(use.get("en"), f"additional English use for {term}"), "coach")
                    audio = pause(audio, 350)
                memory = str(item.get("memory_connector", "")).strip()
                if memory:
                    await add(memory, "coach")
                    audio = pause(audio, 900)
            audio = pause(audio, 1200)

        print("  Fast replay")
        await add("Fast replay.", "coach")
        audio = pause(audio, 700)
        for item in lesson["fast_replay"]:
            role = item.get("speaker")
            if role not in ("male", "female"):
                raise SystemExit(f"Invalid fast_replay speaker: {role}")
            await add(required(item.get("text"), "fast_replay.text"), role)
            audio = pause(audio, 400)

        print("  Shadow practice")
        await add("Shadow practice. Listen, then repeat during the pause.", "coach")
        audio = pause(audio, 900)
        for item in lesson["shadow_practice"]:
            role = item.get("speaker")
            if role not in ("male", "female"):
                raise SystemExit(f"Invalid shadow_practice speaker: {role}")
            await add(required(item.get("text"), "shadow_practice.text"), role)
            try:
                ms = max(0, int(item.get("pause_after_ms", 2500)))
            except (TypeError, ValueError):
                ms = 2500
            audio = pause(audio, ms)
        audio.export(output, format="mp3", bitrate="128k")
    return audio.duration_seconds / 60, count


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a three-voice Scene & Dialogue lesson.")
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    lesson = load_lesson(args.input)
    print(f"Scene & Dialogue lesson: {lesson.get('title', 'Untitled')}")
    print(f"  Scenes: {len(lesson['scenes'])}")
    print(f"  Replay lines: {len(lesson['fast_replay'])}")
    print(f"  Shadow lines: {len(lesson['shadow_practice'])}")
    try:
        minutes, segments = asyncio.run(build(lesson, args.output))
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(130)
    except Exception as exc:
        print(f"Generation failed: {exc}")
        print("Check Internet access for edge-tts and that FFmpeg is installed and available on PATH.")
        sys.exit(1)
    print("\nScene & Dialogue lesson completed.")
    print(f"Audio: {minutes:.1f} minutes")
    print(f"Speech segments: {segments}")
    print(f"File: {args.output}")


if __name__ == "__main__":
    main()
