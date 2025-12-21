import os
import sys
import threading
import subprocess
import queue
import time
import psutil
import logging
from datetime import datetime
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

# ==============================================================================
# 🛡️ UNICODE & ENVIRONMENT STABILIZATION (CRITICAL FOR EMOJIS)
# ==============================================================================
# This forces the Python interpreter to handle emojis in playlists/songs
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass # Older python versions

# ==============================================================================
# 🛠️ GLOBAL SYSTEM CONFIGURATION
# ==============================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_PATH = os.path.join(BASE_DIR, "ffmpeg.exe")
LOG_FILE = os.path.join(BASE_DIR, "xianzo_core_v11.log")
DEFAULT_SAVE_PATH = "F:/Shlok/Downloads/SpotDL"

# Windows Process Flags (Stealth Execution)
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# ==============================================================================
# 🎨 UI DESIGN SYSTEM (MODERN CYBER)
# ==============================================================================
class Theme:
    BG_ROOT      = "#020617"
    BG_SIDEBAR   = "#0f172a"
    BG_CARD      = "#1e293b"
    ACCENT       = "#10b981"
    ACCENT_HOVER = "#059669"
    CRITICAL     = "#ef4444"
    WARNING      = "#f59e0b"
    TEXT_MAIN    = "#f8fafc"
    TEXT_DIM     = "#64748b"
    TERMINAL_BG  = "#000000"

# ==============================================================================
# 🧩 REUSABLE PRO COMPONENTS
# ==============================================================================
class NavItem(ctk.CTkButton):
    def __init__(self, master, text, command, icon="•", **kwargs):
        super().__init__(
            master=master, text=f"  {icon}  {text}", command=command,
            height=52, corner_radius=12, fg_color="transparent",
            text_color=Theme.TEXT_MAIN, hover_color=Theme.BG_CARD,
            anchor="w", font=("Roboto", 14, "bold"), **kwargs
        )

class InfoPanel(ctk.CTkFrame):
    def __init__(self, master, label_text, initial_val, **kwargs):
        super().__init__(master=master, fg_color=Theme.BG_CARD, corner_radius=18, **kwargs)
        self.label = ctk.CTkLabel(self, text=label_text.upper(), font=("Roboto", 10, "bold"), text_color=Theme.TEXT_DIM)
        self.label.pack(pady=(18, 0))
        self.value = ctk.CTkLabel(self, text=initial_val, font=("JetBrains Mono", 34, "bold"), text_color=Theme.ACCENT)
        self.value.pack(pady=(0, 18))

    def update(self, new_val):
        self.value.configure(text=str(new_val))

