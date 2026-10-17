"""
Retro desktop theme modelled on the1azreen.neocities.org, plus custom tkinter widgets.

Panels are "windows" with a neon border, a title bar and a bordered content
area; the footer is a taskbar. The colours follow the selected console's brand
(PlayStation, Xbox, Nintendo, Sega, SNK, Bandai, NEC) and switch live via set_palette().
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

# Status colours mean the same thing on every palette, so they never change
WHITE = "#FFFFFF"
GREEN = "#23A55A"
GREEN_HOVER = "#1A8946"
RED = "#F23F43"
RED_HOVER = "#DA373C"
YELLOW = "#F0B232"
OFFLINE = "#80848E"
STATIC_COLORS = {WHITE, GREEN, GREEN_HOVER, RED, RED_HOVER, YELLOW, OFFLINE}

# Brand specs. "default" is the website's own palette (needy.css): deep purple
# windows, neon yellow borders, teal highlights and a magenta taskbar.
BRANDS = {
    "default": dict(name="Rich Presence", desktop="#120B26", window="#2B1B4F", outer="#3C2E7B",
                    content="#1B1B2F", input="#120F22", border="#F7C948", text="#E8E2F8",
                    strong="#FFE38A", muted="#A39BC6", accent="#6DE0F6", accent_fg="#1B1B2F",
                    taskbar="#FF6FF2", taskbar_fg="#1B1B2F"),
    "sony": dict(name="PlayStation", desktop="#050B1F", window="#0B1F4D", outer="#12307A",
                 content="#0A1530", input="#060E22", border="#6CC4FF", text="#DCE8FF",
                 strong="#F4F8FF", muted="#8FA6CF", accent="#00A3FF", accent_fg="#04122E",
                 taskbar="#0070D1", taskbar_fg="#F4F8FF"),
    "xbox": dict(name="Xbox", desktop="#050D05", window="#0F2A10", outer="#174A18",
                 content="#0A170A", input="#061006", border="#9BF00B", text="#E2F5DC",
                 strong="#F4FFF0", muted="#8FB08A", accent="#52B043", accent_fg="#041004",
                 taskbar="#107C10", taskbar_fg="#F4FFF0"),
    "nintendo": dict(name="Nintendo", desktop="#140405", window="#3A0B10", outer="#5C1219",
                     content="#1E0709", input="#120405", border="#FF6B76", text="#FFE6E8",
                     strong="#FFF6F6", muted="#C79297", accent="#E60012", accent_fg="#FFF6F6",
                     taskbar="#B3000E", taskbar_fg="#FFF6F6"),
    # Sega blue with Sonic-yellow highlights, so it doesn't read as PlayStation
    "sega": dict(name="Sega", desktop="#040E1C", window="#0A2A52", outer="#12407A",
                 content="#071A33", input="#040F1F", border="#E6F2FF", text="#DDEBFA",
                 strong="#FFFFF4", muted="#8DA9C9", accent="#FFCC00", accent_fg="#0A1C33",
                 taskbar="#0089CF", taskbar_fg="#FFFFF4"),
    # Neo Geo black and gold, with SNK red on the taskbar
    "snk": dict(name="SNK", desktop="#0A0907", window="#1F1A12", outer="#3A3020",
                content="#14110C", input="#0B0A07", border="#D4AF37", text="#F1E6C8",
                strong="#FFF4D6", muted="#A8996F", accent="#E8C547", accent_fg="#1A1408",
                taskbar="#C8102E", taskbar_fg="#FFF4D6"),
    # Bandai orange and amber
    "bandai": dict(name="Bandai", desktop="#140A03", window="#33190A", outer="#552B12",
                   content="#1F0F06", input="#120802", border="#FFB000", text="#FFE9D2",
                   strong="#FFF7EC", muted="#C29A78", accent="#F08300", accent_fg="#1F0F06",
                   taskbar="#E8590C", taskbar_fg="#FFF7EC"),
    # NEC navy with TurboGrafx orange
    "nec": dict(name="NEC", desktop="#07081A", window="#151A4A", outer="#232B72",
                content="#0C1030", input="#060820", border="#9FB4FF", text="#E0E6FF",
                strong="#F7F8FF", muted="#8C95C4", accent="#F15A22", accent_fg="#FFF7F2",
                taskbar="#1F2A8C", taskbar_fg="#F7F8FF"),
}

# Words in a console sheet name that pick a brand, checked in this order
BRAND_KEYWORDS = (
    ("sega", ("sega", "genesis", "mega drive", "master system", "saturn", "dreamcast",
              "game gear", "32x", "sg-1000")),
    ("snk", ("neo geo", "neo-geo", "snk")),
    ("bandai", ("wonderswan", "bandai", "playdia")),
    ("nec", ("turbografx", "pc engine", "pc-engine", "supergrafx", "pc-fx", "nec")),
)
NINTENDO_WORDS = ("nes", "snes", "n64", "ds", "3ds", "wii", "switch", "gamecube")


def brand_for(console):
    """Map a console sheet name (PS2, Xbox 360, Wii U, Saturn...) to a BRANDS key."""
    name = (console or "").strip().lower()
    if name.startswith("ps") or "playstation" in name:
        return "sony"
    if "xbox" in name:
        return "xbox"
    for brand, keywords in BRAND_KEYWORDS:
        if any(word in name for word in keywords):
            return brand
    if ("nintendo" in name or "game boy" in name
            or any(word in NINTENDO_WORDS for word in name.split())):
        return "nintendo"
    return "default"


def _mix(a, b, t):
    """Blend two #RRGGBB colours: t=0 gives a, t=1 gives b."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(ca, cb))


