# ui_styles.py
from tkinter import ttk

STYLE_NOTHING   = "Nothing.TButton"
STYLE_CHAOS     = "Chaos.TButton"
STYLE_ANNOTATE  = "Annotate.TButton"
STYLE_DELETE    = "Delete.TButton"
STYLE_CLEAR     = "Clear.TButton"
STYLE_UNSURE    = "Unsure.TButton"
STYLE_DANGER    = "Danger.TButton"  # z.B. Skip Session

def init_ttk_styles(root):
    s = ttk.Style(root)
    try:
        s.theme_use("clam")  # zeigt Farben zuverlässig
    except Exception:
        pass

    base = dict(relief="flat", borderwidth=1, padding=(8, 6), anchor="center")

    s.configure(STYLE_UNSURE,  background="#B497B8", foreground="white", **base)
    s.map(      STYLE_UNSURE,  background=[("active","#A07AA7"),("pressed","#8E5E99")])

    s.configure(STYLE_CHAOS,    background="#E29D60", foreground="white", **base)
    s.map(      STYLE_CHAOS,    background=[("active","#CF6E1D"),("pressed","#B65F19")])

    s.configure(STYLE_ANNOTATE, background="#2ECC71", foreground="white", **base)
    s.map(      STYLE_ANNOTATE, background=[("active","#28B862"),("pressed","#239E54")])

    s.configure(STYLE_DELETE,   background="#FF7580", foreground="white", **base)
    s.map(      STYLE_DELETE,   background=[("active","#FF6471"),("pressed","#FF505E")])

    s.configure(STYLE_CLEAR,    background="#FF3B3B", foreground="white", **base)
    s.map(      STYLE_CLEAR,    background=[("active","#E85A5A"),("pressed","#D94F4F")])

    s.configure(STYLE_NOTHING,   background="#3498DB", foreground="white", **base)
    s.map(      STYLE_NOTHING,   background=[("active","#2E86C1"),("pressed","#2874A6")])

    s.configure(STYLE_DANGER,   background="#C01010", foreground="white", **base)
    s.map(      STYLE_DANGER,   background=[("active","#E85A5A"),("pressed","#D94F4F")])
