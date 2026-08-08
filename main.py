# NWGrabio
# Universal Video Downloader for Windows
# Developed by Nethum Welikada
# Master of Engineering in Internetworking, Dalhousie University, Halifax, Nova Scotia, Canada
# GitHub: https://github.com/NethumWelikada
#
# Supports YouTube, Facebook, TikTok, Instagram, Twitter/X, Vimeo, Reddit and
# hundreds of other sites through the yt-dlp extraction engine.

import os
import sys
import queue
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

try:
    import imageio_ffmpeg
except ImportError:
    imageio_ffmpeg = None

APP_NAME = "NWGrabio"
APP_TAGLINE = "Universal Video Downloader"
DEVELOPER_LINE_1 = "Developed by Nethum Welikada"
DEVELOPER_LINE_2 = "Master of Engineering in Internetworking, Dalhousie University, Halifax, Nova Scotia, Canada"
DEVELOPER_LINE_3 = "GitHub: github.com/NethumWelikada"

# Color palette. Dark theme, brand accent colors.
BG_DARK = "#1A1A1A"
BG_PANEL = "#222222"
BG_FIELD = "#2A2A2A"
FG_TEXT = "#F7F8F9"
FG_MUTED = "#9AA0A6"
ACCENT = "#0066FF"
ACCENT_HOVER = "#2E7CFF"
ACCENT_2 = "#FF7A1A"
BORDER = "#333333"
SUCCESS = "#2ECC71"
ERROR = "#FF5555"

QUALITY_OPTIONS = {
    "Best Available (Auto, up to 8K)": "bestvideo+bestaudio/best",
    "8K (4320p)": "bestvideo[height<=4320]+bestaudio/best",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best",
    "2K (1440p)": "bestvideo[height<=1440]+bestaudio/best",
    "Full HD (1080p)": "bestvideo[height<=1080]+bestaudio/best",
    "HD (720p)": "bestvideo[height<=720]+bestaudio/best",
    "SD (480p)": "bestvideo[height<=480]+bestaudio/best",
    "Low (360p)": "bestvideo[height<=360]+bestaudio/best",
    "Audio Only (MP3)": "bestaudio/best",
}


def get_default_download_folder():
    home = os.path.expanduser("~")
    downloads = os.path.join(home, "Downloads")
    if os.path.isdir(downloads):
        return downloads
    return home


