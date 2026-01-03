import os
import sys
import threading
import subprocess
import requests
import re
from io import BytesIO
from PIL import Image, ImageFilter
import customtkinter as ctk
from tkinter import filedialog

# ==============================================================================
# ⚙️ CONFIGURATION
# ==============================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOWNLOAD_PATH = os.path.join(BASE_DIR, "Downloads") 
FFMPEG_PATH = "ffmpeg.exe"
ARIA2_PATH = "aria2c.exe"
COOKIES_PATH = "cookies.txt"

C_BG_MAIN  = "#0f0f12"
C_SIDEBAR  = "#18181b"
C_ACCENT   = "#7c5dfa" 
C_TEXT_DIM = "#a1a1aa"
C_SUCCESS  = "#10b981"

# ==============================================================================
# 🧠 ENGINE (BACKEND)
# ==============================================================================
class DownloadEngine:
    def __init__(self, log_callback, status_callback, meta_update_callback):
        self.log_callback = log_callback
        self.status_callback = status_callback
        self.meta_update_callback = meta_update_callback 
        self.total_songs = 0
        self.completed_songs = 0

    def get_metadata(self, url):
        # Quick fetch logic (Same as V16)
        cmd = [
            "yt-dlp", "--dump-json", "--no-playlist",
            "--skip-download", "--cookies", COOKIES_PATH, url
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', shell=True)
            if res.returncode == 0:
                import json
                data = json.loads(res.stdout.split('\n')[0])
                return {
                    "title": data.get('title', 'Unknown'),
                    "artist": data.get('uploader', 'Unknown'),
                    "thumbnail": data.get('thumbnail', None)
                }
        except: pass
        return None

    def run_download(self, url, folder, options):
        # options is a dictionary containing all our new Pro settings
        mode = options['mode']
        fmt = options['format']
        template = options['template'] # e.g. "{artist} - {title}"
        use_sponsorblock = options['sponsorblock']
        embed_thumb = options['embed_thumb']

        self.log_callback(f"🚀 ENGINE STARTED | Mode: {mode}")
        self.log_callback(f"⚙️ Config: SponsorBlock={use_sponsorblock}, Embed={embed_thumb}")
        os.makedirs(folder, exist_ok=True)
        self.total_songs = 0
        self.completed_songs = 0

        if mode == "audio":
            # SpotDL Command
            cmd = [
                "spotdl", "download", url,
                "--output", f"{folder}/{template}.{{output-ext}}",
                "--audio", "youtube-music", 
                "--cookie-file", COOKIES_PATH, "--simple-tui"
            ]
            
            # Format Logic
            if "Opus" in fmt: cmd.extend(["--format", "opus", "--bitrate", "disable"])
            elif "MP3" in fmt: cmd.extend(["--format", "mp3", "--bitrate", "320k"])
            else: cmd.extend(["--format", "m4a", "--bitrate", "disable"])
            
            # Pro Features for SpotDL
            if use_sponsorblock: cmd.append("--sponsor-block")
            if not embed_thumb: cmd.append("--skip-album-art")

        else:
            # yt-dlp Command (Video)
            # Convert simple template "{title}" to yt-dlp format "%(title)s"
            yt_template = template.replace("{title}", "%(title)s").replace("{artist}", "%(uploader)s")
            
            cmd = [
                "yt-dlp", url,
                "-f", "bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "--o", f"{folder}/{yt_template}.%(ext)s",
                "--cookies", COOKIES_PATH,
                "--external-downloader", "aria2c", 
                "--external-downloader-args", "-x 16 -s 16 -k 1M",
                "--ffmpeg-location", FFMPEG_PATH, 
            ]
            
            if embed_thumb: cmd.extend(["--embed-thumbnail", "--add-metadata"])
            if use_sponsorblock: cmd.extend(["--sponsorblock-remove", "all"])

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', shell=True
        )

        for line in process.stdout:
            line = line.strip()
            if not line: continue
            self.log_callback(line)
            lower = line.lower()
            
            if "found" in lower and "songs" in lower:
                try:
                    nums = re.findall(r'\d+', line)
                    if nums:
                        self.total_songs = int(nums[0])
                        self.status_callback(f"🎉 Playlist Found: {self.total_songs} Songs")
                except: pass

            if "downloaded" in lower and "\"" in lower: 
                self.completed_songs += 1
                display_total = self.total_songs if self.total_songs > 0 else "?"
                self.status_callback(f"✅ Progress: {self.completed_songs} / {display_total}")

            if mode == "audio" and "downloading" in lower and "-" in line and ":" in line:
                try:
                    parts = line.split(':')[0] 
                    if " - " in parts:
                        artist_live, title_live = parts.split(" - ", 1)
                        self.meta_update_callback(title_live.strip(), artist_live.strip())
                except: pass
            
            if "downloading" in lower and "%" in lower and self.total_songs == 0:
                self.status_callback(f"⚡ Downloading... {line[:15]}...")

