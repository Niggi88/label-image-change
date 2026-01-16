import requests
from PIL import Image
import matplotlib.pyplot as plt
from io import BytesIO



BASE_URL = "http://172.30.20.31:8081"
API_URL = "http://172.30.20.31:8081/review/changed/yesterday" # random

API_URL_RANDOM = "http://172.30.20.31:8081/review/changed/random"
LIMIT = 10

COLOR_PREV = "gray"
COLOR_REVIEWED = "red"


def load_image(url):
    url = BASE_URL + url
    resp = requests.get(url)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content))

def draw_boxes(ax, boxes, color):
    if color == COLOR_PREV:
        facecolor = "yellow"
        edgecolor = "yellow"
        fill = True
        alpha = 0.4
        linewidth = 0
        zorder = 1

    elif color == COLOR_REVIEWED:
        facecolor = "none"
        edgecolor = "red"
        fill = False
        alpha = 1.0
        linewidth = 2
        zorder = 2

    for b in boxes:
        x1, y1, x2, y2 = b["x1"], b["y1"], b["x2"], b["y2"]
        rect = plt.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            facecolor=facecolor,
            edgecolor=edgecolor,
            fill=fill,
            alpha=alpha,
            linewidth=linewidth,
            zorder=zorder,
        )
        ax.add_patch(rect)


def show_pair(pair):
    im1 = load_image(pair["im1_url"])
    im2 = load_image(pair["im2_url"])

    fig, axes = plt.subplots(1,2,figsize=(12,6))
    fig.suptitle(f"{pair['key']} from {pair['reviewed']['batch_timestamp']}" , fontsize=12)

    axes[0].imshow(im1)
    axes[1].imshow(im2)
    axes[0].axis("off")
    
    
    draw_boxes(axes[0], pair["previously"]["boxes"], COLOR_PREV)
    draw_boxes(axes[1], pair["previously"]["boxes"], COLOR_PREV)
    draw_boxes(axes[0], pair["reviewed"]["boxes"], COLOR_REVIEWED)
    draw_boxes(axes[1], pair["reviewed"]["boxes"], COLOR_REVIEWED)
    axes[1].axis("off")

    prev_state = pair["previously"]["pair_state"]
    rev_state = pair["reviewed"]["pair_state"]

    plt.figtext(
        0.5, 0.02,
        f"previously: {prev_state} | reviewed {rev_state}"
    )

    plt.show()


def main():
    resp = requests.get(API_URL)
    resp.raise_for_status()

    data = resp.json()
    items = data.get("items", [])

    for pair in items:
        show_pair(pair)

def show_random(limit):
    resp = requests.get(API_URL_RANDOM, params={"limit": limit})
    resp.raise_for_status()

    data = resp.json()
    items = data.get("items", [])

    for pair in items:
        show_pair(pair)


def show_issues():
    resp = requests.get("http://172.30.20.31:8081/review/validate/known_issues")
    resp.raise_for_status()

    data = resp.json()
    items = data.get("examples", [])

    summary = data.get("summary", [])

    for key, value in summary.items():
        print(f"{key}: {value}")

    for pair in items:
        show_pair(pair)

if __name__ == "__main__":
    # main()
    # show_issues()
    show_random(LIMIT)