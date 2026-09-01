#!/usr/bin/env python3
"""Simple Windows desktop interface for the Dutch vocabulary audio generator."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
GENERATOR = ROOT / "generate_audio.py"

# When launched with pythonw.exe, use python.exe for the child generator so
# its stdout can be captured by the GUI progress window.
PYTHON_EXECUTABLE = Path(sys.executable).with_name("python.exe")
if not PYTHON_EXECUTABLE.exists():
    PYTHON_EXECUTABLE = Path(sys.executable)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_words(path: Path) -> list[dict]:
    data = load_json(path)
    if isinstance(data, dict) and "words" in data:
        data = data["words"]
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON list or a 'words' list.")

    result: list[dict] = []
    for i, item in enumerate(data, 1):
        if not isinstance(item, dict):
            raise ValueError(f"{path.name}: item {i} is not an object.")
        dutch = str(item.get("dutch", "")).strip()
        english = str(item.get("english", "")).strip()
        if not dutch or not english:
            raise ValueError(f"{path.name}: item {i} needs 'dutch' and 'english'.")
        result.append(item)
    return result


def json_files() -> list[Path]:
    DATA_DIR.mkdir(exist_ok=True)
    return sorted(DATA_DIR.glob("*.json"), key=lambda p: p.name.lower())


class AudioGeneratorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Dutch Vocabulary Audio Generator")
        self.root.geometry("760x670")
        self.root.minsize(700, 610)

        self.file_vars: dict[str, tk.BooleanVar] = {}
        self.generation_running = False
        self.log_window: tk.Toplevel | None = None
        self.log_text: tk.Text | None = None

        self.start_var = tk.StringVar(value="1")
        self.end_var = tk.StringVar(value="25")
        self.output_name_var = tk.StringVar(value="lesson.mp3")
        self.lesson_type_var = tk.StringVar(value="Standard lesson (current format)")
        self.summary_var = tk.StringVar(value="Select vocabulary files to begin.")
        self.estimate_var = tk.StringVar(value="Estimated audio: —")
        self.status_var = tk.StringVar(value="Ready")

        self.build_ui()
        self.refresh_files()
        self.start_var.trace_add("write", lambda *_: self.update_summary())
        self.end_var.trace_add("write", lambda *_: self.update_summary())

    def build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(
            main,
            text="Dutch Vocabulary Audio Generator",
            font=("Segoe UI", 18, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            main,
            text="Part 1 — choose vocabulary and range, name the output, then generate the current standard lesson.",
        ).pack(anchor="w", pady=(2, 14))

        file_frame = ttk.LabelFrame(main, text="1. Vocabulary files", padding=10)
        file_frame.pack(fill="x")

        self.file_container = ttk.Frame(file_frame)
        self.file_container.pack(fill="x")

        file_buttons = ttk.Frame(file_frame)
        file_buttons.pack(fill="x", pady=(8, 0))
        ttk.Button(file_buttons, text="Refresh files", command=self.refresh_files).pack(side="left")
        ttk.Button(file_buttons, text="Open data folder", command=self.open_data_folder).pack(side="left", padx=8)

        selection_frame = ttk.LabelFrame(main, text="2. Word selection", padding=10)
        selection_frame.pack(fill="x", pady=(12, 0))

        row = ttk.Frame(selection_frame)
        row.pack(fill="x")
        ttk.Label(row, text="Start word:").pack(side="left")
        ttk.Entry(row, textvariable=self.start_var, width=8).pack(side="left", padx=(6, 18))
        ttk.Label(row, text="End word:").pack(side="left")
        ttk.Entry(row, textvariable=self.end_var, width=8).pack(side="left", padx=(6, 18))
        ttk.Label(row, text="Automatic split:").pack(side="left")
        ttk.Label(row, text="25 words per lesson", font=("Segoe UI", 9, "bold")).pack(side="left", padx=6)

        ttk.Label(selection_frame, textvariable=self.summary_var).pack(anchor="w", pady=(10, 2))
        ttk.Label(selection_frame, textvariable=self.estimate_var).pack(anchor="w")

        output_frame = ttk.LabelFrame(main, text="3. Output file", padding=10)
        output_frame.pack(fill="x", pady=(12, 0))
        output_row = ttk.Frame(output_frame)
        output_row.pack(fill="x")
        ttk.Label(output_row, text="Filename:").pack(side="left")
        ttk.Entry(output_row, textvariable=self.output_name_var).pack(side="left", fill="x", expand=True, padx=(8, 0))
        ttk.Label(
            output_frame,
            text="Saved in output/. If several 25-word lessons are created, _01, _02, etc. are added automatically.",
        ).pack(anchor="w", pady=(6, 0))

        lesson_frame = ttk.LabelFrame(main, text="4. Lesson type", padding=10)
        lesson_frame.pack(fill="x", pady=(12, 0))
        ttk.Combobox(
            lesson_frame,
            textvariable=self.lesson_type_var,
            state="readonly",
            values=["Standard lesson (current format)"],
        ).pack(fill="x")
        ttk.Label(
            lesson_frame,
            text="Lesson type choices will be implemented in Part 2. No lesson logic is changed in Part 1.",
        ).pack(anchor="w", pady=(6, 0))

        action_frame = ttk.Frame(main)
        action_frame.pack(fill="x", pady=(16, 0))
        self.generate_button = ttk.Button(action_frame, text="Generate audio", command=self.start_generation)
        self.generate_button.pack(side="left")
        ttk.Button(action_frame, text="Open output folder", command=self.open_output_folder).pack(side="left", padx=8)

        status_frame = ttk.Frame(main)
        status_frame.pack(fill="x", pady=(12, 0))
        ttk.Label(status_frame, text="Status:", font=("Segoe UI", 9, "bold")).pack(side="left")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left", padx=6)

        self.progress = ttk.Progressbar(main, mode="indeterminate")
        self.progress.pack(fill="x", pady=(6, 0))

        ttk.Label(
            main,
            text="Output files are written to the output folder. Generated audio is not uploaded to GitHub.",
            foreground="#555555",
        ).pack(anchor="w", pady=(10, 0))

    def refresh_files(self) -> None:
        for child in self.file_container.winfo_children():
            child.destroy()
        self.file_vars.clear()

        files = json_files()
        if not files:
            ttk.Label(self.file_container, text="No .json files found in data/.").pack(anchor="w")
            self.summary_var.set("No vocabulary files found.")
            self.estimate_var.set("Estimated audio: —")
            return

        for path in files:
            var = tk.BooleanVar(value=(path.name == "words.json"))
            self.file_vars[path.name] = var
            ttk.Checkbutton(
                self.file_container,
                text=path.name,
                variable=var,
                command=self.update_summary,
            ).pack(anchor="w")

        try:
            total = len(self.get_selected_words())
            self.end_var.set(str(min(25, total)) if total else "25")
        except Exception:
            pass
        self.update_summary()

    def selected_files(self) -> list[Path]:
        return [DATA_DIR / name for name, var in self.file_vars.items() if var.get()]

    def get_selected_words(self) -> list[dict]:
        combined: list[dict] = []
        for path in self.selected_files():
            combined.extend(load_words(path))
        return combined

    def update_summary(self) -> None:
        try:
            total = len(self.get_selected_words())
            if total == 0:
                self.summary_var.set("Selected files contain no words.")
                self.estimate_var.set("Estimated audio: —")
                return

            start = self.parse_int(self.start_var.get(), 1)
            end = self.parse_int(self.end_var.get(), min(25, total))
            if start < 1 or end < start:
                selected = 0
            else:
                selected = max(0, min(total, end) - start + 1)

            lessons = (selected + 24) // 25 if selected else 0
            self.summary_var.set(
                f"Available words: {total}    |    Selected: {selected}    |    Lessons: {lessons}    |    Split: 25 words/lesson"
            )

            # Current tested baseline: 25 words produced about 25.5 minutes.
            estimated_minutes = selected * 25.5 / 25 if selected else 0
            self.estimate_var.set(
                f"Estimated audio: ~{estimated_minutes:.1f} minutes (based on the current standard lesson format)"
            )
        except Exception as exc:
            self.summary_var.set(f"Selection error: {exc}")
            self.estimate_var.set("Estimated audio: —")

    @staticmethod
    def parse_int(value: str, default: int) -> int:
        try:
            return int(value)
        except ValueError:
            return default

    def validate_selection(self) -> tuple[list[dict], int, int]:
        selected_files = self.selected_files()
        if not selected_files:
            raise ValueError("Select at least one JSON vocabulary file.")

        words = self.get_selected_words()
        if not words:
            raise ValueError("The selected files contain no vocabulary items.")

        try:
            start = int(self.start_var.get())
            end = int(self.end_var.get())
        except ValueError:
            raise ValueError("Start and end word numbers must be whole numbers.")

        if start < 1 or end < 1 or start > end:
            raise ValueError("Start must be at least 1 and not greater than end.")
        if end > len(words):
            raise ValueError(f"End word is {end}, but only {len(words)} words are available.")
        return words, start, end

    def output_name(self) -> str:
        name = self.output_name_var.get().strip()
        if not name:
            return "lesson.mp3"
        if not name.lower().endswith(".mp3"):
            name += ".mp3"
        if Path(name).name != name or name in {".", ".."}:
            raise ValueError("Output filename must be a simple filename, not a path.")
        return name

    def create_log_window(self) -> None:
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.destroy()

        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("Audio generation progress")
        self.log_window.geometry("900x620")
        self.log_window.protocol("WM_DELETE_WINDOW", self.hide_log_window)

        frame = ttk.Frame(self.log_window, padding=10)
        frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(frame, wrap="word", state="disabled", font=("Consolas", 10))
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def hide_log_window(self) -> None:
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.withdraw()

    def log(self, text: str) -> None:
        if not self.log_text:
            return
        self.log_text.configure(state="normal")
        self.log_text.insert("end", text)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def open_data_folder(self) -> None:
        DATA_DIR.mkdir(exist_ok=True)
        self.open_folder(DATA_DIR)

    def open_output_folder(self) -> None:
        OUTPUT_DIR.mkdir(exist_ok=True)
        self.open_folder(OUTPUT_DIR)

    @staticmethod
    def open_folder(path: Path) -> None:
        if sys.platform.startswith("win"):
            subprocess.Popen(["explorer", str(path)])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])

    def start_generation(self) -> None:
        if self.generation_running:
            return

        try:
            words, start, end = self.validate_selection()
            selected = words[start - 1:end]
            output_name = self.output_name()
        except Exception as exc:
            messagebox.showerror("Cannot generate audio", str(exc))
            return

        self.create_log_window()
        self.log(f"Selected files: {', '.join(path.name for path in self.selected_files())}\n")
        self.log(f"Selected words: {start}-{end} ({len(selected)} words)\n")
        self.log(f"Lessons: {(len(selected) + 24) // 25} (25 words per lesson)\n")
        self.log("Lesson type: Standard lesson (current format)\n")
        self.log(f"Output base filename: {output_name}\n")
        self.log(f"Estimated audio: ~{len(selected) * 25.5 / 25:.1f} minutes\n\n")

        self.generation_running = True
        self.generate_button.configure(state="disabled")
        self.progress.start(10)
        self.status_var.set("Generating...")

        thread = threading.Thread(target=self.run_generation, args=(selected, output_name), daemon=True)
        thread.start()

    def run_generation(self, selected: list[dict], output_name: str) -> None:
        import tempfile

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8", dir=ROOT
            ) as temp:
                json.dump(selected, temp, ensure_ascii=False, indent=2)
                temp_path = Path(temp.name)

            self.root.after(0, lambda: self.log("Temporary selection file created.\n"))

            output_path = OUTPUT_DIR / output_name
            cmd = [
                str(PYTHON_EXECUTABLE),
                "-u",
                str(GENERATOR),
                "--words",
                str(temp_path),
                "--output",
                str(output_path),
            ]
            self.root.after(0, lambda: self.log(f"Running generator...\n"))

            env = dict(os.environ)
            env["PYTHONUNBUFFERED"] = "1"
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            process = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
                creationflags=creationflags,
            )

            assert process.stdout is not None
            for line in iter(process.stdout.readline, ""):
                self.root.after(0, lambda line=line: self.log(line))
            process.stdout.close()
            return_code = process.wait()

            if return_code == 0:
                self.root.after(0, lambda: self.finish_generation(True, output_path))
            else:
                self.root.after(0, lambda: self.finish_generation(False, None, return_code))
        except Exception as exc:
            error_text = str(exc)
            self.root.after(0, lambda: self.log(f"ERROR: {error_text}\n"))
            self.root.after(0, lambda: self.finish_generation(False, None, None))
        finally:
            if temp_path:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def finish_generation(
        self,
        success: bool,
        output_path: Path | None = None,
        return_code: int | None = None,
    ) -> None:
        self.generation_running = False
        self.generate_button.configure(state="normal")
        self.progress.stop()
        if success:
            self.status_var.set("Completed")
            self.log(f"\nGeneration completed successfully.\nOutput: {output_path}\n")
            messagebox.showinfo("Audio generation complete", "The selected vocabulary has been generated into the output folder.")
        else:
            self.status_var.set("Failed")
            self.log(f"\nGeneration failed. Exit code: {return_code}\n")
            messagebox.showerror("Audio generation failed", "Generation failed. See the progress window for details.")


def main() -> None:
    root = tk.Tk()
    AudioGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
