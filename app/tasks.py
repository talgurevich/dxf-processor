import os
import pandas as pd
import time
import shutil
from celery import Celery
from .dxf_utils import process_dxf_for_loops, visualize_loops
from .utils import update_metrics, convert_to_svg  # ✅ new

UPLOAD_DIR = "uploads"
STATIC_DIR = "static"

celery_app = Celery(
    "tasks",
    broker=os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
)

@celery_app.task
def process_dxf_task(file_path, filename):
    base = os.path.splitext(os.path.basename(filename))[0]
    csv_path = os.path.join(STATIC_DIR, f"{base}.csv")
    img_path = os.path.join(STATIC_DIR, f"{base}.png")
    svg_path = os.path.join(STATIC_DIR, f"{base}.svg")

    start_time = time.time()

    parts = process_dxf_for_loops(file_path)
    df = pd.DataFrame(parts)
    df.to_csv(csv_path, index=False)
    visualize_loops([p["Points"] for p in parts], save_path=img_path)
    convert_to_svg(file_path, svg_path)

    process_time = round(time.time() - start_time, 2)
    area_sum = df["Area (mm²)"].sum()
    perimeter_sum = df["Perimeter (mm)"].sum()
    update_metrics(process_time, area_sum, perimeter_sum)

    return {
        "csv_url": f"/{csv_path}",
        "image_url": f"/{img_path}",
        "svg_url": f"/{svg_path}",
        "csv_html": df.to_html(classes="table", index=False, border=1)
    }
