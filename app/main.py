from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import pandas as pd
import json
import time
import glob
from .dxf_utils import process_dxf_for_loops, visualize_loops

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

FILE_TTL_SECONDS = 30 * 60  # 30 minutes

def update_metrics(process_time, area_sum, perimeter_sum):
    os.makedirs("app/data", exist_ok=True)
    path = "app/data/metrics.json"
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({
                "uploads": 0,
                "total_time": 0.0,
                "total_area": 0.0,
                "total_perimeter": 0.0
            }, f)

    with open(path, "r") as f:
        metrics = json.load(f)

    metrics["uploads"] += 1
    metrics["total_time"] += process_time
    metrics["total_area"] += area_sum
    metrics["total_perimeter"] += perimeter_sum

    with open(path, "w") as f:
        json.dump(metrics, f)

def convert_to_svg(dxf_path, svg_output):
    from ezdxf import readfile
    from ezdxf.addons.drawing import RenderContext, Frontend
    from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
    import matplotlib.pyplot as plt

    doc = readfile(dxf_path)
    msp = doc.modelspace()
    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp)
    ax.set_aspect('equal')
    ax.axis("off")
    fig.savefig(svg_output, format="svg", bbox_inches="tight")
    plt.close(fig)

@app.get("/", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload/")
async def upload_dxf(request: Request, file: UploadFile = File(...)):
    contents = await file.read()

    os.makedirs("uploads", exist_ok=True)
    path = f"uploads/{file.filename}"
    with open(path, "wb") as f:
        f.write(contents)

    base = os.path.splitext(os.path.basename(path))[0]
    csv_path = f"static/{base}.csv"
    img_path = f"static/{base}.png"
    svg_path = f"static/{base}.svg"

    start_time = time.time()

    parts = process_dxf_for_loops(path)
    df = pd.DataFrame(parts)
    df.to_csv(csv_path, index=False)
    visualize_loops([p["Points"] for p in parts], save_path=img_path)
    convert_to_svg(path, svg_path)

    process_time = round(time.time() - start_time, 2)
    area_sum = df["Area (mm²)"].sum()
    perimeter_sum = df["Perimeter (mm)"].sum()
    update_metrics(process_time, area_sum, perimeter_sum)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "csv_url": f"/{csv_path}",
        "image_url": f"/{img_path}",
        "svg_url": f"/{svg_path}",
        "csv_table": df.to_html(classes="table", index=False, border=1)
    })

@app.get("/metrics")
def get_metrics():
    path = "app/data/metrics.json"
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {"uploads": 0}

@app.get("/cleanup")
def cleanup_files():
    now = time.time()
    deleted = []

    for folder in ["uploads", "static"]:
        for path in glob.glob(f"{folder}/*"):
            if os.path.isfile(path) and now - os.path.getmtime(path) > FILE_TTL_SECONDS:
                os.remove(path)
                deleted.append(path)

    return {"deleted": deleted}
