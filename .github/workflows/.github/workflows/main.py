# NWGrabio for Android
# Grab Anything, From Anywhere.
# Developed by Nethum Welikada
# Master of Engineering in Internetworking, Dalhousie University, Halifax, Nova Scotia, Canada
# GitHub: https://github.com/NethumWelikada
#
# Same yt-dlp download engine as the Windows version of NWGrabio, with a
# touch-friendly Kivy interface built for phones and tablets.

import os
import threading

from kivy.app import App
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle

try:
    import yt_dlp
except ImportError:
    yt_dlp = None

APP_NAME = "NWGrabio"
APP_TAGLINE = "Grab Anything, From Anywhere."
DEVELOPER_NAME = "Nethum Welikada"
DEVELOPER_PROGRAM = "Master of Engineering in Internetworking"
DEVELOPER_SCHOOL = "Dalhousie University, Halifax, Nova Scotia, Canada"

BG_MAIN = (247 / 255, 248 / 255, 249 / 255, 1)
BG_CARD = (1, 1, 1, 1)
FG_TEXT = (0.10, 0.10, 0.10, 1)
FG_MUTED = (0.42, 0.45, 0.50, 1)
ACCENT = (0 / 255, 102 / 255, 255 / 255, 1)

# No ffmpeg is bundled on Android, so quality options are limited to
# formats that come pre-combined from the source, no separate merge step.
QUALITY_OPTIONS = {
    "Best available (no merge needed)": "best",
    "Up to 1080p": "best[height<=1080]",
    "Up to 720p": "best[height<=720]",
    "Up to 480p": "best[height<=480]",
    "Audio only (MP3)": "bestaudio/best",
}


def get_download_folder():
    try:
        from android.storage import primary_external_storage_path  # noqa
        base = primary_external_storage_path()
        folder = os.path.join(base, "Download", "NWGrabio")
    except Exception:
        folder = os.path.join(os.path.expanduser("~"), "NWGrabio")
    os.makedirs(folder, exist_ok=True)
    return folder


def request_android_permissions():
    try:
        from android.permissions import request_permissions, Permission
        request_permissions([
            Permission.INTERNET,
            Permission.WRITE_EXTERNAL_STORAGE,
            Permission.READ_EXTERNAL_STORAGE,
        ])
    except Exception:
        pass


class Card(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=dp(14), spacing=dp(8), **kwargs)
        with self.canvas.before:
            Color(*BG_CARD)
            self._rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class SectionLabel(Label):
    def __init__(self, text, **kwargs):
        super().__init__(text=text, color=FG_TEXT, bold=True, halign="left",
                          size_hint_y=None, height=dp(24), **kwargs)
        self.bind(size=lambda *_: setattr(self, "text_size", self.size))


