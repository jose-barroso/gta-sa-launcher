# ---------------------------------------------------------------
# GTA San Andreas Steam Launcher
# Audit: noodlechan (my nickname on steam)
#
# Handles launching of Single-player, SA-MP and MTA. Also does the
# exe-swap trick so SA-MP can run through Steam.
# ---------------------------------------------------------------

import sys
import os
import json
import subprocess
import shutil
import time
import ctypes
import threading
import tkinter as tk
from tkinter import messagebox

# Pillow is required for the animated background and PNG icons
try:
    from PIL import Image, ImageTk
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", "Pillow isn't installed.\nRun: pip install Pillow")
    sys.exit(1)

# Older Pillow builds use ANTIALIAS instead of Resampling.LANCZOS
try:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
except AttributeError:
    RESAMPLE_FILTER = Image.ANTIALIAS

# Give the process its own AppUserModelID so Windows stops showing
# the Python icon in the taskbar. Has to run before tk.Tk().
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("GTA.SA.Launcher.1.0")
except Exception as e:
    print(f"AppUserModelID failed: {e}")

GAME_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
MY_EXECUTABLE = os.path.abspath(sys.argv[0])

# When frozen by PyInstaller, images sit in the temp extraction folder.
# Running as a .py, they sit in the local img/ folder.
if getattr(sys, 'frozen', False):
    IMG_DIR = os.path.join(sys._MEIPASS, "img")
else:
    IMG_DIR = os.path.join(GAME_DIR, "img")

ARGS_FILE = os.path.join(GAME_DIR, "samp_args.json")
ORIGINAL_EXE = "gta_sa_original.exe"
SAMP_EXE = "samp.exe"

# MTA has its own install folder, so hardcoded
MTA_PATH = r"C:\Program Files (x86)\MTA San Andreas 1.6\Multi Theft Auto.exe"

ORIGINAL_EXE_PATH = os.path.join(GAME_DIR, ORIGINAL_EXE)
GTA_SA_PATH = os.path.join(GAME_DIR, "gta_sa.exe")
STEAM_EXE_PATH = os.path.join(GAME_DIR, "gta-sa.exe")

# ---------------------------------------------------------------
# Take over both gta_sa.exe and gta-sa.exe so SA-MP hooks in, and
# push the real game binary to gta_sa_original.exe.
# ---------------------------------------------------------------
try:
    if not os.path.exists(ORIGINAL_EXE_PATH):
        if os.path.exists(GTA_SA_PATH) and os.path.abspath(GTA_SA_PATH) != MY_EXECUTABLE:
            os.rename(GTA_SA_PATH, ORIGINAL_EXE_PATH)
        elif os.path.exists(STEAM_EXE_PATH) and os.path.abspath(STEAM_EXE_PATH) != MY_EXECUTABLE:
            os.rename(STEAM_EXE_PATH, ORIGINAL_EXE_PATH)

    if MY_EXECUTABLE != os.path.abspath(GTA_SA_PATH) and not os.path.exists(GTA_SA_PATH):
        shutil.copy2(MY_EXECUTABLE, GTA_SA_PATH)

    if MY_EXECUTABLE != os.path.abspath(STEAM_EXE_PATH) and not os.path.exists(STEAM_EXE_PATH):
        shutil.copy2(MY_EXECUTABLE, STEAM_EXE_PATH)
except Exception as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showwarning("Install warning",
        f"Couldn't set up the game files:\n{e}\n\n"
        f"You may need to rename the original game to '{ORIGINAL_EXE}' by hand.")
    root.destroy()

# ---------------------------------------------------------------
# SA-MP wants samp.asi alongside samp.dll. A plain copy is enough
# for the launcher to work.
# ---------------------------------------------------------------
if os.path.exists(ARGS_FILE):
    try: os.remove(ARGS_FILE)
    except: pass

samp_dll_path = os.path.join(GAME_DIR, "samp.dll")
samp_asi_path = os.path.join(GAME_DIR, "samp.asi")