# ==============================================================================
# ⚙️ ADVANCED SETTINGS POPUP (Like YTDLnis)
# ==============================================================================
class AdvancedSettings(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Advanced Configuration")
        self.geometry("400x450")
        self.configure(fg_color=C_BG_MAIN)
        self.resizable(False, False)
        
        # Title
        ctk.CTkLabel(self, text="DOWNLOAD SETTINGS", font=("Impact", 18), text_color="gray").pack(pady=20)

        # 1. Filename Template
        ctk.CTkLabel(self, text="Filename Template:", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)
        self.template_var = ctk.StringVar(value="{artist} - {title}")
        self.entry_temp = ctk.CTkEntry(self, textvariable=self.template_var, fg_color=C_SIDEBAR)
        self.entry_temp.pack(fill="x", padx=20, pady=(5, 10))
        
        # Hints
        ctk.CTkLabel(self, text="Tags: {artist}, {title}, {album}", font=("Consolas", 10), text_color="gray").pack(anchor="w", padx=20)

        # 2. SponsorBlock
        self.sb_switch = ctk.CTkSwitch(self, text="Enable SponsorBlock (Skip Intros)", progress_color=C_ACCENT)
        self.sb_switch.pack(pady=20, padx=20, anchor="w")

        # 3. Embed Thumbnail
        self.thumb_switch = ctk.CTkSwitch(self, text="Embed Album Art", progress_color=C_ACCENT)
        self.thumb_switch.select() # On by default
        self.thumb_switch.pack(pady=5, padx=20, anchor="w")

        # Close Button
        ctk.CTkButton(self, text="Save & Close", fg_color=C_SUCCESS, command=self.destroy).pack(pady=30)

    def get_values(self):
        return {
            "template": self.template_var.get(),
            "sponsorblock": bool(self.sb_switch.get()),
            "embed_thumb": bool(self.thumb_switch.get())
        }

# ==============================================================================
# 🖥️ DASHBOARD UI
# ==============================================================================
class XianzoDashboard(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("XIANZO DASHBOARD V17 [CONTROL EDITION]")
        self.geometry("900x600")
        self.configure(fg_color=C_BG_MAIN)
        self.resizable(False, False)

        self.engine = DownloadEngine(self.append_log, self.update_status, self.update_live_meta)
        self.save_path = DEFAULT_DOWNLOAD_PATH
        self.is_terminal_open = False
        
        # Default Advanced Settings
        self.adv_options = {
            "template": "{artist} - {title}",
            "sponsorblock": False,
            "embed_thumb": True
        }

        self.setup_ui()

    def setup_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # === LEFT SIDEBAR ===
        self.sidebar = ctk.CTkFrame(self, width=280, fg_color=C_SIDEBAR, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.art_frame = ctk.CTkFrame(self.sidebar, width=220, height=220, fg_color=C_BG_MAIN, corner_radius=15)
        self.art_frame.pack(pady=(40, 20), padx=20)
        self.art_frame.pack_propagate(False)
        self.art_label = ctk.CTkLabel(self.art_frame, text="🎵", font=("Arial", 60), text_color=C_ACCENT)
        self.art_label.place(relx=0.5, rely=0.5, anchor="center")

        self.lbl_title = ctk.CTkLabel(self.sidebar, text="Ready", font=("Arial", 16, "bold"), wraplength=240)
        self.lbl_title.pack(pady=5)
        self.lbl_artist = ctk.CTkLabel(self.sidebar, text="Waiting for link...", text_color=C_TEXT_DIM)
        self.lbl_artist.pack(pady=0)

        self.mode_switch = ctk.CTkSwitch(self.sidebar, text="Video Mode (4K)", progress_color=C_ACCENT, command=self.toggle_mode_ui)
        self.mode_switch.pack(pady=(40, 0))

        # === RIGHT DASHBOARD ===
        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

        ctk.CTkLabel(self.main_area, text="MEDIA AGENT", font=("Impact", 24), text_color=C_TEXT_DIM).pack(anchor="w")

        self.entry_link = ctk.CTkEntry(self.main_area, placeholder_text="Paste Spotify/YouTube Link...", height=50, font=("Arial", 14))
        self.entry_link.pack(fill="x", pady=(20, 10))

        # Folder & Settings Row
        self.ctrl_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        self.ctrl_frame.pack(fill="x", pady=5)
        
        self.btn_browse = ctk.CTkButton(self.ctrl_frame, text="📂 Change Folder", width=120, fg_color=C_SIDEBAR, command=self.select_folder)
        self.btn_browse.pack(side="left")
        
        # ⚙️ NEW: SETTINGS BUTTON
        self.btn_settings = ctk.CTkButton(self.ctrl_frame, text="⚙️ Settings", width=100, fg_color=C_SIDEBAR, command=self.open_settings)
        self.btn_settings.pack(side="left", padx=10)
        
        self.lbl_path = ctk.CTkLabel(self.ctrl_frame, text=f".../{os.path.basename(self.save_path)}", text_color="gray")
        self.lbl_path.pack(side="left", padx=10)

        ctk.CTkLabel(self.main_area, text="AUDIO FORMAT TARGET:", font=("Arial", 10, "bold"), text_color="gray").pack(anchor="w", pady=(15, 5))
        self.fmt_var = ctk.StringVar(value="M4A (Recommended)")
        self.fmt_selector = ctk.CTkSegmentedButton(self.main_area, values=["M4A (Recommended)", "Opus (Best Quality)", "MP3 (Legacy)"],
                                                   variable=self.fmt_var, selected_color=C_ACCENT, height=35)
        self.fmt_selector.pack(fill="x", pady=(0, 15))

        self.btn_start = ctk.CTkButton(self.main_area, text="START DOWNLOAD", height=60, 
                                       fg_color=C_ACCENT, font=("Arial", 16, "bold"), command=self.start_process)
        self.btn_start.pack(fill="x", pady=(10, 10))

        self.lbl_status = ctk.CTkLabel(self.main_area, text="System Idle", font=("Consolas", 18, "bold"), text_color=C_SUCCESS)
        self.lbl_status.pack(pady=10)

        self.term_btn = ctk.CTkButton(self.main_area, text="Show System Logs ▼", fg_color="transparent", 
                                      text_color="gray", hover_color=C_SIDEBAR, command=self.toggle_terminal)
        self.term_btn.pack(side="bottom", anchor="e")

        self.terminal = ctk.CTkTextbox(self.main_area, height=150, fg_color="#000000", text_color="#00ff00", font=("Consolas", 12))

    # ======================================================
    # 🎮 LOGIC
    # ======================================================
    def select_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.save_path = path
            self.lbl_path.configure(text=f".../{os.path.basename(path)}")

    def open_settings(self):
        # Open the popup
        self.popup = AdvancedSettings(self)
        # Wait for it to close to capture values (simple implementation)
        self.wait_window(self.popup)
        # Update our options dictionary
        try:
            new_vals = self.popup.get_values()
            self.adv_options.update(new_vals)
            print("Settings Saved:", self.adv_options)
        except: pass

    def toggle_terminal(self):
        if self.is_terminal_open:
            self.terminal.pack_forget()
            self.term_btn.configure(text="Show System Logs ▼")
            self.is_terminal_open = False
        else:
            self.terminal.pack(fill="x", pady=10, side="bottom")
            self.term_btn.configure(text="Hide System Logs ▲")
            self.is_terminal_open = True

    def toggle_mode_ui(self):
        if self.mode_switch.get() == 1:
            self.fmt_selector.configure(state="disabled")
        else:
            self.fmt_selector.configure(state="normal")

    def start_process(self):
        url = self.entry_link.get().strip()
        if not url: return

        self.btn_start.configure(state="disabled", text="ANALYZING...")
        self.lbl_title.configure(text="Scanning...")
        threading.Thread(target=self.run_sequence, args=(url,), daemon=True).start()

    def run_sequence(self, url):
        self.update_status("🔍 Scanning Metadata...")
        meta = self.engine.get_metadata(url)
        if meta: self.after(0, lambda: self.update_ui_meta(meta))
        
        # Prepare Options Packet
        options = self.adv_options.copy()
        options['mode'] = "video" if self.mode_switch.get() == 1 else "audio"
        options['format'] = self.fmt_var.get()
        
        self.engine.run_download(url, self.save_path, options)
        self.after(0, lambda: self.btn_start.configure(state="normal", text="START DOWNLOAD"))

    def update_ui_meta(self, meta):
        self.lbl_title.configure(text=meta['title'])
        self.lbl_artist.configure(text=meta['artist'])
        if meta['thumbnail']:
            try:
                resp = requests.get(meta['thumbnail'])
                img = Image.open(BytesIO(resp.content))
                ctk_img = ctk.CTkImage(img, size=(200, 200))
                self.art_label.configure(image=ctk_img, text="")
            except: pass

    def update_live_meta(self, title, artist):
        self.after(0, lambda: self.lbl_title.configure(text=title))
        self.after(0, lambda: self.lbl_artist.configure(text=artist))

    def append_log(self, text):
        self.terminal.insert("end", text + "\n")
        self.terminal.see("end")

    def update_status(self, text):
        self.lbl_status.configure(text=text)

if __name__ == "__main__":
    app = XianzoDashboard()
    app.mainloop()