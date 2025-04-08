from PIL import Image

try:
    resample_filter = Image.Resampling.LANCZOS
except AttributeError:
    resample_filter = Image.ANTIALIAS

def resize_with_aspect_ratio(pil_img, base_width=None, base_height=None):
    """
    Resize an image while maintaining its aspect ratio.

    Args:
        pil_img: A Pillow Image object.
        base_width: The desired width while maintaining aspect ratio (optional).
        base_height: The desired height while maintaining aspect ratio (optional).

    Returns:
        A resized Pillow Image object.
    """
    original_width, original_height = pil_img.size

    if base_width is not None:  # Resize by width
        w_ratio = base_width / float(original_width)
        new_width = base_width
        new_height = int((original_height * w_ratio))
    elif base_height is not None:  # Resize by height
        h_ratio = base_height / float(original_height)
        new_width = int((original_width * h_ratio))
        new_height = base_height
    else:
        raise ValueError("You must specify either base_width or base_height.")

    return pil_img.resize((new_width, new_height), resample_filter)