def _palette(s):
    """Expand a brand spec into every named colour role the UI uses.

    Live recolouring swaps colours by value, so each role must have a unique
    hex: duplicates are nudged by one step of blue, which is invisible.
    """
    roles = {
        "DESKTOP": s["desktop"],
        "BG": s["content"],
        "BG_SECONDARY": s["window"],
        "BG_TERTIARY": s["input"],
        "BG_HOVER": s["outer"],
        "CARD": _mix(s["content"], s["window"], 0.45),
        "DIVIDER": _mix(s["outer"], s["border"], 0.25),
        "TEXT": s["text"],
        "TEXT_STRONG": s["strong"],
        "TEXT_MUTED": s["muted"],
        "LINK": s["border"],
        "BLURPLE": s["accent"],
        "BLURPLE_HOVER": _mix(s["accent"], WHITE, 0.25),
        "ACCENT_FG": s["accent_fg"],
        "GREY": s["outer"],
        "GREY_HOVER": _mix(s["outer"], WHITE, 0.15),
        "DISABLED_BG": _mix(s["window"], s["content"], 0.5),
        "DISABLED_FG": _mix(s["muted"], s["window"], 0.55),
        "BORDER": s["border"],
        "TITLE_BG": s["window"],
        "TITLE_FG": s["border"],
        "TITLE_ACTIVE": s["accent"],
        "TITLE_ACTIVE_FG": s["accent_fg"],
        "TASKBAR": s["taskbar"],
        "TASKBAR_HOVER": _mix(s["taskbar"], WHITE, 0.2),
        "TASKBAR_FG": s["taskbar_fg"],
    }
    used = {c.upper() for c in STATIC_COLORS}
    for role, color in roles.items():
        color = color.upper()
        r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
        step = 1
        while color in used:
            # Try b+1, b-1, b+2, b-2... staying inside 0-255
            offset = (step + 1) // 2 * (1 if step % 2 else -1)
            step += 1
            if 0 <= b + offset <= 255:
                color = f"#{r:02X}{g:02X}{b + offset:02X}"
        used.add(color)
        roles[role] = color
    return roles


PALETTES = {key: _palette(spec) for key, spec in BRANDS.items()}
BRAND = "default"
globals().update(PALETTES[BRAND])

# variant -> (background, hover background, foreground, relief)
BUTTON_VARIANTS = {}


def _build_variants():
    BUTTON_VARIANTS.update({
        "primary": (BLURPLE, BLURPLE_HOVER, ACCENT_FG, "raised"),
        "success": (GREEN, GREEN_HOVER, WHITE, "raised"),
        "secondary": (GREY, GREY_HOVER, TEXT_STRONG, "raised"),
        "danger": (RED, RED_HOVER, WHITE, "raised"),
        "ghost": (DESKTOP, BG_HOVER, TEXT_MUTED, "flat"),
        "tab": (BG_SECONDARY, BG_HOVER, TEXT, "raised"),
        "tab_active": (BLURPLE, BLURPLE, ACCENT_FG, "sunken"),
        "icon": (BG_TERTIARY, BG_HOVER, TEXT_MUTED, "raised"),
        "icon_active": (BG_HOVER, BG_HOVER, TEXT_STRONG, "sunken"),
        "taskbar": (TASKBAR, TASKBAR_HOVER, TASKBAR_FG, "raised"),
    })


_build_variants()


