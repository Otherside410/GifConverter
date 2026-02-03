import os
import shutil
import subprocess
import tempfile
import threading
import tkinter as tk
from tkinter import filedialog, messagebox


class GifConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Video -> GIF")
        self.root.resizable(False, False)

        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.fps = tk.IntVar(value=15)
        self.width = tk.IntVar(value=0)
        self.height = tk.IntVar(value=0)
        self.start_time = tk.StringVar()
        self.end_time = tk.StringVar()
        self.status_var = tk.StringVar(value="Pret.")
        self.ffmpeg_proc: subprocess.Popen | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        padding = {"padx": 8, "pady": 6}

        tk.Label(self.root, text="Video source").grid(row=0, column=0, sticky="w", **padding)
        tk.Entry(self.root, textvariable=self.input_path, width=48).grid(
            row=0, column=1, sticky="w", **padding
        )
        tk.Button(self.root, text="Choisir...", command=self._choose_input).grid(
            row=0, column=2, sticky="w", **padding
        )

        tk.Label(self.root, text="GIF sortie").grid(row=1, column=0, sticky="w", **padding)
        tk.Entry(self.root, textvariable=self.output_path, width=48).grid(
            row=1, column=1, sticky="w", **padding
        )
        tk.Button(self.root, text="Enregistrer...", command=self._choose_output).grid(
            row=1, column=2, sticky="w", **padding
        )

        tk.Label(self.root, text="FPS").grid(row=2, column=0, sticky="w", **padding)
        tk.Spinbox(self.root, from_=1, to=60, textvariable=self.fps, width=8).grid(
            row=2, column=1, sticky="w", **padding
        )

        tk.Label(self.root, text="Largeur (px)").grid(row=3, column=0, sticky="w", **padding)
        tk.Spinbox(self.root, from_=0, to=3840, textvariable=self.width, width=8).grid(
            row=3, column=1, sticky="w", **padding
        )
        tk.Label(self.root, text="0 = auto").grid(row=3, column=2, sticky="w", **padding)

        tk.Label(self.root, text="Hauteur (px)").grid(row=4, column=0, sticky="w", **padding)
        tk.Spinbox(self.root, from_=0, to=2160, textvariable=self.height, width=8).grid(
            row=4, column=1, sticky="w", **padding
        )
        tk.Label(self.root, text="0 = auto").grid(row=4, column=2, sticky="w", **padding)

        tk.Label(self.root, text="Début (s)").grid(row=5, column=0, sticky="w", **padding)
        tk.Entry(self.root, textvariable=self.start_time, width=10).grid(
            row=5, column=1, sticky="w", **padding
        )
        tk.Label(self.root, text="Fin (s)").grid(row=6, column=0, sticky="w", **padding)
        tk.Entry(self.root, textvariable=self.end_time, width=10).grid(
            row=6, column=1, sticky="w", **padding
        )

        self.convert_button = tk.Button(self.root, text="Convertir", command=self._convert)
        self.convert_button.grid(row=7, column=1, sticky="e", **padding)
        tk.Button(self.root, text="Quitter", command=self._on_close).grid(
            row=7, column=2, sticky="w", **padding
        )
        tk.Label(self.root, textvariable=self.status_var, fg="#444").grid(
            row=8, column=0, columnspan=3, sticky="w", **padding
        )

    def _choose_input(self) -> None:
        path = filedialog.askopenfilename(
            title="Choisir une video",
            filetypes=[
                ("Videos", "*.mp4 *.mov *.mkv *.avi *.webm *.m4v"),
                ("Tous", "*.*"),
            ],
        )
        if path:
            self.input_path.set(path)
            if not self.output_path.get():
                base = os.path.splitext(path)[0]
                self.output_path.set(base + ".gif")

    def _choose_output(self) -> None:
        path = filedialog.asksaveasfilename(
            title="Enregistrer le GIF",
            defaultextension=".gif",
            filetypes=[("GIF", "*.gif")],
        )
        if path:
            self.output_path.set(path)

    def _parse_float(self, value: str, label: str) -> float | None:
        if not value.strip():
            return None
        try:
            return float(value)
        except ValueError:
            messagebox.showerror("Erreur", f"{label} doit etre un nombre.")
            return None

    def _convert(self) -> None:
        if self.convert_button["state"] == "disabled":
            return
        if not shutil.which("ffmpeg"):
            messagebox.showerror(
                "Erreur",
                "ffmpeg est requis. Installez-le puis reessayez.",
            )
            return

        input_path = self.input_path.get().strip()
        output_path = self.output_path.get().strip()

        if not input_path:
            messagebox.showerror("Erreur", "Selectionnez une video source.")
            return
        if not os.path.isfile(input_path):
            messagebox.showerror("Erreur", "La video source est introuvable.")
            return
        if not output_path:
            messagebox.showerror("Erreur", "Selectionnez un fichier de sortie.")
            return
        output_dir = os.path.dirname(output_path) or "."
        if not os.path.isdir(output_dir):
            messagebox.showerror("Erreur", "Le dossier de sortie est introuvable.")
            return

        start = self._parse_float(self.start_time.get(), "Debut")
        if start is None and self.start_time.get().strip():
            return
        end = self._parse_float(self.end_time.get(), "Fin")
        if end is None and self.end_time.get().strip():
            return
        if start is not None and end is not None and end <= start:
            messagebox.showerror("Erreur", "Fin doit etre superieur au debut.")
            return

        fps = max(1, int(self.fps.get()))
        width = max(0, int(self.width.get()))
        height = max(0, int(self.height.get()))

        vf_parts = [f"fps={fps}"]
        if width > 0 or height > 0:
            scale_w = width if width > 0 else -1
            scale_h = height if height > 0 else -1
            vf_parts.append(f"scale={scale_w}:{scale_h}:flags=lanczos")
        vf = ",".join(vf_parts)
        filter_chain = f"{vf},split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"

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
            ("Generation de la palette", cmd_palette),
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
        self.status_var.set("Conversion en cours...")

        def worker() -> None:
            output_lines: list[str] = []
            for label, cmd in steps:
                self.root.after(0, self.status_var.set, f"{label}...")
                code, details = self._run_ffmpeg_cmd(cmd)
                if details:
                    output_lines.append(details)
                if code != 0:
                    combined = "\n".join(output_lines).strip()
                    self.root.after(
                        0, self._finalize_conversion, code, output_path, combined, palette_path
                    )
                    return
            combined = "\n".join(output_lines).strip()
            self.root.after(0, self._finalize_conversion, 0, output_path, combined, palette_path)

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
            return 1, f"Echec de lancement ffmpeg: {exc}"

        self.ffmpeg_proc = proc
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if line:
                print(f"[ffmpeg] {line}")
                output_lines.append(line)
                if line.startswith("progress="):
                    if line.endswith("end"):
                        self.root.after(0, self.status_var.set, "Finalisation...")
                    else:
                        self.root.after(0, self.status_var.set, "Conversion en cours...")

        proc.wait()
        self.ffmpeg_proc = None
        return proc.returncode, "\n".join(output_lines).strip()

    def _finish_error(self, details: str) -> None:
        self.convert_button.configure(state="normal")
        self.status_var.set("Pret.")
        messagebox.showerror("Erreur", details)

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
        self.status_var.set("Pret.")

        if code != 0:
            messagebox.showerror("Erreur", details or "Conversion echouee.")
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
                or "Le GIF cree est vide. Verifiez debut/fin et les options.",
            )
            return

        messagebox.showinfo("Termine", "GIF cree avec succes.")

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
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    GifConverterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
