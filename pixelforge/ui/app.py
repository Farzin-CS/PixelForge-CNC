from __future__ import annotations

import os
import sys
from typing import Any

import customtkinter as ctk
from PIL import Image

from pixelforge.engine.material_presets import MATERIAL_PRESETS, DEFAULT_MATERIAL
from pixelforge.engine.types import GCodeStats
from pixelforge.ui.theme import COLORS, FONTS, setup_theme
from pixelforge.ui.widgets import PreviewPanel, CNCEntry, FastScrollFrame
from pixelforge.ui.dialogs import SuccessDialog, ErrorDialog
from pixelforge.ui.controllers import AppController
from pixelforge.ui.translations import t, TRANSLATIONS
from pixelforge.engine.settings import load_settings, save_settings


class PixelForgeApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("PixelForge CNC")
        self._settings = load_settings()

        w = self._settings.get("window_width", 1200)
        h = self._settings.get("window_height", 780)
        x = self._settings.get("window_x")
        y = self._settings.get("window_y")
        geom = f"{w}x{h}"
        if x is not None and y is not None:
            geom += f"+{x}+{y}"
        self.root.geometry(geom)
        self.root.minsize(1000, 650)

        icon_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "pixelforge.ico"
        )
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass

        setup_theme()
        self.root.configure(fg_color=COLORS["bg_dark"])

        self.image_path: str | None = None
        self.lang: str = self._settings.get("language", "en")
        self._smart_suggestions: dict[str, Any] | None = None
        self._2d_widgets: list[tuple[Any, dict]] = []
        self._3d_widgets: list[tuple[Any, dict]] = []

        self._controller: AppController | None = None
        self._build_ui()
        self._apply_saved_settings()
        self._controller = AppController(self)

        self.root.bind("<Control-o>", lambda e: self._controller.on_browse_image())
        self.root.bind("<Control-p>", lambda e: self._controller.on_run_conversion())
        self.root.bind("<Control-s>", lambda e: self._controller.on_save_config())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self._build_header()
        content = ctk.CTkFrame(self.root, fg_color=COLORS["bg_dark"])
        content.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._build_left_panel(content)
        self._build_right_panel(content)
        self._build_status_bar()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self.root, fg_color=COLORS["bg_dark"], height=60)
        header.pack(fill="x", padx=16, pady=(12, 4))
        header.pack_propagate(False)

        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", fill="y")

        self._title_label = ctk.CTkLabel(
            title_frame, text=t(self.lang, "app_name"), font=FONTS["title"],
            text_color=COLORS["accent"], anchor="w",
        )
        self._title_label.pack(anchor="w")

        info_frame = ctk.CTkFrame(header, fg_color="transparent")
        info_frame.pack(side="right", fill="y")

        lang_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
        lang_frame.pack(anchor="e", pady=(2, 0))

        self._en_btn = ctk.CTkButton(
            lang_frame, text="EN", width=36, height=24,
            font=FONTS["tiny"], fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda: self.set_language("en"),
        )
        self._en_btn.pack(side="left", padx=2)

        self._fa_btn = ctk.CTkButton(
            lang_frame, text="FA", width=36, height=24,
            font=FONTS["tiny"], fg_color=COLORS["bg_mid"],
            hover_color=COLORS["accent"],
            command=lambda: self.set_language("fa"),
        )
        self._fa_btn.pack(side="left", padx=2)

        self._shortcuts_label = ctk.CTkLabel(
            info_frame, text=t(self.lang, "shortcuts_hint"),
            font=FONTS["tiny"], text_color=COLORS["text_dim"],
        )
        self._shortcuts_label.pack(anchor="e")

        self._version_label = ctk.CTkLabel(
            info_frame, text=t(self.lang, "version"),
            font=FONTS["tiny"], text_color=COLORS["text_dim"],
        )
        self._version_label.pack(anchor="e")

    def _build_left_panel(self, parent) -> None:
        scroll_speed = self._settings.get("scroll_speed_multiplier", 3)
        self._scroll = FastScrollFrame(
            parent, fg_color=COLORS["bg_dark"],
            scrollbar_button_color=COLORS["bg_mid"],
            scrollbar_button_hover_color=COLORS["accent"],
            width=400, scroll_multiplier=scroll_speed,
        )
        self._scroll.pack(side="left", fill="y", padx=(0, 12))

        self._build_file_section(self._scroll)
        self._build_engraving_mode_section(self._scroll)
        self._build_mode_section(self._scroll)
        self._build_material_section(self._scroll)
        self._build_dimension_section(self._scroll)
        self._build_cnc_section(self._scroll)
        self._build_image_section(self._scroll)
        self._build_smart_section(self._scroll)
        self._build_2d_section(self._scroll)
        self._build_strategy_section(self._scroll)
        self._build_action_section(self._scroll)

    def _build_right_panel(self, parent) -> None:
        self._tabview = ctk.CTkTabview(
            parent, fg_color=COLORS["preview_bg"],
            segmented_button_fg_color=COLORS["bg_mid"],
            segmented_button_selected_color=COLORS["accent"],
            segmented_button_selected_hover_color=COLORS["accent_hover"],
        )
        self._tabview.pack(side="right", fill="both", expand=True)

        self._tab_original = self._tabview.add(t(self.lang, "preview_original"))
        self._tab_engraving = self._tabview.add(t(self.lang, "preview_engraving"))
        self._tab_depth = self._tabview.add(t(self.lang, "preview_depth"))
        self._tab_contours = self._tabview.add(t(self.lang, "preview_contours"))

        self._preview_original = PreviewPanel(
            self._tab_original, placeholder_text=t(self.lang, "preview_placeholder")
        )
        self._preview_original.pack(fill="both", expand=True, padx=4, pady=4)

        self._preview_engraving = PreviewPanel(
            self._tab_engraving, placeholder_text=t(self.lang, "preview_placeholder")
        )
        self._preview_engraving.pack(fill="both", expand=True, padx=4, pady=4)

        self._preview_depth = PreviewPanel(
            self._tab_depth, placeholder_text=t(self.lang, "preview_placeholder")
        )
        self._preview_depth.pack(fill="both", expand=True, padx=4, pady=4)

        self._preview_contours = PreviewPanel(
            self._tab_contours, placeholder_text=t(self.lang, "preview_placeholder_2d")
        )
        self._preview_contours.pack(fill="both", expand=True, padx=4, pady=4)

    def _build_file_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_file_title = self._make_section_title(card, t(self.lang, "sec_file"))

        file_row = ctk.CTkFrame(card, fg_color="transparent")
        file_row.pack(fill="x", pady=(0, 4))

        self._file_entry = ctk.CTkEntry(
            file_row, placeholder_text=t(self.lang, "no_image"),
            font=FONTS["body"], fg_color=COLORS["bg_input"],
            text_color=COLORS["text_bright"], border_color=COLORS["border"],
        )
        self._file_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        self._browse_btn = ctk.CTkButton(
            file_row, text=t(self.lang, "browse"), font=FONTS["button_small"],
            fg_color=COLORS["bg_mid"], hover_color=COLORS["accent"],
            width=80, command=self._on_browse,
        )
        self._browse_btn.pack(side="right")

        self._image_info_label = ctk.CTkLabel(
            card, text=t(self.lang, "preview_formats"),
            font=FONTS["tiny"], text_color=COLORS["text_dim"], anchor="w",
        )
        self._image_info_label.pack(anchor="w", pady=(2, 0))

    def _build_engraving_mode_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_eng_mode_title = self._make_section_title(card, t(self.lang, "sec_engraving_mode"))

        self._eng_mode_var = ctk.StringVar(value="raster_3d")
        modes = [
            ("raster_3d", "mode_3d", "mode_3d_desc"),
            ("contour_2d", "mode_contour", "mode_contour_desc"),
            ("line_art", "mode_lineart", "mode_lineart_desc"),
        ]

        self._eng_mode_widgets = []
        for value, name_key, desc_key in modes:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", pady=1)
            rb = ctk.CTkRadioButton(
                row, text=t(self.lang, name_key),
                variable=self._eng_mode_var, value=value,
                font=FONTS["body_bold"], fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"], text_color=COLORS["text"],
                command=self._on_engraving_mode_change,
            )
            rb.pack(side="left")
            desc = ctk.CTkLabel(
                row, text=f"  -- {t(self.lang, desc_key)}",
                font=FONTS["small"], text_color=COLORS["text_dim"],
            )
            desc.pack(side="left")
            self._eng_mode_widgets.append((rb, desc, name_key, desc_key))

    def _build_mode_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_mode_title = self._make_section_title(card, t(self.lang, "sec_mode"))

        self._mode_var = ctk.StringVar(value="full")
        modes = [
            ("full", "mode_full", "mode_full_desc"),
            ("portrait", "mode_portrait", "mode_portrait_desc"),
            ("center", "mode_center", "mode_center_desc"),
            ("fit", "mode_fit", "mode_fit_desc"),
        ]

        self._mode_widgets = []
        for value, name_key, desc_key in modes:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", pady=1)
            rb = ctk.CTkRadioButton(
                row, text=t(self.lang, name_key),
                variable=self._mode_var, value=value,
                font=FONTS["body_bold"], fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"], text_color=COLORS["text"],
            )
            rb.pack(side="left")
            desc_lbl = ctk.CTkLabel(
                row, text=f"  -- {t(self.lang, desc_key)}",
                font=FONTS["small"], text_color=COLORS["text_dim"],
            )
            desc_lbl.pack(side="left")
            self._mode_widgets.append((rb, desc_lbl, name_key, desc_key))

    def _build_material_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_material_title = self._make_section_title(card, t(self.lang, "sec_material"))

        mat_row = ctk.CTkFrame(card, fg_color="transparent")
        mat_row.pack(fill="x", pady=(0, 6))

        self._material_label_text = ctk.CTkLabel(
            mat_row, text=t(self.lang, "material_label"),
            font=FONTS["body"], text_color=COLORS["text"],
        )
        self._material_label_text.pack(side="left", padx=(0, 8))

        self._material_var = ctk.StringVar(value=DEFAULT_MATERIAL)
        self._material_menu = ctk.CTkOptionMenu(
            mat_row, variable=self._material_var,
            values=list(MATERIAL_PRESETS.keys()),
            font=FONTS["body"], fg_color=COLORS["bg_input"],
            button_color=COLORS["bg_mid"], button_hover_color=COLORS["accent"],
            command=self._on_material_change, width=140,
        )
        self._material_menu.pack(side="left")

        self._material_info = ctk.CTkLabel(
            card, text="", font=FONTS["tiny"],
            text_color=COLORS["text_dim"], anchor="w", wraplength=360,
        )
        self._material_info.pack(anchor="w", pady=(0, 4))

        bit_row = ctk.CTkFrame(card, fg_color="transparent")
        bit_row.pack(fill="x")

        self._bit_label_text = ctk.CTkLabel(
            bit_row, text=t(self.lang, "recommended_bit"),
            font=FONTS["small"], text_color=COLORS["text_dim"],
        )
        self._bit_label_text.pack(side="left")

        self._bit_value_label = ctk.CTkLabel(
            bit_row, text="", font=FONTS["small_bold"],
            text_color=COLORS["text_bright"],
        )
        self._bit_value_label.pack(side="left", padx=(4, 0))

        self._update_material_info()

    def _build_dimension_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_dim_title = self._make_section_title(card, t(self.lang, "sec_dimensions"))

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))

        self._width_entry = CNCEntry(row1, t(self.lang, "width"), value=20.0)
        self._width_entry.pack(side="left")

        self._height_entry = CNCEntry(row1, t(self.lang, "height"), value=25.0)
        self._height_entry.pack(side="left", padx=(16, 0))

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x")

        self._spacing_entry = CNCEntry(row2, t(self.lang, "spacing"), value=0.05)
        self._spacing_entry.pack(side="left")

        self._spacing_hint = ctk.CTkLabel(
            row2, text=f"  {t(self.lang, 'spacing_hint')}",
            font=FONTS["tiny"], text_color=COLORS["text_dim"],
        )
        self._spacing_hint.pack(side="left", padx=(8, 0))
        self._3d_widgets.append((self._spacing_entry, {"side": "left"}))
        self._3d_widgets.append((self._spacing_hint, {"side": "left", "padx": (8, 0)}))

    def _build_cnc_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_cnc_title = self._make_section_title(card, t(self.lang, "sec_cnc"))

        row1 = ctk.CTkFrame(card, fg_color="transparent")
        row1.pack(fill="x", pady=(0, 6))

        self._depth_entry = CNCEntry(row1, t(self.lang, "max_depth"), value=-0.08)
        self._depth_entry.pack(side="left")

        self._safe_z_entry = CNCEntry(row1, t(self.lang, "safe_z"), value=2.0)
        self._safe_z_entry.pack(side="left", padx=(16, 0))

        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", pady=(0, 6))

        self._feed_entry = CNCEntry(row2, t(self.lang, "feed"), value=200.0)
        self._feed_entry.pack(side="left")

        self._rpm_entry = CNCEntry(row2, t(self.lang, "rpm"), value=10000)
        self._rpm_entry.pack(side="left", padx=(16, 0))

        row3 = ctk.CTkFrame(card, fg_color="transparent")
        row3.pack(fill="x")

        self._plunge_entry = CNCEntry(row3, t(self.lang, "plunge"), value=100.0)
        self._plunge_entry.pack(side="left")

        self._ramp_entry = CNCEntry(row3, t(self.lang, "ramp_angle"), value=2.0)
        self._ramp_entry.pack(side="left", padx=(16, 0))

        self._3d_widgets.append((self._depth_entry, {"side": "left"}))
        self._3d_widgets.append((self._ramp_entry, {"side": "left", "padx": (16, 0)}))

    def _build_strategy_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_strategy_title = self._make_section_title(card, t(self.lang, "sec_strategy"))

        self._strategy_var = ctk.StringVar(value="zigzag")
        strategies = [
            ("zigzag", "strategy_zigzag"),
            ("climb", "strategy_climb"),
            ("conventional", "strategy_conventional"),
        ]

        self._strategy_widgets = []
        for value, label_key in strategies:
            rb = ctk.CTkRadioButton(
                card, text=t(self.lang, label_key),
                variable=self._strategy_var, value=value,
                font=FONTS["body"], fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"], text_color=COLORS["text"],
            )
            rb.pack(anchor="w", pady=1)
            self._strategy_widgets.append((rb, label_key))

        detail_row = ctk.CTkFrame(card, fg_color="transparent")
        detail_row.pack(fill="x", pady=(6, 0))
        self._detail_label_3d = ctk.CTkLabel(
            detail_row, text=t(self.lang, "detail_level"),
            font=FONTS["body"], text_color=COLORS["text"],
        )
        self._detail_label_3d.pack(side="left")
        self._detail_slider_3d = ctk.CTkSlider(
            detail_row, from_=0.0, to=1.0, variable=self._detail_level_var,
            progress_color=COLORS["accent"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], width=160,
        )
        self._detail_slider_3d.pack(side="left", padx=(8, 4), fill="x", expand=True)
        self._detail_val_label_3d = ctk.CTkLabel(
            detail_row, text="0.50", font=FONTS["small_bold"],
            text_color=COLORS["text_bright"], width=36, anchor="e",
        )
        self._detail_val_label_3d.pack(side="left")
        self._detail_slider_3d.configure(command=self._on_detail_change_3d)

        self._3d_widgets.append((card.master, {"fill": "x", "padx": 4, "pady": (0, 4)}))
        self._3d_widgets.append((detail_row, {"fill": "x", "pady": (0, 4)}))

    def _build_2d_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_2d_title = self._make_section_title(card, t(self.lang, "sec_2d"))

        self._passes_entry = CNCEntry(card, t(self.lang, "passes"), value=1)
        self._passes_entry.pack(fill="x", pady=(0, 4))

        detail_row = ctk.CTkFrame(card, fg_color="transparent")
        detail_row.pack(fill="x", pady=(2, 0))
        self._detail_label = ctk.CTkLabel(
            detail_row, text=t(self.lang, "detail_level"),
            font=FONTS["body"], text_color=COLORS["text"],
        )
        self._detail_label.pack(side="left")
        self._detail_level_var = ctk.DoubleVar(value=0.5)
        self._detail_slider = ctk.CTkSlider(
            detail_row, from_=0.0, to=1.0, variable=self._detail_level_var,
            progress_color=COLORS["accent"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], width=160,
        )
        self._detail_slider.pack(side="left", padx=(8, 4), fill="x", expand=True)
        self._detail_val_label = ctk.CTkLabel(
            detail_row, text="0.50", font=FONTS["small_bold"],
            text_color=COLORS["text_bright"], width=36, anchor="e",
        )
        self._detail_val_label.pack(side="left")
        self._detail_slider.configure(command=self._on_detail_change)

        self._2d_widgets.append((card.master, {"fill": "x", "padx": 4, "pady": (0, 4)}))
        card.master.pack_forget()
        self._2d_widgets.append((detail_row, {"fill": "x", "pady": (0, 4)}))

    def _build_image_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_image_title = self._make_section_title(card, t(self.lang, "sec_image"))

        cb_frame = ctk.CTkFrame(card, fg_color="transparent")
        cb_frame.pack(fill="x", pady=(0, 8))

        self._bg_var = ctk.BooleanVar(value=False)
        self._contrast_var = ctk.BooleanVar(value=True)
        self._sharpen_var = ctk.BooleanVar(value=True)
        self._smooth_var = ctk.BooleanVar(value=True)
        self._invert_var = ctk.BooleanVar(value=False)

        checks = [
            ("remove_bg", self._bg_var),
            ("clahe", self._contrast_var),
            ("sharpen", self._sharpen_var),
            ("smooth", self._smooth_var),
            ("invert", self._invert_var),
        ]

        self._cb_widgets = []
        for i, (key, var) in enumerate(checks):
            cb = ctk.CTkCheckBox(
                cb_frame, text=t(self.lang, key), variable=var,
                font=FONTS["small"], fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"], text_color=COLORS["text"],
            )
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=(0, 12), pady=2)
            self._cb_widgets.append((cb, key))

        gamma_row = ctk.CTkFrame(card, fg_color="transparent")
        gamma_row.pack(fill="x", pady=(4, 0))

        self._gamma_label_text = ctk.CTkLabel(
            gamma_row, text=t(self.lang, "gamma"),
            font=FONTS["body"], text_color=COLORS["text"],
        )
        self._gamma_label_text.pack(side="left")

        self._gamma_var = ctk.DoubleVar(value=0.80)
        self._gamma_slider = ctk.CTkSlider(
            gamma_row, from_=0.3, to=1.5, variable=self._gamma_var,
            progress_color=COLORS["accent"], button_color=COLORS["accent"],
            button_hover_color=COLORS["accent_hover"], width=200,
        )
        self._gamma_slider.pack(side="left", padx=(12, 0), fill="x", expand=True)

    def _build_smart_section(self, parent) -> None:
        card = self._make_card(parent)
        self._sec_smart_title = self._make_section_title(card, t(self.lang, "sec_smart"))

        self._smart_var = ctk.BooleanVar(value=True)
        self._smart_cb = ctk.CTkCheckBox(
            card, text=t(self.lang, "smart_auto"), variable=self._smart_var,
            font=FONTS["body_bold"], fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"], text_color=COLORS["text"],
        )
        self._smart_cb.pack(anchor="w", pady=(0, 6))

        self._smart_labels: dict[str, ctk.CTkLabel] = {}
        fields = [
            ("complexity", "smart_complexity"),
            ("detail", "smart_detail"),
            ("portrait", "smart_portrait"),
            ("spacing_note", "smart_spacing"),
            ("depth_note", "smart_depth"),
            ("gamma_note", "smart_gamma"),
            ("mode_note", "smart_mode"),
        ]

        for key, label_key in fields:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", pady=1)
            lbl = ctk.CTkLabel(
                row, text=t(self.lang, label_key), font=FONTS["small"],
                text_color=COLORS["text_dim"], width=110, anchor="w",
            )
            lbl.pack(side="left")
            val_label = ctk.CTkLabel(
                row, text="--", font=FONTS["small_bold"],
                text_color=COLORS["text_bright"], anchor="w",
            )
            val_label.pack(side="left", padx=(4, 0))
            self._smart_labels[key] = val_label

        self._apply_suggestions_btn = ctk.CTkButton(
            card, text=t(self.lang, "smart_apply"), font=FONTS["button_small"],
            fg_color=COLORS["bg_mid"], hover_color=COLORS["accent"],
            height=30, command=self._on_apply_suggestions,
        )
        self._apply_suggestions_btn.pack(fill="x", pady=(8, 0))

    def _on_detail_change(self, value: float) -> None:
        self._detail_val_label.configure(text=f"{value:.2f}")

    def _on_detail_change_3d(self, value: float) -> None:
        self._detail_val_label_3d.configure(text=f"{value:.2f}")
        self._detail_val_label.configure(text=f"{value:.2f}")

    def _build_action_section(self, parent) -> None:
        card = self._make_card(parent)

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 8))

        self._run_btn = ctk.CTkButton(
            btn_row, text=t(self.lang, "run"), font=FONTS["run_button"],
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
            height=48, command=self._on_run,
        )
        self._run_btn.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self._cancel_btn = ctk.CTkButton(
            btn_row, text=t(self.lang, "cancel"), font=FONTS["button"],
            fg_color=COLORS["bg_mid"], hover_color=COLORS["danger"],
            height=48, command=self._on_cancel, state="disabled",
        )
        self._cancel_btn.pack(side="left", padx=(4, 0))

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x")

        actions = [
            ("save_gcode", self._on_save_gcode),
            ("save_preview", self._on_save_preview),
            ("save_config", self._on_save_config),
            ("load_config", self._on_load_config),
        ]

        self._action_btns = []
        for key, cmd in actions:
            btn = ctk.CTkButton(
                btn_row, text=t(self.lang, key), font=FONTS["button_small"],
                fg_color=COLORS["bg_mid"], hover_color=COLORS["accent"],
                height=32, command=cmd,
            )
            btn.pack(side="left", expand=True, fill="x", padx=2)
            self._action_btns.append((btn, key))

    def _build_status_bar(self) -> None:
        status_frame = ctk.CTkFrame(self.root, fg_color=COLORS["bg_mid"], height=36)
        status_frame.pack(fill="x", side="bottom")
        status_frame.pack_propagate(False)

        self._status_var = ctk.StringVar(value=t(self.lang, "ready"))
        self._status_label = ctk.CTkLabel(
            status_frame, textvariable=self._status_var, font=FONTS["status"],
            text_color=COLORS["text_dim"], anchor="w",
        )
        self._status_label.pack(side="left", padx=12, fill="x", expand=True)

        self._progress_bar = ctk.CTkProgressBar(
            status_frame, width=200, height=16,
            progress_color=COLORS["accent"], fg_color=COLORS["bg_card"],
        )
        self._progress_bar.pack(side="right", padx=12)
        self._progress_bar.set(0)

    def _apply_saved_settings(self) -> None:
        s = self._settings
        if s.get("language") == "fa":
            self.set_language("fa")
        if "mode" in s:
            self._mode_var.set(s["mode"])
        if "material" in s:
            self._material_var.set(s["material"])
            self._update_material_info()
        if "engraving_mode" in s:
            self._eng_mode_var.set(s["engraving_mode"])
            self._update_engraving_mode_visibility()
        if "width_mm" in s:
            self._width_entry.set(s["width_mm"])
        if "height_mm" in s:
            self._height_entry.set(s["height_mm"])
        if "line_spacing_mm" in s:
            self._spacing_entry.set(s["line_spacing_mm"])
        if "max_depth" in s:
            self._depth_entry.set(s["max_depth"])
        if "safe_z" in s:
            self._safe_z_entry.set(s["safe_z"])
        if "feed_rate" in s:
            self._feed_entry.set(s["feed_rate"])
        if "spindle_rpm" in s:
            self._rpm_entry.set(s["spindle_rpm"])
        if "plunge_rate" in s:
            self._plunge_entry.set(s["plunge_rate"])
        if "ramp_angle" in s:
            self._ramp_entry.set(s["ramp_angle"])
        if "carving_strategy" in s:
            self._strategy_var.set(s["carving_strategy"])
        if "remove_background" in s:
            self._bg_var.set(s["remove_background"])
        if "contrast_enhance" in s:
            self._contrast_var.set(s["contrast_enhance"])
        if "sharpen_edges" in s:
            self._sharpen_var.set(s["sharpen_edges"])
        if "bilateral_filter" in s:
            self._smooth_var.set(s["bilateral_filter"])
        if "invert" in s:
            self._invert_var.set(s["invert"])
        if "gamma" in s:
            self._gamma_var.set(s["gamma"])
        if "smart_settings" in s:
            self._smart_var.set(s["smart_settings"])
        if "contour_passes" in s:
            self._passes_entry.set(s["contour_passes"])
        if "detail_level" in s:
            self._detail_level_var.set(s["detail_level"])
            self._detail_val_label.configure(text=f"{s['detail_level']:.2f}")
            self._detail_val_label_3d.configure(text=f"{s['detail_level']:.2f}")

    def _collect_settings(self) -> dict[str, Any]:
        try:
            geo = self.root.geometry()
            parts = geo.replace("x", "+").split("+")
            self._settings["window_width"] = int(parts[0])
            self._settings["window_height"] = int(parts[1])
            self._settings["window_x"] = int(parts[2])
            self._settings["window_y"] = int(parts[3])
        except Exception:
            pass

        self._settings["language"] = self.lang
        self._settings["engraving_mode"] = self._eng_mode_var.get()
        self._settings["mode"] = self._mode_var.get()
        self._settings["material"] = self._material_var.get()
        self._settings["width_mm"] = float(self._width_entry.get())
        self._settings["height_mm"] = float(self._height_entry.get())
        self._settings["line_spacing_mm"] = float(self._spacing_entry.get())
        self._settings["max_depth"] = float(self._depth_entry.get())
        self._settings["safe_z"] = float(self._safe_z_entry.get())
        self._settings["feed_rate"] = float(self._feed_entry.get())
        self._settings["spindle_rpm"] = int(float(self._rpm_entry.get()))
        self._settings["plunge_rate"] = float(self._plunge_entry.get())
        self._settings["ramp_angle"] = float(self._ramp_entry.get())
        self._settings["carving_strategy"] = self._strategy_var.get()
        self._settings["remove_background"] = self._bg_var.get()
        self._settings["contrast_enhance"] = self._contrast_var.get()
        self._settings["sharpen_edges"] = self._sharpen_var.get()
        self._settings["bilateral_filter"] = self._smooth_var.get()
        self._settings["invert"] = self._invert_var.get()
        self._settings["gamma"] = self._gamma_var.get()
        self._settings["smart_settings"] = self._smart_var.get()
        self._settings["contour_passes"] = int(float(self._passes_entry.get()))
        self._settings["detail_level"] = self._detail_level_var.get()
        return self._settings

    def _on_close(self) -> None:
        self._collect_settings()
        save_settings(self._settings)
        self.root.destroy()

    def _make_card(self, parent) -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=8)
        card.pack(fill="x", padx=4, pady=(0, 4))
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)
        return inner

    def _make_section_title(self, parent, text: str) -> ctk.CTkLabel:
        lbl = ctk.CTkLabel(
            parent, text=text, font=FONTS["section"],
            text_color=COLORS["accent"], anchor="w",
        )
        lbl.pack(anchor="w", pady=(0, 6))
        return lbl

    def set_language(self, lang: str) -> None:
        self.lang = lang
        self._apply_language()

    def _apply_language(self) -> None:
        L = self.lang
        self._title_label.configure(text=t(L, "app_name"))
        self._version_label.configure(text=t(L, "version"))
        self._shortcuts_label.configure(text=t(L, "shortcuts_hint"))

        if L == "en":
            self._en_btn.configure(fg_color=COLORS["accent"])
            self._fa_btn.configure(fg_color=COLORS["bg_mid"])
        else:
            self._en_btn.configure(fg_color=COLORS["bg_mid"])
            self._fa_btn.configure(fg_color=COLORS["accent"])

        self._sec_file_title.configure(text=t(L, "sec_file"))
        self._sec_mode_title.configure(text=t(L, "sec_mode"))
        self._sec_material_title.configure(text=t(L, "sec_material"))
        self._sec_dim_title.configure(text=t(L, "sec_dimensions"))
        self._sec_cnc_title.configure(text=t(L, "sec_cnc"))
        self._sec_strategy_title.configure(text=t(L, "sec_strategy"))
        self._sec_image_title.configure(text=t(L, "sec_image"))
        self._sec_smart_title.configure(text=t(L, "sec_smart"))
        self._sec_eng_mode_title.configure(text=t(L, "sec_engraving_mode"))
        self._sec_2d_title.configure(text=t(L, "sec_2d"))
        self._detail_label.configure(text=t(L, "detail_level"))
        self._detail_label_3d.configure(text=t(L, "detail_level"))

        self._run_btn.configure(text=t(L, "run"))
        self._cancel_btn.configure(text=t(L, "cancel"))
        self._browse_btn.configure(text=t(L, "browse"))
        for rb, desc_lbl, name_key, desc_key in self._mode_widgets:
            rb.configure(text=t(L, name_key))
            desc_lbl.configure(text=f"  -- {t(L, desc_key)}")
        for rb, desc_lbl, name_key, desc_key in self._eng_mode_widgets:
            rb.configure(text=t(L, name_key))
            desc_lbl.configure(text=f"  -- {t(L, desc_key)}")

        self._material_label_text.configure(text=t(L, "material_label"))
        self._bit_label_text.configure(text=t(L, "recommended_bit"))
        self._spacing_hint.configure(text=f"  {t(L, 'spacing_hint')}")

        for rb, label_key in self._strategy_widgets:
            rb.configure(text=t(L, label_key))

        for cb, key in self._cb_widgets:
            cb.configure(text=t(L, key))
        self._gamma_label_text.configure(text=t(L, "gamma"))

        self._smart_cb.configure(text=t(L, "smart_auto"))
        label_keys = {
            "complexity": "smart_complexity",
            "detail": "smart_detail",
            "portrait": "smart_portrait",
            "spacing_note": "smart_spacing",
            "depth_note": "smart_depth",
            "gamma_note": "smart_gamma",
            "mode_note": "smart_mode",
        }
        for field_key, lk in label_keys.items():
            if field_key in self._smart_labels:
                self._smart_labels[field_key].configure(text=t(L, lk))
        self._apply_suggestions_btn.configure(text=t(L, "smart_apply"))

        self._run_btn.configure(text=t(L, "run"))
        for btn, key in self._action_btns:
            btn.configure(text=t(L, key))

        tab_keys = ["preview_original", "preview_engraving", "preview_depth", "preview_contours"]
        for i, key in enumerate(tab_keys):
            try:
                self._tabview.tab(i).configure(text=t(L, key))
            except Exception:
                pass

        if self._status_var.get() in ["Ready", "\u0622\u0645\u0627\u062f\u0647"]:
            self._status_var.set(t(L, "ready"))

    def _update_engraving_mode_visibility(self) -> None:
        mode = self._eng_mode_var.get()
        is_3d = mode == "raster_3d"
        for widget, pack_kwargs in self._3d_widgets:
            if is_3d:
                try:
                    widget.pack(**pack_kwargs)
                except Exception:
                    pass
            else:
                try:
                    widget.pack_forget()
                except Exception:
                    pass
        for widget, pack_kwargs in self._2d_widgets:
            if not is_3d:
                try:
                    widget.pack(**pack_kwargs)
                except Exception:
                    pass
            else:
                try:
                    widget.pack_forget()
                except Exception:
                    pass

    def _on_engraving_mode_change(self) -> None:
        self._update_engraving_mode_visibility()

    def show_original(self, pil_img: Image.Image, info: str, filename: str) -> None:
        self._preview_original.set_image(pil_img)
        self._image_info_label.configure(text=info)
        self._file_entry.delete(0, "end")
        self._file_entry.insert(0, filename)
        self._status_var.set(f"{t(self.lang, 'loaded')} {filename}")

    def update_smart_display(self, analysis: dict[str, Any], suggestions: dict[str, Any]) -> None:
        self._smart_suggestions = suggestions

        c = analysis.get("complexity", "medium")
        self._smart_labels["complexity"].configure(text=c.capitalize())

        d = analysis.get("detail_score", 0)
        if d > 0.6:
            dt = t(self.lang, "smart_high")
        elif d > 0.3:
            dt = t(self.lang, "smart_medium")
        else:
            dt = t(self.lang, "smart_low")
        self._smart_labels["detail"].configure(text=f"{dt} ({d:.2f})")
        self._smart_labels["portrait"].configure(
            text=t(self.lang, "smart_yes") if analysis.get("is_portrait")
            else t(self.lang, "smart_no")
        )
        self._smart_labels["spacing_note"].configure(text=analysis.get("spacing_note", "--"))
        self._smart_labels["depth_note"].configure(text=analysis.get("depth_note", "--"))
        self._smart_labels["gamma_note"].configure(text=analysis.get("gamma_note", "--"))
        self._smart_labels["mode_note"].configure(text=analysis.get("mode_note", "--"))

    def get_config(self) -> dict[str, Any]:
        return {
            "engraving_mode": self._eng_mode_var.get(),
            "mode": self._mode_var.get(),
            "material": self._material_var.get(),
            "width_mm": float(self._width_entry.get()),
            "height_mm": float(self._height_entry.get()),
            "line_spacing_mm": float(self._spacing_entry.get()),
            "max_depth": float(self._depth_entry.get()),
            "safe_z": float(self._safe_z_entry.get()),
            "feed_rate": float(self._feed_entry.get()),
            "spindle_rpm": int(float(self._rpm_entry.get())),
            "plunge_rate": float(self._plunge_entry.get()),
            "remove_background": self._bg_var.get(),
            "invert": self._invert_var.get(),
            "contrast_enhance": self._contrast_var.get(),
            "sharpen_edges": self._sharpen_var.get(),
            "bilateral_filter": self._smooth_var.get(),
            "gamma": self._gamma_var.get(),
            "smart_settings": self._smart_var.get(),
            "skip_threshold": 0.005,
            "start_z": 0.3,
            "ramp_angle": float(self._ramp_entry.get()),
            "carving_strategy": self._strategy_var.get(),
            "contour_passes": int(float(self._passes_entry.get())),
            "detail_level": self._detail_level_var.get(),
        }

    def apply_config(self, config: dict[str, Any]) -> None:
        for key, entry in [
            ("mode", self._mode_var), ("material", self._material_var),
            ("width_mm", self._width_entry), ("height_mm", self._height_entry),
            ("line_spacing_mm", self._spacing_entry), ("max_depth", self._depth_entry),
            ("safe_z", self._safe_z_entry), ("feed_rate", self._feed_entry),
            ("spindle_rpm", self._rpm_entry), ("plunge_rate", self._plunge_entry),
            ("ramp_angle", self._ramp_entry), ("carving_strategy", self._strategy_var),
            ("remove_background", self._bg_var), ("invert", self._invert_var),
            ("contrast_enhance", self._contrast_var), ("sharpen_edges", self._sharpen_var),
            ("bilateral_filter", self._smooth_var), ("gamma", self._gamma_var),
            ("smart_settings", self._smart_var),
            ("detail_level", self._detail_level_var),
        ]:
            if key in config:
                try:
                    entry.set(config[key])
                except Exception:
                    pass
        if "engraving_mode" in config:
            self._eng_mode_var.set(config["engraving_mode"])
            self._update_engraving_mode_visibility()
        if "material" in config:
            self._update_material_info()

    def update_cnc_from_material(self, preset: dict) -> None:
        self._depth_entry.set(preset["max_depth"])
        self._safe_z_entry.set(preset["safe_z"])
        self._feed_entry.set(preset["feed_rate"])
        self._rpm_entry.set(preset["spindle_rpm"])
        self._plunge_entry.set(preset["plunge_rate"])
        self._spacing_entry.set(preset["line_spacing_mm"])
        self._update_material_info()

    def start_processing(self) -> None:
        self._run_btn.configure(state="disabled", text=t(self.lang, "processing"))
        self._cancel_btn.configure(state="normal")
        self._status_var.set(t(self.lang, "processing_msg"))
        self._progress_bar.set(0)

    def stop_processing(self) -> None:
        self._run_btn.configure(state="normal", text=t(self.lang, "run"))
        self._cancel_btn.configure(state="disabled")

    def update_progress(self, percent: float, message: str) -> None:
        self._progress_bar.set(min(percent, 1.0))
        self._status_var.set(message)

    def show_result(self, result) -> None:
        import cv2

        if result.depth_map is not None:
            depth_rgb = cv2.cvtColor(result.depth_map, cv2.COLOR_GRAY2RGB)
            depth_pil = Image.fromarray(depth_rgb)
            self._preview_depth.set_image(depth_pil)

        if result.engraving_preview is not None:
            engrave_rgb = cv2.cvtColor(result.engraving_preview, cv2.COLOR_BGR2RGB)
            engrave_pil = Image.fromarray(engrave_rgb)
            self._preview_engraving.set_image(engrave_pil)
            self._preview_contours.clear()

        if result.contour_preview is not None:
            contour_rgb = cv2.cvtColor(result.contour_preview, cv2.COLOR_BGR2RGB)
            contour_pil = Image.fromarray(contour_rgb)
            self._preview_contours.set_image(contour_pil)

        stats = result.stats
        if stats:
            self._status_var.set(
                f"{t(self.lang, 'done')} {stats.total_lines:,} lines  |  {result.image_dims} px"
            )

        cfg = result.config
        used_settings = {
            "engraving_mode": cfg.get("engraving_mode", "--"),
            "mode": cfg.get("mode", "--"),
            "material": cfg.get("material", "--"),
            "max_depth": cfg.get("max_depth", "--"),
            "line_spacing_mm": cfg.get("line_spacing_mm", "--"),
            "gamma": cfg.get("gamma", "--"),
        }

        stats_dict = {}
        if stats:
            stats_dict = {
                "total_lines": stats.total_lines,
                "rapid_moves": stats.rapid_moves,
                "cutting_moves": stats.cutting_moves,
                "ramp_moves": stats.ramp_moves,
                "cutting_distance_mm": stats.cutting_distance_mm,
            }
            if hasattr(stats, "contour_count"):
                stats_dict["contour_count"] = stats.contour_count

        SuccessDialog(
            self.root, stats=stats_dict, used_settings=used_settings,
            on_save=self._controller.on_save_gcode_from_dialog, lang=self.lang,
        )

    def set_status(self, message: str) -> None:
        self._status_var.set(message)

    def show_error(self, title: str, message: str, details: str = "") -> None:
        ErrorDialog(self.root, title=title, message=message, details=details, lang=self.lang)

    def show_warning(self, title: str, message: str) -> None:
        ErrorDialog(self.root, title=title, message=message, lang=self.lang)

    def _on_browse(self) -> None:
        if self._controller:
            self._controller.on_browse_image()

    def _on_run(self) -> None:
        if self._controller:
            self._controller.on_run_conversion()

    def _on_cancel(self) -> None:
        if self._controller:
            self._controller.on_cancel_conversion()

    def _on_apply_suggestions(self) -> None:
        if self._controller:
            self._controller.on_apply_suggestions()

    def _on_save_gcode(self) -> None:
        if self._controller:
            self._controller.on_save_gcode()

    def _on_save_preview(self) -> None:
        if self._controller:
            self._controller.on_save_preview()

    def _on_save_config(self) -> None:
        if self._controller:
            self._controller.on_save_config()

    def _on_load_config(self) -> None:
        if self._controller:
            self._controller.on_load_config()

    def _on_material_change(self, choice: str) -> None:
        if self._controller:
            self._controller.on_material_change(choice)

    def _update_material_info(self) -> None:
        mat = self._material_var.get()
        preset = MATERIAL_PRESETS.get(mat, MATERIAL_PRESETS[DEFAULT_MATERIAL])
        info = (
            f"RPM: {preset['spindle_rpm']}  |  "
            f"Feed: {preset['feed_rate']} mm/min  |  "
            f"Depth: {preset['max_depth']} mm"
        )
        self._material_info.configure(text=info)
        self._bit_value_label.configure(text=preset["recommended_bit"])


def main() -> None:
    root = ctk.CTk()
    try:
        root.tk.call("tk", "scaling", 1.25)
    except Exception:
        pass
    PixelForgeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