# ==============================================================================
# ⚙️ THE BEAST KERNEL (V11 ENGINE)
# ==============================================================================
class XKernel:
    def __init__(self, log_fn, progress_fn):
        self.log_fn = log_fn
        self.on_success = progress_fn
        self.proc = None
        self.abort_flag = threading.Event()
        
        logging.basicConfig(filename=LOG_FILE, level=logging.INFO, 
                            format='%(asctime)s | %(levelname)s | %(message)s')

    def _boost_priority(self):
        if sys.platform == "win32" and self.proc:
            try:
                p = psutil.Process(self.proc.pid)
                p.nice(psutil.HIGH_PRIORITY_CLASS)
            except: pass

    def run_engine(self, url, save_path, mode):
        self.abort_flag.clear()
        
        # 🛡️ CRITICAL FIX: Ensure Directory Exists
        try:
            os.makedirs(save_path, exist_ok=True)
        except Exception as e:
            self.log_fn(f"🔥 DIR ERROR: {str(e)}")
            return

        physical_cores = psutil.cpu_count(logical=True) or 4
        threads = str(physical_cores + 4) if "BEAST" in mode else "4"
        
        # --- THE XIANZO AUDIOPHILE COMMAND ---
        cmd = [
            "spotdl", "download", url,
            "--output", "{artist} - {title}.{output-ext}",
            "--format", "m4a",
            "--bitrate", "disable", 
            "--threads", threads,
            "--ffmpeg", FFMPEG_PATH,
            "--audio", "youtube-music", "youtube",
            "--simple-tui"
        ]

        # 🛡️ CRITICAL FIX: UTF-8 Subprocess Environment
        sub_env = os.environ.copy()
        sub_env["PYTHONIOENCODING"] = "utf-8"

        self.log_fn(f"🚀 KERNEL START | THREADS: {threads} | MODE: {mode}")

        try:
            self.proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, cwd=save_path, creationflags=CREATE_NO_WINDOW,
                env=sub_env, encoding="utf-8", errors="replace"
            )
            
            self._boost_priority()

            for line in iter(self.proc.stdout.readline, ""):
                if self.abort_flag.is_set(): break
                raw_out = line.strip()
                if not raw_out: continue
                
                if "Downloaded" in raw_out:
                    self.log_fn(f"✅ SUCCESS: {raw_out}")
                    self.on_success()
                elif "Processing" in raw_out:
                    self.log_fn(f"🔍 ANALYZING: {raw_out}")
                elif "error" in raw_out.lower():
                    self.log_fn(f"⚠️ LOG: {raw_out}")
                else:
                    self.log_fn(f"📡 {raw_out}")

            self.proc.wait()
            self.log_fn("✨ SEQUENCE TERMINATED.")
        except Exception as e:
            self.log_fn(f"🔥 CRITICAL FAILURE: {str(e)}")
        finally:
            self.proc = None

    def kill_sequence(self):
        self.abort_flag.set()
        if self.proc:
            try:
                parent = psutil.Process(self.proc.pid)
                for child in parent.children(recursive=True):
                    child.kill()
                parent.kill()
                self.log_fn("🛑 EMERGENCY STOP EXECUTED.")
            except: pass

