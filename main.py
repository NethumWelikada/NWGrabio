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
import webbrowser
import urllib.request
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

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

APP_NAME = "NWGrabio"
APP_TAGLINE = "Grab Anything, From Anywhere."
APP_VERSION = "1.1.0"
DEVELOPER_NAME = "Nethum Welikada"
DEVELOPER_PROGRAM = "Master of Engineering in Internetworking"
DEVELOPER_SCHOOL = "Dalhousie University, Halifax, Nova Scotia, Canada"
DEVELOPER_GITHUB_LABEL = "github.com/NethumWelikada"
DEVELOPER_GITHUB_URL = "https://github.com/NethumWelikada"


def resource_path(relative_path):
    """Resolve a bundled resource path whether running from source or from
    a PyInstaller build (onefile or onedir)."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

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
        self.geometry("900x720")
        self.minsize(780, 640)
        self.configure(bg=BG_DARK)

        try:
            self.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        self.output_dir = tk.StringVar(value=get_default_download_folder())
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value=list(QUALITY_OPTIONS.keys())[0])
        self.status_var = tk.StringVar(value="Ready")
        self.title_var = tk.StringVar(value="Paste a link and click Fetch Info to preview it here.")
        self.progress_value = tk.DoubleVar(value=0.0)
        self.thumbnail_photo = None

        self.msg_queue = queue.Queue()
        self.download_thread = None
        self.cancel_flag = threading.Event()

        self._build_style()
        self._build_menu()
        self._build_layout()
        self._poll_queue()

        self.ffmpeg_path = get_ffmpeg_path()

        if yt_dlp is None:
            self._log("The download engine is missing from this build. Please reinstall NWGrabio.", ERROR)

        if self.ffmpeg_path is None:
            self._log(
                "The media processing engine was not detected. Some high "
                "resolution downloads may not be available. Please reinstall "
                "NWGrabio.",
                ACCENT_2,
            )
        else:
            self._log("Ready. Paste a link above to get started, or click How it works for a quick guide.", SUCCESS)

        self._check_clipboard_for_link()
        self.after(600, self._maybe_show_first_run_help)

    def _check_clipboard_for_link(self):
        try:
            clip = self.clipboard_get().strip()
        except Exception:
            return
        if clip.lower().startswith(("http://", "https://")) and not self.url_var.get():
            self.url_var.set(clip)
            self._log("Detected a link on your clipboard and filled it in automatically.")

    def _maybe_show_first_run_help(self):
        marker = os.path.join(os.path.expanduser("~"), ".nwgrabio_seen_help")
        if os.path.exists(marker):
            return
        try:
            with open(marker, "w") as f:
                f.write("1")
        except Exception:
            pass
        self._show_help()

    # ---------- menu & about ----------

    def _build_menu(self):
        menubar = tk.Menu(self, tearoff=0, bg=BG_PANEL, fg=FG_TEXT, activebackground=ACCENT, activeforeground="#FFFFFF")

        file_menu = tk.Menu(menubar, tearoff=0, bg=BG_PANEL, fg=FG_TEXT, activebackground=ACCENT, activeforeground="#FFFFFF")
        file_menu.add_command(label="Choose download folder...", command=self._browse_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=BG_PANEL, fg=FG_TEXT, activebackground=ACCENT, activeforeground="#FFFFFF")
        help_menu.add_command(label="How to use NWGrabio", command=self._show_help)
        help_menu.add_command(label="Supported sites", command=self._show_supported_sites)
        help_menu.add_separator()
        help_menu.add_command(label="About NWGrabio", command=self._show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _dialog_shell(self, title, width=520, height=460):
        win = tk.Toplevel(self)
        win.title(title)
        win.configure(bg=BG_DARK)
        win.geometry(f"{width}x{height}")
        win.minsize(width, height)
        win.transient(self)
        try:
            win.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass
        win.grab_set()
        return win

    def _show_about(self):
        win = self._dialog_shell(f"About {APP_NAME}", 520, 420)

        ttk.Label(win, text=APP_NAME, style="Title.TLabel").pack(anchor="w", padx=24, pady=(24, 0))
        ttk.Label(win, text=APP_TAGLINE, style="Tagline.TLabel").pack(anchor="w", padx=24, pady=(2, 16))

        body = tk.Frame(win, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=24)

        def row(label, value):
            r = tk.Frame(body, bg=BG_DARK)
            r.pack(fill="x", pady=4)
            tk.Label(r, text=label, bg=BG_DARK, fg=FG_MUTED, font=("Segoe UI", 9), width=14, anchor="w").pack(side="left")
            tk.Label(r, text=value, bg=BG_DARK, fg=FG_TEXT, font=("Segoe UI", 10), anchor="w", wraplength=340, justify="left").pack(side="left", fill="x")

        row("Version", APP_VERSION)
        row("Developer", DEVELOPER_NAME)
        row("Program", DEVELOPER_PROGRAM)
        row("University", DEVELOPER_SCHOOL)

        link = tk.Label(
            body, text=DEVELOPER_GITHUB_LABEL, bg=BG_DARK, fg=ACCENT,
            font=("Segoe UI", 10, "underline"), cursor="hand2", anchor="w"
        )
        link.pack(fill="x", pady=(8, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(DEVELOPER_GITHUB_URL))

        ttk.Label(
            win,
            text="Built with yt-dlp and ffmpeg, both open source projects, "
                 "used under their own licenses.",
            style="Muted.TLabel",
            wraplength=460,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(20, 0))

        ttk.Button(win, text="Close", style="Secondary.TButton", command=win.destroy).pack(
            anchor="e", padx=24, pady=20
        )

    def _show_help(self):
        win = self._dialog_shell("How to use NWGrabio", 560, 560)

        ttk.Label(win, text="How to use NWGrabio", style="Title.TLabel").pack(
            anchor="w", padx=24, pady=(24, 4)
        )
        ttk.Label(
            win, text="Four steps, no technical knowledge needed.",
            style="Tagline.TLabel"
        ).pack(anchor="w", padx=24, pady=(0, 16))

        steps = [
            ("1. Copy a link", "Open YouTube, Facebook, TikTok, Instagram, or almost any other site in your browser and copy the video's link."),
            ("2. Paste it in NWGrabio", "Click the URL box and press Ctrl+V, or click the Paste button."),
            ("3. Pick a quality", "Click Fetch Info to see what you are about to download, then choose a quality from the dropdown. Best Available automatically picks the highest resolution the source offers, up to 8K."),
            ("4. Click Download", "Watch the progress bar. When it says Download complete, your file is in the folder shown, your Downloads folder by default."),
        ]

        body = tk.Frame(win, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=24)

        for heading, text in steps:
            card = tk.Frame(body, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
            card.pack(fill="x", pady=6)
            tk.Label(card, text=heading, bg=BG_PANEL, fg=ACCENT, font=("Segoe UI", 10, "bold"), anchor="w").pack(
                fill="x", padx=14, pady=(10, 2)
            )
            tk.Label(
                card, text=text, bg=BG_PANEL, fg=FG_TEXT, font=("Segoe UI", 9),
                anchor="w", justify="left", wraplength=480
            ).pack(fill="x", padx=14, pady=(0, 10))

        ttk.Label(
            win,
            text="Tip: choosing Audio Only (MP3) downloads just the sound track, useful for music or podcasts.",
            style="Muted.TLabel",
            wraplength=500,
            justify="left",
        ).pack(anchor="w", padx=24, pady=(14, 0))

        ttk.Button(win, text="Got it", style="Accent.TButton", command=win.destroy).pack(
            anchor="e", padx=24, pady=20
        )

    def _show_supported_sites(self):
        win = self._dialog_shell("Supported sites", 480, 420)
        ttk.Label(win, text="Supported sites", style="Title.TLabel").pack(anchor="w", padx=24, pady=(24, 4))
        ttk.Label(
            win,
            text="NWGrabio works with over a thousand sites through the yt-dlp engine, including:",
            style="Panel.TLabel", wraplength=420, justify="left"
        ).pack(anchor="w", padx=24, pady=(0, 12))

        sites = [
            "YouTube (videos, Shorts, playlists)", "Facebook (public videos and reels)",
            "TikTok", "Instagram (public posts and reels)", "Twitter / X",
            "Vimeo", "Reddit", "Dailymotion", "Twitch clips",
            "Most news, blog, and media sites",
        ]
        body = tk.Frame(win, bg=BG_DARK)
        body.pack(fill="both", expand=True, padx=24)
        for s in sites:
            row = tk.Frame(body, bg=BG_DARK)
            row.pack(fill="x", pady=3)
            tk.Label(row, text="•", bg=BG_DARK, fg=ACCENT, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))
            tk.Label(row, text=s, bg=BG_DARK, fg=FG_TEXT, font=("Segoe UI", 10), anchor="w").pack(side="left")

        ttk.Label(
            win,
            text="Some content may be private or region-restricted by the site itself, which is outside the app's control.",
            style="Muted.TLabel", wraplength=430, justify="left"
        ).pack(anchor="w", padx=24, pady=(14, 0))

        ttk.Button(win, text="Close", style="Secondary.TButton", command=win.destroy).pack(
            anchor="e", padx=24, pady=20
        )

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

        logo_canvas = tk.Canvas(header, width=44, height=44, bg=BG_DARK, highlightthickness=0)
        logo_canvas.pack(side="left", padx=(0, 12))
        logo_canvas.create_oval(2, 2, 42, 42, outline=ACCENT, width=3)
        logo_canvas.create_line(22, 12, 22, 28, fill=ACCENT, width=4)
        logo_canvas.create_polygon(12, 22, 32, 22, 22, 34, fill=ACCENT)
        logo_canvas.create_oval(30, 30, 40, 40, fill=ACCENT_2, outline="")

        title_col = ttk.Frame(header, style="TFrame")
        title_col.pack(side="left")
        ttk.Label(title_col, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_col, text=APP_TAGLINE, style="Tagline.TLabel").pack(anchor="w")

        ttk.Button(
            header, text="How it works", style="Secondary.TButton", command=self._show_help
        ).pack(side="right", pady=(6, 0))

        # URL input row
        url_frame = ttk.Frame(self, style="TFrame")
        url_frame.pack(fill="x", padx=24, pady=(10, 4))

        ttk.Label(url_frame, text="Video or page URL").pack(anchor="w")
        entry_row = ttk.Frame(url_frame, style="TFrame")
        entry_row.pack(fill="x", pady=(4, 0))

        self.url_entry = ttk.Entry(entry_row, textvariable=self.url_var, style="TEntry")
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.url_entry.bind("<Return>", lambda e: self._fetch_info())

        ttk.Button(
            entry_row, text="Paste", style="Secondary.TButton", command=self._paste_url
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            entry_row, text="Fetch Info", style="Accent.TButton", command=self._fetch_info
        ).pack(side="left", padx=(8, 0))

        # Info panel with thumbnail preview
        info_panel = tk.Frame(self, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        info_panel.pack(fill="x", padx=24, pady=(14, 4))
        inner = tk.Frame(info_panel, bg=BG_PANEL)
        inner.pack(fill="x", padx=14, pady=12)

        self.thumb_label = tk.Label(inner, bg=BG_FIELD, width=20, height=5)
        self.thumb_label.pack(side="left", padx=(0, 14))

        ttk.Label(inner, textvariable=self.title_var, style="Panel.TLabel", wraplength=620, justify="left").pack(
            side="left", fill="x", expand=True, anchor="w"
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
        footer_text = (
            f"Developed by {DEVELOPER_NAME}  |  {DEVELOPER_PROGRAM}, {DEVELOPER_SCHOOL}"
        )
        footer_label = ttk.Label(footer, text=footer_text, style="Muted.TLabel", wraplength=850)
        footer_label.pack(side="left", anchor="w")
        about_link = tk.Label(
            footer, text="About", bg=BG_DARK, fg=ACCENT, font=("Segoe UI", 9, "underline"),
            cursor="hand2"
        )
        about_link.pack(side="right")
        about_link.bind("<Button-1>", lambda e: self._show_about())

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
            messagebox.showerror(APP_NAME, "The download engine is missing from this build. Please reinstall NWGrabio.")
            return

        self.status_var.set("Fetching info...")
        self.title_var.set("Fetching video information...")
        self.thumbnail_photo = None
        self.thumb_label.configure(image="", width=20, height=5)
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

            thumb_url = info.get("thumbnail")
            if thumb_url and Image is not None and ImageTk is not None:
                try:
                    req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        raw = resp.read()
                    import io
                    img = Image.open(io.BytesIO(raw)).convert("RGB")
                    img.thumbnail((160, 90))
                    self.msg_queue.put(("thumbnail_ready", img))
                except Exception:
                    pass
        except Exception as exc:
            self.msg_queue.put(("info_error", str(exc)))

    # ---------- download ----------

    def _start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning(APP_NAME, "Please enter a video or page URL first.")
            return
        if yt_dlp is None:
            messagebox.showerror(APP_NAME, "The download engine is missing from this build. Please reinstall NWGrabio.")
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
                elif kind == "thumbnail_ready":
                    self.thumbnail_photo = ImageTk.PhotoImage(payload)
                    self.thumb_label.configure(image=self.thumbnail_photo, width=160, height=90)
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
