"""
Discord-inspired dark theme and custom tkinter widgets.
"""
import os
import tkinter as tk
from tkinter import ttk

FONTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")


def load_fonts():
    """Register the bundled pixel fonts for this process (Windows only)."""
    try:
        import ctypes
        FR_PRIVATE = 0x10
        for name in os.listdir(FONTS_DIR):
            if name.lower().endswith(".ttf"):
                ctypes.windll.gdi32.AddFontResourceExW(os.path.join(FONTS_DIR, name), FR_PRIVATE, 0)
    except Exception:
        pass


load_fonts()

# Pixel fonts render crisply at multiples of their design grid, so sizes are in
# pixels (negative values). Missing fonts fall back to Tk's default font.
PIXEL = "Press Start 2P"   # arcade font: headings, buttons, tabs
TERMINAL = "VT323"         # narrow terminal font: body text and inputs
SYMBOL = "Segoe UI Symbol" # glyphs the pixel fonts lack (⚙ ✓ ✕)

FONT_TITLE = (PIXEL, -16)
FONT_DISPLAY = (PIXEL, -24)
FONT_HEADING = (PIXEL, -8)
FONT_BUTTON = (PIXEL, -8)
FONT_BODY_LARGE = (TERMINAL, -24)
FONT_BODY = (TERMINAL, -20)
FONT_SMALL = (TERMINAL, -18)

# Discord dark palette
BG = "#313338"
BG_SECONDARY = "#2B2D31"
BG_TERTIARY = "#1E1F22"
BG_HOVER = "#3A3C42"
CARD = "#232428"
DIVIDER = "#3F4147"
TEXT = "#DBDEE1"
TEXT_STRONG = "#F2F3F5"
TEXT_MUTED = "#949BA4"
LINK = "#00A8FC"
BLURPLE = "#5865F2"
BLURPLE_HOVER = "#4752C4"
GREEN = "#23A55A"
GREEN_HOVER = "#1A8946"
RED = "#F23F43"
RED_HOVER = "#DA373C"
YELLOW = "#F0B232"
GREY = "#4E5058"
GREY_HOVER = "#6D6F78"
OFFLINE = "#80848E"
DISABLED_BG = "#2E3035"
DISABLED_FG = "#5C5E66"

# variant -> (background, hover background, foreground)
BUTTON_VARIANTS = {
    "primary": (BLURPLE, BLURPLE_HOVER, "#FFFFFF"),
    "success": (GREEN, GREEN_HOVER, "#FFFFFF"),
    "secondary": (GREY, GREY_HOVER, "#FFFFFF"),
    "danger": (RED, RED_HOVER, "#FFFFFF"),
    "ghost": (BG_SECONDARY, BG_HOVER, TEXT_MUTED),
    "tab": ("#383A40", "#404249", TEXT_MUTED),
    "tab_active": ("#4E5058", "#4E5058", TEXT_STRONG),
}


def apply_theme(root):
    """Configure ttk styles and option defaults for the dark theme."""
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TCombobox", fieldbackground=BG_TERTIARY, background=BG_TERTIARY,
                    foreground=TEXT, arrowcolor=TEXT_MUTED, bordercolor=BG_TERTIARY,
                    lightcolor=BG_TERTIARY, darkcolor=BG_TERTIARY, insertcolor=TEXT,
                    padding=(8, 6), arrowsize=14)
    style.map("TCombobox",
              fieldbackground=[("disabled", BG_SECONDARY), ("readonly", BG_TERTIARY)],
              foreground=[("disabled", TEXT_MUTED), ("readonly", TEXT)],
              selectbackground=[("readonly", BG_TERTIARY)],
              selectforeground=[("readonly", TEXT)],
              background=[("active", BG_TERTIARY), ("pressed", BG_TERTIARY)],
              arrowcolor=[("active", TEXT), ("pressed", TEXT)],
              bordercolor=[("focus", BLURPLE)],
              lightcolor=[("focus", BLURPLE)],
              darkcolor=[("focus", BLURPLE)])

    root.option_add("*TCombobox*Listbox.background", BG_TERTIARY)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", BLURPLE)
    root.option_add("*TCombobox*Listbox.selectForeground", "#FFFFFF")
    root.option_add("*TCombobox*Listbox.font", FONT_BODY)
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # Scrolling over a readonly combobox would silently change the selected game
    root.unbind_class("TCombobox", "<MouseWheel>")

    style.layout("Dark.Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Dark.Vertical.TScrollbar", troughcolor=BG, background=BG_TERTIARY,
                    bordercolor=BG, lightcolor=BG_TERTIARY, darkcolor=BG_TERTIARY,
                    arrowsize=8, width=8, gripcount=0)
    style.map("Dark.Vertical.TScrollbar", background=[("active", "#1A1B1E")])


