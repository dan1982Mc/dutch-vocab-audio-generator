#!/usr/bin/env python3
"""Simple Windows desktop interface for the Dutch vocabulary audio generator."""
from __future__ import annotations

import json
import subprocess
import sys
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
GENERATOR = ROOT / "generate_audio.py"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def load_words(path: Path) -> list[dict]:
    data = load_json(path)
    if isinstance(data, dict) and "words" in data:
        data = data["words"]
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON list or a 'words' list.")
    result = []
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
        self.root.geometry("720x610")
        self.root.minsize(680, 560)

        self.file_vars: dict[str, tk.BooleanVar] = {}
        self.words: list[dict] = []
        self.generation_running = False
        self.log_window: tk.Toplevel | None = None
        self.log_text: tk.Text | None = None

        self.start_var = tk.StringVar(value="1")
        self.end_var = tk.StringVar(value="25")
        self.lesson_type_var = tk.StringVar(value="Standard lesson (current format)")
        self.summary_var = tk.StringVar(value="Select vocabulary files to begin.")
        self.status_var = tk.StringVar(value="Ready")

        self.build_ui()
        self.refresh_files()

    def build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=16)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="Dutch Vocabulary Audio Generator", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(main, text="Part 1: select vocabulary, choose a range, then generate the current lesson format.").pack(anchor="w", pady=(2, 14))

        file_frame = ttk.LabelFrame(main, text="1. Vocabulary files (data folder)", padding=10)
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
        ttk.Label(row, text="Default lesson split:").pack(side="left")
        ttk.Label(row, text="25 words").pack(side="left", padx=6)

        ttk.Label(selection_frame, textvariable=self.summary_var).pack(anchor="w", pady=(10, 0))

        lesson_frame = ttk.LabelFrame(main, text="3. Lesson type", padding=10)
        lesson_frame.pack(fill="x", pady=(12, 0))
        ttk.Combobox(
            lesson_frame,
            textvariable=self.lesson_type_var,
            state="readonly",
            values=["Standard lesson (current format)"],
        ).pack(fill="x")
        ttk.Label(lesson_frame, text="More lesson types will be implemented in Part 2.").pack(anchor="w", pady=(6, 0))

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

    def refresh_files(self) -> None:
        for child in self.file_container.winfo_children():
            child.destroy()
        self.file_vars.clear()

        files = json_files()
        if not files:
            ttk.Label(self.file_container, text="No .json files found in data/.").pack(anchor="w")
            self.summary_var.set("No vocabulary files found.")
            return

        for path in files:
            var = tk.BooleanVar(value=(path.name == "words.json"))
            self.file_vars[path.name] = var
            ttk.Checkbutton(self.file_container, text=path.name, variable=var, command=self.update_summary).pack(anchor="w")

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
            self.words = self.get_selected_words()
            total = len(self.words)
            if total == 0:
                self.summary_var.set("Selected files contain no words.")
                return
            start = self.parse_int(self.start_var.get(), 1)
            end = self.parse_int(self.end_var.get(), min(25, total))
            selected = max(0, min(total, end) - max(1, start) + 1) if start <= end else 0
            lessons = (selected + 24) // 25 if selected else 0
            self.summary_var.set(
                f"Available words: {total}    |    Selected: {selected}    |    Lessons: {lessons}    |    Split: 25 words/lesson"
            )
        except Exception as exc:
            self.summary_var.set(f"Selection error: {exc}")

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

    def create_log_window(self) -> None:
        if self.log_window and self.log_window.winfo_exists():
            self.log_window.lift()
            return

        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("Audio generation progress")
        self.log_window.geometry("850x600")
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
        except Exception as exc:
            messagebox.showerror("Cannot generate audio", str(exc))
            return

        self.create_log_window()
        if self.log_window:
            self.log_window.deiconify()
            self.log_window.lift()
        self.log("Starting audio generation...\n")
        self.log(f"Selected words: {start}-{end} ({len(selected)} words)\n")
        self.log("Lesson type: Standard lesson (current format)\n")
        self.log("Lesson size: 25 words\n")

        self.generation_running = True
        self.generate_button.configure(state="disabled")
        self.progress.start(10)
        self.status_var.set("Generating...")

        thread = threading.Thread(target=self.run_generation, args=(selected,), daemon=True)
        thread.start()

    def run_generation(self, selected: list[dict]) -> None:
        # Use a temporary JSON file so the existing generator can remain the
        # authoritative lesson engine. No permanent vocabulary file is changed.
        import tempfile

        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8", dir=ROOT
            ) as temp:
                json.dump(selected, temp, ensure_ascii=False, indent=2)
                temp_path = Path(temp.name)

            self.root.after(0, lambda: self.log("Temporary selection file created.\n"))

            cmd = [sys.executable, str(GENERATOR), "--words", str(temp_path)]
            self.root.after(0, lambda: self.log(f"Running: {' '.join(cmd)}\n\n"))

            process = subprocess.Popen(
                cmd,
                cwd=ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )

            assert process.stdout is not None
            for line in process.stdout:
                self.root.after(0, lambda line=line: self.log(line))

            return_code = process.wait()
            if return_code == 0:
                self.root.after(0, lambda: self.finish_generation(True))
            else:
                self.root.after(0, lambda: self.finish_generation(False, return_code))
        except Exception as exc:
            self.root.after(0, lambda: self.log(f"ERROR: {exc}\n"))
            self.root.after(0, lambda: self.finish_generation(False, None))
        finally:
            if temp_path:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass

    def finish_generation(self, success: bool, return_code: int | None = None) -> None:
        self.generation_running = False
        self.generate_button.configure(state="normal")
        self.progress.stop()
        if success:
            self.status_var.set("Completed")
            self.log("\nGeneration completed successfully.\n")
            messagebox.showinfo("Audio generation complete", "The selected vocabulary has been generated into the output folder.")
        else:
            self.status_var.set("Failed")
            self.log(f"\nGeneration failed. Exit code: {return_code}\n")
            messagebox.showerror("Audio generation failed", "Generation failed. See the progress window for details.")


def main() -> None:
    root = tk.Tk()
    app = AudioGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
