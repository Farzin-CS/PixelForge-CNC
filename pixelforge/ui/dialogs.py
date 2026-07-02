from __future__ import annotations

import customtkinter as ctk
from typing import Callable

from pixelforge.ui.theme import COLORS, FONTS
from pixelforge.ui.translations import t


class SuccessDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        title: str = "Conversion Complete",
        message: str = "G-code generated successfully",
        stats: dict | None = None,
        used_settings: dict | None = None,
        on_save: Callable[[], None] | None = None,
        lang: str = "en",
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("440x420")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 440) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 420) // 2
        self.geometry(f"+{px}+{py}")

        header = ctk.CTkLabel(
            self, text=title, font=FONTS["section"], text_color=COLORS["success"],
        )
        header.pack(pady=(16, 6))

        msg = ctk.CTkLabel(
            self, text=message, font=FONTS["body"], text_color=COLORS["text"],
        )
        msg.pack(pady=(0, 10))

        if stats:
            stats_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=8)
            stats_frame.pack(padx=30, fill="x", pady=(0, 8))

            stat_items = [
                ("Lines:", f"{stats.get('total_lines', 0):,}"),
                ("Rapid moves:", f"{stats.get('rapid_moves', 0):,}"),
                ("Cutting moves:", f"{stats.get('cutting_moves', 0):,}"),
                ("Ramp entries:", f"{stats.get('ramp_moves', 0):,}"),
                ("Cutting dist:", f"{stats.get('cutting_distance_mm', 0):.1f} mm"),
            ]
            if stats.get("contour_count", 0) > 0:
                stat_items.insert(0, ("Contours:", f"{stats.get('contour_count', 0):,}"))

            for i, (label, value) in enumerate(stat_items):
                lbl = ctk.CTkLabel(
                    stats_frame, text=label, font=FONTS["small"],
                    text_color=COLORS["text_dim"], anchor="w",
                )
                lbl.grid(row=i, column=0, padx=(12, 8), pady=3, sticky="w")
                val = ctk.CTkLabel(
                    stats_frame, text=value, font=FONTS["small_bold"],
                    text_color=COLORS["text_bright"], anchor="e",
                )
                val.grid(row=i, column=1, padx=(8, 12), pady=3, sticky="e")
            stats_frame.columnconfigure(1, weight=1)

        if used_settings:
            us_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], corner_radius=8)
            us_frame.pack(padx=30, fill="x", pady=(0, 10))

            us_title = ctk.CTkLabel(
                us_frame, text=t(lang, "used_settings"), font=FONTS["small_bold"],
                text_color=COLORS["accent"], anchor="w",
            )
            us_title.pack(anchor="w", padx=12, pady=(6, 2))

            us_items = [
                (t(lang, "used_mode"), used_settings.get("mode", "--")),
                (t(lang, "used_material"), used_settings.get("material", "--")),
                (t(lang, "used_depth"), used_settings.get("max_depth", "--")),
                (t(lang, "used_spacing"), used_settings.get("line_spacing_mm", "--")),
                (t(lang, "used_gamma"), used_settings.get("gamma", "--")),
            ]

            for i, (label, value) in enumerate(us_items):
                lbl = ctk.CTkLabel(
                    us_frame, text=label, font=FONTS["small"],
                    text_color=COLORS["text_dim"], anchor="w",
                )
                lbl.grid(row=i + 1, column=0, padx=(12, 8), pady=1, sticky="w")
                val = ctk.CTkLabel(
                    us_frame, text=str(value), font=FONTS["small_bold"],
                    text_color=COLORS["text_bright"], anchor="e",
                )
                val.grid(row=i + 1, column=1, padx=(8, 12), pady=1, sticky="e")
            us_frame.columnconfigure(1, weight=1)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(4, 16))

        if on_save:
            save_btn = ctk.CTkButton(
                btn_frame, text=t(lang, "dlg_save"), font=FONTS["button_small"],
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                width=120, command=lambda: [on_save(), self.destroy()],
            )
            save_btn.pack(side="left", padx=8)

        close_btn = ctk.CTkButton(
            btn_frame, text=t(lang, "dlg_close"), font=FONTS["button_small"],
            fg_color=COLORS["bg_mid"], hover_color=COLORS["bg_card"],
            width=100, command=self.destroy,
        )
        close_btn.pack(side="left", padx=8)


class ErrorDialog(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        title: str = "Error",
        message: str = "An error occurred",
        details: str = "",
        lang: str = "en",
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("450x280")
        self.resizable(False, False)
        self.configure(fg_color=COLORS["bg_dark"])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() - 450) // 2
        py = parent.winfo_y() + (parent.winfo_height() - 280) // 2
        self.geometry(f"+{px}+{py}")

        header = ctk.CTkLabel(
            self, text=title, font=FONTS["section"], text_color=COLORS["error"],
        )
        header.pack(pady=(20, 8))

        msg = ctk.CTkLabel(
            self, text=message, font=FONTS["body"],
            text_color=COLORS["text"], wraplength=380,
        )
        msg.pack(padx=30, pady=(0, 12))

        if details:
            self._details_visible = False
            self._details_frame = ctk.CTkFrame(
                self, fg_color=COLORS["bg_input"], corner_radius=6
            )
            self._details_text = ctk.CTkTextbox(
                self._details_frame, font=FONTS["tiny"],
                fg_color=COLORS["bg_input"], text_color=COLORS["text_dim"],
                height=80, activate_scrollbars=True,
            )
            self._details_text.insert("1.0", details)
            self._details_text.configure(state="disabled")

            toggle_btn = ctk.CTkButton(
                self, text=t(lang, "dlg_show_details"), font=FONTS["tiny"],
                fg_color="transparent", hover_color=COLORS["bg_mid"],
                text_color=COLORS["text_dim"], width=100,
                command=self._toggle_details,
            )
            toggle_btn.pack(pady=(0, 8))

        close_btn = ctk.CTkButton(
            self, text=t(lang, "dlg_ok"), font=FONTS["button_small"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            width=100, command=self.destroy,
        )
        close_btn.pack(pady=(0, 20))

    def _toggle_details(self) -> None:
        if self._details_visible:
            self._details_frame.pack_forget()
            self._details_visible = False
        else:
            self._details_frame.pack(padx=30, fill="x", pady=(0, 4))
            self._details_text.pack(fill="x", padx=4, pady=4)
            self._details_visible = True
