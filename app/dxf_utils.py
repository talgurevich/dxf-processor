import ezdxf
import math
import matplotlib.pyplot as plt

CLOSE_TOLERANCE = 1e-2  # mm
ARC_SEGMENTS = 10       # Segments to approximate arcs

def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def almost_equal(p1, p2, tol=CLOSE_TOLERANCE):
    return distance(p1, p2) <= tol

def arc_to_segments(arc, segments=ARC_SEGMENTS):
    center = arc.dxf.center
    radius = arc.dxf.radius
    start_angle = math.radians(arc.dxf.start_angle)
    end_angle = math.radians(arc.dxf.end_angle)
    if end_angle < start_angle:
        end_angle += 2 * math.pi
    step = (end_angle - start_angle) / segments
    return [
        (
            round(center[0] + radius * math.cos(start_angle + i * step), 4),
            round(center[1] + radius * math.sin(start_angle + i * step), 4)
        )
        for i in range(segments + 1)
    ]

def extract_lines_and_arcs(doc):
    msp = doc.modelspace()
    lines = []

    for entity in msp.query("LINE"):
        start = (round(entity.dxf.start[0], 4), round(entity.dxf.start[1], 4))
        end = (round(entity.dxf.end[0], 4), round(entity.dxf.end[1], 4))
        lines.append((start, end))

    for arc in msp.query("ARC"):
        points = arc_to_segments(arc)
        for i in range(len(points) - 1):
            lines.append((points[i], points[i + 1]))

    return lines

def find_loops(lines):
    used = set()
    loops = []

    for idx, (start, end) in enumerate(lines):
        if idx in used:
            continue

        loop = [start, end]
        used.add(idx)
        changed = True

        while changed:
            changed = False
            for j, (s, e) in enumerate(lines):
                if j in used:
                    continue
                if almost_equal(loop[-1], s):
                    loop.append(e)
                    used.add(j)
                    changed = True
                    break
                elif almost_equal(loop[-1], e):
                    loop.append(s)
                    used.add(j)
                    changed = True
                    break

        if almost_equal(loop[0], loop[-1]) and len(loop) > 3:
            loops.append(loop)

    return loops

def calculate_perimeter(points):
    return sum(distance(points[i], points[i+1]) for i in range(len(points) - 1))

def calculate_area(points):
    x = [p[0] for p in points]
    y = [p[1] for p in points]
    return 0.5 * abs(sum(x[i]*y[i+1] - x[i+1]*y[i] for i in range(len(points) - 1)))

def process_dxf_for_loops(path):
    doc = ezdxf.readfile(path)
    lines = extract_lines_and_arcs(doc)
    loops = find_loops(lines)
    parts = []

    for loop in loops:
        perimeter = round(calculate_perimeter(loop), 2)
        area = round(calculate_area(loop), 2)
        parts.append({
            "Num Points": len(loop),
            "Perimeter (mm)": perimeter,
            "Area (mm²)": area,
            "Points": loop
        })

    return parts

def visualize_loops(loops, save_path="static/output.png"):
    plt.figure(figsize=(10, 8))
    for loop in loops:
        x, y = zip(*loop)
        plt.plot(x, y, marker='o')
    plt.axis("equal")
    plt.grid(True)
    plt.savefig(save_path)
    plt.close()
