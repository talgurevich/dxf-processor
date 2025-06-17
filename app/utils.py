import os
import json
import matplotlib.pyplot as plt
from ezdxf import readfile
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend

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
