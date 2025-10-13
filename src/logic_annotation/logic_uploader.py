from abc import ABC, abstractmethod
from pathlib import Path
from PIL import Image
from tkinter import messagebox
from src.config import LOCAL_LOG_DIR, USERNAME
import requests
import json
from urllib.parse import urljoin
from io import BytesIO


class BaseUploader:
    @abstractmethod
    def upload_results():
        pass
    
    @abstractmethod
    def ask_upload():
        pass


class SessionUploader(BaseUploader):
    def __init__(self, handler):
        self.handler = handler
        self.api_base = handler.api_base

    def upload_results(self, session_info=None):
        """
        Upload the annotations.json for the current session.
        """

        target_info = session_info or self.handler.current_session_info()
        ann_file = target_info.path / "annotations.json"

        if not ann_file.exists():
            raise RuntimeError("No annotations.json to upload")
        
        with open(ann_file, "r") as f:
            data = json.load(f)
        
        meta = data.get("_meta", {})
        if not meta.get("completed", False):
            raise RuntimeError(f"Session {target_info.session} not marked completed – refusing upload.")

        session_id = f"{target_info.store}_{target_info.session}"

        try:
            with open(ann_file, 'rb') as f:
                files = {'file': (f"{session_id}.json", f)}
                data = {
                    'username': USERNAME,
                    'session_id': session_id
                }
                path = f"results/annotations"
                url = urljoin(self.api_base + "/", path.lstrip("/"))
                response = requests.post(url, files=files, data=data)
                if response.status_code == 200:
                    print(f"✅ Uploaded {session_id}.json")
                else:
                    print(f"Failed to upload {session_id}.json — Status {response.status_code}")
                    print(response.text)
        except Exception as e:
            print(f"Error uploading {ann_file}: {e}")

        response.raise_for_status()
        return response.json()
    

    def upload_images(self, session_info=None):
        """
        Upload all images for the current session to the API.
        Uses the /upload_image endpoint on the server.
        """
        target_info = session_info or self.handler.current_session_info()

            
        for img_file in sorted(target_info.path.glob("*.jpeg")):
            relative_path = str(img_file.relative_to(self.handler.dataset_dir))
            try:
                with open(img_file, "rb") as f:
                    files = {"file": (img_file.name, f)}
                    data = {"relative_path": relative_path}
                    url = f"{self.api_base.rstrip('/')}/upload_image"
                    resp = requests.post(url, files=files, data=data, timeout=30)
                    resp.raise_for_status()
                    print(f"✅ Uploaded image {relative_path}")
            except Exception as e:
                print(f"❌ Failed to upload {img_file}: {e}")
            

    def ask_upload(self, session_info=None) -> bool:
        target_info = session_info or self.handler.current_session_info()

        confirm = messagebox.askyesno(
            "Session finished",
            f"Session {target_info.session} is complete.\n\n"
            "Do you want to upload your annotations now?"
        )
        if not confirm:
            return False

        try:
            self.upload_results(target_info)
            self.upload_images(target_info)
            messagebox.showinfo(
                "Upload complete", f"Session {target_info.session} uploaded successfully."
            )
            return True
        except Exception as e:
            messagebox.showerror("Upload failed", f"Something went wrong:\n{e}")
            return False


class BatchUploader(BaseUploader):
    def __init__(self, handler):
        self.handler = handler
        self.api_base = handler.api_base

    def upload_results(self, results: dict):
        """
        Ergebnisse für das Batch hochladen.
        results: Dict[str, Any], keys = "store_session_path|pair_id"
        """
        if not self.handler.batch_id:
            raise RuntimeError("Kein aktives Batch geladen")

        path = f"/batches/{self.handler.batch_id}/results"
        url = urljoin(self.api_base + "/", path.lstrip("/"))
        resp = requests.post(url, json=results, timeout=30)
        resp.raise_for_status()
        return resp.json()
    
    def ask_upload(self):
            confirm = messagebox.askyesno(
                "Batch finished",
                "You have reached the end of this batch.\n\nDo you want to upload your results now?"
            )
            if not confirm:
                return False

            try:
                results = self.handler.saver.annotations
                self.upload_results(results)
                messagebox.showinfo("Upload complete", "Batch has been uploaded and marked completed.")
                self.handler.load_current_pairs()  # fetch fresh batch
                return True
            except Exception as e:
                messagebox.showerror("Upload failed", f"Something went wrong:\n{e}")
                return False