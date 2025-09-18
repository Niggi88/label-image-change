# ui_annotation_displayer.py
from PIL import Image, ImageTk

class AnnotationDisplayer:
    def __init__(self):
        self._images = []  # keep refs to Tk images

    def display_pair(self, canvas_left, canvas_right, pair, annotations, max_w=1200, max_h=800):
        """
        Show images + annotations for a given ImagePair.
        Scales images to half the width and full height of available space.
        """
        pid = str(pair.pair_id)
        data = annotations.get(pid, {})

        # clear old drawings
        for canvas in (canvas_left, canvas_right):
            canvas.delete("all")

        half_w = max_w // 2

        # show scaled images
        self._draw_image(canvas_left, pair.image1, half_w, max_h)
        self._draw_image(canvas_right, pair.image2, half_w, max_h)

        # check saved annotation state
        state = data.get("pair_state")
        if state in ("chaos", "nothing", "unsure"):
            self._draw_outline(canvas_left, state)
            self._draw_outline(canvas_right, state)
        elif state == "annotated":
            for canvas in (canvas_left, canvas_right):
                boxes = data.get("boxes", [])
                for b in boxes:
                    if b["annotation_type"] == "item_removed":
                        self._draw_boxes(canvas_left, [b], highlight=True)
                        self._draw_boxes(canvas_right, [b], highlight=False)
                    elif b["annotation_type"] == "item_added":
                        self._draw_boxes(canvas_left, [b], highlight=False)                        
                        self._draw_boxes(canvas_right, [b], highlight=True)



    def _scale_image(self, pil_img, max_w, max_h):
        w, h = pil_img.size
        scale = min(max_w / w, max_h / h)
        return pil_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    def _draw_image(self, canvas, annot_img, max_w, max_h):
        from PIL import Image, ImageTk
        pil_img = Image.open(annot_img.img_path)
        w, h = pil_img.size
        canvas.img_size = (w, h)  # store true image size

        pil_img = self._scale_image(pil_img, max_w, max_h)
        tk_img = ImageTk.PhotoImage(pil_img)
        self._images.append(tk_img)

        w, h = pil_img.size
        canvas.config(width=w, height=h)
        canvas.create_image(0, 0, image=tk_img, anchor="nw")


    def _draw_outline(self, canvas, state):
        color = {"chaos": "yellow", "nothing": "blue", "unsure": "purple"}[state]
        w, h = canvas.winfo_width(), canvas.winfo_height()
        canvas.create_rectangle(0, 0, w, h, outline=color, width=5, tags="outline")

    def _draw_boxes(self, canvas, boxes, highlight=None):
        if not hasattr(canvas, "img_size"):
            return  # image not loaded/scaled yet

        img_w, img_h = canvas.img_size
        scale_x = canvas.winfo_width() / img_w
        scale_y = canvas.winfo_height() / img_h

        for i, b in enumerate(boxes):
            if highlight:
                outline = "green"
            elif not highlight:
                outline = "red"
            elif highlight is None:
                outline = "blue"

            canvas.create_rectangle(
                int(b["x1"] * scale_x),
                int(b["y1"] * scale_y),
                int(b["x2"] * scale_x),
                int(b["y2"] * scale_y),
                outline=outline, width=2, tags="box"
            )