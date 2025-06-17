from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from .utils import parse_dxf_file, convert_to_svg, update_metrics

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload", response_class=HTMLResponse)
async def upload_dxf(request: Request, file: UploadFile = File(...)):
    contents = await file.read()

    os.makedirs("uploads", exist_ok=True)
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(contents)

    shapes = parse_dxf_file(file_path)
    svg_path, bounds = convert_to_svg(shapes, file.filename)
    update_metrics(shapes, bounds)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "shapes": shapes,
        "svg_path": svg_path,
        "bounds": bounds
    })