if os.path.exists(samp_dll_path) and not os.path.exists(samp_asi_path):
    try: shutil.copy2(samp_dll_path, samp_asi_path)
    except: pass

# ---------------------------------------------------------------
# SA-MP calls us back with "-c" plus the server args when you join
# a server. We stash them in a file and exit. The launcher picks
# them up next and forwards them to the real game.
# ---------------------------------------------------------------
if len(sys.argv) > 1 and "-c" in sys.argv:
    with open(ARGS_FILE, "w") as f:
        json.dump(sys.argv[1:], f)
    sys.exit(0)

# ---------------------------------------------------------------
# Watches for the game closing and grabs the args file SA-MP writes.
# ---------------------------------------------------------------
def is_running(process_name):
    try:
        output = subprocess.check_output(
            f'tasklist /NH /FI "IMAGENAME eq {process_name}"',
            shell=True, creationflags=0x08000000)
        return process_name.lower() in output.decode().lower()
    except:
        return False

def background_monitor():
    time.sleep(4)
    while True:
        if os.path.exists(ARGS_FILE):
            try:
                with open(ARGS_FILE, "r") as f:
                    args = json.load(f)
                os.remove(ARGS_FILE)

                if os.path.exists(ORIGINAL_EXE_PATH):
                    subprocess.Popen([ORIGINAL_EXE_PATH] + args, cwd=GAME_DIR)
                    time.sleep(5)
            except Exception as e:
                print(f"Monitor error: {e}")

        samp_running = is_running(SAMP_EXE)
        gta_running = is_running(ORIGINAL_EXE)

        # Kill ourselves once both game processes are gone
        if not samp_running and not gta_running:
            os._exit(0)

        time.sleep(2)

def launch_singleplayer():
    root.withdraw()
    if os.path.exists(ORIGINAL_EXE_PATH):
        process = subprocess.Popen([ORIGINAL_EXE_PATH], cwd=GAME_DIR)
        process.wait()
    else:
        messagebox.showerror("Error", f"Couldn't find '{ORIGINAL_EXE}'.")
    os._exit(0)

def launch_samp():
    if not os.path.exists(samp_dll_path):
        messagebox.showerror("Error", "samp.dll not found. Install SA-MP in the game folder first.")
        return

    samp_path = os.path.join(GAME_DIR, SAMP_EXE)
    if os.path.exists(samp_path):
        # explorer is used here so SA-MP inherits the right working dir
        subprocess.Popen(['explorer', SAMP_EXE], cwd=GAME_DIR)
        root.withdraw()
        threading.Thread(target=background_monitor, daemon=True).start()
    else:
        messagebox.showerror("Error", "samp.exe not found.")

def launch_mta():
    if os.path.exists(MTA_PATH):
        try:
            # MTA has its own working folder, keep it there
            subprocess.Popen([MTA_PATH], cwd=os.path.dirname(MTA_PATH))
            root.withdraw()
        except Exception as e:
            messagebox.showerror("Error", f"Couldn't start MTA:\n{e}")
    else:
        messagebox.showerror("Error", f"MTA not found at:\n{MTA_PATH}")

# ---------------------------------------------------------------
# GUI setup
# ---------------------------------------------------------------
root = tk.Tk()
root.title("GTA San Andreas (Steam Launcher)")
root.geometry("300x450")
root.resizable(False, False)
root.eval('tk::PlaceWindow . center')
root.protocol("WM_DELETE_WINDOW", lambda: os._exit(0))

