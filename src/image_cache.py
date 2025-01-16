from collections import OrderedDict
import threading
from PIL import Image, ImageTk
from utils import resize_with_aspect_ratio


class ImageCache:
    def __init__(self, cache_size=5):
        self.cache_size = cache_size
        self.cache = OrderedDict()
        self.lock = threading.Lock()

    def get(self, image_path):
        """Get image from cache or load it if not present"""
        str_path = str(image_path)
        with self.lock:
            if str_path in self.cache:
                # Move to end to mark as recently used
                self.cache.move_to_end(str_path)
                return self.cache[str_path]
            return None

    def add(self, image_path, image):
        """Add image to cache, removing oldest if necessary"""
        str_path = str(image_path)
        with self.lock:
            self.cache[str_path] = image
            self.cache.move_to_end(str_path)
            
            # Remove oldest items if cache is too big
            while len(self.cache) > self.cache_size:
                self.cache.popitem(last=False)

    def preload_images(self, image_paths, callback=None):
        """Preload images in a background thread"""
        def load_images():
            for path in image_paths:
                if self.get(path) is None:  # Only load if not in cache
                    try:
                        pil_img = Image.open(path)
                        pil_img = resize_with_aspect_ratio(pil_img, 1000, 1000)
                        tk_image = ImageTk.PhotoImage(pil_img)
                        self.add(path, tk_image)
                    except Exception as e:
                        print(f"Error preloading image {path}: {e}")
            if callback:
                callback()

        thread = threading.Thread(target=load_images)
        thread.daemon = True
        thread.start()