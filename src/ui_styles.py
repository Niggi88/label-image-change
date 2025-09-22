# ui_styles.py
from tkinter import ttk

# Globale Layout-Konstanten
BUTTON_WIDTH   = 18
BUTTON_PADX    = 5
BUTTON_PADY    = 10
BUTTON_IPADY   = 6
OUTER_PADX     = 100   # linker/rechter Rand für AnnotationFrame
BAR_PADY       = (30, 5)   # Abstand Button-Bar nach unten
NAV_PADY       = (10, 20)  # Abstand Navigation-Bar

# Style-Namen (optional für Farben)
STYLE_NOTHING  = "Nothing.TButton"
STYLE_CHAOS    = "Chaos.TButton"
STYLE_UNSURE   = "Unsure.TButton"
STYLE_ANNOTATE = "Annotate.TButton"
STYLE_DELETE   = "Delete.TButton"
STYLE_RESET    = "Reset.TButton"

STYLE_SESSION = "Session.TLabel"
STYLE_STATUS  = "Status.TLabel"


def init_ttk_styles(root):
    """Initialisiere Theme + Styles"""
    s = ttk.Style(root)
    try:
        s.theme_use("clam")
    except Exception:
        pass

    base = dict(relief="flat", borderwidth=1, padding=(10, 8), anchor="center")

    # Beispiel: kannst du erweitern wie im alten Styles-File
    s.configure(STYLE_NOTHING,  background="#3498DB", foreground="white", **base)
    s.configure(STYLE_CHAOS,    background="#E29D60", foreground="white", **base)
    s.configure(STYLE_UNSURE,   background="#B497B8", foreground="white", **base)
    s.configure(STYLE_ANNOTATE, background="#2ECC71", foreground="white", **base)
    s.configure(STYLE_DELETE,   background="#FF7580", foreground="white", **base)
    s.configure(STYLE_RESET,    background="#FF3B3B", foreground="white", **base)

    # Labels
    s.configure(STYLE_SESSION, font=("TkDefaultFont", 14, "bold"))
    s.configure(STYLE_STATUS,  font=("TkDefaultFont", 12))