# Windows taskbar icon is a pain. GetForegroundWindow can grab the
# wrong handle, so we use GetAncestor on the Tk window id instead.
def set_taskbar_icon(root_window, icon_path):
    try:
        # Windows constants
        WM_SETICON = 0x0080
        ICON_SMALL = 0
        ICON_BIG = 1
        IMAGE_ICON = 1
        LR_LOADFROMFILE = 0x0010
        GA_ROOT = 2

        # Make sure the window is realised before grabbing its handle
        root_window.update_idletasks()
        hwnd = ctypes.windll.user32.GetAncestor(root_window.winfo_id(), GA_ROOT)

        if not hwnd:
            print("Couldn't get window handle")
            return

        hicon_big = ctypes.windll.user32.LoadImageW(0, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
        hicon_small = ctypes.windll.user32.LoadImageW(0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)

        if not hicon_big or not hicon_small:
            print("Failed to load icon from .ico")
            return

        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
        ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
    except Exception as e:
        print(f"Taskbar icon failed: {e}")

# Apply window icon
try:
    icon_path = os.path.join(IMG_DIR, "icon.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(default=icon_path)

        icon_img = Image.open(icon_path).resize((64, 64), RESAMPLE_FILTER)
        icon_photo = ImageTk.PhotoImage(icon_img)
        root.iconphoto(True, icon_photo)
        root.icon_photo_ref = icon_photo  # keep ref alive

        # Run twice - sometimes the first call lands before the window is ready
        root.after(150, lambda: set_taskbar_icon(root, icon_path))
        root.after(800, lambda: set_taskbar_icon(root, icon_path))
except Exception as e:
    print(f"Icon load failed: {e}")

# Animated background
bg_label = tk.Label(root)
bg_label.place(x=0, y=0, relwidth=1, relheight=1)

frames = []
bg_path = os.path.join(IMG_DIR, "bg.webp")

if os.path.exists(bg_path):
    try:
        im = Image.open(bg_path)
        if getattr(im, "is_animated", False):
            # Need to seek each frame and copy before resizing
            for i in range(im.n_frames):
                im.seek(i)
                frame_img = im.copy().resize((300, 450), RESAMPLE_FILTER)
                frames.append(ImageTk.PhotoImage(frame_img))
        else:
            frame_img = im.resize((300, 450), RESAMPLE_FILTER)
            frames.append(ImageTk.PhotoImage(frame_img))
    except Exception as e:
        print(f"bg.webp load failed: {e}")
else:
    print(f"Not found: {bg_path}")

if frames:
    def animate_bg(idx=0):
        bg_label.config(image=frames[idx])
        root.after(50, animate_bg, (idx + 1) % len(frames))
    animate_bg()
else:
    bg_label.config(bg="#1a1a1a")

# Button factory - stacks from the bottom up because of side=BOTTOM
def create_button(parent, text, icon_path, command):
    frame = tk.Frame(parent, bg="#ffffff", highlightbackground="#aaaaaa", highlightthickness=1, bd=0)
    frame.pack(side=tk.BOTTOM, pady=5, padx=15, fill="x")

    img = None
    if os.path.exists(icon_path):
        try:
            pil_img = Image.open(icon_path).resize((32, 32), RESAMPLE_FILTER)
            img = ImageTk.PhotoImage(pil_img)
        except Exception as e:
            print(f"Icon load failed for {icon_path}: {e}")

    btn = tk.Button(
        frame,
        text=text,
        image=img,
        compound="left",
        command=command,
        bg="#ffffff",
        fg="#000000",
        activebackground="#e0e0e0",
        activeforeground="#000000",
        font=("Segoe UI", 10, "bold"),
        bd=0,
        padx=5,
        pady=5,
        anchor="w",
        cursor="hand2"
    )
    btn.image = img
    btn.pack(fill="x")

    # Simple hover effect
    btn.bind("<Enter>", lambda e: btn.config(bg="#e0e0e0"))
    btn.bind("<Leave>", lambda e: btn.config(bg="#ffffff"))

# Order matters here - side=BOTTOM stacks upward, so MTA goes first
# and ends up at the bottom of the window
create_button(root, "MTA (Multi Theft Auto)", os.path.join(IMG_DIR, "mta.png"), launch_mta)
create_button(root, "SA-MP (Multiplayer)", os.path.join(IMG_DIR, "samp.png"), launch_samp)
create_button(root, "GTA SA (Singleplayer)", os.path.join(IMG_DIR, "sp.png"), launch_singleplayer)

root.mainloop()
