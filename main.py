#!/usr/bin/env python3
"""Video to GIF converter with modern dark UI and video preview."""

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path
from tkinter import messagebox

import cv2
import customtkinter as ctk
from PIL import Image, ImageTk


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


class VideoPreview(ctk.CTkFrame):
    """Video preview widget with timeline and playback controls."""

    PREVIEW_WIDTH = 480
    PREVIEW_HEIGHT = 270

    def __init__(self, parent: ctk.CTk, on_time_change: callable = None) -> None:
        super().__init__(parent)

        self.on_time_change = on_time_change
        self.cap: cv2.VideoCapture | None = None
        self.video_path: str | None = None
        self.total_frames = 0
        self.fps = 30.0
        self.duration = 0.0
        self.current_frame = 0
        self.is_playing = False
        self.play_thread: threading.Thread | None = None
        self._photo_image: ImageTk.PhotoImage | None = None

        # Markers for start/end
        self.marked_start: float | None = None
        self.marked_end: float | None = None

        self._font_normal = ctk.CTkFont(size=12)
        self._font_small = ctk.CTkFont(size=11)
        self._font_tiny = ctk.CTkFont(size=9)

        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        # Video canvas
        self.canvas = ctk.CTkLabel(
            self,
            text="Sélectionnez une vidéo\npour l'aperçu",
            width=self.PREVIEW_WIDTH,
            height=self.PREVIEW_HEIGHT,
            fg_color=("gray85", "gray20"),
            corner_radius=8,
        )
        self.canvas.grid(row=0, column=0, padx=8, pady=8, sticky="nsew")

        # Timeline slider
        timeline_frame = ctk.CTkFrame(self, fg_color="transparent")
        timeline_frame.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 2))
        timeline_frame.grid_columnconfigure(1, weight=1)

        self.time_label = ctk.CTkLabel(timeline_frame, text="0:00", font=self._font_small, width=50)
        self.time_label.grid(row=0, column=0, padx=(0, 8))

        self.timeline = ctk.CTkSlider(
            timeline_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._on_timeline_change,
        )
        self.timeline.grid(row=0, column=1, sticky="ew")
        self.timeline.set(0)

        # Bind mouse wheel for timeline scrubbing
        self.timeline.bind("<Button-4>", lambda e: self._on_scroll(-1))  # Linux scroll up
        self.timeline.bind("<Button-5>", lambda e: self._on_scroll(1))   # Linux scroll down
        self.timeline.bind("<MouseWheel>", self._on_mousewheel)          # Windows/macOS

        self.duration_label = ctk.CTkLabel(timeline_frame, text="0:00", font=self._font_small, width=50)
        self.duration_label.grid(row=0, column=2, padx=(8, 0))

        # Markers info display
        markers_frame = ctk.CTkFrame(self, fg_color="transparent")
        markers_frame.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))
        markers_frame.grid_columnconfigure(1, weight=1)

        # Start marker display
        self.start_marker_label = ctk.CTkLabel(
            markers_frame,
            text="",
            font=self._font_small,
            text_color=("#2d8a27", "#4dba47"),
            anchor="w",
        )
        self.start_marker_label.grid(row=0, column=0, sticky="w")

        # Duration/segment display
        self.segment_label = ctk.CTkLabel(
            markers_frame,
            text="",
            font=self._font_small,
            text_color="gray",
            anchor="center",
        )
        self.segment_label.grid(row=0, column=1)

        # End marker display
        self.end_marker_label = ctk.CTkLabel(
            markers_frame,
            text="",
            font=self._font_small,
            text_color=("#8b2635", "#cb4655"),
            anchor="e",
        )
        self.end_marker_label.grid(row=0, column=2, sticky="e")

        # Controls
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=3, column=0, sticky="ew", padx=8, pady=(4, 8))
        controls_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        self.play_button = ctk.CTkButton(
            controls_frame,
            text="▶",
            width=40,
            font=self._font_normal,
            command=self._toggle_play,
        )
        self.play_button.grid(row=0, column=0, padx=2)

        ctk.CTkButton(
            controls_frame,
            text="⏮ -1s",
            width=60,
            font=self._font_small,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._seek_relative(-1),
        ).grid(row=0, column=1, padx=2)

        ctk.CTkButton(
            controls_frame,
            text="+1s ⏭",
            width=60,
            font=self._font_small,
            fg_color="transparent",
            border_width=1,
            command=lambda: self._seek_relative(1),
        ).grid(row=0, column=2, padx=2)

        self.start_button = ctk.CTkButton(
            controls_frame,
            text="◀ Début",
            width=80,
            font=self._font_small,
            fg_color=("#2d5a27", "#2d5a27"),
            hover_color=("#3d7a37", "#3d7a37"),
            command=self._set_start,
        )
        self.start_button.grid(row=0, column=3, padx=2)

        self.end_button = ctk.CTkButton(
            controls_frame,
            text="Fin ▶",
            width=80,
            font=self._font_small,
            fg_color=("#8b2635", "#8b2635"),
            hover_color=("#ab4655", "#ab4655"),
            command=self._set_end,
        )
        self.end_button.grid(row=0, column=4, padx=2)

    def load_video(self, path: str) -> bool:
        """Load a video file for preview."""
        self._stop_playback()

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            self.canvas.configure(text="Impossible de lire\nla vidéo")
            return False

        self.video_path = path
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        self.duration = self.total_frames / self.fps if self.fps > 0 else 0

        # Reset markers
        self.marked_start = None
        self.marked_end = None
        self._clear_markers()

        self.timeline.configure(to=max(1, self.total_frames - 1), number_of_steps=min(1000, self.total_frames))
        self.duration_label.configure(text=self._format_time(self.duration))

        self._seek_frame(0)
        return True

    def _clear_markers(self) -> None:
        """Clear all visual markers."""
        self.start_marker_label.configure(text="")
        self.end_marker_label.configure(text="")
        self.segment_label.configure(text="")

    def set_marker(self, which: str, time_value: float | None) -> None:
        """Set a marker externally (e.g., from text input)."""
        if which == "start":
            self.marked_start = time_value
        elif which == "end":
            self.marked_end = time_value
        self._update_markers()

    def _format_time(self, seconds: float) -> str:
        """Format seconds as M:SS or H:MM:SS."""
        seconds = max(0, seconds)
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def _seek_frame(self, frame_num: int) -> None:
        """Seek to a specific frame and display it."""
        if self.cap is None:
            return

        frame_num = max(0, min(frame_num, self.total_frames - 1))
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()

        if ret:
            self.current_frame = frame_num
            self._display_frame(frame)
            current_time = frame_num / self.fps if self.fps > 0 else 0
            self.time_label.configure(text=self._format_time(current_time))
            self.timeline.set(frame_num)

    def _display_frame(self, frame) -> None:
        """Display a frame on the canvas."""
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame_rgb.shape[:2]

        # Calculate scaling to fit preview size
        scale = min(self.PREVIEW_WIDTH / w, self.PREVIEW_HEIGHT / h)
        new_w, new_h = int(w * scale), int(h * scale)

        frame_resized = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
        image = Image.fromarray(frame_resized)
        self._photo_image = ImageTk.PhotoImage(image)

        self.canvas.configure(image=self._photo_image, text="")

    def _on_timeline_change(self, value: float) -> None:
        """Handle timeline slider changes."""
        if self.cap is None:
            return
        self._seek_frame(int(value))

    def _on_scroll(self, direction: int) -> None:
        """Handle scroll wheel on timeline (direction: -1 = back, 1 = forward)."""
        if self.cap is None:
            return
        # Move by ~0.5 second per scroll step
        frames_to_move = int(self.fps * 0.5) * direction
        new_frame = self.current_frame + frames_to_move
        self._seek_frame(new_frame)

    def _on_mousewheel(self, event) -> None:
        """Handle mousewheel on Windows/macOS."""
        if self.cap is None:
            return
        # event.delta is positive for scroll up, negative for scroll down
        direction = -1 if event.delta > 0 else 1
        self._on_scroll(direction)

    def _toggle_play(self) -> None:
        """Toggle play/pause."""
        if self.cap is None:
            return

        if self.is_playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        """Start video playback."""
        self.is_playing = True
        self.play_button.configure(text="⏸")

        def play_worker():
            while self.is_playing and self.cap is not None:
                if self.current_frame >= self.total_frames - 1:
                    self.after(0, self._stop_playback)
                    break

                ret, frame = self.cap.read()
                if ret:
                    self.current_frame += 1
                    self.after(0, lambda f=frame: self._display_frame(f))
                    self.after(0, lambda: self.timeline.set(self.current_frame))
                    current_time = self.current_frame / self.fps if self.fps > 0 else 0
                    self.after(0, lambda t=current_time: self.time_label.configure(text=self._format_time(t)))

                # Control playback speed
                import time
                time.sleep(1.0 / self.fps if self.fps > 0 else 0.033)

        self.play_thread = threading.Thread(target=play_worker, daemon=True)
        self.play_thread.start()

    def _stop_playback(self) -> None:
        """Stop video playback."""
        self.is_playing = False
        self.play_button.configure(text="▶")

    def _seek_relative(self, seconds: float) -> None:
        """Seek relative to current position."""
        if self.cap is None:
            return
        frames_to_seek = int(seconds * self.fps)
        new_frame = self.current_frame + frames_to_seek
        self._seek_frame(new_frame)

    def _set_start(self) -> None:
        """Set current position as start time."""
        if self.cap is not None:
            current_time = self.current_frame / self.fps if self.fps > 0 else 0
            self.marked_start = current_time
            self._update_markers()
            if self.on_time_change:
                self.on_time_change("start", current_time)

    def _set_end(self) -> None:
        """Set current position as end time."""
        if self.cap is not None:
            current_time = self.current_frame / self.fps if self.fps > 0 else 0
            self.marked_end = current_time
            self._update_markers()
            if self.on_time_change:
                self.on_time_change("end", current_time)

    def _update_markers(self) -> None:
        """Update the visual markers display."""
        # Update start marker
        if self.marked_start is not None:
            self.start_marker_label.configure(text=f"◀ Début: {self._format_time(self.marked_start)}")
        else:
            self.start_marker_label.configure(text="")

        # Update end marker
        if self.marked_end is not None:
            self.end_marker_label.configure(text=f"Fin: {self._format_time(self.marked_end)} ▶")
        else:
            self.end_marker_label.configure(text="")

        # Update segment duration
        if self.marked_start is not None and self.marked_end is not None:
            duration = self.marked_end - self.marked_start
            if duration > 0:
                self.segment_label.configure(text=f"⏱ {self._format_time(duration)}")
            else:
                self.segment_label.configure(text="⚠ Fin < Début")
        else:
            self.segment_label.configure(text="")

    def get_current_time(self) -> float:
        """Get current playback time in seconds."""
        if self.cap is None:
            return 0
        return self.current_frame / self.fps if self.fps > 0 else 0

    def cleanup(self) -> None:
        """Release video resources."""
        self._stop_playback()
        if self.cap is not None:
            self.cap.release()
            self.cap = None


class GifConverterApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        # Window setup
        self.title("GIF Converter")
        self.geometry("1050x580")
        self.minsize(900, 500)

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

        # Video preview
        self.video_preview: VideoPreview | None = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Watch for input path changes
        self.input_path.trace_add("write", self._on_input_change)
        # Watch for start/end time changes to sync markers
        self.start_time.trace_add("write", self._on_start_time_change)
        self.end_time.trace_add("write", self._on_end_time_change)

    def _build_ui(self) -> None:
        # Main container with two columns
        self.grid_columnconfigure(0, weight=0)  # Preview
        self.grid_columnconfigure(1, weight=1)  # Controls
        self.grid_rowconfigure(0, weight=1)

        # --- Left: Video Preview ---
        self.video_preview = VideoPreview(self, on_time_change=self._on_preview_time_change)
        self.video_preview.grid(row=0, column=0, padx=(16, 8), pady=16, sticky="ns")

        # --- Right: Controls ---
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.grid(row=0, column=1, padx=(8, 16), pady=16, sticky="nsew")
        controls_frame.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            controls_frame,
            text="Video → GIF",
            font=self.font_title,
        )
        title.grid(row=0, column=0, columnspan=3, pady=(0, 16), sticky="w")

        # --- Input file ---
        ctk.CTkLabel(controls_frame, text="Vidéo source", font=self.font_normal, anchor="w").grid(
            row=1, column=0, sticky="w", pady=6
        )
        input_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        input_frame.grid(row=1, column=1, columnspan=2, sticky="ew", pady=6)
        input_frame.grid_columnconfigure(0, weight=1)

        self.input_entry = ctk.CTkEntry(
            input_frame, textvariable=self.input_path, placeholder_text="Sélectionnez une vidéo...", font=self.font_normal
        )
        self.input_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            input_frame, text="Parcourir", width=90, font=self.font_normal, command=self._choose_input
        ).grid(row=0, column=1)

        # --- Output file ---
        ctk.CTkLabel(controls_frame, text="GIF sortie", font=self.font_normal, anchor="w").grid(
            row=2, column=0, sticky="w", pady=6
        )
        output_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        output_frame.grid(row=2, column=1, columnspan=2, sticky="ew", pady=6)
        output_frame.grid_columnconfigure(0, weight=1)

        self.output_entry = ctk.CTkEntry(
            output_frame, textvariable=self.output_path, placeholder_text="Chemin du GIF...", font=self.font_normal
        )
        self.output_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(
            output_frame, text="Enregistrer", width=90, font=self.font_normal, command=self._choose_output
        ).grid(row=0, column=1)

        # --- Options frame ---
        options_frame = ctk.CTkFrame(controls_frame)
        options_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=12)
        options_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # FPS
        ctk.CTkLabel(options_frame, text="FPS", font=self.font_normal).grid(row=0, column=0, padx=12, pady=10)
        self.fps_slider = ctk.CTkSlider(
            options_frame, from_=5, to=30, number_of_steps=25, variable=self.fps, width=90
        )
        self.fps_slider.grid(row=1, column=0, padx=12, pady=(0, 6))
        # Bind mouse wheel for FPS adjustment
        self.fps_slider.bind("<Button-4>", lambda e: self._on_fps_scroll(-1))  # Linux scroll up
        self.fps_slider.bind("<Button-5>", lambda e: self._on_fps_scroll(1))   # Linux scroll down
        self.fps_slider.bind("<MouseWheel>", self._on_fps_mousewheel)          # Windows/macOS

        self.fps_label = ctk.CTkLabel(options_frame, textvariable=self.fps, font=self.font_normal)
        self.fps_label.grid(row=2, column=0, padx=12, pady=(0, 10))

        # Width
        ctk.CTkLabel(options_frame, text="Largeur", font=self.font_normal).grid(row=0, column=1, padx=12, pady=10)
        self.width_entry = ctk.CTkEntry(
            options_frame, textvariable=self.width_var, width=70, justify="center", font=self.font_normal
        )
        self.width_entry.grid(row=1, column=1, padx=12, pady=(0, 6))
        ctk.CTkLabel(options_frame, text="0 = auto", font=self.font_small, text_color="gray").grid(
            row=2, column=1, padx=12, pady=(0, 10)
        )

        # Height
        ctk.CTkLabel(options_frame, text="Hauteur", font=self.font_normal).grid(row=0, column=2, padx=12, pady=10)
        self.height_entry = ctk.CTkEntry(
            options_frame, textvariable=self.height_var, width=70, justify="center", font=self.font_normal
        )
        self.height_entry.grid(row=1, column=2, padx=12, pady=(0, 6))
        ctk.CTkLabel(options_frame, text="0 = auto", font=self.font_small, text_color="gray").grid(
            row=2, column=2, padx=12, pady=(0, 10)
        )

        # --- Duration frame (now shows selected times) ---
        dur_frame = ctk.CTkFrame(controls_frame)
        dur_frame.grid(row=4, column=0, columnspan=3, sticky="ew", pady=8)
        dur_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        ctk.CTkLabel(dur_frame, text="Segment :", font=self.font_normal).grid(row=0, column=0, padx=8, pady=10)

        ctk.CTkLabel(dur_frame, text="Début", font=self.font_small, text_color="gray").grid(row=0, column=1, padx=4, pady=10)
        self.start_entry = ctk.CTkEntry(
            dur_frame, textvariable=self.start_time, width=70, placeholder_text="0", justify="center", font=self.font_normal
        )
        self.start_entry.grid(row=0, column=2, padx=4, pady=10)

        ctk.CTkLabel(dur_frame, text="Fin", font=self.font_small, text_color="gray").grid(row=0, column=3, padx=4, pady=10)
        self.end_entry = ctk.CTkEntry(
            dur_frame, textvariable=self.end_time, width=70, placeholder_text="∞", justify="center", font=self.font_normal
        )
        self.end_entry.grid(row=0, column=4, padx=(4, 8), pady=10)

        # --- Progress bar ---
        self.progress = ctk.CTkProgressBar(controls_frame, mode="indeterminate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(12, 4))
        self.progress.set(0)

        # --- Status ---
        self.status_label = ctk.CTkLabel(
            controls_frame, textvariable=self.status_var, font=self.font_small, text_color="gray"
        )
        self.status_label.grid(row=6, column=0, columnspan=3, sticky="w", pady=(0, 12))

        # --- Buttons ---
        btn_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        btn_frame.grid(row=7, column=0, columnspan=3, sticky="sew", pady=(8, 0))
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

    def _on_preview_time_change(self, which: str, time_value: float) -> None:
        """Handle time changes from video preview."""
        time_str = f"{time_value:.1f}"
        if which == "start":
            self.start_time.set(time_str)
        elif which == "end":
            self.end_time.set(time_str)

    def _on_input_change(self, *args) -> None:
        """Handle input path changes to load video preview."""
        path = self.input_path.get().strip()
        if path and os.path.isfile(path) and self.video_preview:
            self.video_preview.load_video(path)

    def _on_start_time_change(self, *args) -> None:
        """Sync start time with video preview markers."""
        if not self.video_preview:
            return
        value = self.start_time.get().strip()
        if value:
            try:
                self.video_preview.set_marker("start", float(value))
            except ValueError:
                pass
        else:
            self.video_preview.set_marker("start", None)

    def _on_end_time_change(self, *args) -> None:
        """Sync end time with video preview markers."""
        if not self.video_preview:
            return
        value = self.end_time.get().strip()
        if value:
            try:
                self.video_preview.set_marker("end", float(value))
            except ValueError:
                pass
        else:
            self.video_preview.set_marker("end", None)

    def _on_fps_scroll(self, direction: int) -> None:
        """Handle scroll wheel on FPS slider."""
        current = self.fps.get()
        new_val = current + direction
        new_val = max(5, min(30, new_val))
        self.fps.set(new_val)

    def _on_fps_mousewheel(self, event) -> None:
        """Handle mousewheel on FPS slider (Windows/macOS)."""
        direction = -1 if event.delta > 0 else 1
        self._on_fps_scroll(direction)

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
        # Cleanup video preview
        if self.video_preview:
            self.video_preview.cleanup()

        # Terminate ffmpeg if running
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
