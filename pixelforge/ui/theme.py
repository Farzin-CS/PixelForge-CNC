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
}

FONTS = {
    "title": ("Segoe UI", 24, "bold"),
    "subtitle": ("Segoe UI", 10),
    "section": ("Segoe UI", 11, "bold"),
    "body": ("Segoe UI", 10),
    "body_bold": ("Segoe UI", 10, "bold"),
    "small": ("Segoe UI", 9),
    "small_bold": ("Segoe UI", 9, "bold"),
    "tiny": ("Segoe UI", 8),
    "button": ("Segoe UI", 11, "bold"),
    "button_small": ("Segoe UI", 9),
    "run_button": ("Segoe UI", 13, "bold"),
    "status": ("Segoe UI", 9),
    "placeholder": ("Segoe UI", 22, "bold"),
}

def setup_theme() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
