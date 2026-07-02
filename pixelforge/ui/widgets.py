from __future__ import annotations

import customtkinter as ctk
from typing import Callable

from pixelforge.ui.theme import COLORS, FONTS


class FastScrollFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, scroll_multiplier: int = 3, **kwargs):
        super().__init__(master, **kwargs)
        self._scroll_multiplier = scroll_multiplier
        self.bind("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event) -> None:
        self._parent_canvas.yview_scroll(
            int(-1 * (event.delta / 120) * self._scroll_multiplier), "units"
        )


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, placeholder_text: str = "Open an image to begin", **kwargs):
        super().__init__(master, fg_color=COLORS["preview_bg"], **kwargs)

        self._placeholder_text = placeholder_text
        self._original_pil = None
        self._zoom = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self._drag_start_x = 0
        self._drag_start_y = 0
        self._min_zoom = 0.25
        self._max_zoom = 5.0

        self._image_label = ctk.CTkLabel(self, text="", fg_color="transparent")
        self._image_label.pack(fill="both", expand=True)

        self._placeholder_label = ctk.CTkLabel(
            self, text=placeholder_text, font=FONTS["subtitle"],
            text_color=COLORS["text_dim"], fg_color="transparent",
        )
        self._placeholder_label.pack(expand=True)

        self._zoom_bar = ctk.CTkFrame(self, fg_color=COLORS["bg_mid"], height=28)
        self._zoom_bar.pack(fill="x", side="bottom")
        self._zoom_bar.pack_propagate(False)

        self._zoom_out_btn = ctk.CTkButton(
            self._zoom_bar, text="-", width=28, height=22,
            font=FONTS["tiny"], fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent"], command=self._zoom_out,
        )
        self._zoom_out_btn.pack(side="left", padx=(8, 2), pady=3)

        self._zoom_label = ctk.CTkLabel(
            self._zoom_bar, text="100%", font=FONTS["tiny"],
            text_color=COLORS["text_dim"], width=45,
        )
        self._zoom_label.pack(side="left", padx=2)

        self._zoom_in_btn = ctk.CTkButton(
            self._zoom_bar, text="+", width=28, height=22,
            font=FONTS["tiny"], fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent"], command=self._zoom_in,
        )
        self._zoom_in_btn.pack(side="left", padx=(2, 8), pady=3)

        self._zoom_reset_btn = ctk.CTkButton(
            self._zoom_bar, text="Fit", width=40, height=22,
            font=FONTS["tiny"], fg_color=COLORS["bg_card"],
            hover_color=COLORS["accent"], command=self._zoom_fit,
        )
        self._zoom_reset_btn.pack(side="left", padx=2, pady=3)

        self.bind("<MouseWheel>", self._on_mousewheel)
        self._image_label.bind("<MouseWheel>", self._on_mousewheel)
        self.bind("<ButtonPress-1>", self._on_drag_start)
        self.bind("<B1-Motion>", self._on_drag_move)
        self.bind("<ButtonRelease-1>", self._on_drag_end)
        self._image_label.bind("<ButtonPress-1>", self._on_drag_start)
        self._image_label.bind("<B1-Motion>", self._on_drag_move)
        self._image_label.bind("<ButtonRelease-1>", self._on_drag_end)

        self._current_ctk_image = None

    def set_image(self, pil_image) -> None:
        self._placeholder_label.pack_forget()
        self._image_label.pack(fill="both", expand=True)
        self._original_pil = pil_image
        self._zoom = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self._refresh_display()

    def clear(self) -> None:
        self._image_label.pack_forget()
        self._original_pil = None
        self._current_ctk_image = None
        self._placeholder_label.pack(expand=True)
        self._zoom_label.configure(text="100%")

    def _get_fit_scale(self) -> float:
        if self._original_pil is None:
            return 1.0
        self.update_idletasks()
        pw = max(self.winfo_width(), 100)
        ph = max(self.winfo_height() - 28, 80)
        img_w, img_h = self._original_pil.size
        return min((pw - 20) / img_w, (ph - 20) / img_h)

    def _refresh_display(self) -> None:
        if self._original_pil is None:
            return
        self.update_idletasks()
        pw = max(self.winfo_width(), 100)
        ph = max(self.winfo_height() - 28, 80)
        fit_scale = self._get_fit_scale()
        effective_scale = fit_scale * self._zoom
        img_w, img_h = self._original_pil.size
        new_w = max(1, int(img_w * effective_scale))
        new_h = max(1, int(img_h * effective_scale))
        resized = self._original_pil.resize((new_w, new_h))
        self._current_ctk_image = ctk.CTkImage(resized, size=(new_w, new_h))
        self._image_label.configure(image=self._current_ctk_image, text="")
        self._zoom_label.configure(text=f"{int(self._zoom * 100)}%")

    def _zoom_in(self) -> None:
        self._zoom = min(self._max_zoom, self._zoom * 1.25)
        self._refresh_display()

    def _zoom_out(self) -> None:
        self._zoom = max(self._min_zoom, self._zoom / 1.25)
        self._refresh_display()

    def _zoom_fit(self) -> None:
        self._zoom = 1.0
        self._offset_x = 0
        self._offset_y = 0
        self._refresh_display()

    def _on_mousewheel(self, event) -> None:
        if self._original_pil is None:
            return
        if event.delta > 0:
            self._zoom = min(self._max_zoom, self._zoom * 1.1)
        else:
            self._zoom = max(self._min_zoom, self._zoom / 1.1)
        self._refresh_display()

    def _on_drag_start(self, event) -> None:
        self._drag_start_x = event.x
        self._drag_start_y = event.y

    def _on_drag_move(self, event) -> None:
        dx = event.x - self._drag_start_x
        dy = event.y - self._drag_start_y
        self._drag_start_x = event.x
        self._drag_start_y = event.y
        if self._zoom > 1.0 and self._original_pil is not None:
            self._offset_x += dx
            self._offset_y += dy
            self.update_idletasks()
            pw = max(self.winfo_width(), 100)
            ph = max(self.winfo_height() - 28, 80)
            fit_scale = self._get_fit_scale()
            iw = int(self._original_pil.size[0] * fit_scale * self._zoom)
            ih = int(self._original_pil.size[1] * fit_scale * self._zoom)
            max_ox = max(0, (iw - pw) // 2)
            max_oy = max(0, (ih - ph) // 2)
            self._offset_x = max(-max_ox, min(max_ox, self._offset_x))
            self._offset_y = max(-max_oy, min(max_oy, self._offset_y))

    def _on_drag_end(self, event) -> None:
        pass


class CNCEntry(ctk.CTkFrame):
    def __init__(
        self,
        master,
        label: str,
        value: float | int = 0.0,
        width: int = 80,
        **kwargs,
    ):
        super().__init__(master, fg_color="transparent", **kwargs)

        self._label = ctk.CTkLabel(
            self, text=label, font=FONTS["body"],
            text_color=COLORS["text"], width=len(label) * 8 + 10, anchor="w",
        )
        self._label.pack(side="left", padx=(0, 6))

        self._var = ctk.StringVar(value=str(value))
        self._entry = ctk.CTkEntry(
            self, textvariable=self._var, width=width, font=FONTS["body"],
            fg_color=COLORS["bg_input"], text_color=COLORS["text_bright"],
            border_color=COLORS["border"],
        )
        self._entry.pack(side="left")
        self._entry.bind("<FocusOut>", self._validate)

        self._invalid_border = "#e74c3c"
        self._valid_border = COLORS["border"]

    def _validate(self, event=None) -> None:
        try:
            float(self._var.get())
            self._entry.configure(border_color=self._valid_border)
        except ValueError:
            self._entry.configure(border_color=self._invalid_border)

    def get(self) -> str:
        return self._var.get()

    def get_float(self) -> float:
        return float(self._var.get())

    def set(self, value) -> None:
        self._var.set(str(value))

    def set_label(self, text: str) -> None:
        self._label.configure(text=text)
