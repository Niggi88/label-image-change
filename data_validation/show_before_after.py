import requests
from PIL import Image
import matplotlib.pyplot as plt
from io import BytesIO



BASE_URL = "http://172.30.20.31:8081"
API_URL = "http://172.30.20.31:8081/review/changed/random"
LIMIT = 10

COLOR_PREV = "blue"
COLOR_REVIEWED = "green"


def load_image(url):
    url = BASE_URL + url
    resp = requests.get(url)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content))

def draw_boxes(ax, boxes, color):
    for b in boxes:
        x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]
        rect = plt.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 -y1,
            fill=False,
            edgecolor=color,
            linewidth=2,
        )
        ax.add_patch(rect)

def show_pair(pair):
    im1 = load_image(pair["im1_url"])
    im2 = load_image(pair["im2_url"])

    fig, axes = plt.subplots(1,2,figsize=(12,6))
    fig.suptitle(pair["key"], fontsize=12)

    axes[0].imshow(im1)
    axes[0].axis("off")
    
    draw_boxes(axes[0], pair["previously"]["boxes"], COLOR_PREV)
    draw_boxes(axes[1], pair["reviewed"]["boxes"], COLOR_REVIEWED)

    axes[1].imshow(im2)
    axes[1].axis("off")

    prev_state = pair["previously"]["pair_state"]
    rev_state = pair["reviewed"]["pair_state"]

    plt.figtext(
        0.5, 0.02,
        f"previously: {prev_state} | reviewed {rev_state}"
    )

    plt.show()


def main():
    resp = requests.get(API_URL, params={"limit": LIMIT})
    resp.raise_for_status()

    data = resp.json()
    items = data.get("items", [])

    for pair in items:
        show_pair(pair)


if __name__ == "__main__":
    main()