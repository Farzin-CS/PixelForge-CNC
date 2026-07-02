"""
build_exe.py -- Build PixelForge CNC into a standalone .exe
Run: python build_exe.py
Requirements: pip install pyinstaller
"""
import subprocess
import sys
import os

def build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "pixelforge.ico")

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", "PixelForge CNC",
        "--clean",
    ]

    if os.path.exists(icon_path):
        cmd.extend(["--icon", icon_path])

    cmd.extend([
        "--hidden-import", "cv2",
        "--hidden-import", "numpy",
        "--hidden-import", "PIL",
        "--hidden-import", "PIL._tkinter_finder",
        "--hidden-import", "tkinter",
        "--hidden-import", "customtkinter",
    ])

    entry = os.path.join(script_dir, "run.py")
    cmd.append(entry)

    print("Building PixelForge CNC executable...")
    result = subprocess.run(cmd, cwd=script_dir)

    if result.returncode == 0:
        exe_path = os.path.join(script_dir, "dist", "PixelForge CNC.exe")
        print(f"\nBUILD SUCCESSFUL -> {exe_path}")
    else:
        print("\nBUILD FAILED")
        sys.exit(1)

if __name__ == "__main__":
    build()