class NWGrabioApp(App):
    def build(self):
        self.title = f"{APP_NAME} - {APP_TAGLINE}"
        Window.clearcolor = BG_MAIN
        request_android_permissions()

        self.download_dir = get_download_folder()
        self.last_downloaded_path = None
        self.cancel_flag = threading.Event()
        self.download_thread = None
        self._fetch_trigger = None

        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))

        scroll = ScrollView(size_hint=(1, 1))
        content = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None, padding=(0, 0, 0, dp(20)))
        content.bind(minimum_height=content.setter("height"))
        scroll.add_widget(content)
        root.add_widget(scroll)

        # Header
        header = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(56))
        title_lbl = Label(text=f"[b]{APP_NAME}[/b]", markup=True, color=FG_TEXT,
                           font_size=dp(22), halign="left", size_hint_y=None, height=dp(30))
        title_lbl.bind(size=lambda *_: setattr(title_lbl, "text_size", title_lbl.size))
        tagline_lbl = Label(text=APP_TAGLINE, color=ACCENT, bold=True, font_size=dp(13),
                             halign="left", size_hint_y=None, height=dp(22))
        tagline_lbl.bind(size=lambda *_: setattr(tagline_lbl, "text_size", tagline_lbl.size))
        header.add_widget(title_lbl)
        header.add_widget(tagline_lbl)
        content.add_widget(header)

        # Card: link
        link_card = Card(size_hint_y=None, height=dp(190))
        link_card.add_widget(SectionLabel("Add a link"))
        self.url_input = TextInput(
            hint_text="Paste a YouTube, Facebook, TikTok, Instagram link...",
            multiline=False, size_hint_y=None, height=dp(44),
            background_color=(0.96, 0.97, 0.99, 1), foreground_color=FG_TEXT,
        )
        self.url_input.bind(text=self._on_url_changed)
        link_card.add_widget(self.url_input)

        self.info_label = Label(
            text="Paste a link above. Details load automatically.",
            color=FG_MUTED, font_size=dp(12), halign="left", valign="top",
            size_hint_y=None, height=dp(70),
        )
        self.info_label.bind(size=lambda *_: setattr(self.info_label, "text_size", self.info_label.size))
        link_card.add_widget(self.info_label)
        content.add_widget(link_card)

        # Card: settings
        settings_card = Card(size_hint_y=None, height=dp(120))
        settings_card.add_widget(SectionLabel("Quality"))
        self.quality_spinner = Spinner(
            text=list(QUALITY_OPTIONS.keys())[0], values=list(QUALITY_OPTIONS.keys()),
            size_hint_y=None, height=dp(44), background_color=ACCENT,
        )
        settings_card.add_widget(self.quality_spinner)
        content.add_widget(settings_card)

        # Card: download action
        action_card = Card(size_hint_y=None, height=dp(150))
        action_card.add_widget(SectionLabel("Download"))
        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        self.download_btn = Button(text="Download", background_color=ACCENT)
        self.download_btn.bind(on_release=lambda *_: self.start_download())
        self.cancel_btn = Button(text="Cancel", background_color=(0.86, 0.20, 0.20, 1), disabled=True)
        self.cancel_btn.bind(on_release=lambda *_: self.cancel_download())
        self.open_btn = Button(text="Open File", background_color=(0.09, 0.64, 0.29, 1), disabled=True)
        self.open_btn.bind(on_release=lambda *_: self.open_downloaded_file())
        btn_row.add_widget(self.download_btn)
        btn_row.add_widget(self.cancel_btn)
        btn_row.add_widget(self.open_btn)
        action_card.add_widget(btn_row)

        self.progress = ProgressBar(max=100, size_hint_y=None, height=dp(8))
        action_card.add_widget(self.progress)

        self.status_label = Label(text="Ready", color=FG_MUTED, font_size=dp(12),
                                   halign="left", size_hint_y=None, height=dp(20))
        self.status_label.bind(size=lambda *_: setattr(self.status_label, "text_size", self.status_label.size))
        action_card.add_widget(self.status_label)
        content.add_widget(action_card)

        # Footer credit
        footer = Label(
            text=f"{DEVELOPER_NAME}  |  {DEVELOPER_PROGRAM}, {DEVELOPER_SCHOOL}",
            color=FG_MUTED, font_size=dp(10), halign="center",
            size_hint_y=None, height=dp(40),
        )
        footer.bind(size=lambda *_: setattr(footer, "text_size", (footer.width, None)))
        content.add_widget(footer)

        if yt_dlp is None:
            self._set_status("The download engine failed to load. Please reinstall the app.")

        return root

    # ---------- auto fetch ----------

    def _on_url_changed(self, _instance, value):
        if self._fetch_trigger:
            self._fetch_trigger.cancel()
        url = value.strip()
        if not (url.startswith("http://") or url.startswith("https://")):
            return
        self._fetch_trigger = Clock.schedule_once(lambda dt: self.fetch_info(url), 0.8)

    def fetch_info(self, url):
        if yt_dlp is None:
            return
        self.info_label.text = "Fetching video information..."
        threading.Thread(target=self._fetch_worker, args=(url,), daemon=True).start()

    def _fetch_worker(self, url):
        try:
            opts = {"quiet": True, "no_warnings": True, "skip_download": True, "noplaylist": True}
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            title = info.get("title", "Unknown title")
            uploader = info.get("uploader", "Unknown source")
            duration = info.get("duration")
            duration_str = ""
            if duration:
                minutes, seconds = divmod(int(duration), 60)
                duration_str = f"  |  {minutes}m {seconds}s"
            self._update_info(f"{title}\nSource: {uploader}{duration_str}")
        except Exception as exc:
            self._update_info(f"Could not load video info: {exc}")

    @mainthread
    def _update_info(self, text):
        self.info_label.text = text

    # ---------- download ----------

    def start_download(self):
        url = self.url_input.text.strip()
        if not url:
            self._set_status("Please paste a link first.")
            return
        if yt_dlp is None:
            self._set_status("The download engine is unavailable.")
            return
        if self.download_thread and self.download_thread.is_alive():
            return

        self.cancel_flag.clear()
        self.download_btn.disabled = True
        self.cancel_btn.disabled = False
        self.open_btn.disabled = True
        self.progress.value = 0
        self._set_status("Starting download...")

        self.download_thread = threading.Thread(target=self._download_worker, args=(url,), daemon=True)
        self.download_thread.start()

    def _download_worker(self, url):
        quality_label = self.quality_spinner.text
        fmt = QUALITY_OPTIONS.get(quality_label, "best")
        is_audio_only = quality_label.startswith("Audio only")

        def progress_hook(d):
            if self.cancel_flag.is_set():
                raise yt_dlp.utils.DownloadError("Cancelled by user")
            if d.get("status") == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                percent = (downloaded / total * 100) if total else 0
                self._update_progress(percent, f"Downloading {percent:0.1f}%")
            elif d.get("status") == "finished":
                fn = d.get("filename")
                if fn:
                    self.last_downloaded_path = fn
                self._update_progress(100, "Processing...")

        ydl_opts = {
            "format": fmt,
            "outtmpl": os.path.join(self.download_dir, "%(title)s.%(ext)s"),
            "progress_hooks": [progress_hook],
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
        }
        if is_audio_only:
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
            ]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self._download_done(True, f"Download complete. Saved to {self.download_dir}")
        except Exception as exc:
            if self.cancel_flag.is_set():
                self._download_done(False, "Cancelled.")
            else:
                self._download_done(False, f"Download failed: {exc}")

    def cancel_download(self):
        if self.download_thread and self.download_thread.is_alive():
            self.cancel_flag.set()
            self._set_status("Cancelling...")

    @mainthread
    def _update_progress(self, percent, text):
        self.progress.value = percent
        self.status_label.text = text

    @mainthread
    def _download_done(self, success, text):
        self.status_label.text = text
        self.download_btn.disabled = False
        self.cancel_btn.disabled = True
        if success:
            self.open_btn.disabled = False

    def _set_status(self, text):
        self.status_label.text = text

    # ---------- open / share file ----------

    def open_downloaded_file(self):
        if not self.last_downloaded_path or not os.path.isfile(self.last_downloaded_path):
            self._set_status("No downloaded file to open yet.")
            return
        try:
            from jnius import autoclass, cast

            Intent = autoclass("android.content.Intent")
            File = autoclass("java.io.File")
            FileProvider = autoclass("androidx.core.content.FileProvider")
            PythonActivity = autoclass("org.kivy.android.PythonActivity")

            activity = PythonActivity.mActivity
            file_obj = File(self.last_downloaded_path)
            authority = f"{activity.getPackageName()}.fileprovider"
            uri = FileProvider.getUriForFile(activity, authority, file_obj)

            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(uri, "video/*")
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            activity.startActivity(intent)
        except Exception as exc:
            self._set_status(f"Could not open file: {exc}")


if __name__ == "__main__":
    NWGrabioApp().run()