def apply_dark_title_bar(window):
    """Use a dark native title bar on Windows 10/11 (no-op elsewhere)."""
    try:
        import ctypes
        window.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
        dwm = ctypes.windll.dwmapi
        enabled = ctypes.c_int(1)
        # DWMWA_USE_IMMERSIVE_DARK_MODE is 20 on newer builds, 19 on older ones
        if dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(enabled), ctypes.sizeof(enabled)) != 0:
            dwm.DwmSetWindowAttribute(hwnd, 19, ctypes.byref(enabled), ctypes.sizeof(enabled))
        # DWMWA_CAPTION_COLOR (Windows 11), COLORREF is 0x00BBGGRR
        r, g, b = (int(BG_TERTIARY[i:i + 2], 16) for i in (1, 3, 5))
        color = ctypes.c_int(b << 16 | g << 8 | r)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
    except Exception:
        pass


def ellipsize(text, limit):
    """Shorten text to the given length with a trailing ellipsis."""
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle on a canvas."""
    points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
              x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
              x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, outline="", **kwargs)


def section_label(parent, text, bg=BG):
    """Uppercase section heading, like Discord's settings pages."""
    return tk.Label(parent, text=text.upper(), bg=bg, fg=TEXT_MUTED,
                    font=FONT_HEADING, anchor="w")


def hint_label(parent, text, bg=BG, wraplength=470):
    """Muted helper text shown under a field."""
    return tk.Label(parent, text=text, bg=bg, fg=TEXT_MUTED, font=FONT_SMALL,
                    anchor="w", justify="left", wraplength=wraplength)


def divider(parent):
    """Thin horizontal separator line."""
    return tk.Frame(parent, bg=DIVIDER, height=1)


def make_entry(parent, textvariable=None):
    """Create a dark input box. Returns (container, entry); grid the container."""
    box = tk.Frame(parent, bg=BG_TERTIARY, highlightthickness=1,
                   highlightbackground=BG_TERTIARY)
    entry = tk.Entry(box, textvariable=textvariable, bg=BG_TERTIARY, fg=TEXT,
                     insertbackground=TEXT, disabledbackground=BG_SECONDARY,
                     disabledforeground=TEXT_MUTED, selectbackground=BLURPLE,
                     selectforeground="#FFFFFF", relief="flat", bd=0,
                     highlightthickness=0, font=FONT_BODY)
    entry.pack(fill="x", padx=10, pady=7)
    entry.bind("<FocusIn>", lambda e: box.config(highlightbackground=BLURPLE), add="+")
    entry.bind("<FocusOut>", lambda e: box.config(highlightbackground=BG_TERTIARY), add="+")
    return box, entry


class Form:
    """Stacks widgets vertically in a single stretching grid column."""

    def __init__(self, body):
        self.body = body
        self.row = 0
        body.columnconfigure(0, weight=1)

    def add(self, widget, pady=0, sticky="ew"):
        widget.grid(row=self.row, column=0, sticky=sticky, pady=pady)
        self.row += 1
        return widget


