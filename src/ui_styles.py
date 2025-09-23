# ui_styles.py
from tkinter import ttk

# Layout constants
BUTTON_WIDTH   = 18
BUTTON_PADX    = 6
BUTTON_PADY    = 12
BUTTON_IPADY   = 8
OUTER_PADX     = 100
BAR_PADY       = (30, 5)
NAV_PADY       = (10, 20)

# Style names
STYLE_NOTHING  = "Nothing.TButton"
STYLE_CHAOS    = "Chaos.TButton"
STYLE_UNSURE   = "Unsure.TButton"
STYLE_ANNOTATE = "Annotate.TButton"
STYLE_DELETE   = "Delete.TButton"
STYLE_RESET    = "Reset.TButton"
STYLE_SKIP     = "Skip.TButton"

STYLE_SESSION  = "Session.TLabel"
STYLE_STATUS   = "Status.TLabel"

STYLE_NAV = "Nav.TButton"

def init_ttk_styles(root):
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except Exception:
        pass

    # Base style for buttons
    base = dict(
        relief="flat",
        borderwidth=0,
        padding=(14, 10),
        anchor="center",
        font=("Arial", 18)
    )

    # Button colors
    s.configure(STYLE_NOTHING,  background="#3498DB", foreground="white", **base)
    s.configure(STYLE_CHAOS,    background="#E29D60", foreground="white", **base)
    s.configure(STYLE_UNSURE,   background="#B497B8", foreground="white", **base)
    s.configure(STYLE_ANNOTATE, background="#2ECC71", foreground="white", **base)
    s.configure(STYLE_DELETE,   background="#FF7580", foreground="white", **base)
    s.configure(STYLE_RESET,    background="#FF3B3B", foreground="white", **base)
    s.configure(STYLE_SKIP,     background="#c50000", foreground="white", **base)

    # Hover/active pastel tones
    for style, color in [
        (STYLE_NOTHING, "#5dade2"),
        (STYLE_CHAOS,   "#edbb99"),
        (STYLE_UNSURE,  "#d2b4de"),
        (STYLE_ANNOTATE,"#58d68d"),
        (STYLE_DELETE,  "#f1948a"),
        (STYLE_RESET,   "#f08080"),
        (STYLE_SKIP,    "#e57373"),
    ]:
        s.map(style,
              background=[("active", color)],
              relief=[("pressed", "flat")])

    # Labels
    s.configure(STYLE_SESSION, font=("Arial", 20))
    s.configure(STYLE_STATUS,  font=("Arial", 12))


    s.configure(
        STYLE_NAV,
        background="#e0e0e0",
        foreground="black",
        relief="flat",
        borderwidth=0,
        padding=(20, 10),
        font=("Arial", 14)
    )

    s.map(STYLE_NAV,
          background=[("active", "#bdbdbd")],
          relief=[("pressed", "flat")])