def apply_theme(root):
    """Configure ttk styles and option defaults for the current palette."""
    root.configure(bg=DESKTOP)
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure("TCombobox", fieldbackground=BG_TERTIARY, background=BG_SECONDARY,
                    foreground=TEXT, arrowcolor=BORDER, bordercolor=BG_HOVER,
                    lightcolor=BG_TERTIARY, darkcolor=BG_TERTIARY, insertcolor=TEXT,
                    padding=(8, 6), arrowsize=14)
    style.map("TCombobox",
              fieldbackground=[("disabled", BG_SECONDARY), ("readonly", BG_TERTIARY)],
              foreground=[("disabled", TEXT_MUTED), ("readonly", TEXT)],
              selectbackground=[("readonly", BG_TERTIARY)],
              selectforeground=[("readonly", TEXT)],
              background=[("active", BG_HOVER), ("pressed", BG_HOVER)],
              arrowcolor=[("active", TEXT_STRONG), ("pressed", TEXT_STRONG)],
              bordercolor=[("focus", BORDER)],
              lightcolor=[("focus", BG_TERTIARY)],
              darkcolor=[("focus", BG_TERTIARY)])

    root.option_add("*TCombobox*Listbox.background", BG_TERTIARY)
    root.option_add("*TCombobox*Listbox.foreground", TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", BLURPLE)
    root.option_add("*TCombobox*Listbox.selectForeground", ACCENT_FG)
    root.option_add("*TCombobox*Listbox.font", FONT_BODY)
    root.option_add("*TCombobox*Listbox.relief", "flat")
    root.option_add("*TCombobox*Listbox.borderWidth", 0)

    # Scrolling over a readonly combobox would silently change the selected game
    root.unbind_class("TCombobox", "<MouseWheel>")

    # Chunky scrollbar like the site's: border-coloured thumb on the window colour
    style.layout("Dark.Vertical.TScrollbar", [
        ("Vertical.Scrollbar.trough", {"sticky": "ns", "children": [
            ("Vertical.Scrollbar.thumb", {"expand": "1", "sticky": "nswe"})]})])
    style.configure("Dark.Vertical.TScrollbar", troughcolor=BG_SECONDARY, background=BORDER,
                    bordercolor=BG_SECONDARY, lightcolor=BORDER, darkcolor=BORDER,
                    arrowsize=10, width=10, gripcount=0)
    style.map("Dark.Vertical.TScrollbar", background=[("active", TASKBAR)])


def apply_dark_title_bar(window):
    """Use a dark native title bar tinted to the palette on Windows 10/11."""
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
        r, g, b = (int(DESKTOP[i:i + 2], 16) for i in (1, 3, 5))
        color = ctypes.c_int(b << 16 | g << 8 | r)
        dwm.DwmSetWindowAttribute(hwnd, 35, ctypes.byref(color), ctypes.sizeof(color))
    except Exception:
        pass


# ---------------------------------------------------------------- live palette

COLOR_OPTIONS = ("bg", "fg", "activebackground", "activeforeground", "highlightbackground",
                 "highlightcolor", "insertbackground", "selectbackground", "selectforeground",
                 "disabledbackground", "disabledforeground", "readonlybackground")


def _swap(value, mapping):
    return mapping.get(str(value).upper()) if value else None


def _recolor(widget, mapping):
    """Swap old palette colours for new ones on a widget and its children."""
    if isinstance(widget, FlatButton):
        widget.configure(disabledforeground=DISABLED_FG)  # configure() repaints the rest
    elif not isinstance(widget, ttk.Widget):
        for option in COLOR_OPTIONS:
            try:
                new = _swap(widget.cget(option), mapping)
            except tk.TclError:
                continue
            if new:
                widget.configure(**{option: new})

    if isinstance(widget, Toggle):
        widget.redraw()
    elif isinstance(widget, tk.Canvas):
        for item in widget.find_all():
            for option in ("fill", "outline"):
                try:
                    new = _swap(widget.itemcget(item, option), mapping)
                except tk.TclError:
                    continue
                if new:
                    widget.itemconfigure(item, **{option: new})
    elif isinstance(widget, tk.Text):
        for tag in widget.tag_names():
            new = _swap(widget.tag_cget(tag, "foreground"), mapping)
            if new:
                widget.tag_configure(tag, foreground=new)
    elif isinstance(widget, ttk.Combobox):
        # The dropdown list only exists once it has been opened; recolour it too
        try:
            popdown = widget.tk.call("ttk::combobox::PopdownWindow", widget)
            widget.tk.call(f"{popdown}.f.l", "configure", "-background", BG_TERTIARY,
                           "-foreground", TEXT, "-selectbackground", BLURPLE,
                           "-selectforeground", ACCENT_FG)
        except tk.TclError:
            pass

    for child in widget.winfo_children():
        _recolor(child, mapping)


def set_palette(root, brand):
    """Switch the whole UI to another brand palette, in place.

    Returns True when the palette actually changed.
    """
    global BRAND
    brand = brand if brand in PALETTES else "default"
    if brand == BRAND:
        return False
    old, new = PALETTES[BRAND], PALETTES[brand]
    mapping = {old[role].upper(): new[role] for role in old}
    BRAND = brand
    globals().update(new)
    _build_variants()
    apply_theme(root)
    _recolor(root, mapping)
    apply_dark_title_bar(root)
    return True


def brand_name():
    """Display name of the current palette's brand."""
    return BRANDS[BRAND]["name"]


# ------------------------------------------------------------------- helpers

def ellipsize(text, limit):
    """Shorten text to the given length with a trailing ellipsis."""
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle on a canvas."""
    points = [x1 + radius, y1, x2 - radius, y1, x2, y1, x2, y1 + radius,
              x2, y2 - radius, x2, y2, x2 - radius, y2, x1 + radius, y2,
              x1, y2, x1, y2 - radius, x1, y1 + radius, x1, y1]
    return canvas.create_polygon(points, smooth=True, outline="", **kwargs)


def section_label(parent, text, bg=None):
    """Uppercase section heading in the border colour, like the site's subtitles."""
    return tk.Label(parent, text=text.upper(), bg=bg or BG, fg=TITLE_FG,
                    font=FONT_HEADING, anchor="w")


def hint_label(parent, text, bg=None, wraplength=440):
    """Muted helper text shown under a field."""
    return tk.Label(parent, text=text, bg=bg or BG, fg=TEXT_MUTED, font=FONT_SMALL,
                    anchor="w", justify="left", wraplength=wraplength)


def divider(parent):
    """Thin horizontal separator line."""
    return tk.Frame(parent, bg=DIVIDER, height=2)


def make_entry(parent, textvariable=None):
    """Create an inset input box. Returns (container, entry); grid the container."""
    box = tk.Frame(parent, bg=BG_TERTIARY, highlightthickness=2,
                   highlightbackground=BG_HOVER)
    entry = tk.Entry(box, textvariable=textvariable, bg=BG_TERTIARY, fg=TEXT,
                     insertbackground=TEXT, disabledbackground=BG_SECONDARY,
                     disabledforeground=TEXT_MUTED, selectbackground=BLURPLE,
                     selectforeground=ACCENT_FG, relief="flat", bd=0,
                     highlightthickness=0, font=FONT_BODY)
    entry.pack(fill="x", padx=10, pady=6)
    # Colours are looked up at event time so they follow the live palette
    entry.bind("<FocusIn>", lambda e: box.config(highlightbackground=BORDER), add="+")
    entry.bind("<FocusOut>", lambda e: box.config(highlightbackground=BG_HOVER), add="+")
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


class Window(tk.Frame):
    """A website-style window: neon border, title bar with _ □ ×, bordered content.

    Put children in `.content`. The title bar lights up while the pointer is
    over the window, like `.window:hover` on the site.
    """

    instances = []

    def __init__(self, master, title=""):
        super().__init__(master, bg=BORDER, padx=2, pady=2)
        self.body = tk.Frame(self, bg=BG_SECONDARY, padx=4, pady=4)
        self.body.pack(fill="both", expand=True)

        title_border = tk.Frame(self.body, bg=BORDER, padx=2, pady=2)
        title_border.pack(fill="x")
        self.title_bar = tk.Frame(title_border, bg=TITLE_BG)
        self.title_bar.pack(fill="x")
        self.title_icon = tk.Label(self.title_bar, text="◆", bg=TITLE_BG, fg=TITLE_FG,
                                   font=(SYMBOL, 9), padx=4)
        self.title_icon.pack(side="left")
        self.title_label = tk.Label(self.title_bar, text=title, bg=TITLE_BG, fg=TITLE_FG,
                                    font=FONT_HEADING, pady=5, anchor="w")
        self.title_label.pack(side="left", fill="x", expand=True)
        for glyph in ("×", "□", "_"):
            tk.Label(self.title_bar, text=glyph, bg=BG_HOVER, fg=TEXT_STRONG, font=FONT_HEADING,
                     relief="raised", bd=2, width=2).pack(side="right", padx=(0, 3), pady=2)

        content_border = tk.Frame(self.body, bg=BORDER, padx=2, pady=2)
        content_border.pack(fill="both", expand=True, pady=(4, 0))
        self.content = tk.Frame(content_border, bg=BG)
        self.content.pack(fill="both", expand=True)

        self.active = False
        if not Window.instances:
            root = self.winfo_toplevel()
            root.bind_all("<Motion>", Window._track_pointer, add="+")
            root.bind("<Leave>", lambda e: Window._track_pointer(None), add="+")
        Window.instances.append(self)
        self.bind("<Destroy>", self._forget, add="+")

    def set_title(self, title):
        self.title_label.config(text=title)

    def _forget(self, event):
        if event.widget is self and self in Window.instances:
            Window.instances.remove(self)

    def _set_active(self, active):
        if active == self.active:
            return
        self.active = active
        bar_bg = TITLE_ACTIVE if active else TITLE_BG
        bar_fg = TITLE_ACTIVE_FG if active else TITLE_FG
        self.body.config(bg=BG_HOVER if active else BG_SECONDARY)
        self.title_bar.config(bg=bar_bg)
        for label in (self.title_icon, self.title_label):
            label.config(bg=bar_bg, fg=bar_fg)

    @staticmethod
    def _track_pointer(event):
        for window in list(Window.instances):
            try:
                inside = False
                if event is not None and window.winfo_ismapped():
                    x = event.x_root - window.winfo_rootx()
                    y = event.y_root - window.winfo_rooty()
                    inside = 0 <= x < window.winfo_width() and 0 <= y < window.winfo_height()
                window._set_active(inside)
            except tk.TclError:
                pass


class FlatButton(tk.Label):
    """Retro bevelled button with hover and pressed states. Supports state=tk.DISABLED."""

    def __init__(self, master, text="", command=None, variant="primary",
                 padx=16, pady=8, font=FONT_BUTTON, **kwargs):
        self._command = command
        self._variant = variant
        self._hover = False
        self._pressed = False
        super().__init__(master, text=text, padx=padx, pady=pady, font=font, bd=2,
                         disabledforeground=DISABLED_FG, **kwargs)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<ButtonPress-1>", self._on_press)
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
        bg, hover, fg, relief = BUTTON_VARIANTS[self._variant]
        if self._enabled():
            if self._pressed and relief == "raised":
                relief = "sunken"
            super().configure(bg=hover if self._hover else bg, fg=fg, relief=relief, cursor="hand2")
        else:
            super().configure(bg=DISABLED_BG, relief="flat" if relief == "flat" else "groove",
                              cursor="arrow")

    def _on_enter(self, event):
        self._hover = True
        self._refresh()

    def _on_leave(self, event):
        self._hover = False
        self._pressed = False
        self._refresh()

    def _on_press(self, event):
        self._pressed = True
        self._refresh()

    def _on_click(self, event):
        self._pressed = False
        self._refresh()
        inside = 0 <= event.x < self.winfo_width() and 0 <= event.y < self.winfo_height()
        if inside and self._enabled() and self._command:
            self._command()


class Toggle(tk.Canvas):
    """Boxy pixel-style switch bound to a BooleanVar."""

    WIDTH, HEIGHT = 44, 22

    def __init__(self, master, variable, bg=None):
        super().__init__(master, width=self.WIDTH, height=self.HEIGHT, bg=bg or BG,
                         highlightthickness=0, cursor="hand2")
        self.variable = variable
        self.bind("<Button-1>", lambda e: self.variable.set(not self.variable.get()))
        self.variable.trace_add("write", lambda *_: self._draw())
        self._draw()

    def redraw(self):
        self._draw()

    def _draw(self):
        self.delete("all")
        on = self.variable.get()
        w, h = self.WIDTH, self.HEIGHT
        self.create_rectangle(1, 1, w - 1, h - 1, fill=GREEN if on else OFFLINE,
                              outline=BORDER, width=2)
        x = w - h + 3 if on else 4
        self.create_rectangle(x, 4, x + h - 8, h - 4, fill=WHITE, outline="")
        self.create_text(x + (h - 8) / 2, h / 2, text="✓" if on else "✕",
                         fill=GREEN if on else OFFLINE, font=(SYMBOL, 8, "bold"))


class ScrollFrame(tk.Frame):
    """Vertically scrollable container; put children in `.inner`."""

    def __init__(self, master, bg=None):
        bg = bg or BG
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
