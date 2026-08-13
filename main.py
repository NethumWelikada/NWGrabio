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
import json
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
GITHUB_REPO = "NethumWelikada/NWGrabio"
GITHUB_RELEASES_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases/latest"
WEBSITE_URL = "https://nethumwelikada.github.io/NWGrabio/"


def resource_path(relative_path):
    """Resolve a bundled resource path whether running from source or from
    a PyInstaller build (onefile or onedir)."""
    base_path = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


# Brand palette. Only three colors are the brand's own: ACCENT, TEXT, and
# BACKGROUND. Panel and border tones below are neutral shades built from
# that same background so the interface stays cohesive without introducing
# new brand colors. SUCCESS and ERROR are kept as the minimum functional
# colors needed for clear pass/fail feedback, which is standard even in
# strictly branded interfaces.
BG_MAIN = "#F7F8F9"
BG_CARD = "#FFFFFF"
BG_CARD_TINT = "#EAF1FF"
BG_FIELD = "#FFFFFF"
FG_TEXT = "#1A1A1A"
FG_MUTED = "#6B7280"
ACCENT = "#0066FF"
ACCENT_HOVER = "#0052CC"
BORDER = "#E4E7EC"
BORDER_LIGHT = "#D0D5DD"
SUCCESS = "#16A34A"
ERROR = "#DC2626"

# Kept as aliases so the rest of the file, which was written against a dark
# theme, needs no further renaming.
BG_DARK = BG_MAIN
BG_GLASS = BG_CARD
BG_GLASS_LIGHT = BG_CARD_TINT
ACCENT_2 = ACCENT_HOVER

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


SETTINGS_FILE = os.path.join(os.path.expanduser("~"), ".nwgrabio_settings.json")


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(updates):
    settings = load_settings()
    settings.update(updates)
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f)
    except Exception:
        pass


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


def parse_version(text):
    """Turn '1.3.0' or 'v1.3.0' into (1, 3, 0) for comparison. Returns None
    if the text doesn't look like a version number."""
    text = text.strip().lstrip("vV")
    parts = text.split(".")
    try:
        return tuple(int(p) for p in parts)
    except ValueError:
        return None


def looks_like_url(text):
    text = text.strip().lower()
    return text.startswith("http://") or text.startswith("https://")