class FlatButton(tk.Label):
    """Flat, colored button with hover state. Supports state=tk.DISABLED."""

    def __init__(self, master, text="", command=None, variant="primary",
                 padx=16, pady=8, font=FONT_BUTTON, **kwargs):
        self._command = command
        self._variant = variant
        self._hover = False
        super().__init__(master, text=text, padx=padx, pady=pady, font=font,
                         disabledforeground=DISABLED_FG, **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonRelease-1>", self._on_click)
        self._refresh()

    def configure(self, cnf=None, **kwargs):
        if "command" in kwargs:
            self._command = kwargs.pop("command")
        if "variant" in kwargs:
            self._variant = kwargs.pop("variant")
        result = super().configure(cnf, **kwargs)
        self._refresh()
        return result

    config = configure

    def _enabled(self):
        return str(self.cget("state")) != tk.DISABLED

    def _refresh(self):
        bg, hover, fg = BUTTON_VARIANTS[self._variant]
        if self._enabled():
            super().configure(bg=hover if self._hover else bg, fg=fg, cursor="hand2")
        else:
            super().configure(bg=DISABLED_BG, cursor="arrow")

    def _on_enter(self, event):
        self._hover = True
        self._refresh()

    def _on_leave(self, event):
        self._hover = False
        self._refresh()

    def _on_click(self, event):
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        if inside and self._enabled() and self._command:
            self._command()


class Toggle(tk.Canvas):
    """Discord-style switch bound to a BooleanVar."""

    WIDTH, HEIGHT = 40, 24

    def __init__(self, master, variable, bg=BG):
        super().__init__(master, width=self.WIDTH, height=self.HEIGHT, bg=bg,
                         highlightthickness=0, cursor="hand2")
        self.variable = variable
        self.bind("<Button-1>", lambda e: self.variable.set(not self.variable.get()))
        self.variable.trace_add("write", lambda *_: self._draw())
        self._draw()

    def _draw(self):
        self.delete("all")
        on = self.variable.get()
        h = self.HEIGHT
        round_rect(self, 0, 0, self.WIDTH, h, h // 2, fill=GREEN if on else OFFLINE)
        x = self.WIDTH - h + 3 if on else 3
        self.create_oval(x, 3, x + h - 6, h - 3, fill="#FFFFFF", outline="")
        mark = "✓" if on else "✕"
        self.create_text(x + (h - 6) / 2, h / 2, text=mark,
                         fill=GREEN if on else OFFLINE, font=(SYMBOL, 8, "bold"))


class ScrollFrame(tk.Frame):
    """Vertically scrollable container; put children in `.inner`."""

    def __init__(self, master, bg=BG):
        super().__init__(master, bg=bg)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(self, bg=bg, highlightthickness=0, bd=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", style="Dark.Vertical.TScrollbar",
                                       command=self.canvas.yview)
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        self.canvas.configure(yscrollcommand=self._on_yscroll)

        self.inner = tk.Frame(self.canvas, bg=bg)
        window = self.canvas.create_window(0, 0, window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfigure(window, width=e.width))

    def _on_yscroll(self, first, last):
        """Only show the scrollbar when the content overflows."""
        self.scrollbar.set(first, last)
        if float(first) <= 0 and float(last) >= 1:
            self.scrollbar.grid_remove()
        else:
            self.scrollbar.grid()

    def scroll(self, units):
        if self.canvas.yview() != (0.0, 1.0):
            self.canvas.yview_scroll(units, "units")


def route_mousewheel(root):
    """Scroll whichever ScrollFrame is under the pointer."""
    def on_wheel(event):
        try:
            widget = root.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):
            return
        if widget is None or widget.winfo_class() in ("Text", "Listbox"):
            return
        while widget is not None:
            if isinstance(widget, ScrollFrame):
                widget.scroll(-1 if event.delta > 0 else 1)
                return
            widget = widget.master

    root.bind_all("<MouseWheel>", on_wheel)
