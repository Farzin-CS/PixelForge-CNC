from __future__ import annotations

import customtkinter as ctk

COLORS = {
    "bg_dark": "#1a1a2e",
    "bg_mid": "#16213e",
    "bg_card": "#0f3460",
    "bg_input": "#1a1a3e",
    "accent": "#e94560",
    "accent_hover": "#c0392b",
    "accent_dim": "#e9456088",
    "text": "#ecf0f1",
    "text_dim": "#95a5a6",
    "text_bright": "#ffffff",
    "border": "#2c3e50",
    "preview_bg": "#0d1117",
    "gold": "#f4d03f",
    "success": "#2ecc71",
    "warning": "#f39c12",
    "error": "#e74c3c",
    "danger": "#e74c3c",
}

import sys

if sys.platform == "darwin":
    _FONT = "Helvetica"
elif sys.platform == "linux":
    _FONT = "sans-serif"
else:
    _FONT = "Segoe UI"

FONTS = {
    "title": (_FONT, 24, "bold"),
    "subtitle": (_FONT, 10),
    "section": (_FONT, 11, "bold"),
    "body": (_FONT, 10),
    "body_bold": (_FONT, 10, "bold"),
    "small": (_FONT, 9),
    "small_bold": (_FONT, 9, "bold"),
    "tiny": (_FONT, 8),
    "button": (_FONT, 11, "bold"),
    "button_small": (_FONT, 9),
    "run_button": (_FONT, 13, "bold"),
    "status": (_FONT, 9),
    "placeholder": (_FONT, 22, "bold"),
}

def setup_theme() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
