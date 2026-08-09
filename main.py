# NWGrabio
# Grab Anything, From Anywhere.
# Developed by Nethum Welikada
# Master of Engineering in Internetworking, Dalhousie University, Halifax, Nova Scotia, Canada
# GitHub: https://github.com/NethumWelikada
#
# Supports YouTube, Facebook, TikTok, Instagram, Twitter/X, Vimeo, Reddit and
# hundreds of other sites through the yt-dlp extraction engine.

import io
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

try:
    import pywinstyles
except ImportError:
    pywinstyles = None

APP_NAME = "NWGrabio"
APP_TAGLINE = "Grab Anything, From Anywhere."
APP_VERSION = "1.2.0"
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


# Glass inspired dark palette. Panels use a lifted, faintly translucent tone
# so that, combined with the real Windows Acrylic backdrop blur applied at
# startup, the interface reads as frosted glass rather than flat dark boxes.
BG_DARK = "#0B0C10"
BG_GLASS = "#14161D"
BG_GLASS_LIGHT = "#1C1F29"
BG_FIELD = "#1A1D26"
FG_TEXT = "#F5F7FA"
FG_MUTED = "#8A93A6"
ACCENT = "#3D8BFF"
ACCENT_HOVER = "#5B9EFF"
ACCENT_2 = "#FF7A1A"
BORDER = "#23262F"
BORDER_LIGHT = "#333849"
SUCCESS = "#34D399"
ERROR = "#FF6161"

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

SUPPORTED_SITE_BADGES = ["YouTube", "Facebook", "TikTok", "Instagram", "Twitter / X", "Vimeo", "+1000 more"]
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


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


def looks_like_url(text):
    text = text.strip().lower()
    return text.startswith("http://") or text.startswith("https://")


class NWGrabioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - {APP_TAGLINE}")
        self.geometry("860x680")
        self.minsize(760, 600)
        self.configure(bg=BG_DARK)

        # Start invisible, fade in once the window is ready. Purely cosmetic,
        # and safely skipped if the platform does not support it.
        try:
            self.attributes("-alpha", 0.0)
        except Exception:
            pass

        try:
            self.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        self._app_icon_image = None
        if Image is not None and ImageTk is not None:
            try:
                icon_img = Image.open(resource_path("icon.ico")).convert("RGBA")
                icon_img = icon_img.resize((40, 40), Image.LANCZOS)
                self._app_icon_image = ImageTk.PhotoImage(icon_img)
            except Exception:
                self._app_icon_image = None

        self._apply_glass_backdrop()

        self.output_dir = tk.StringVar(value=get_default_download_folder())
        self.url_var = tk.StringVar()
        self.quality_var = tk.StringVar(value=list(QUALITY_OPTIONS.keys())[0])
        self.playlist_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.title_var = tk.StringVar(
            value="Paste a video or page link above. NWGrabio fetches details automatically, no extra clicks."
        )
        self.progress_value = tk.DoubleVar(value=0.0)
        self.thumbnail_photo = None
        self.last_downloaded_path = None
        self.recent_downloads = []

        self.msg_queue = queue.Queue()
        self.download_thread = None
        self.cancel_flag = threading.Event()
        self._fetch_after_id = None
        self._fetching_dots_job = None

        self._build_style()
        self._build_menu()
        self._build_layout()
        self._poll_queue()

        self.url_var.trace_add("write", self._on_url_changed)

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
            self._log("Ready. Paste a link above to get started.", SUCCESS)

        self.bind("<Configure>", self._on_resize)
        self._check_clipboard_for_link()
        self.after(60, self._fade_in)

    # ---------- window chrome ----------

    def _apply_glass_backdrop(self):
        """Apply the dark, translucent Windows title bar where supported.
        Deliberately does not use full Acrylic/Mica blur: on many Windows
        builds that composites a light system tint over the whole window,
        washing out a custom dark palette. A slight window-level alpha
        (set in _fade_in) gives the transparency effect instead, reliably,
        while our own dark colors stay dark. Safe no-op everywhere else."""
        if pywinstyles is None or os.name != "nt":
            return
        try:
            pywinstyles.apply_style(self, "dark")
        except Exception:
            pass

    WINDOW_ALPHA = 0.94

    def _fade_in(self):
        try:
            alpha = float(self.attributes("-alpha"))
        except Exception:
            return
        if alpha < self.WINDOW_ALPHA:
            alpha = min(self.WINDOW_ALPHA, alpha + 0.08)
            try:
                self.attributes("-alpha", alpha)
            except Exception:
                return
            self.after(15, self._fade_in)

    def _on_resize(self, event):
        if event.widget is not self:
            return
        width = max(560, event.width - 260)
        for label in getattr(self, "_wrap_labels", []):
            try:
                label.configure(wraplength=width)
            except Exception:
                pass

    def _check_clipboard_for_link(self):
        try:
            clip = self.clipboard_get().strip()
        except Exception:
            return
        if looks_like_url(clip) and not self.url_var.get():
            self.url_var.set(clip)

    # ---------- menu ----------

    def _build_menu(self):
        menubar = tk.Menu(self, tearoff=0, bg=BG_GLASS, fg=FG_TEXT, activebackground=ACCENT, activeforeground="#FFFFFF")

        file_menu = tk.Menu(menubar, tearoff=0, bg=BG_GLASS, fg=FG_TEXT, activebackground=ACCENT, activeforeground="#FFFFFF")
        file_menu.add_command(label="Choose download folder...", command=self._browse_folder)
        file_menu.add_command(label="Open download folder", command=self._open_folder)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy)
        menubar.add_cascade(label="File", menu=file_menu)

        help_menu = tk.Menu(menubar, tearoff=0, bg=BG_GLASS, fg=FG_TEXT, activebackground=ACCENT, activeforeground="#FFFFFF")
        help_menu.add_command(label="About & Help tab", command=lambda: self.notebook.select(self.about_tab))
        help_menu.add_command(label="Visit GitHub", command=lambda: webbrowser.open(DEVELOPER_GITHUB_URL))
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    # ---------- style ----------

    def _build_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure("TFrame", background=BG_DARK)
        style.configure("Glass.TFrame", background=BG_GLASS)
        style.configure("GlassLight.TFrame", background=BG_GLASS_LIGHT)

        style.configure("TLabel", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=BG_DARK, foreground=FG_MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 22, "bold"))
        style.configure("Tagline.TLabel", background=BG_DARK, foreground=ACCENT, font=("Segoe UI", 10, "bold"))
        style.configure("Glass.TLabel", background=BG_GLASS, foreground=FG_TEXT, font=("Segoe UI", 10))
        style.configure("GlassMuted.TLabel", background=BG_GLASS, foreground=FG_MUTED, font=("Segoe UI", 9))
        style.configure("Badge.TLabel", background=BG_GLASS_LIGHT, foreground=ACCENT, font=("Segoe UI", 8, "bold"))

        style.configure("TEntry", fieldbackground=BG_FIELD, foreground=FG_TEXT, insertcolor=FG_TEXT,
                         bordercolor=BORDER_LIGHT, lightcolor=BG_FIELD, darkcolor=BG_FIELD, padding=9)

        style.configure("TCombobox", fieldbackground=BG_FIELD, background=BG_FIELD, foreground=FG_TEXT,
                         arrowcolor=FG_TEXT, bordercolor=BORDER_LIGHT, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", BG_FIELD)], foreground=[("readonly", FG_TEXT)])
        self.option_add("*TCombobox*Listbox*Background", BG_FIELD)
        self.option_add("*TCombobox*Listbox*Foreground", FG_TEXT)
        self.option_add("*TCombobox*Listbox*selectBackground", ACCENT)

        style.configure("Accent.TButton", background=ACCENT, foreground="#FFFFFF", font=("Segoe UI", 10, "bold"),
                         padding=10, borderwidth=0)
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER), ("disabled", BORDER)])

        style.configure("Secondary.TButton", background=BG_GLASS_LIGHT, foreground=FG_TEXT, font=("Segoe UI", 10),
                         padding=8, borderwidth=1)
        style.map("Secondary.TButton", background=[("active", BORDER_LIGHT)])

        style.configure("Danger.TButton", background=ERROR, foreground="#FFFFFF", font=("Segoe UI", 10, "bold"),
                         padding=8, borderwidth=0)
        style.map("Danger.TButton", background=[("disabled", BORDER)])

        style.configure("Success.TButton", background=SUCCESS, foreground="#0B1310", font=("Segoe UI", 10, "bold"),
                         padding=8, borderwidth=0)
        style.map("Success.TButton", background=[("disabled", BORDER)])

        style.configure("Dark.Horizontal.TProgressbar", troughcolor=BG_FIELD, background=ACCENT,
                         bordercolor=BG_FIELD, lightcolor=ACCENT, darkcolor=ACCENT, thickness=10)

        style.configure("TCheckbutton", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 9))
        style.map("TCheckbutton", background=[("active", BG_DARK)])

        style.configure("TNotebook", background=BG_DARK, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_GLASS, foreground=FG_MUTED, padding=(18, 10),
                         font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("TNotebook.Tab",
                  background=[("selected", BG_DARK)],
                  foreground=[("selected", FG_TEXT)])

    # ---------- layout ----------

    def _build_layout(self):
        self._wrap_labels = []

        self.notebook = ttk.Notebook(self, style="TNotebook")
        self.notebook.pack(fill="both", expand=True)

        self.download_tab = ttk.Frame(self.notebook, style="TFrame")
        self.about_tab = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.download_tab, text="  Download  ")
        self.notebook.add(self.about_tab, text="  About & Help  ")

        self._build_download_tab(self.download_tab)
        self._build_about_tab(self.about_tab)

    def _build_download_tab(self, root):
        # Header
        header = ttk.Frame(root, style="TFrame")
        header.pack(fill="x", padx=24, pady=(20, 8))

        logo_holder = tk.Frame(header, bg=BG_DARK, width=40, height=40)
        logo_holder.pack(side="left", padx=(0, 12))
        logo_holder.pack_propagate(False)
        if self._app_icon_image is not None:
            tk.Label(logo_holder, image=self._app_icon_image, bg=BG_DARK).pack(fill="both", expand=True)
        else:
            logo_canvas = tk.Canvas(logo_holder, width=40, height=40, bg=BG_DARK, highlightthickness=0)
            logo_canvas.pack(fill="both", expand=True)
            logo_canvas.create_oval(2, 2, 38, 38, outline=ACCENT, width=3)
            logo_canvas.create_line(20, 11, 20, 25, fill=ACCENT, width=4)
            logo_canvas.create_polygon(11, 20, 29, 20, 20, 31, fill=ACCENT)
            logo_canvas.create_oval(27, 27, 36, 36, fill=ACCENT_2, outline="")

        title_col = ttk.Frame(header, style="TFrame")
        title_col.pack(side="left")
        ttk.Label(title_col, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_col, text=APP_TAGLINE, style="Tagline.TLabel").pack(anchor="w")

        # Site badges
        badges = ttk.Frame(root, style="TFrame")
        badges.pack(fill="x", padx=24, pady=(0, 14))
        for name in SUPPORTED_SITE_BADGES:
            chip = tk.Label(badges, text=name, bg=BG_GLASS_LIGHT, fg=ACCENT, font=("Segoe UI", 8, "bold"),
                             padx=10, pady=3)
            chip.pack(side="left", padx=(0, 6))

        # URL input, no fetch button, auto-detects on paste or typing
        url_frame = ttk.Frame(root, style="TFrame")
        url_frame.pack(fill="x", padx=24, pady=(4, 4))
        ttk.Label(url_frame, text="Video or page URL").pack(anchor="w")

        entry_row = ttk.Frame(url_frame, style="TFrame")
        entry_row.pack(fill="x", pady=(4, 0))
        self.url_entry = ttk.Entry(entry_row, textvariable=self.url_var, style="TEntry")
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=4)
        self.url_entry.bind("<Return>", lambda e: self._fetch_info())

        ttk.Button(entry_row, text="Paste", style="Secondary.TButton", command=self._paste_url).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(entry_row, text="Clear", style="Secondary.TButton", command=self._clear_url).pack(
            side="left", padx=(8, 0)
        )

        hint = ttk.Label(
            url_frame,
            text="Paste a link and NWGrabio fetches it automatically, no extra clicks needed.",
            style="Muted.TLabel",
        )
        hint.pack(anchor="w", pady=(4, 0))

        # Info panel with thumbnail preview, glass styled
        self.info_panel = tk.Frame(root, bg=BG_GLASS, highlightbackground=BORDER_LIGHT, highlightthickness=1)
        self.info_panel.pack(fill="x", padx=24, pady=(14, 4))
        inner = tk.Frame(self.info_panel, bg=BG_GLASS)
        inner.pack(fill="x", padx=14, pady=12)

        self.thumb_label = tk.Label(inner, bg=BG_FIELD, width=20, height=5)
        self.thumb_label.pack(side="left", padx=(0, 14))

        title_label = ttk.Label(inner, textvariable=self.title_var, style="Glass.TLabel", wraplength=620, justify="left")
        title_label.pack(side="left", fill="x", expand=True, anchor="w")
        self._wrap_labels.append(title_label)

        # Options row: quality, playlist toggle, folder
        options_row = ttk.Frame(root, style="TFrame")
        options_row.pack(fill="x", padx=24, pady=(14, 4))

        quality_col = ttk.Frame(options_row, style="TFrame")
        quality_col.pack(side="left", fill="x", expand=True)
        ttk.Label(quality_col, text="Quality").pack(anchor="w")
        self.quality_combo = ttk.Combobox(
            quality_col, textvariable=self.quality_var, values=list(QUALITY_OPTIONS.keys()),
            state="readonly", style="TCombobox"
        )
        self.quality_combo.pack(fill="x", pady=(4, 0), ipady=3)
        ttk.Checkbutton(
            quality_col, text="Download the full playlist if this link is part of one",
            variable=self.playlist_var, style="TCheckbutton"
        ).pack(anchor="w", pady=(8, 0))

        folder_col = ttk.Frame(options_row, style="TFrame")
        folder_col.pack(side="left", fill="x", expand=True, padx=(16, 0))
        ttk.Label(folder_col, text="Save to folder").pack(anchor="w")
        folder_inner = ttk.Frame(folder_col, style="TFrame")
        folder_inner.pack(fill="x", pady=(4, 0))
        self.folder_entry = ttk.Entry(folder_inner, textvariable=self.output_dir, style="TEntry")
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=3)
        ttk.Button(folder_inner, text="Browse", style="Secondary.TButton", command=self._browse_folder).pack(
            side="left", padx=(8, 0)
        )

        # Action row
        action_row = ttk.Frame(root, style="TFrame")
        action_row.pack(fill="x", padx=24, pady=(18, 4))

        self.download_btn = ttk.Button(action_row, text="Download", style="Accent.TButton", command=self._start_download)
        self.download_btn.pack(side="left")

        self.cancel_btn = ttk.Button(action_row, text="Cancel", style="Danger.TButton", command=self._cancel_download)
        self.cancel_btn.pack(side="left", padx=(8, 0))
        self.cancel_btn.state(["disabled"])

        self.open_folder_btn = ttk.Button(
            action_row, text="Open Folder", style="Success.TButton", command=self._open_folder
        )
        self.open_folder_btn.pack(side="left", padx=(8, 0))
        self.open_folder_btn.state(["disabled"])

        status_label = ttk.Label(action_row, textvariable=self.status_var, style="Muted.TLabel")
        status_label.pack(side="left", padx=(16, 0))

        # Toast banner, hidden until a download completes
        self.toast = tk.Label(root, bg=SUCCESS, fg="#0B1310", font=("Segoe UI", 9, "bold"), anchor="w", padx=14, pady=6)

        # Progress bar
        progress_frame = ttk.Frame(root, style="TFrame")
        progress_frame.pack(fill="x", padx=24, pady=(14, 4))
        self.progress_bar = ttk.Progressbar(
            progress_frame, style="Dark.Horizontal.TProgressbar", variable=self.progress_value, maximum=100
        )
        self.progress_bar.pack(fill="x", ipady=4)

        # Log + recent downloads, side by side, both expand responsively
        body_row = ttk.Frame(root, style="TFrame")
        body_row.pack(fill="both", expand=True, padx=24, pady=(14, 16))

        log_col = ttk.Frame(body_row, style="TFrame")
        log_col.pack(side="left", fill="both", expand=True)
        ttk.Label(log_col, text="Activity log").pack(anchor="w")
        log_container = tk.Frame(log_col, bg=BG_FIELD, highlightbackground=BORDER_LIGHT, highlightthickness=1)
        log_container.pack(fill="both", expand=True, pady=(4, 0))
        self.log_text = tk.Text(
            log_container, bg=BG_FIELD, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat",
            wrap="word", font=("Consolas", 9), padx=10, pady=8, height=8
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_container, command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set, state="disabled")

        recent_col = ttk.Frame(body_row, style="TFrame")
        recent_col.pack(side="left", fill="both", padx=(16, 0))
        ttk.Label(recent_col, text="Recent downloads").pack(anchor="w")
        self.recent_container = tk.Frame(recent_col, bg=BG_GLASS, highlightbackground=BORDER_LIGHT, highlightthickness=1, width=260)
        self.recent_container.pack(fill="both", expand=True, pady=(4, 0))
        self.recent_container.pack_propagate(False)
        self._refresh_recent_list()

    def _build_about_tab(self, root):
        canvas_scroll = tk.Canvas(root, bg=BG_DARK, highlightthickness=0)
        vscroll = ttk.Scrollbar(root, orient="vertical", command=canvas_scroll.yview)
        scroll_frame = ttk.Frame(canvas_scroll, style="TFrame")

        scroll_frame.bind("<Configure>", lambda e: canvas_scroll.configure(scrollregion=canvas_scroll.bbox("all")))
        canvas_scroll.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas_scroll.configure(yscrollcommand=vscroll.set)
        canvas_scroll.pack(side="left", fill="both", expand=True)
        vscroll.pack(side="right", fill="y")

        pad = 28

        top_row = tk.Frame(scroll_frame, bg=BG_DARK)
        top_row.pack(fill="x", padx=pad, pady=(24, 0))
        if self._app_icon_image is not None:
            tk.Label(top_row, image=self._app_icon_image, bg=BG_DARK).pack(side="left", padx=(0, 12))
        title_col = tk.Frame(top_row, bg=BG_DARK)
        title_col.pack(side="left")
        ttk.Label(title_col, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_col, text=APP_TAGLINE, style="Tagline.TLabel").pack(anchor="w", pady=(0, 20))

        # Developer card
        dev_card = tk.Frame(scroll_frame, bg=BG_GLASS, highlightbackground=BORDER_LIGHT, highlightthickness=1)
        dev_card.pack(fill="x", padx=pad, pady=(0, 20))
        dev_inner = tk.Frame(dev_card, bg=BG_GLASS)
        dev_inner.pack(fill="x", padx=18, pady=16)

        def dev_row(label, value):
            r = tk.Frame(dev_inner, bg=BG_GLASS)
            r.pack(fill="x", pady=3)
            tk.Label(r, text=label, bg=BG_GLASS, fg=FG_MUTED, font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
            tk.Label(r, text=value, bg=BG_GLASS, fg=FG_TEXT, font=("Segoe UI", 10), anchor="w").pack(side="left")

        dev_row("Version", APP_VERSION)
        dev_row("Developer", DEVELOPER_NAME)
        dev_row("Program", DEVELOPER_PROGRAM)
        dev_row("University", DEVELOPER_SCHOOL)

        link = tk.Label(dev_inner, text=DEVELOPER_GITHUB_LABEL, bg=BG_GLASS, fg=ACCENT,
                         font=("Segoe UI", 10, "underline"), cursor="hand2", anchor="w")
        link.pack(anchor="w", pady=(6, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(DEVELOPER_GITHUB_URL))

        tk.Label(
            dev_inner, text="Licensed under the MIT License. Built with yt-dlp and ffmpeg, open source "
                            "projects used under their own licenses.",
            bg=BG_GLASS, fg=FG_MUTED, font=("Segoe UI", 9), wraplength=560, justify="left", anchor="w"
        ).pack(anchor="w", pady=(10, 0))

        # How it works
        ttk.Label(scroll_frame, text="How it works", style="Title.TLabel").pack(anchor="w", padx=pad, pady=(4, 4))
        steps = [
            ("1. Copy a link", "Open YouTube, Facebook, TikTok, Instagram, or almost any other site and copy the video's link."),
            ("2. Paste it in NWGrabio", "Click the URL box and press Ctrl+V, or use the Paste button. Details load automatically."),
            ("3. Pick a quality", "Choose a quality from the dropdown. Best Available automatically picks the highest resolution offered, up to 8K."),
            ("4. Click Download", "Watch the progress bar. When it says Download complete, click Open Folder to jump straight to the file."),
        ]
        for heading, text in steps:
            card = tk.Frame(scroll_frame, bg=BG_GLASS, highlightbackground=BORDER_LIGHT, highlightthickness=1)
            card.pack(fill="x", padx=pad, pady=6)
            tk.Label(card, text=heading, bg=BG_GLASS, fg=ACCENT, font=("Segoe UI", 10, "bold"), anchor="w").pack(
                fill="x", padx=14, pady=(10, 2)
            )
            step_label = tk.Label(card, text=text, bg=BG_GLASS, fg=FG_TEXT, font=("Segoe UI", 9), anchor="w",
                                   justify="left", wraplength=560)
            step_label.pack(fill="x", padx=14, pady=(0, 10))
            self._wrap_labels.append(step_label)

        # Supported sites
        ttk.Label(scroll_frame, text="Supported sites", style="Title.TLabel").pack(anchor="w", padx=pad, pady=(16, 4))
        ttk.Label(
            scroll_frame, text="NWGrabio works with over a thousand sites through the yt-dlp engine, including:",
            style="Muted.TLabel", wraplength=560, justify="left"
        ).pack(anchor="w", padx=pad, pady=(0, 10))

        sites_frame = tk.Frame(scroll_frame, bg=BG_DARK)
        sites_frame.pack(fill="x", padx=pad, pady=(0, 24))
        sites = ["YouTube (videos, Shorts, playlists)", "Facebook (public videos and reels)", "TikTok",
                 "Instagram (public posts and reels)", "Twitter / X", "Vimeo", "Reddit", "Dailymotion",
                 "Twitch clips", "Most news, blog, and media sites"]
        for s in sites:
            row = tk.Frame(sites_frame, bg=BG_DARK)
            row.pack(fill="x", pady=2)
            tk.Label(row, text="•", bg=BG_DARK, fg=ACCENT, font=("Segoe UI", 11, "bold")).pack(side="left", padx=(0, 8))
            tk.Label(row, text=s, bg=BG_DARK, fg=FG_TEXT, font=("Segoe UI", 10), anchor="w").pack(side="left")

    # ---------- recent downloads ----------

    def _refresh_recent_list(self):
        for child in self.recent_container.winfo_children():
            child.destroy()

        if not self.recent_downloads:
            tk.Label(
                self.recent_container, text="Nothing downloaded yet this session.",
                bg=BG_GLASS, fg=FG_MUTED, font=("Segoe UI", 9), wraplength=230, justify="left"
            ).pack(padx=12, pady=12, anchor="w")
            return

        for item in self.recent_downloads:
            row = tk.Frame(self.recent_container, bg=BG_GLASS_LIGHT, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", padx=8, pady=4)
            name = item["name"] if len(item["name"]) <= 34 else item["name"][:31] + "..."
            tk.Label(row, text=name, bg=BG_GLASS_LIGHT, fg=FG_TEXT, font=("Segoe UI", 9), anchor="w",
                     wraplength=230, justify="left").pack(fill="x", padx=8, pady=(6, 2))
            open_link = tk.Label(row, text="Open folder", bg=BG_GLASS_LIGHT, fg=ACCENT,
                                  font=("Segoe UI", 8, "underline"), cursor="hand2", anchor="w")
            open_link.pack(fill="x", padx=8, pady=(0, 6))
            open_link.bind("<Button-1>", lambda e, p=item["path"], d=item["dir"]: self._open_folder(p, d))

    # ---------- toast ----------

    def _show_toast(self, text, bg=SUCCESS, fg="#0B1310", duration_ms=4000):
        self.toast.configure(text=text, bg=bg, fg=fg)
        self.toast.pack(fill="x", padx=24, pady=(0, 4), before=self.progress_bar.master)
        self.after(duration_ms, self._hide_toast)

    def _hide_toast(self):
        self.toast.pack_forget()

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

    def _clear_url(self):
        self.url_var.set("")
        self.title_var.set("Paste a video or page link above. NWGrabio fetches details automatically, no extra clicks.")
        self.thumbnail_photo = None
        self.thumb_label.configure(image="", width=20, height=5)

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.output_dir.get())
        if folder:
            self.output_dir.set(folder)

    def _open_folder(self, file_path=None, folder=None):
        target_file = file_path or self.last_downloaded_path
        target_dir = folder or self.output_dir.get() or get_default_download_folder()
        try:
            if target_file and os.path.isfile(target_file):
                subprocess.Popen(f'explorer /select,"{target_file}"')
            elif os.path.isdir(target_dir):
                os.startfile(target_dir)
            else:
                messagebox.showinfo(APP_NAME, "No downloaded file to show yet.")
        except Exception as exc:
            self._log(f"Could not open folder: {exc}", ERROR)

    # ---------- auto fetch on paste / type ----------

    def _on_url_changed(self, *_args):
        if self._fetch_after_id is not None:
            try:
                self.after_cancel(self._fetch_after_id)
            except Exception:
                pass
            self._fetch_after_id = None

        url = self.url_var.get().strip()
        if not looks_like_url(url):
            return
        self._fetch_after_id = self.after(700, self._fetch_info)

    def _start_fetching_animation(self):
        self._fetching_dots = 0
        self._fetching_anim_active = True
        self._animate_fetching_dots()
        self._start_spinner("Fetching info")

    def _animate_fetching_dots(self):
        if not getattr(self, "_fetching_anim_active", False):
            return
        self._fetching_dots = (self._fetching_dots + 1) % 4
        self.title_var.set("Fetching video information" + "." * self._fetching_dots)
        self._fetching_dots_job = self.after(350, self._animate_fetching_dots)

    def _stop_fetching_animation(self):
        self._fetching_anim_active = False
        if self._fetching_dots_job is not None:
            try:
                self.after_cancel(self._fetching_dots_job)
            except Exception:
                pass
            self._fetching_dots_job = None

    # ---------- generic loading spinner (status bar) ----------

    def _start_spinner(self, base_text):
        self._spinner_index = 0
        self._spinner_active = True
        self._spinner_base = base_text
        self._animate_spinner()

    def _animate_spinner(self):
        if not getattr(self, "_spinner_active", False):
            return
        frame = SPINNER_FRAMES[self._spinner_index % len(SPINNER_FRAMES)]
        self._spinner_index += 1
        self.status_var.set(f"{frame}  {self._spinner_base}")
        self._spinner_job = self.after(90, self._animate_spinner)

    def _stop_spinner(self, final_text=None):
        self._spinner_active = False
        job = getattr(self, "_spinner_job", None)
        if job is not None:
            try:
                self.after_cancel(job)
            except Exception:
                pass
            self._spinner_job = None
        if final_text is not None:
            self.status_var.set(final_text)

    # ---------- fetch info ----------

    def _fetch_info(self):
        url = self.url_var.get().strip()
        if not url or yt_dlp is None:
            return

        self._start_fetching_animation()
        self.thumbnail_photo = None
        self.thumb_label.configure(image="", width=20, height=5)
        threading.Thread(target=self._fetch_info_worker, args=(url,), daemon=True).start()

    def _fetch_info_worker(self, url):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": not self.playlist_var.get()}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if info.get("entries"):
                entries = [e for e in info["entries"] if e]
                title = f"Playlist: {info.get('title', 'Untitled playlist')} ({len(entries)} videos)"
                uploader = info.get("uploader", "Unknown source")
                summary = f"{title}\nSource: {uploader}"
                thumb_url = entries[0].get("thumbnail") if entries else None
            else:
                title = info.get("title", "Unknown title")
                uploader = info.get("uploader", "Unknown source")
                duration = info.get("duration")
                duration_str = ""
                if duration:
                    minutes, seconds = divmod(int(duration), 60)
                    hours, minutes = divmod(minutes, 60)
                    duration_str = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
                summary = f"{title}\nSource: {uploader}"
                if duration_str:
                    summary += f"  |  Duration: {duration_str}"
                thumb_url = info.get("thumbnail")

            self.msg_queue.put(("info_ready", summary))
            self.msg_queue.put(("status", "Ready to download"))

            if thumb_url and Image is not None and ImageTk is not None:
                try:
                    req = urllib.request.Request(thumb_url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        raw = resp.read()
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
        self.open_folder_btn.state(["disabled"])
        self.progress_bar.configure(mode="determinate")
        self.progress_value.set(0)
        self._start_spinner("Starting download")
        self._log(f"Starting download: {url}")

        self.download_thread = threading.Thread(target=self._download_worker, args=(url, out_dir), daemon=True)
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
                self.msg_queue.put(("status", f"Downloading  {percent:0.1f}%  |  {speed_str}  |  ETA {eta_str}"))
            elif d.get("status") == "finished":
                self.msg_queue.put(("merging_start", None))
                fn = d.get("filename")
                if fn:
                    self.msg_queue.put(("last_file", fn))

        def pp_hook(d):
            if d.get("status") == "finished":
                fp = (d.get("info_dict") or {}).get("filepath")
                if fp:
                    self.msg_queue.put(("last_file", fp))

        ydl_opts = {
            "format": fmt,
            "outtmpl": os.path.join(out_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "postprocessor_hooks": [pp_hook],
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": not self.playlist_var.get(),
        }

        if self.ffmpeg_path and self.ffmpeg_path != "ffmpeg":
            ydl_opts["ffmpeg_location"] = self.ffmpeg_path

        if is_audio_only:
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
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
            self._start_spinner("Cancelling")
            self._log("Cancelling download...", ACCENT_2)

    # ---------- queue polling ----------

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_queue.get_nowait()
                if kind == "info_ready":
                    self._stop_fetching_animation()
                    self._stop_spinner()
                    self.title_var.set(payload)
                    self._log("Video information loaded.")
                    self._pulse_panel_border()
                elif kind == "thumbnail_ready":
                    self.thumbnail_photo = ImageTk.PhotoImage(payload)
                    self.thumb_label.configure(image=self.thumbnail_photo, width=160, height=90)
                elif kind == "info_error":
                    self._stop_fetching_animation()
                    self._stop_spinner(final_text="Ready")
                    self.title_var.set("Could not load video information. Check the link and try again.")
                    self._log(f"Fetch info failed: {payload}", ERROR)
                elif kind == "progress":
                    self.progress_value.set(payload)
                elif kind == "status":
                    self._stop_spinner()
                    self.status_var.set(payload)
                elif kind == "merging_start":
                    self.progress_bar.configure(mode="indeterminate")
                    self.progress_bar.start(12)
                    self._start_spinner("Processing / merging streams")
                elif kind == "last_file":
                    self.last_downloaded_path = payload
                elif kind == "done_ok":
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    self.progress_value.set(100)
                    self._stop_spinner(final_text="Download complete")
                    self._log(f"Download finished. Saved to: {payload}", SUCCESS)
                    self._reset_buttons()
                    self.open_folder_btn.state(["!disabled"])
                    name = os.path.basename(self.last_downloaded_path) if self.last_downloaded_path else "Download"
                    self.recent_downloads.insert(0, {"name": name, "path": self.last_downloaded_path, "dir": payload})
                    self.recent_downloads = self.recent_downloads[:5]
                    self._refresh_recent_list()
                    self._show_toast("Download complete. Click Open Folder to view your file.", bg=SUCCESS, fg="#0B1310")
                elif kind == "done_cancelled":
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    self._stop_spinner(final_text="Cancelled")
                    self._log("Download cancelled by user.", ACCENT_2)
                    self._reset_buttons()
                elif kind == "done_error":
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    self._stop_spinner(final_text="Download failed")
                    self._log(f"Download failed: {payload}", ERROR)
                    self._reset_buttons()
                    self._show_toast("Download failed. See the activity log for details.", bg=ERROR, fg="#FFFFFF")
        except queue.Empty:
            pass
        self.after(150, self._poll_queue)

    def _reset_buttons(self):
        self.download_btn.state(["!disabled"])
        self.cancel_btn.state(["disabled"])

    def _pulse_panel_border(self, step=0):
        pulse_sequence = [ACCENT, ACCENT, BORDER_LIGHT, BORDER_LIGHT, BORDER]
        if step >= len(pulse_sequence):
            self.info_panel.configure(highlightbackground=BORDER_LIGHT)
            return
        self.info_panel.configure(highlightbackground=pulse_sequence[step])
        self.after(160, lambda: self._pulse_panel_border(step + 1))


def main():
    app = NWGrabioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