class Select2Combo(tk.Frame):
    """A searchable dropdown selector styled like the Select2 pattern common
    in modern web apps: a clickable field showing the current value, and a
    popup with a live-filter search box above the option list."""

    def __init__(self, parent, values, textvariable, on_change=None):
        super().__init__(parent, bg=BG_MAIN)
        self.values = list(values)
        self.var = textvariable
        self.on_change = on_change
        self.popup = None

        self.field = tk.Frame(self, bg=BG_FIELD, highlightbackground=BORDER_LIGHT,
                               highlightthickness=1, cursor="hand2")
        self.field.pack(fill="x")

        self.value_label = tk.Label(self.field, textvariable=self.var, bg=BG_FIELD, fg=FG_TEXT,
                                     font=("Segoe UI", 9), anchor="w", cursor="hand2")
        self.value_label.pack(side="left", fill="x", expand=True, padx=10, pady=5)

        self.arrow_label = tk.Label(self.field, text="\u25BE", bg=BG_FIELD, fg=FG_MUTED,
                                     font=("Segoe UI", 9), cursor="hand2")
        self.arrow_label.pack(side="right", padx=10)

        for widget in (self.field, self.value_label, self.arrow_label):
            widget.bind("<Button-1>", self._toggle)

    def _toggle(self, event=None):
        if self.popup is not None:
            self._close()
        else:
            self._open()

    def _open(self):
        self.field.configure(highlightbackground=ACCENT)
        self.popup = tk.Toplevel(self)
        self.popup.overrideredirect(True)
        self.popup.configure(bg=BORDER_LIGHT)

        height = min(220, 26 * len(self.values) + 38)
        self._popup_height = height
        self._reposition_popup()

        self.search_var = tk.StringVar()
        search_entry = tk.Entry(self.popup, textvariable=self.search_var, bg=BG_FIELD, fg=FG_TEXT,
                                 relief="flat", font=("Segoe UI", 10), insertbackground=FG_TEXT)
        search_entry.pack(fill="x", padx=1, pady=(1, 0), ipady=3, ipadx=6)
        search_entry.focus_set()
        search_entry.bind("<KeyRelease>", self._filter)
        search_entry.bind("<Escape>", lambda e: self._close())

        self.list_frame = tk.Frame(self.popup, bg=BG_FIELD)
        self.list_frame.pack(fill="both", expand=True, padx=1, pady=(0, 1))

        self._render_options(self.values)
        self.popup.bind("<FocusOut>", lambda e: self.after(120, self._close_if_unfocused))

        # Keep the popup glued to the field if the main window is moved or
        # resized while the dropdown is open, instead of staying pinned to
        # its original screen position.
        self._root_window = self.winfo_toplevel()
        self._root_configure_id = self._root_window.bind("<Configure>", self._on_root_configure, add="+")

    def _on_root_configure(self, event=None):
        if self.popup is None:
            return
        self._reposition_popup()

    def _reposition_popup(self):
        if self.popup is None:
            return
        x = self.field.winfo_rootx()
        y = self.field.winfo_rooty() + self.field.winfo_height() + 2
        width = self.field.winfo_width()
        height = getattr(self, "_popup_height", 220)
        self.popup.geometry(f"{width}x{height}+{x}+{y}")

    def _close_if_unfocused(self):
        if self.popup is None:
            return
        try:
            focused = self.popup.focus_get()
        except Exception:
            focused = None
        if focused is None:
            self._close()

    def _render_options(self, values):
        for child in self.list_frame.winfo_children():
            child.destroy()
        if not values:
            tk.Label(self.list_frame, text="No matches", bg=BG_FIELD, fg=FG_MUTED,
                     font=("Segoe UI", 9), anchor="w", padx=12, pady=8).pack(fill="x")
            return
        for value in values:
            row = tk.Label(self.list_frame, text=value, bg=BG_FIELD, fg=FG_TEXT, anchor="w",
                            font=("Segoe UI", 9), padx=10, pady=5, cursor="hand2")
            row.pack(fill="x")
            row.bind("<Enter>", lambda e, r=row: r.configure(bg=BG_CARD_TINT, fg=ACCENT))
            row.bind("<Leave>", lambda e, r=row: r.configure(bg=BG_FIELD, fg=FG_TEXT))
            row.bind("<Button-1>", lambda e, v=value: self._select(v))

    def _filter(self, event=None):
        query = self.search_var.get().strip().lower()
        filtered = [v for v in self.values if query in v.lower()] if query else self.values
        self._render_options(filtered)

    def _select(self, value):
        self.var.set(value)
        self._close()
        if self.on_change:
            self.on_change(value)

    def _close(self):
        self.field.configure(highlightbackground=BORDER_LIGHT)
        if getattr(self, "_root_configure_id", None):
            try:
                self._root_window.unbind("<Configure>", self._root_configure_id)
            except Exception:
                pass
            self._root_configure_id = None
        if self.popup is not None:
            try:
                self.popup.destroy()
            except Exception:
                pass
            self.popup = None


class NWGrabioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} - {APP_TAGLINE}")
        self.geometry("640x635")
        self.minsize(620, 615)
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
                icon_img = icon_img.resize((28, 28), Image.LANCZOS)
                self._app_icon_image = ImageTk.PhotoImage(icon_img)
            except Exception:
                self._app_icon_image = None

        self.output_dir = tk.StringVar(value=get_default_download_folder())
        self.url_var = tk.StringVar()
        saved_settings = load_settings()
        saved_quality = saved_settings.get("quality")
        default_quality = saved_quality if saved_quality in QUALITY_OPTIONS else list(QUALITY_OPTIONS.keys())[0]
        self.quality_var = tk.StringVar(value=default_quality)
        self.playlist_var = tk.BooleanVar(value=False)
        self.subtitles_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.title_var = tk.StringVar(
            value="Paste a video or page link above. NWGrabio fetches details automatically, no extra clicks."
        )
        self.progress_value = tk.DoubleVar(value=0.0)
        self.thumbnail_photo = None
        self.last_downloaded_path = None
        self.recent_downloads = []
        self.download_queue = []

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
        self.after(2000, lambda: self._check_for_updates(manual=False))
        self.after(60, self._fade_in)

    # ---------- window chrome ----------

    WINDOW_ALPHA = 1.0

    def _fade_in(self):
        try:
            alpha = float(self.attributes("-alpha"))
        except Exception:
            return
        if alpha < self.WINDOW_ALPHA:
            alpha = min(self.WINDOW_ALPHA, alpha + 0.1)
            try:
                self.attributes("-alpha", alpha)
            except Exception:
                return
            self.after(12, self._fade_in)

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
        help_menu.add_command(label="About NWGrabio", command=self._show_about)
        help_menu.add_command(label="Check for Updates", command=lambda: self._check_for_updates(manual=True))
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
                         bordercolor=BORDER_LIGHT, lightcolor=BG_FIELD, darkcolor=BG_FIELD, padding=5)

        style.configure("TCombobox", fieldbackground=BG_FIELD, background=BG_FIELD, foreground=FG_TEXT,
                         arrowcolor=FG_TEXT, bordercolor=BORDER_LIGHT, padding=6)
        style.map("TCombobox", fieldbackground=[("readonly", BG_FIELD)], foreground=[("readonly", FG_TEXT)])
        self.option_add("*TCombobox*Listbox*Background", BG_FIELD)
        self.option_add("*TCombobox*Listbox*Foreground", FG_TEXT)
        self.option_add("*TCombobox*Listbox*selectBackground", ACCENT)

        style.configure("Accent.TButton", background=ACCENT, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"),
                         padding=6, borderwidth=0)
        style.map("Accent.TButton", background=[("active", ACCENT_HOVER), ("disabled", BORDER)])

        style.configure("Secondary.TButton", background=BG_GLASS_LIGHT, foreground=FG_TEXT, font=("Segoe UI", 9),
                         padding=5, borderwidth=1)
        style.map("Secondary.TButton", background=[("active", BORDER_LIGHT)])

        style.configure("Danger.TButton", background=ERROR, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"),
                         padding=5, borderwidth=0)
        style.map("Danger.TButton", background=[("disabled", BORDER)])

        style.configure("Success.TButton", background=SUCCESS, foreground="#FFFFFF", font=("Segoe UI", 9, "bold"),
                         padding=5, borderwidth=0)
        style.map("Success.TButton", background=[("disabled", BORDER)])

        style.configure("Dark.Horizontal.TProgressbar", troughcolor=BG_FIELD, background=ACCENT,
                         bordercolor=BG_FIELD, lightcolor=ACCENT, darkcolor=ACCENT, thickness=7)

        style.configure("TCheckbutton", background=BG_DARK, foreground=FG_TEXT, font=("Segoe UI", 8))
        style.map("TCheckbutton", background=[("active", BG_DARK)])

    # ---------- layout ----------

    def _build_layout(self):
        self._wrap_labels = []
        self._build_download_tab(self)

    def _section_label(self, parent, text):
        row = tk.Frame(parent, bg=BG_MAIN)
        row.pack(fill="x", anchor="w", pady=(0, 4))
        tk.Frame(row, bg=ACCENT, width=3, height=12).pack(side="left", padx=(0, 6), pady=(1, 0))
        tk.Label(row, text=text, bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 9, "bold")).pack(side="left")

    def _card(self, parent, **pack_opts):
        card = tk.Frame(parent, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        defaults = dict(fill="x", pady=(0, 8))
        defaults.update(pack_opts)
        card.pack(**defaults)
        inner = tk.Frame(card, bg=BG_CARD)
        inner.pack(fill="both", expand=True, padx=12, pady=8)
        return inner

    def _build_download_tab(self, root):
        content = root
        pad = 14

        # Header
        header = tk.Frame(content, bg=BG_MAIN)
        header.pack(fill="x", padx=pad, pady=(12, 3))

        logo_holder = tk.Frame(header, bg=BG_MAIN, width=28, height=28)
        logo_holder.pack(side="left", padx=(0, 12))
        logo_holder.pack_propagate(False)
        if self._app_icon_image is not None:
            tk.Label(logo_holder, image=self._app_icon_image, bg=BG_MAIN).pack(fill="both", expand=True)
        else:
            logo_canvas = tk.Canvas(logo_holder, width=28, height=28, bg=BG_MAIN, highlightthickness=0)
            logo_canvas.pack(fill="both", expand=True)
            logo_canvas.create_oval(1, 1, 27, 27, outline=ACCENT, width=2)
            logo_canvas.create_line(14, 8, 14, 18, fill=ACCENT, width=3)
            logo_canvas.create_polygon(8, 14, 20, 14, 14, 22, fill=ACCENT)

        title_col = tk.Frame(header, bg=BG_MAIN)
        title_col.pack(side="left")
        tk.Label(title_col, text=APP_NAME, bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(title_col, text=APP_TAGLINE, bg=BG_MAIN, fg=ACCENT, font=("Segoe UI", 8, "bold")).pack(anchor="w")

        badges = tk.Frame(content, bg=BG_MAIN)
        badges.pack(fill="x", padx=pad, pady=(2, 8))
        for name in SUPPORTED_SITE_BADGES:
            tk.Label(badges, text=name, bg=BG_CARD_TINT, fg=ACCENT, font=("Segoe UI", 7, "bold"),
                     padx=5, pady=1).pack(side="left", padx=(0, 4))

        # Card: add a link
        link_card = self._card(content, padx=pad)
        self._section_label(link_card, "Add a link")

        entry_row = tk.Frame(link_card, bg=BG_CARD)
        entry_row.pack(fill="x")
        self.url_entry = ttk.Entry(entry_row, textvariable=self.url_var, style="TEntry")
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=1)
        self.url_entry.bind("<Return>", lambda e: self._fetch_info())
        ttk.Button(entry_row, text="Paste", style="Secondary.TButton", command=self._paste_url).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(entry_row, text="+ Queue", style="Secondary.TButton", command=self._add_to_queue).pack(
            side="left", padx=(8, 0)
        )
        ttk.Button(entry_row, text="Clear", style="Secondary.TButton", command=self._clear_url).pack(
            side="left", padx=(8, 0)
        )

        self.queue_hint_var = tk.StringVar(value="Paste a link, details load automatically.")
        tk.Label(link_card, textvariable=self.queue_hint_var,
                 bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 5))

        preview_row = tk.Frame(link_card, bg=BG_CARD_TINT, highlightbackground=BORDER, highlightthickness=1)
        preview_row.pack(fill="x")
        preview_inner = tk.Frame(preview_row, bg=BG_CARD_TINT)
        preview_inner.pack(fill="x", padx=8, pady=6)

        self.thumb_label = tk.Label(preview_inner, bg=BG_FIELD, width=10, height=3)
        self.thumb_label.pack(side="left", padx=(0, 8))

        title_label = tk.Label(preview_inner, textvariable=self.title_var, bg=BG_CARD_TINT, fg=FG_TEXT,
                                font=("Segoe UI", 9), wraplength=380, justify="left", anchor="w")
        title_label.pack(side="left", fill="x", expand=True, anchor="w")
        self._wrap_labels.append(title_label)
        self.info_panel = preview_row

        # Card: download settings
        settings_card = self._card(content, padx=pad)
        self._section_label(settings_card, "Download settings")

        options_row = tk.Frame(settings_card, bg=BG_CARD)
        options_row.pack(fill="x")

        quality_col = tk.Frame(options_row, bg=BG_CARD)
        quality_col.pack(side="left", fill="x", expand=True)
        tk.Label(quality_col, text="Quality", bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        self.quality_combo = Select2Combo(
            quality_col, values=list(QUALITY_OPTIONS.keys()), textvariable=self.quality_var,
            on_change=lambda v: save_settings({"quality": v})
        )
        self.quality_combo.pack(fill="x", pady=(2, 0))
        ttk.Checkbutton(
            quality_col, text="Download full playlist",
            variable=self.playlist_var, style="TCheckbutton"
        ).pack(anchor="w", pady=(6, 0))
        ttk.Checkbutton(
            quality_col, text="Also save subtitles (.srt)",
            variable=self.subtitles_var, style="TCheckbutton"
        ).pack(anchor="w", pady=(3, 0))

        folder_col = tk.Frame(options_row, bg=BG_CARD)
        folder_col.pack(side="left", fill="x", expand=True, padx=(14, 0))
        tk.Label(folder_col, text="Save to folder", bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 8)).pack(anchor="w")
        folder_inner = tk.Frame(folder_col, bg=BG_CARD)
        folder_inner.pack(fill="x", pady=(2, 0))
        self.folder_entry = ttk.Entry(folder_inner, textvariable=self.output_dir, style="TEntry")
        self.folder_entry.pack(side="left", fill="x", expand=True, ipady=1)
        ttk.Button(folder_inner, text="Browse", style="Secondary.TButton", command=self._browse_folder).pack(
            side="left", padx=(6, 0)
        )

        # Toast banner, hidden until a download completes or fails
        self.toast = tk.Label(content, bg=SUCCESS, fg="#FFFFFF", font=("Segoe UI", 8, "bold"), anchor="w", padx=10, pady=4)

        # Card: download action, progress, and status
        action_card = self._card(content, padx=pad)
        self._action_card_frame = action_card.master
        self._section_label(action_card, "Download")

        action_row = tk.Frame(action_card, bg=BG_CARD)
        action_row.pack(fill="x")
        self.download_btn = ttk.Button(action_row, text="Download", style="Accent.TButton", command=self._start_download)
        self.download_btn.pack(side="left")
        self.cancel_btn = ttk.Button(action_row, text="Cancel", style="Danger.TButton", command=self._cancel_download)
        self.cancel_btn.pack(side="left", padx=(6, 0))
        self.cancel_btn.state(["disabled"])
        self.open_folder_btn = ttk.Button(
            action_row, text="Open Folder", style="Success.TButton", command=self._open_folder
        )
        self.open_folder_btn.pack(side="left", padx=(6, 0))
        self.open_folder_btn.state(["disabled"])

        self.progress_bar = ttk.Progressbar(
            action_card, style="Dark.Horizontal.TProgressbar", variable=self.progress_value, maximum=100
        )
        self.progress_bar.pack(fill="x", ipady=2, pady=(8, 3))

        status_label = tk.Label(action_card, textvariable=self.status_var, bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 8))
        status_label.pack(anchor="w")

        # Activity log and recent downloads, side by side, sized to fit
        # within the window without needing an internal scrollbar.
        body_row = tk.Frame(content, bg=BG_MAIN)
        body_row.pack(fill="x", padx=pad, pady=(0, 10))

        log_col = tk.Frame(body_row, bg=BG_MAIN)
        log_col.pack(side="left", fill="both", expand=True)
        self._section_label(log_col, "Activity log")
        log_container = tk.Frame(log_col, bg=BG_FIELD, highlightbackground=BORDER, highlightthickness=1, height=90)
        log_container.pack(fill="x")
        log_container.pack_propagate(False)
        self.log_text = tk.Text(
            log_container, bg=BG_FIELD, fg=FG_TEXT, insertbackground=FG_TEXT, relief="flat",
            wrap="word", font=("Consolas", 8), padx=8, pady=4
        )
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll = ttk.Scrollbar(log_container, command=self.log_text.yview)
        log_scroll.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=log_scroll.set, state="disabled")

        recent_col = tk.Frame(body_row, bg=BG_MAIN)
        recent_col.pack(side="left", fill="both", padx=(10, 0))
        self._section_label(recent_col, "Recent downloads")
        self.recent_container = tk.Frame(recent_col, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1,
                                          width=190, height=90)
        self.recent_container.pack(fill="both")
        self.recent_container.pack_propagate(False)
        self._refresh_recent_list()

    # ---------- update check ----------

    def _check_for_updates(self, manual=False):
        threading.Thread(target=self._update_check_worker, args=(manual,), daemon=True).start()

    def _update_check_worker(self, manual):
        try:
            req = urllib.request.Request(
                GITHUB_RELEASES_API, headers={"Accept": "application/vnd.github+json", "User-Agent": "NWGrabio"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            latest_tag = data.get("tag_name", "")
            release_url = data.get("html_url", GITHUB_RELEASES_PAGE)

            current = parse_version(APP_VERSION)
            latest = parse_version(latest_tag)

            if current is not None and latest is not None and latest > current:
                self.msg_queue.put(("update_available", (latest_tag, release_url)))
            elif manual:
                self.msg_queue.put(("update_none", None))
        except Exception:
            if manual:
                self.msg_queue.put(("update_check_failed", None))

    def _show_update_dialog(self, latest_tag, release_url):
        win = tk.Toplevel(self)
        win.title("Update available")
        win.configure(bg=BG_MAIN)
        win.geometry("360x180")
        win.resizable(False, False)
        win.transient(self)
        try:
            win.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        tk.Label(win, text="A new version of NWGrabio is available",
                 bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 11, "bold"),
                 wraplength=320, justify="left").pack(anchor="w", padx=20, pady=(20, 4))
        tk.Label(win, text=f"You have {APP_VERSION}. The latest version is {latest_tag.lstrip('vV')}.",
                 bg=BG_MAIN, fg=FG_MUTED, font=("Segoe UI", 9),
                 wraplength=320, justify="left").pack(anchor="w", padx=20)

        btn_row = tk.Frame(win, bg=BG_MAIN)
        btn_row.pack(side="bottom", fill="x", padx=20, pady=20)
        ttk.Button(btn_row, text="Later", style="Secondary.TButton", command=win.destroy).pack(side="right")
        ttk.Button(
            btn_row, text="Download Update", style="Accent.TButton",
            command=lambda: (webbrowser.open(WEBSITE_URL), win.destroy())
        ).pack(side="right", padx=(0, 8))

    def _show_about(self):
        win = tk.Toplevel(self)
        win.title(f"About {APP_NAME}")
        win.configure(bg=BG_MAIN)
        win.geometry("480x460")
        win.resizable(False, False)
        win.transient(self)
        try:
            win.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        top_row = tk.Frame(win, bg=BG_MAIN)
        top_row.pack(fill="x", padx=24, pady=(22, 0))
        if self._app_icon_image is not None:
            tk.Label(top_row, image=self._app_icon_image, bg=BG_MAIN).pack(side="left", padx=(0, 12))
        title_col = tk.Frame(top_row, bg=BG_MAIN)
        title_col.pack(side="left")
        tk.Label(title_col, text=APP_NAME, bg=BG_MAIN, fg=FG_TEXT, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        tk.Label(title_col, text=APP_TAGLINE, bg=BG_MAIN, fg=ACCENT, font=("Segoe UI", 10, "bold")).pack(anchor="w")

        dev_card = tk.Frame(win, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        dev_card.pack(fill="x", padx=24, pady=18)
        dev_inner = tk.Frame(dev_card, bg=BG_CARD)
        dev_inner.pack(fill="x", padx=16, pady=14)

        def dev_row(label, value):
            r = tk.Frame(dev_inner, bg=BG_CARD)
            r.pack(fill="x", pady=3)
            tk.Label(r, text=label, bg=BG_CARD, fg=FG_MUTED, font=("Segoe UI", 9), width=12, anchor="w").pack(side="left")
            tk.Label(r, text=value, bg=BG_CARD, fg=FG_TEXT, font=("Segoe UI", 10), anchor="w").pack(side="left")

        dev_row("Version", APP_VERSION)
        dev_row("Developer", DEVELOPER_NAME)
        dev_row("Program", DEVELOPER_PROGRAM)
        dev_row("University", DEVELOPER_SCHOOL)

        link = tk.Label(dev_inner, text=DEVELOPER_GITHUB_LABEL, bg=BG_CARD, fg=ACCENT,
                         font=("Segoe UI", 10, "underline"), cursor="hand2", anchor="w")
        link.pack(anchor="w", pady=(8, 0))
        link.bind("<Button-1>", lambda e: webbrowser.open(DEVELOPER_GITHUB_URL))

        tk.Label(
            win, text="Licensed under the MIT License. Built with yt-dlp and ffmpeg, open source "
                      "projects used under their own licenses.",
            bg=BG_MAIN, fg=FG_MUTED, font=("Segoe UI", 9), wraplength=430, justify="left"
        ).pack(anchor="w", padx=24)

        tk.Label(
            win, text="Works with YouTube, Facebook, TikTok, Instagram, Twitter/X, Vimeo, Reddit, "
                      "and over 1000 other sites through the yt-dlp engine.",
            bg=BG_MAIN, fg=FG_MUTED, font=("Segoe UI", 9), wraplength=430, justify="left"
        ).pack(anchor="w", padx=24, pady=(10, 0))

        ttk.Button(win, text="Close", style="Secondary.TButton", command=win.destroy).pack(
            anchor="e", padx=24, pady=20
        )

    # ---------- recent downloads ----------

    def _refresh_recent_list(self):
        for child in self.recent_container.winfo_children():
            child.destroy()

        if not self.recent_downloads:
            tk.Label(
                self.recent_container, text="Nothing yet.",
                bg=BG_GLASS, fg=FG_MUTED, font=("Segoe UI", 8), wraplength=170, justify="left"
            ).pack(padx=8, pady=8, anchor="w")
            return

        for item in self.recent_downloads[:2]:
            row = tk.Frame(self.recent_container, bg=BG_GLASS_LIGHT, highlightbackground=BORDER, highlightthickness=1)
            row.pack(fill="x", padx=5, pady=3)
            name = item["name"] if len(item["name"]) <= 24 else item["name"][:21] + "..."
            tk.Label(row, text=name, bg=BG_GLASS_LIGHT, fg=FG_TEXT, font=("Segoe UI", 8), anchor="w",
                     wraplength=170, justify="left").pack(fill="x", padx=6, pady=(4, 1))
            open_link = tk.Label(row, text="Open folder", bg=BG_GLASS_LIGHT, fg=ACCENT,
                                  font=("Segoe UI", 7, "underline"), cursor="hand2", anchor="w")
            open_link.pack(fill="x", padx=6, pady=(0, 4))
            open_link.bind("<Button-1>", lambda e, p=item["path"], d=item["dir"]: self._open_folder(p, d))

    # ---------- toast ----------

    def _show_toast(self, text, bg=SUCCESS, fg="#FFFFFF", duration_ms=4000):
        self.toast.configure(text=text, bg=bg, fg=fg)
        self.toast.pack(fill="x", padx=14, pady=(0, 3), before=self._action_card_frame)
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

    def _add_to_queue(self):
        url = self.url_var.get().strip()
        if not looks_like_url(url):
            messagebox.showinfo(APP_NAME, "Paste a valid link first, then click + Queue.")
            return
        self.download_queue.append(url)
        self._clear_url()
        count = len(self.download_queue)
        self.queue_hint_var.set(
            f"{count} link{'s' if count != 1 else ''} queued. Paste another and click + Queue, "
            f"or click Download to start."
        )

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
        urls = list(self.download_queue)
        current = self.url_var.get().strip()
        if current and looks_like_url(current):
            urls.append(current)
        if not urls:
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

        self.download_queue = []
        self._clear_url()
        self.queue_hint_var.set("Paste a link, details load automatically.")

        self.cancel_flag.clear()
        self.download_btn.state(["disabled"])
        self.cancel_btn.state(["!disabled"])
        self.open_folder_btn.state(["disabled"])
        self.progress_bar.configure(mode="determinate")
        self.progress_value.set(0)
        self._start_spinner("Starting download")
        if len(urls) > 1:
            self._log(f"Starting batch download of {len(urls)} links.")
        else:
            self._log(f"Starting download: {urls[0]}")

        self.download_thread = threading.Thread(target=self._download_worker, args=(urls, out_dir), daemon=True)
        self.download_thread.start()

    def _download_worker(self, urls, out_dir):
        quality_label = self.quality_var.get()
        fmt = QUALITY_OPTIONS.get(quality_label, "bestvideo+bestaudio/best")
        is_audio_only = quality_label.startswith("Audio Only")
        total = len(urls)
        completed = 0
        failed = 0

        for idx, url in enumerate(urls, start=1):
            if self.cancel_flag.is_set():
                break

            prefix = f"Item {idx}/{total}  |  " if total > 1 else ""

            def progress_hook(d, prefix=prefix):
                if self.cancel_flag.is_set():
                    raise yt_dlp.utils.DownloadError("Cancelled by user")
                if d.get("status") == "downloading":
                    total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate")
                    downloaded = d.get("downloaded_bytes", 0)
                    percent = (downloaded / total_bytes * 100) if total_bytes else 0
                    speed = d.get("speed")
                    eta = d.get("eta")
                    speed_str = f"{speed / 1024 / 1024:.2f} MB/s" if speed else "..."
                    eta_str = f"{eta}s" if eta else "..."
                    self.msg_queue.put(("progress", percent))
                    self.msg_queue.put(("status", f"{prefix}Downloading  {percent:0.1f}%  |  {speed_str}  |  ETA {eta_str}"))
                elif d.get("status") == "finished":
                    self.msg_queue.put(("merging_start", prefix))
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
                # Explicitly enabled: if a download is cancelled or fails
                # partway through, downloading the same link again resumes
                # from the partial file instead of starting over.
                "continuedl": True,
            }

            if self.ffmpeg_path and self.ffmpeg_path != "ffmpeg":
                ydl_opts["ffmpeg_location"] = self.ffmpeg_path

            if self.subtitles_var.get():
                ydl_opts["writesubtitles"] = True
                ydl_opts["writeautomaticsub"] = True
                ydl_opts["subtitleslangs"] = ["en"]
                ydl_opts["subtitlesformat"] = "srt"

            if is_audio_only:
                ydl_opts["postprocessors"] = [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
                ]
                ydl_opts.pop("merge_output_format", None)

            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                completed += 1
                self.msg_queue.put(("item_done", out_dir))
            except Exception as exc:
                if self.cancel_flag.is_set():
                    break
                failed += 1
                self.msg_queue.put(("item_error", str(exc)))

        if self.cancel_flag.is_set():
            self.msg_queue.put(("batch_cancelled", None))
        else:
            self.msg_queue.put(("batch_finished", (completed, failed, out_dir)))

    def _cancel_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.cancel_flag.set()
            self._start_spinner("Cancelling")
            self._log("Cancelling download... Partial files are kept, so downloading the same link again will resume.", ACCENT_2)

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
                elif kind == "item_done":
                    self._log(f"Saved: {os.path.basename(self.last_downloaded_path or 'file')}", SUCCESS)
                    name = os.path.basename(self.last_downloaded_path) if self.last_downloaded_path else "Download"
                    self.recent_downloads.insert(0, {"name": name, "path": self.last_downloaded_path, "dir": payload})
                    self.recent_downloads = self.recent_downloads[:5]
                    self._refresh_recent_list()
                elif kind == "item_error":
                    self._log(f"An item in the queue failed: {payload}", ERROR)
                elif kind == "batch_finished":
                    completed, failed, out_dir = payload
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    self.progress_value.set(100)
                    self._reset_buttons()
                    if completed > 0:
                        self.open_folder_btn.state(["!disabled"])
                    if failed == 0:
                        summary = "Download complete" if completed == 1 else f"All {completed} downloads complete"
                        self._stop_spinner(final_text=summary)
                        self._show_toast(f"{summary}. Click Open Folder to view your files.", bg=SUCCESS, fg="#FFFFFF")
                    else:
                        summary = f"Finished: {completed} succeeded, {failed} failed"
                        self._stop_spinner(final_text=summary)
                        self._show_toast(f"{summary}. See the activity log for details.", bg=ERROR, fg="#FFFFFF")
                elif kind == "batch_cancelled":
                    self.progress_bar.stop()
                    self.progress_bar.configure(mode="determinate")
                    self._stop_spinner(final_text="Cancelled")
                    self._log("Download cancelled by user.", ACCENT_2)
                    self._reset_buttons()
                elif kind == "update_available":
                    latest_tag, release_url = payload
                    self._show_update_dialog(latest_tag, release_url)
                elif kind == "update_none":
                    messagebox.showinfo(APP_NAME, f"You're up to date. NWGrabio {APP_VERSION} is the latest version.")
                elif kind == "update_check_failed":
                    messagebox.showinfo(APP_NAME, "Could not check for updates. Check your internet connection and try again.")
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
