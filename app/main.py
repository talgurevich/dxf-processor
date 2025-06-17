from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import os
import pandas as pd
import json
import time
import glob
from .dxf_utils import process_dxf_for_loops, visualize_loops
from .tasks import process_dxf_task
from .utils import update_metrics, convert_to_svg  
from celery.result import AsyncResult
from urllib.parse import urlencode

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

FILE_TTL_SECONDS = 30 * 60  # 30 minutes

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

    task = process_dxf_task.delay(path)

    return templates.TemplateResponse("processing.html", {
        "request": request,
        "task_id": task.id
    })

@app.get("/status/{task_id}")
def check_status(task_id: str):
    task = AsyncResult(task_id)
    if task.state == "PENDING":
        return {"status": "PENDING"}
    elif task.state == "FAILURE":
        return {"status": "FAILURE"}
    elif task.state == "SUCCESS":
        return {
            "status": "SUCCESS",
            "result": task.result  # Expecting dict with 'csv_url', 'image_url', 'svg_url'
        }
    else:
        return {"status": task.state}

@app.get("/results", response_class=HTMLResponse)
def results(request: Request, csv_url: str, image_url: str, svg_url: str):
    csv_path = csv_url.lstrip("/")
    if not os.path.exists(csv_path):
        return HTMLResponse("<h2>❌ CSV file not found.</h2>")

    df = pd.read_csv(csv_path)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "csv_url": csv_url,
        "image_url": image_url,
        "svg_url": svg_url,
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
