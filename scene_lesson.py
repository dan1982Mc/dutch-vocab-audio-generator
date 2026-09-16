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
    """Generate one speech segment, retrying transient Edge-TTS failures."""
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            await edge_tts.Communicate(text, voice=voice, rate=rate).save(str(path))
            if not path.exists() or path.stat().st_size == 0:
                raise RuntimeError("Edge-TTS returned an empty audio file.")
            return AudioSegment.from_file(path, format="mp3")
        except Exception as exc:
            last_error = exc
            if attempt < 3:
                print(f"    TTS retry {attempt}/2: {voice} - {type(exc).__name__}", flush=True)
                await asyncio.sleep(1.5 * attempt)
    raise last_error  # type: ignore[misc]


def required(value: Any, field: str) -> str:
    value = str(value or "").strip()
    if not value:
        raise SystemExit(f"Scene lesson JSON needs a non-empty '{field}'.")
    return value


def load_lesson(path: Path) -> dict[str, Any]:
    try:
        # Match the GUI loader: accept UTF-8 BOM and Markdown fenced JSON.
        text = path.read_text(encoding="utf-8-sig").strip()
        if not text:
            raise SystemExit(f"File is empty: {path}")
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        data = json.loads(text)
    except FileNotFoundError:
        raise SystemExit(f"File not found: {path}")
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in {path}: {exc.msg}, line {exc.lineno}, column {exc.colno}")
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
            print(f"    [{count}] {role}: {text[:70]}", flush=True)
            audio += await speech(text, voices[role], rates[role], temp / f"{count:06d}.mp3")

        async def add_coach(text: str, language: str) -> None:
            """Use a Dutch voice for Dutch coach fields and the coach voice for English."""
            role = "female" if language == "nl" else "coach"
            await add(text, role)

        for scene in lesson["scenes"]:
            number = scene.get("scene_number", "")
            title = str(scene.get("title", "")).strip()
            print(f"  Scene {number}: {title}", flush=True)

            # Keep the English coach for the section label, but use a Dutch
            # voice for the Dutch scene title so it is pronounced correctly.
            await add(f"Scene {number}.", "coach")
            audio = pause(audio, 400)
            if title:
                await add(title, "female")
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

                # Language follows the JSON field structure:
                # term/forms/explanation.nl/nl_example/additional_uses.nl/note = Dutch
                # explanation.en_meaning/additional_uses.en/memory_connector = English
                await add_coach(term, "nl")
                audio = pause(audio, 500)

                forms = item.get("forms", [])
                if isinstance(forms, list):
                    for form in forms:
                        form_text = str(form or "").strip()
                        if form_text:
                            await add_coach(form_text, "nl")
                            audio = pause(audio, 250)
                audio = pause(audio, 400)

                await add_coach(required(explanation.get("nl"), f"coach explanation.nl for {term}"), "nl")
                audio = pause(audio, 500)
                await add_coach(required(explanation.get("nl_example"), f"coach explanation.nl_example for {term}"), "nl")
                audio = pause(audio, 500)
                await add_coach(required(explanation.get("en_meaning"), f"coach explanation.en_meaning for {term}"), "en")
                audio = pause(audio, 700)

                for use in item.get("additional_uses", []):
                    await add_coach(required(use.get("nl"), f"additional use for {term}"), "nl")
                    audio = pause(audio, 350)
                    await add_coach(required(use.get("en"), f"additional English use for {term}"), "en")
                    audio = pause(audio, 350)
                    note = str(use.get("note", "")).strip()
                    if note:
                        await add_coach(note, "nl")
                        audio = pause(audio, 350)

                memory = str(item.get("memory_connector", "")).strip()
                if memory:
                    await add_coach(memory, "en")
                    audio = pause(audio, 900)
            audio = pause(audio, 1200)

        print("  Fast replay", flush=True)
        await add("Fast replay.", "coach")
        audio = pause(audio, 700)
        for item in lesson["fast_replay"]:
            role = item.get("speaker")
            if role not in ("male", "female"):
                raise SystemExit(f"Invalid fast_replay speaker: {role}")
            await add(required(item.get("text"), "fast_replay.text"), role)
            audio = pause(audio, 400)

        print("  Shadow practice", flush=True)
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
        print(f"Generation failed: {type(exc).__name__}: {exc}")
        print("Check Internet access for edge-tts and that FFmpeg is installed and available on PATH.")
        sys.exit(1)
    print("\nScene & Dialogue lesson completed.")
    print(f"Audio: {minutes:.1f} minutes")
    print(f"Speech segments: {segments}")
    print(f"File: {args.output}")


if __name__ == "__main__":
    main()