def get_ffmpeg_path():
    """Return a usable ffmpeg executable path.

    Preference order:
    1. The ffmpeg bundled inside the app via imageio-ffmpeg (always available,
       no separate install needed).
    2. A system-installed ffmpeg found on PATH, if present.
    Returns None if neither is available.
    """
    if imageio_ffmpeg is not None:
        try:
            path = imageio_ffmpeg.get_ffmpeg_exe()
            if path and os.path.isfile(path):
                return path
        except Exception:
            pass

    try:
        subprocess.run(
            ["ffmpeg", "-version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        return "ffmpeg"
    except Exception:
        return None


class NWGrabioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - {APP_TAGLINE}")
        self.geometry("880x680")
        self.minsize(760, 600)
        self.configure(bg=BG_DARK)

        self.output_dir = tk.StringVar(value=get_default_download_folder())
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value=list(QUALITY_OPTIONS.keys())[0])
        self.status_var = tk.StringVar(value="Ready")
        self.title_var = tk.StringVar(value="No video loaded yet")
        self.progress_value = tk.DoubleVar(value=0.0)

        self.msg_queue = queue.Queue()
        self.download_thread = None
        self.cancel_flag = threading.Event()

        self._build_style()
        self._build_layout()
        self._poll_queue()

        self.ffmpeg_path = get_ffmpeg_path()

        if yt_dlp is None:
            self._log("yt-dlp module not found. Install requirements first: pip install -r requirements.txt", ERROR)

        if self.ffmpeg_path is None:
            self._log(
                "ffmpeg was not detected. Merging separate high resolution video "
                "and audio streams (needed for most 4K and 8K downloads) requires "
                "ffmpeg. Run install.bat once, which installs the bundled ffmpeg "
                "engine automatically. See the installation guide.",
                ACCENT_2,
            )
        else:
            self._log("ffmpeg engine ready.", SUCCESS)

    # ---------- UI construction ----------

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=BG_DARK)
        style.configure("Panel.TFrame", background=BG_PANEL)

        style.configure(
            "TLabel",
            background=BG_DARK,
            foreground=FG_TEXT,
            font=("Segoe UI", 10),
        )
        style.configure(
            "Muted.TLabel",
            background=BG_DARK,
            foreground=FG_MUTED,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Title.TLabel",
            background=BG_DARK,
            foreground=FG_TEXT,
            font=("Segoe UI", 20, "bold"),
        )
        style.configure(
            "Tagline.TLabel",
            background=BG_DARK,
            foreground=ACCENT,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Panel.TLabel",
            background=BG_PANEL,
            foreground=FG_TEXT,
            font=("Segoe UI", 10),
        )

        style.configure(
            "TEntry",
            fieldbackground=BG_FIELD,
            foreground=FG_TEXT,
            insertcolor=FG_TEXT,
            bordercolor=BORDER,
            lightcolor=BG_FIELD,
            darkcolor=BG_FIELD,
            padding=8,
        )

        style.configure(
            "TCombobox",
            fieldbackground=BG_FIELD,
            background=BG_FIELD,
            foreground=FG_TEXT,
            arrowcolor=FG_TEXT,
            bordercolor=BORDER,
            padding=6,
        )
        style.map(
            "TCombobox",
            fieldbackground=[("readonly", BG_FIELD)],
            foreground=[("readonly", FG_TEXT)],
        )
        self.option_add("*TCombobox*Listbox*Background", BG_FIELD)
        self.option_add("*TCombobox*Listbox*Foreground", FG_TEXT)
        self.option_add("*TCombobox*Listbox*selectBackground", ACCENT)

        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            padding=10,
            borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER)])

        style.configure(
            "Secondary.TButton",
            background=BG_FIELD,
            foreground=FG_TEXT,
            font=("Segoe UI", 10),
            padding=8,
            borderwidth=1,
        )
        style.map("Secondary.TButton", background=[("active", BORDER)])

        style.configure(
            "Danger.TButton",
            background=ERROR,
            foreground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            padding=8,
            borderwidth=0,
        )

        style.configure(
            "Dark.Horizontal.TProgressbar",
            troughcolor=BG_FIELD,
            background=ACCENT,
            bordercolor=BG_FIELD,
            lightcolor=ACCENT,
            darkcolor=ACCENT,
        )

    def _build_layout(self):
        header = ttk.Frame(self, style="TFrame")
        header.pack(fill="x", padx=24, pady=(20, 10))

        ttk.Label(header, text=APP_NAME, style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="  " + APP_TAGLINE, style="Tagline.TLabel").pack(
            side="left", padx=(10, 0), pady=(8, 0)
        )

        # URL input row
        url_frame = ttk.Frame(self, style="TFrame")
        url_frame.pack(fill="x", padx=24, pady=(10, 4))

        ttk.Label(url_frame, text="Video or page URL").pack(anchor="w")
        entry_row = ttk.Frame(url_frame, style="TFrame")
        entry_row.pack(fill="x", pady=(4, 0))

        self.url_entry = ttk.Entry(entry_row, textvariable=self.url_var, style="TEntry")
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=4)

        ttk.Button(
            entry_row, text="Paste", style="Secondary.TButton", command=self._paste_url
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            entry_row, text="Fetch Info", style="Accent.TButton", command=self._fetch_info
        ).pack(side="left", padx=(8, 0))

        # Info panel
        info_panel = ttk.Frame(self, style="Panel.TFrame")
        info_panel.pack(fill="x", padx=24, pady=(14, 4))
        inner = ttk.Frame(info_panel, style="Panel.TFrame")
        inner.pack(fill="x", padx=14, pady=12)
        ttk.Label(inner, textvariable=self.title_var, style="Panel.TLabel", wraplength=800).pack(
            anchor="w"
        )

        # Options row
        options_row = ttk.Frame(self, style="TFrame")
        options_row.pack(fill="x", padx=24, pady=(14, 4))

        quality_col = ttk.Frame(options_row, style="TFrame")
        quality_col.pack(side="left", fill="x", expand=True)
        ttk.Label(quality_col, text="Quality").pack(anchor="w")
        self.quality_combo = ttk.Combobox(
            quality_col,
            textvariable=self.quality_var,
            values=list(QUALITY_OPTIONS.keys()),
            state="readonly",
            style="TCombobox",
        )
        self.quality_combo.pack(fill="x", pady=(4, 0), ipady=3)

        folder_col = ttk.Frame(options_row, style="TFrame")
        folder_col.pack(side="left", fill="x", expand=True, padx=(16, 0))
        ttk.Label(folder_col, text="Save to folder").pack(anchor="w")
        folder_inner = ttk.Frame(folder_col, style="TFrame")
        folder_inner.pack(fill="x", pady=(4, 0))
        self.folder_entry = ttk.Entry(folder_inner, textvariable=self.output_dir, style="TEntry")
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=3)
        ttk.Button(
            folder_inner, text="Browse", style="Secondary.TButton", command=self._browse_folder
        ).pack(side="left", padx=(8, 0))

        # Action row
        action_row = ttk.Frame(self, style="TFrame")
        action_row.pack(fill="x", padx=24, pady=(18, 4))

        self.download_btn = ttk.Button(
            action_row, text="Download", style="Accent.TButton", command=self._start_download
        )
        self.download_btn.pack(side="left")

        self.cancel_btn = ttk.Button(
            action_row, text="Cancel", style="Danger.TButton", command=self._cancel_download
        )
        self.cancel_btn.pack(side="left", padx=(8, 0))
        self.cancel_btn.state(["disabled"])

        ttk.Label(action_row, textvariable=self.status_var, style="Muted.TLabel").pack(
            side="left", padx=(16, 0)
        )

        # Progress bar
        progress_frame = ttk.Frame(self, style="TFrame")
        progress_frame.pack(fill="x", padx=24, pady=(14, 4))
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            style="Dark.Horizontal.TProgressbar",
            variable=self.progress_value,
            maximum=100,
        )
        self.progress_bar.pack(fill="x", ipady=4)

        # Log console
        log_frame = ttk.Frame(self, style="TFrame")
        log_frame.pack(fill="both", expand=True, padx=24, pady=(14, 8))
        ttk.Label(log_frame, text="Activity log").pack(anchor="w")

        log_container = tk.Frame(log_frame, bg=BG_FIELD, highlightbackground=BORDER, highlightthickness=1)
        log_container.pack(fill="both", expand=True, pady=(4, 0))

        self.log_text = tk.Text(
            log_container,
            bg=BG_FIELD,
            fg=FG_TEXT,
            insertbackground=FG_TEXT,
            relief="flat",
            wrap="word",
            font=("Consolas", 9),
            padx=10,
            pady=8,
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_container, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set, state="disabled")

        # Footer
        footer = ttk.Frame(self, style="TFrame")
        footer.pack(fill="x", padx=24, pady=(0, 16))
        ttk.Label(footer, text=DEVELOPER_LINE_1, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(footer, text=DEVELOPER_LINE_2, style="Muted.TLabel").pack(anchor="w")
        ttk.Label(footer, text=DEVELOPER_LINE_3, style="Muted.TLabel").pack(anchor="w")

    # ---------- helpers ----------

    def _log(self, message, color=None):
        self.log_text.configure(state="normal")
        tag = None
        if color:
            tag = f"c_{color}"
            if tag not in self.log_text.tag_names():
                self.log_text.tag_configure(tag, foreground=color)
        self.log_text.insert("end", message + "\n", tag)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _paste_url(self):
        try:
            clip = self.clipboard_get()
            self.url_var.set(clip.strip())
        except Exception:
            pass

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir.get())
        if folder:
            self.output_dir.set(folder)

    # ---------- fetch info ----------

    def _fetch_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_NAME, "Please enter a video or page URL first.")
            return
        if yt_dlp is None:
            messagebox.showerror(APP_NAME, "yt-dlp is not installed. See the installation guide.")
            return

        self.status_var.set("Fetching info...")
        self.title_var.set("Fetching video information...")
        threading.Thread(target=self._fetch_info_worker, args=(url,), daemon=True).start()

    def _fetch_info_worker(self, url):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            title = info.get("title", "Unknown title")
            uploader = info.get("uploader", "Unknown source")
            duration = info.get("duration")
            duration_str = ""
            if duration:
                minutes, seconds = divmod(int(duration), 60)
                hours, minutes = divmod(minutes, 60)
                if hours:
                    duration_str = f"{hours}h {minutes}m {seconds}s"
                else:
                    duration_str = f"{minutes}m {seconds}s"
            summary = f"{title}\nSource: {uploader}"
            if duration_str:
                summary += f"  |  Duration: {duration_str}"
            self.msg_queue.put(("info_ready", summary))
            self.msg_queue.put(("status", "Ready to download"))
        except Exception as exc:
            self.msg_queue.put(("info_error", str(exc)))

    # ---------- download ----------

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_NAME, "Please enter a video or page URL first.")
            return
        if yt_dlp is None:
            messagebox.showerror(APP_NAME, "yt-dlp is not installed. See the installation guide.")
            return
        if self.download_thread and self.download_thread.is_alive():
            messagebox.showinfo(APP_NAME, "A download is already in progress.")
            return

        out_dir = self.output_dir.get().strip() or get_default_download_folder()
        os.makedirs(out_dir, exist_ok=True)

        self.cancel_flag.clear()
        self.download_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.progress_value.set(0)
        self.status_var.set("Starting download...")
        self._log(f"Starting download: {url}")

        self.download_thread = threading.Thread(
            target=self._download_worker, args=(url, out_dir), daemon=True
        )
        self.download_thread.start()

    def _download_worker(self, url, out_dir):
        quality_label = self.quality_var.get()
        fmt = QUALITY_OPTIONS.get(quality_label, "bestvideo+bestaudio/best")
        is_audio_only = quality_label.startswith("Audio Only")

        def progress_hook(d):
            if self.cancel_flag.is_set():
                raise yt_dlp.utils.DownloadError("Cancelled by user")
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                speed = d.get("speed")
                eta = d.get("eta")
                speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "..."
                eta_str = f"{eta}s" if eta else "..."
                self.msg_queue.put(("progress", percent))
                self.msg_queue.put(
                    ("status", f"Downloading  {percent:0.1f}%  |  {speed_str}  |  ETA {eta_str}")
                )
            elif d.get("status") == "finished":
                self.msg_queue.put(("status", "Processing / merging streams..."))
                self.msg_queue.put(("progress", 100))

        ydl_opts = {
            "format": fmt,
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }

        if self.ffmpeg_path and self.ffmpeg_path != "ffmpeg":
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path

        if is_audio_only:
            ydl_opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ]
            ydl_opts.pop("merge_output_format", None)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.msg_queue.put(("done_ok", out_dir))
        except Exception as exc:
            if self.cancel_flag.is_set():
                self.msg_queue.put(("done_cancelled", None))
            else:
                self.msg_queue.put(("done_error", str(exc)))

    def _cancel_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.cancel_flag.set()
            self.status_var.set("Cancelling...")
            self._log("Cancelling download...", ACCENT_2)

    # ---------- queue polling ----------

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "info_ready":
                    self.title_var.set(payload)
                    self._log("Video information loaded.")
                elif kind == "info_error":
                    self.title_var.set("Could not load video information.")
                    self.status_var.set("Ready")
                    self._log(f"Fetch info failed: {payload}", ERROR)
                elif kind == "progress":
                    self.progress_value.set(payload)
                elif kind == "status":
                    self.status_var.set(payload)
                elif kind == "done_ok":
                    self.status_var.set("Download complete")
                    self._log(f"Download finished. Saved to: {payload}", SUCCESS)
                    self._reset_buttons()
                elif kind == "done_cancelled":
                    self.status_var.set("Cancelled")
                    self._log("Download cancelled by user.", ACCENT_2)
                    self._reset_buttons()
                elif kind == "done_error":
                    self.status_var.set("Download failed")
                    self._log(f"Download failed: {payload}", ERROR)
                    self._reset_buttons()
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _reset_buttons(self):
        self.download_btn.state(["!disabled"])
        self.cancel_btn.state(["disabled"])


def main():
    app = NWGrabioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
