from pathlib import Path

class ImagePairList(list):
    def __init__(self, src):

        self.src = Path(src)

        self.images = sorted(self.src.glob("*.jpeg"), key=lambda file: int(file.name.split("-")[0]))
        assert len(self.images) > 0, f"no images found at {src}"
        self.image_pairs = list(zip(self.images[:-1], self.images[1:]))
        # self.model_name = None
    def __getitem__(self, index):
        # Allow indexing into image_pairs
        return self.image_pairs[index]
    
    def __iter__(self):
        return iter(self.image_pairs)
    
    def __len__(self):
        return len(self.image_pairs)
    
    def ids(self):
        return list(range(len(self)))


class FlatPairList:
    """
    Adapter für eine flache Liste aus unsicheren Paaren.
    Erwartet Items als Dict mit:
      - session_path: Path   (Session-Ordner mit annotations.json)
      - pair_id: int         (Original-Index in dieser Session)
      - im1_path: Path
      - im2_path: Path
    """
    def __init__(self, items):
        self._items = items

    def __getitem__(self, index):
        it = self._items[index]
        # bevorzugt URLs (remote), fallback auf lokale Pfade
        im1 = it.get("im1_url") or it.get("im1_path")
        im2 = it.get("im2_url") or it.get("im2_path")
        return (im1, im2)

    def __len__(self):
        return len(self._items)

    def ids(self):
        return list(range(len(self._items)))

    def meta_at(self, index):
        it = self._items[index]
        return {
            "store_session_path": it["store_session_path"],
            "pair_id": it["pair_id"],
            "im1": it.get("im1_url") or it.get("im1_path"),
            "im2": it.get("im2_url") or it.get("im2_path"),
            "predicted": it.get("predicted"),
            "expected": it.get("expected"),
            "unsure_by": it.get("unsure_by"),
            "annotated_by": it.get("annotated_by"),
            "model_name": it.get("model_name"),   
            "source": it.get("source"),
        }

    def _key_of(self, it):
        return f"{str(it['store_session_path'])}|{int(it['pair_id'])}"

    def keys(self):
        return { self._key_of(it) for it in self._items }

    def extend_unique(self, items):
        """Append only new items, skip existing keys. Return number added."""
        existing = self.keys()
        added = 0
        for it in items:
            k = self._key_of(it)
            if k in existing:
                continue
            self._items.append(it)
            existing.add(k)
            added += 1
        return added