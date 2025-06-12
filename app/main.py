from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import pandas as pd
from .dxf_utils import process_dxf_for_loops, visualize_loops

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload/")
async def upload_dxf(file: UploadFile = File(...)):
    contents = await file.read()
    os.makedirs("uploads", exist_ok=True)
    path = f"uploads/{file.filename}"
    with open(path, "wb") as f:
        f.write(contents)

    parts = process_dxf_for_loops(path)
    df = pd.DataFrame(parts)
    base = os.path.splitext(os.path.basename(path))[0]

    csv_path = f"static/{base}.csv"
    img_path = f"static/{base}.png"

    df.to_csv(csv_path, index=False)
    visualize_loops([p["Points"] for p in parts], save_path=img_path)

    return {
        "CSV Download": f"/{csv_path}",
        "Preview Image": f"/{img_path}"
    }