# ==============================================================================
# 🖥️ XIANZO MASTER INTERFACE (V11.0)
# ==============================================================================
class XianzoProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("XIANZO • SpotDL Architect v11.0 [FINAL]")
        self.geometry("1300x880")
        self.configure(fg_color=Theme.BG_ROOT)
        
        self.engine = XKernel(self.push_to_buffer, self.update_stats)
        self.msg_buffer = queue.Queue()
        self.session_total = 0
        self.download_path = DEFAULT_SAVE_PATH

        self.assemble_ui()
        self.start_buffer_monitor()

    def assemble_ui(self):
        # Sidebar
        self.side_nav = ctk.CTkFrame(self, width=300, fg_color=Theme.BG_SIDEBAR, corner_radius=0)
        self.side_nav.pack(side="left", fill="y")
        self.side_nav.pack_propagate(False)

        ctk.CTkLabel(self.side_nav, text="XIANZO", font=("Orbitron", 42, "bold"), text_color=Theme.ACCENT).pack(pady=(60, 5))
        ctk.CTkLabel(self.side_nav, text="ULTRASONIC V11.0", font=("JetBrains Mono", 11), text_color=Theme.TEXT_DIM).pack(pady=(0, 60))

        self.stat_display = InfoPanel(self.side_nav, "Completed", "0")
        self.stat_display.pack(padx=35, pady=10, fill="x")

        ctk.CTkLabel(self.side_nav, text="CONTROLS", font=("Roboto", 12, "bold"), text_color=Theme.TEXT_DIM).pack(pady=(45, 12), padx=40, anchor="w")
        NavItem(self.side_nav, "Dashboard", lambda: None, "🏠").pack(padx=30, pady=6, fill="x")
        NavItem(self.side_nav, "Open Folder", lambda: os.startfile(self.download_path), "📂").pack(padx=30, pady=6, fill="x")
        NavItem(self.side_nav, "Set Directory", self.pick_folder, "⚙️").pack(padx=30, pady=6, fill="x")

        # Main Work Area
        self.work_area = ctk.CTkFrame(self, fg_color="transparent")
        self.work_area.pack(side="right", fill="both", expand=True, padx=50, pady=50)

        self.sys_status = ctk.CTkLabel(self.work_area, text="● KERNEL READY", font=("Roboto", 14, "bold"), text_color=Theme.ACCENT)
        self.sys_status.pack(anchor="w")

        ctk.CTkLabel(self.work_area, text="Launch Sequence", font=("Roboto", 36, "bold"), text_color=Theme.TEXT_MAIN).pack(anchor="w", pady=(8, 35))

        self.input_matrix = ctk.CTkFrame(self.work_area, fg_color=Theme.BG_SIDEBAR, corner_radius=28)
        self.input_matrix.pack(fill="x", pady=10)

        self.url_field = ctk.CTkEntry(self.input_matrix, placeholder_text="Paste Spotify Link here...", height=75, border_width=0, fg_color=Theme.BG_CARD, font=("Roboto", 16))
        self.url_field.pack(fill="x", padx=40, pady=40)

        self.cmd_strip = ctk.CTkFrame(self.work_area, fg_color="transparent")
        self.cmd_strip.pack(fill="x", pady=15)

        self.btn_fire = ctk.CTkButton(self.cmd_strip, text="EXECUTE ENGINE", height=68, fg_color=Theme.ACCENT, hover_color=Theme.ACCENT_HOVER, font=("Roboto", 18, "bold"), command=self.handle_launch)
        self.btn_fire.pack(side="left", fill="x", expand=True, padx=(0, 18))

        self.btn_kill = ctk.CTkButton(self.cmd_strip, text="STOP", width=150, height=68, fg_color=Theme.CRITICAL, font=("Roboto", 16, "bold"), command=self.engine.kill_sequence)
        self.btn_kill.pack(side="left")

        self.mode_pick = ctk.CTkOptionMenu(self.work_area, values=["NORMAL", "BEAST MODE"], fg_color=Theme.BG_SIDEBAR, button_color=Theme.ACCENT, width=300, height=45)
        self.mode_pick.pack(pady=25, anchor="w")

        self.term_container = ctk.CTkFrame(self.work_area, fg_color=Theme.TERMINAL_BG, corner_radius=22, border_width=1, border_color=Theme.BG_CARD)
        self.term_container.pack(fill="both", expand=True, pady=(20, 0))

        self.pro_terminal = ctk.CTkTextbox(self.term_container, fg_color="transparent", text_color=Theme.ACCENT, font=("Consolas", 14), padx=32, pady=32)
        self.pro_terminal.pack(fill="both", expand=True)
        self.pro_terminal.configure(state="disabled")

    def push_to_buffer(self, txt):
        tag = datetime.now().strftime("%H:%M:%S")
        self.msg_buffer.put(f"[{tag}] {txt}")

    def start_buffer_monitor(self):
        while not self.msg_buffer.empty():
            line = self.msg_buffer.get()
            self.pro_terminal.configure(state="normal")
            self.pro_terminal.insert("end", f"{line}\n")
            self.pro_terminal.see("end")
            self.pro_terminal.configure(state="disabled")
        self.after(100, self.start_buffer_monitor)

    def update_stats(self):
        self.session_total += 1
        self.stat_display.update(self.session_total)

    def pick_folder(self):
        p = filedialog.askdirectory()
        if p: self.download_path = p

    def handle_launch(self):
        url = self.url_field.get().strip()
        if not url: return
        self.btn_fire.configure(state="disabled", text="RUNNING...")
        self.sys_status.configure(text="● SYSTEM BUSY", text_color=Theme.WARNING)
        threading.Thread(target=self.execute_worker, args=(url, self.mode_pick.get()), daemon=True).start()

    def execute_worker(self, url, mode):
        self.engine.run_engine(url, self.download_path, mode)
        self.btn_fire.configure(state="normal", text="EXECUTE ENGINE")
        self.sys_status.configure(text="● KERNEL READY", text_color=Theme.ACCENT)

if __name__ == "__main__":
    XianzoProApp().mainloop()