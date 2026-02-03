#!/usr/bin/env python3
"""Video to GIF converter with modern dark UI."""

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk


class FileDialog(ctk.CTkToplevel):
    """Custom dark-themed file dialog."""

    VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}

    def __init__(
        self,
        parent: ctk.CTk,
        title: str = "Sélectionner un fichier",
        mode: str = "open",
        filetypes: list[tuple[str, str]] | None = None,
        initial_dir: str | None = None,
    ) -> None:
        super().__init__(parent)

        self.mode = mode
        self.filetypes = filetypes
        self.result: str | None = None
        self.current_path = Path(initial_dir or Path.home())

        self._font_normal = ctk.CTkFont(size=13)
        self._font_small = ctk.CTkFont(size=12)
        self._font_bold = ctk.CTkFont(size=13, weight="bold")

        self._build_ui()

        # Window setup after UI is built
        self.title(title)
        self.geometry("700x500")
        self.minsize(500, 400)
        self.transient(parent)
        self.grab_set()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 700) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 500) // 2
        self.geometry(f"700x500+{x}+{y}")

        # Refresh list after window is mapped
        self.after(50, self._refresh_list)
        self.wait_window()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Navigation bar
        nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        nav_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        nav_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(
            nav_frame, text="⬆", width=40, font=self._font_bold, command=self._go_up
        ).grid(row=0, column=0, padx=(0, 8))

        self.path_entry = ctk.CTkEntry(nav_frame, font=self._font_normal, height=32)
        self.path_entry.grid(row=0, column=1, sticky="ew")
        self.path_entry.bind("<Return>", lambda e: self._navigate_to_path())

        ctk.CTkButton(
            nav_frame, text="Aller", width=60, font=self._font_normal, command=self._navigate_to_path
        ).grid(row=0, column=2, padx=(8, 0))

        # File list - directly in the window
        self.scrollable = ctk.CTkScrollableFrame(self, label_text="")
        self.scrollable.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self.scrollable.grid_columnconfigure(0, weight=1)

        # Bottom bar
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent")
        bottom_frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))
        bottom_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(bottom_frame, text="Nom :", font=self._font_normal).grid(row=0, column=0, padx=(0, 8))
        self.filename_entry = ctk.CTkEntry(bottom_frame, font=self._font_normal, height=32)
        self.filename_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))

        btn_text = "Ouvrir" if self.mode == "open" else "Enregistrer"
        ctk.CTkButton(
            bottom_frame, text=btn_text, width=100, font=self._font_bold, command=self._confirm
        ).grid(row=0, column=2, padx=(0, 8))

        ctk.CTkButton(
            bottom_frame,
            text="Annuler",
            width=100,
            font=self._font_normal,
            fg_color="transparent",
            border_width=2,
            command=self._cancel,
        ).grid(row=0, column=3)

    def _refresh_list(self) -> None:
        for widget in self.scrollable.winfo_children():
            widget.destroy()

        self.path_entry.delete(0, "end")
        self.path_entry.insert(0, str(self.current_path))

        try:
            items = sorted(self.current_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            items = []

        row = 0
        for item in items:
            if item.name.startswith("."):
                continue

            is_dir = item.is_dir()
            if not is_dir and self.mode == "open":
                ext = item.suffix.lower()
                if ext not in self.VIDEO_EXTENSIONS:
                    continue

            icon = "📁" if is_dir else "🎬"
            name = item.name

            btn = ctk.CTkButton(
                self.scrollable,
                text=f"  {icon}  {name}",
                font=self._font_small,
                height=30,
                anchor="w",
                fg_color="transparent",
                hover_color=("gray70", "gray30"),
                text_color=("gray10", "gray90"),
                command=lambda p=item: self._on_item_click(p),
            )
            btn.grid(row=row, column=0, sticky="ew", pady=1, padx=2)
            btn.bind("<Double-Button-1>", lambda e, p=item: self._on_item_double_click(p))
            row += 1

        if row == 0:
            ctk.CTkLabel(
                self.scrollable,
                text="Aucun fichier vidéo trouvé" if self.mode == "open" else "Dossier vide",
                font=self._font_small,
                text_color="gray",
            ).grid(row=0, column=0, pady=20)

    def _on_item_click(self, path: Path) -> None:
        self.filename_entry.delete(0, "end")
        if not path.is_dir():
            self.filename_entry.insert(0, path.name)

    def _on_item_double_click(self, path: Path) -> None:
        if path.is_dir():
            self.current_path = path
            self._refresh_list()
        else:
            self.filename_entry.delete(0, "end")
            self.filename_entry.insert(0, path.name)
            self._confirm()

    def _go_up(self) -> None:
        parent = self.current_path.parent
        if parent != self.current_path:
            self.current_path = parent
            self._refresh_list()

    def _navigate_to_path(self) -> None:
        path = Path(self.path_entry.get().strip())
        if path.is_dir():
            self.current_path = path
            self._refresh_list()

    def _confirm(self) -> None:
        filename = self.filename_entry.get().strip()
        if not filename:
            return

        full_path = self.current_path / filename

        if self.mode == "open":
            if full_path.is_file():
                self.result = str(full_path)
                self.destroy()
        else:
            if not filename.lower().endswith(".gif"):
                filename += ".gif"
                full_path = self.current_path / filename
            self.result = str(full_path)
            self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


class GifConverterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        # Window setup
        self.title("GIF Converter")
        self.geometry("580x480")
        self.resizable(False, False)

        # Theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        # Fonts
        self.font_normal = ctk.CTkFont(size=13)
        self.font_small = ctk.CTkFont(size=11)
        self.font_title = ctk.CTkFont(size=22, weight="bold")
        self.font_button = ctk.CTkFont(size=13, weight="bold")

        # Variables
        self.input_path = ctk.StringVar()
        self.output_path = ctk.StringVar()
        self.fps = ctk.IntVar(value=15)
        self.width_var = ctk.IntVar(value=480)
        self.height_var = ctk.IntVar(value=0)
        self.start_time = ctk.StringVar()
        self.end_time = ctk.StringVar()
        self.status_var = ctk.StringVar(value="Prêt")
        self.ffmpeg_proc: subprocess.Popen | None = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        # Main container
        self.grid_columnconfigure(0, weight=1)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        main_frame.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Video → GIF",
            font=self.font_title,
        )
        title.grid(row=0, column=0, columnspan=3, pady=(0, 20), sticky="w")

        # --- Input file ---
        ctk.CTkLabel(main_frame, text="Vidéo source", font=self.font_normal, anchor="w").grid(
            row=1, column=0, sticky="w", pady=8
        )
        input_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        input_frame.grid(row=1, column=1, columnspan=2, sticky="ew", pady=8)
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(
            input_frame, textvariable=self.input_path, placeholder_text="Sélectionnez une vidéo...", font=self.font_normal
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            input_frame, text="Parcourir", width=100, font=self.font_normal, command=self._choose_input
        ).grid(row=0, column=1)

        # --- Output file ---
        ctk.CTkLabel(main_frame, text="GIF sortie", font=self.font_normal, anchor="w").grid(
            row=2, column=0, sticky="w", pady=8
        )
        output_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        output_frame.grid(row=2, column=1, columnspan=2, sticky="ew", pady=8)
        output_frame.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(
            output_frame, textvariable=self.output_path, placeholder_text="Chemin du GIF...", font=self.font_normal
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            output_frame, text="Enregistrer", width=100, font=self.font_normal, command=self._choose_output
        ).grid(row=0, column=1)

        # --- Options frame ---
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=16)
        options_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        # FPS
        ctk.CTkLabel(options_frame, text="FPS", font=self.font_normal).grid(row=0, column=0, padx=12, pady=12)
        self.fps_slider = ctk.CTkSlider(
            options_frame, from_=5, to=30, number_of_steps=25, variable=self.fps, width=100
        )
        self.fps_slider.grid(row=1, column=0, padx=12, pady=(0, 8))
        self.fps_label = ctk.CTkLabel(options_frame, textvariable=self.fps, font=self.font_normal)
        self.fps_label.grid(row=2, column=0, padx=12, pady=(0, 12))

        # Width
        ctk.CTkLabel(options_frame, text="Largeur", font=self.font_normal).grid(row=0, column=1, padx=12, pady=12)
        self.width_entry = ctk.CTkEntry(
            options_frame, textvariable=self.width_var, width=80, justify="center", font=self.font_normal
        )
        self.width_entry.grid(row=1, column=1, padx=12, pady=(0, 8))
        ctk.CTkLabel(options_frame, text="0 = auto", font=self.font_small, text_color="gray").grid(
            row=2, column=1, padx=12, pady=(0, 12)
        )

        # Height
        ctk.CTkLabel(options_frame, text="Hauteur", font=self.font_normal).grid(row=0, column=2, padx=12, pady=12)
        self.height_entry = ctk.CTkEntry(
            options_frame, textvariable=self.height_var, width=80, justify="center", font=self.font_normal
        )
        self.height_entry.grid(row=1, column=2, padx=12, pady=(0, 8))
        ctk.CTkLabel(options_frame, text="0 = auto", font=self.font_small, text_color="gray").grid(
            row=2, column=2, padx=12, pady=(0, 12)
        )

        # Duration frame
        ctk.CTkLabel(options_frame, text="Durée", font=self.font_normal).grid(row=0, column=3, padx=12, pady=12)
        dur_frame = ctk.CTkFrame(options_frame, fg_color="transparent")
        dur_frame.grid(row=1, column=3, padx=12, pady=(0, 8))
        self.start_entry = ctk.CTkEntry(
            dur_frame, textvariable=self.start_time, width=50, placeholder_text="Début", justify="center", font=self.font_small
        )
        self.start_entry.grid(row=0, column=0, padx=2)
        ctk.CTkLabel(dur_frame, text="→", font=self.font_normal).grid(row=0, column=1, padx=4)
        self.end_entry = ctk.CTkEntry(
            dur_frame, textvariable=self.end_time, width=50, placeholder_text="Fin", justify="center", font=self.font_small
        )
        self.end_entry.grid(row=0, column=2, padx=2)
        ctk.CTkLabel(options_frame, text="secondes", font=self.font_small, text_color="gray").grid(
            row=2, column=3, padx=12, pady=(0, 12)
        )

        # --- Progress bar ---
        self.progress = ctk.CTkProgressBar(main_frame, mode="indeterminate")
        self.progress.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(8, 4))
        self.progress.set(0)

        # --- Status ---
        self.status_label = ctk.CTkLabel(
            main_frame, textvariable=self.status_var, font=self.font_small, text_color="gray"
        )
        self.status_label.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 16))

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(8, 0))
        btn_frame.grid_columnconfigure(0, weight=1, uniform="btn")
        btn_frame.grid_columnconfigure(1, weight=1, uniform="btn")

        self.convert_button = ctk.CTkButton(
            btn_frame,
            text="Convertir",
            font=self.font_button,
            height=42,
            command=self._convert,
        )
        self.convert_button.grid(row=0, column=0, padx=(0, 6), sticky="ew")

        self.quit_button = ctk.CTkButton(
            btn_frame,
            text="Quitter",
            font=self.font_button,
            height=42,
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=self._on_close,
        )
        self.quit_button.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _choose_input(self) -> None:
        initial_dir = None
        current = self.input_path.get().strip()
        if current and os.path.exists(os.path.dirname(current)):
            initial_dir = os.path.dirname(current)

        dialog = FileDialog(
            self,
            title="Choisir une vidéo",
            mode="open",
            initial_dir=initial_dir,
        )
        path = dialog.result
        if path:
            self.input_path.set(path)
            if not self.output_path.get():
                base = os.path.splitext(path)[0]
                self.output_path.set(base + ".gif")

    def _choose_output(self) -> None:
        initial_dir = None
        current = self.output_path.get().strip()
        if current and os.path.exists(os.path.dirname(current)):
            initial_dir = os.path.dirname(current)
        elif self.input_path.get().strip():
            initial_dir = os.path.dirname(self.input_path.get().strip())

        dialog = FileDialog(
            self,
            title="Enregistrer le GIF",
            mode="save",
            initial_dir=initial_dir,
        )
        path = dialog.result
        if path:
            self.output_path.set(path)

    def _parse_float(self, value: str, label: str) -> float | None:
        if not value.strip():
            return None
        try:
            return float(value)
        except ValueError:
            messagebox.showerror("Erreur", f"{label} doit être un nombre.")
            return None

    def _convert(self) -> None:
        if self.convert_button.cget("state") == "disabled":
            return
        if not shutil.which("ffmpeg"):
            messagebox.showerror(
                "Erreur",
                "ffmpeg est requis. Installez-le puis réessayez.",
            )
            return

        input_path = self.input_path.get().strip()
        output_path = self.output_path.get().strip()

        if not input_path:
            messagebox.showerror("Erreur", "Sélectionnez une vidéo source.")
            return
        if not os.path.isfile(input_path):
            messagebox.showerror("Erreur", "La vidéo source est introuvable.")
            return
        if not output_path:
            messagebox.showerror("Erreur", "Sélectionnez un fichier de sortie.")
            return
        output_dir = os.path.dirname(output_path) or "."
        if not os.path.isdir(output_dir):
            messagebox.showerror("Erreur", "Le dossier de sortie est introuvable.")
            return

        start = self._parse_float(self.start_time.get(), "Début")
        if start is None and self.start_time.get().strip():
            return
        end = self._parse_float(self.end_time.get(), "Fin")
        if end is None and self.end_time.get().strip():
            return
        if start is not None and end is not None and end <= start:
            messagebox.showerror("Erreur", "Fin doit être supérieur au début.")
            return

        fps = max(1, int(self.fps.get()))
        width = max(0, int(self.width_var.get()))
        height = max(0, int(self.height_var.get()))

        vf_parts = [f"fps={fps}"]
        if width > 0 or height > 0:
            scale_w = width if width > 0 else -1
            scale_h = height if height > 0 else -1
            vf_parts.append(f"scale={scale_w}:{scale_h}:flags=lanczos")
        vf = ",".join(vf_parts)

        duration = None
        if start is not None and end is not None:
            duration = end - start
        elif end is not None:
            duration = end

        input_args: list[str] = []
        if start is not None:
            input_args += ["-ss", str(start)]
        if duration is not None:
            input_args += ["-t", str(duration)]
        input_args += ["-i", input_path]

        output_dir = os.path.dirname(output_path) or "."
        palette_fd, palette_path = tempfile.mkstemp(suffix=".png", dir=output_dir)
        os.close(palette_fd)

        cmd_palette = [
            "ffmpeg",
            "-y",
            "-progress",
            "pipe:1",
            "-nostats",
            *input_args,
            "-an",
            "-sn",
            "-vf",
            f"{vf},palettegen",
            palette_path,
        ]
        cmd_gif = [
            "ffmpeg",
            "-y",
            "-progress",
            "pipe:1",
            "-nostats",
            *input_args,
            "-i",
            palette_path,
            "-an",
            "-sn",
            "-filter_complex",
            f"{vf}[x];[x][1:v]paletteuse",
            output_path,
        ]

        steps = [
            ("Génération de la palette", cmd_palette),
            ("Encodage du GIF", cmd_gif),
        ]

        self._run_conversion(steps, output_path, palette_path)

    def _run_conversion(
        self,
        steps: list[tuple[str, list[str]]],
        output_path: str,
        palette_path: str,
    ) -> None:
        self.convert_button.configure(state="disabled")
        self.progress.start()
        self.status_var.set("Conversion en cours...")

        def worker() -> None:
            output_lines: list[str] = []
            for label, cmd in steps:
                self.after(0, self.status_var.set, f"{label}...")
                code, details = self._run_ffmpeg_cmd(cmd)
                if details:
                    output_lines.append(details)
                if code != 0:
                    combined = "\n".join(output_lines).strip()
                    self.after(
                        0, self._finalize_conversion, code, output_path, combined, palette_path
                    )
                    return
            combined = "\n".join(output_lines).strip()
            self.after(0, self._finalize_conversion, 0, output_path, combined, palette_path)

        threading.Thread(target=worker, daemon=True).start()

    def _run_ffmpeg_cmd(self, cmd: list[str]) -> tuple[int, str]:
        print("[ffmpeg] cmd:", " ".join(cmd))
        output_lines: list[str] = []
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        except Exception as exc:
            return 1, f"Échec de lancement ffmpeg: {exc}"

        self.ffmpeg_proc = proc
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if line:
                print(f"[ffmpeg] {line}")
                output_lines.append(line)

        proc.wait()
        self.ffmpeg_proc = None
        return proc.returncode, "\n".join(output_lines).strip()

    def _finalize_conversion(
        self, code: int, output_path: str, details: str, palette_path: str
    ) -> None:
        if palette_path and os.path.exists(palette_path):
            try:
                os.remove(palette_path)
            except OSError:
                pass
        self.ffmpeg_proc = None
        self.convert_button.configure(state="normal")
        self.progress.stop()
        self.progress.set(0)
        self.status_var.set("Prêt")

        if code != 0:
            messagebox.showerror("Erreur", details or "Conversion échouée.")
            return

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            messagebox.showerror(
                "Erreur",
                details
                or "Le GIF créé est vide. Vérifiez début/fin et les options.",
            )
            return

        size_kb = os.path.getsize(output_path) / 1024
        if size_kb > 1024:
            size_str = f"{size_kb / 1024:.1f} Mo"
        else:
            size_str = f"{size_kb:.0f} Ko"
        messagebox.showinfo("Terminé", f"GIF créé avec succès !\nTaille : {size_str}")

    def _on_close(self) -> None:
        proc = self.ffmpeg_proc
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self.destroy()


def main() -> None:
    app = GifConverterApp()
    app.mainloop()


if __name__ == "__main__":
    main()
