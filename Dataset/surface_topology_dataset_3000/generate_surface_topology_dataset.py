"""Generate the GRIP surface-topology visual reasoning dataset.

The renderer is intentionally schematic: topology, not photorealism, is the signal.
Every sample is deterministic under random.seed(image_index).
"""

from __future__ import annotations

import argparse
import json
import math
import random
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw


BG = (253, 250, 244)
INK = (31, 43, 49)
MESH_INK = (57, 76, 84)
PALETTE = [
    (83, 145, 150),
    (91, 126, 160),
    (138, 110, 159),
    (176, 118, 93),
    (104, 148, 112),
    (183, 143, 73),
]
AA = 2
SURFACE_TYPES = (
    "sphere_handles",
    "polyhedral_mesh",
    "mobius_vs_cylinder",
    "klein_vs_torus",
)


def blend(color: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(c * (1 - amount) + 255 * amount) for c in color)


class Canvas:
    def __init__(self, size: int):
        self.size = size
        self.image = Image.new("RGB", (size * AA, size * AA), BG)
        self.draw = ImageDraw.Draw(self.image)

    @staticmethod
    def _p(point):
        return tuple(round(float(v) * AA) for v in point)

    def line(self, points, fill=INK, width=2, joint="curve"):
        self.draw.line([self._p(p) for p in points], fill=fill, width=max(1, round(width * AA)), joint=joint)

    def polygon(self, points, fill=None, outline=INK, width=2):
        pts = [self._p(p) for p in points]
        self.draw.polygon(pts, fill=fill)
        if outline:
            self.draw.line(pts + [pts[0]], fill=outline, width=max(1, round(width * AA)), joint="curve")

    def ellipse(self, box, fill=None, outline=INK, width=2):
        self.draw.ellipse(tuple(round(v * AA) for v in box), fill=fill, outline=outline, width=max(1, round(width * AA)))

    def arc(self, box, start, end, fill=INK, width=2):
        self.draw.arc(tuple(round(v * AA) for v in box), start=start, end=end, fill=fill, width=max(1, round(width * AA)))

    def save(self, path: Path):
        self.image.resize((self.size, self.size), Image.Resampling.LANCZOS).save(path, optimize=True)


def cubic(p0, p1, p2, p3, steps=40):
    points = []
    for i in range(steps + 1):
        t = i / steps
        s = 1 - t
        points.append((
            s**3 * p0[0] + 3 * s * s * t * p1[0] + 3 * s * t * t * p2[0] + t**3 * p3[0],
            s**3 * p0[1] + 3 * s * s * t * p1[1] + 3 * s * t * t * p2[1] + t**3 * p3[1],
        ))
    return points


def rotation_matrix(yaw_degrees: float, tilt_degrees: float):
    yaw = math.radians(yaw_degrees)
    tilt = math.radians(tilt_degrees)
    cy, sy = math.cos(yaw), math.sin(yaw)
    ct, st = math.cos(tilt), math.sin(tilt)
    return (
        (cy, 0.0, sy),
        (st * sy, ct, -st * cy),
        (-ct * sy, st, ct * cy),
    )


def rotate(point, matrix):
    return tuple(sum(matrix[r][c] * point[c] for c in range(3)) for r in range(3))


def fit_projection(points, size, margin=70):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    span = max(max(xs) - min(xs), max(ys) - min(ys), 1e-9)
    scale = (size - 2 * margin) / span
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    return [(size / 2 + (p[0] - cx) * scale, size / 2 - (p[1] - cy) * scale) for p in points]


def boundary_mesh(genus: int):
    """Cubical boundary of a block with `genus` separated through-tunnels."""
    width, height, depth = max(5, 3 * genus + 2), 6, 2
    # Each tunnel has a clearly visible 2x2 mouth and is separated from its
    # neighbours and the exterior by at least one voxel wall.
    holes = {
        (2 + 3 * j + dx, 2 + dy)
        for j in range(genus)
        for dx in (0, 1)
        for dy in (0, 1)
    }
    occupied = {
        (x, y, z)
        for x in range(width)
        for y in range(height)
        for z in range(depth)
        if (x, y) not in holes
    }
    directions = [
        ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
        ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
        ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1))),
        ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
        ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
        ((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
    ]
    vertex_index = {}
    vertices = []
    faces = []
    for x, y, z in sorted(occupied):
        for (dx, dy, dz), corners in directions:
            if (x + dx, y + dy, z + dz) in occupied:
                continue
            face = []
            for ox, oy, oz in corners:
                p = (x + ox, y + oy, z + oz)
                if p not in vertex_index:
                    vertex_index[p] = len(vertices)
                    vertices.append(p)
                face.append(vertex_index[p])
            faces.append(face)
    edges = sorted({tuple(sorted((a, b))) for face in faces for a, b in zip(face, face[1:] + face[:1])})
    expected = 2 - 2 * genus
    assert len(vertices) - len(edges) + len(faces) == expected
    return {"vertices": vertices, "edges": edges, "faces": faces}


MESHES = {g: boundary_mesh(g) for g in range(4)}


def render_sphere_handles(canvas: Canvas, genus: int, color, rng):
    fill = blend(color, 0.69)
    x0, y0, x1, y1 = 74, 142, canvas.size - 74, canvas.size - 142
    canvas.ellipse((x0, y0, x1, y1), fill=fill, outline=INK, width=3)
    canvas.arc((x0 + 18, y0 + 26, x1 - 18, y1 - 26), 190, 350, fill=MESH_INK, width=1.2)
    canvas.arc((x0 + 34, y0 + 8, x1 - 34, y1 - 8), 12, 168, fill=MESH_INK, width=1.2)
    if genus == 0:
        canvas.ellipse((canvas.size / 2 - 36, y0 + 8, canvas.size / 2 + 36, y1 - 8), outline=MESH_INK, width=1.2)
        canvas.line([(x0 + 15, canvas.size / 2), (x1 - 15, canvas.size / 2)], fill=MESH_INK, width=1.2)
        return
    usable = x1 - x0 - 74
    gap = usable / genus
    hole_w = min(88, gap * 0.67)
    hole_h = 91 if genus == 1 else 76
    for j in range(genus):
        cx = x0 + 37 + gap * (j + 0.5)
        cy = canvas.size / 2 + rng.uniform(-5, 5)
        outer = (cx - hole_w * .66, cy - hole_h * .65, cx + hole_w * .66, cy + hole_h * .65)
        inner = (cx - hole_w / 2, cy - hole_h / 2, cx + hole_w / 2, cy + hole_h / 2)
        canvas.ellipse(outer, fill=blend(color, .48), outline=MESH_INK, width=1.4)
        canvas.ellipse(inner, fill=BG, outline=INK, width=3)
        canvas.arc((inner[0] + 7, inner[1] + 7, inner[2] - 7, inner[3] - 7), 190, 350, fill=MESH_INK, width=1.1)


def project_mesh(mesh, yaw, tilt):
    matrix = rotation_matrix(yaw, tilt)
    center = tuple(sum(p[k] for p in mesh["vertices"]) / len(mesh["vertices"]) for k in range(3))
    return [rotate(tuple(p[k] - center[k] for k in range(3)), matrix) for p in mesh["vertices"]]


def render_polyhedral(canvas: Canvas, mesh, color, yaw, tilt):
    projected = project_mesh(mesh, yaw, tilt)
    points2 = fit_projection(projected, canvas.size, margin=58)
    face_order = sorted(range(len(mesh["faces"])), key=lambda i: sum(projected[v][2] for v in mesh["faces"][i]) / 4)
    face_normals = []
    for i in face_order:
        face = mesh["faces"][i]
        depth = sum(projected[v][2] for v in face) / 4
        amount = 0.76 if depth < 0 else 0.62
        canvas.polygon([points2[v] for v in face], fill=blend(color, amount), outline=None)
    for face in mesh["faces"]:
        p, q, r = (projected[v] for v in face[:3])
        u = tuple(q[k] - p[k] for k in range(3))
        v = tuple(r[k] - p[k] for k in range(3))
        face_normals.append((u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]))
    edge_faces = {tuple(edge): [] for edge in mesh["edges"]}
    for face_index, face in enumerate(mesh["faces"]):
        for a, b in zip(face, face[1:] + face[:1]):
            edge_faces[tuple(sorted((a, b)))].append(face_index)
    for edge, adjacent in edge_faces.items():
        normals = [face_normals[i] for i in adjacent]
        visible = any(normal[2] > 1e-7 for normal in normals)
        crease = len(normals) != 2 or any(
            abs(sum(normals[0][k] * normal[k] for k in range(3))) <
            math.sqrt(sum(x * x for x in normals[0])) * math.sqrt(sum(x * x for x in normal)) * 0.999
            for normal in normals[1:]
        )
        if visible and crease:
            a, b = edge
            canvas.line((points2[a], points2[b]), fill=INK, width=1.65)


def parametric_mesh(kind: str, nu=36, nv=9):
    vertices = []
    for i in range(nu):
        u = 2 * math.pi * i / nu
        for j in range(nv):
            if kind == "cylinder":
                v = -0.58 + 1.16 * j / (nv - 1)
                p = (1.55 * math.cos(u), 1.55 * math.sin(u), v)
            elif kind == "mobius":
                v = -0.48 + 0.96 * j / (nv - 1)
                p = ((1.45 + v * math.cos(u / 2)) * math.cos(u),
                     (1.45 + v * math.cos(u / 2)) * math.sin(u),
                     v * math.sin(u / 2))
            elif kind == "torus":
                v = 2 * math.pi * j / nv
                p = ((1.35 + .54 * math.cos(v)) * math.cos(u),
                     (1.35 + .54 * math.cos(v)) * math.sin(u),
                     .54 * math.sin(v))
            else:
                raise ValueError(kind)
            vertices.append(p)
    faces = []
    vwrap = kind == "torus"
    jmax = nv if vwrap else nv - 1
    for i in range(nu):
        ni = (i + 1) % nu
        for j in range(jmax):
            nj = (j + 1) % nv
            faces.append([i * nv + j, ni * nv + j, ni * nv + nj, i * nv + nj])
    return {"vertices": vertices, "faces": faces}


PARAMETRIC = {k: parametric_mesh(k) for k in ("cylinder", "mobius", "torus")}


def render_parametric(canvas: Canvas, kind: str, color, yaw, tilt):
    mesh = PARAMETRIC[kind]
    matrix = rotation_matrix(yaw, tilt)
    projected = [rotate(p, matrix) for p in mesh["vertices"]]
    points2 = fit_projection(projected, canvas.size, margin=66)
    order = sorted(range(len(mesh["faces"])), key=lambda i: sum(projected[v][2] for v in mesh["faces"][i]) / 4)
    for i in order:
        face = mesh["faces"][i]
        canvas.polygon([points2[v] for v in face], fill=blend(color, .73), outline=None)
    nu, nv = 36, 9
    for i in range(0, nu, 3):
        canvas.line([points2[i * nv + j] for j in range(nv)], fill=MESH_INK, width=1.05)
    for j in range(nv):
        pts = [points2[i * nv + j] for i in range(nu)]
        pts.append(pts[0])
        canvas.line(pts, fill=INK if j in (0, nv - 1) else MESH_INK, width=1.35 if j in (0, nv - 1) else .85)


def render_klein(canvas: Canvas, color, mirror=False):
    """Classic self-intersecting bottle schematic with explicit over/under break."""
    if mirror:
        flip = lambda p: (canvas.size - p[0], p[1])
    else:
        flip = lambda p: p
    fill = blend(color, .68)
    body = [
        (145, 355), (125, 310), (132, 255), (175, 220), (215, 218),
        (225, 172), (222, 105), (260, 78), (298, 106), (296, 165),
        (292, 205), (335, 225), (385, 270), (390, 330), (360, 380),
        (300, 407), (220, 405), (165, 385),
    ]
    canvas.polygon([flip(p) for p in body], fill=fill, outline=INK, width=3)
    # The neck bends down and passes through the body; erase a small crossing interval,
    # then redraw the foreground wall to make the immersion legible.
    neck_outer = cubic((260, 80), (365, 78), (410, 148), (337, 220), 42)
    neck_inner = cubic((296, 108), (350, 110), (359, 151), (293, 202), 36)
    canvas.line([flip(p) for p in neck_outer], fill=INK, width=3)
    canvas.line([flip(p) for p in neck_inner], fill=INK, width=3)
    canvas.line([flip(p) for p in cubic((337, 220), (285, 272), (244, 307), (252, 359), 40)], fill=INK, width=3)
    canvas.line([flip(p) for p in cubic((293, 202), (255, 242), (218, 282), (221, 350), 40)], fill=INK, width=3)
    # Mesh contour lines.
    arc_a, arc_b = flip((160, 275)), flip((365, 390))
    arc_box = (min(arc_a[0], arc_b[0]), min(arc_a[1], arc_b[1]), max(arc_a[0], arc_b[0]), max(arc_a[1], arc_b[1]))
    canvas.arc(arc_box, 5, 175, fill=MESH_INK, width=1.2)
    canvas.line([flip(p) for p in cubic((165, 360), (220, 330), (315, 330), (365, 360), 35)], fill=MESH_INK, width=1.2)
    # Crossing patch on top.
    canvas.line([flip(p) for p in cubic((245, 255), (260, 270), (276, 279), (298, 288), 14)], fill=BG, width=10)
    canvas.line([flip(p) for p in cubic((245, 255), (260, 270), (276, 279), (298, 288), 14)], fill=INK, width=2)


def topology_record(surface_type: str, occurrence: int):
    if surface_type in ("sphere_handles", "polyhedral_mesh"):
        genus = GENUS_SCHEDULE[occurrence]
        return {
            "surface_variant": f"genus_{genus}_closed_surface" if surface_type == "sphere_handles" else f"genus_{genus}_cubical_mesh",
            "genus": genus,
            "genus_kind": "orientable_handle_genus",
            "is_orientable": True,
            "boundary_count": 0,
            "euler_characteristic": 2 - 2 * genus,
        }
    if surface_type == "mobius_vs_cylinder":
        if occurrence % 2 == 0:
            return {"surface_variant": "cylindrical_band", "genus": 0, "genus_kind": "orientable_handle_genus", "is_orientable": True, "boundary_count": 2, "euler_characteristic": 0}
        return {"surface_variant": "mobius_strip", "genus": 1, "genus_kind": "nonorientable_crosscap_genus", "is_orientable": False, "boundary_count": 1, "euler_characteristic": 0}
    if occurrence % 2 == 0:
        return {"surface_variant": "torus", "genus": 1, "genus_kind": "orientable_handle_genus", "is_orientable": True, "boundary_count": 0, "euler_characteristic": 0}
    return {"surface_variant": "klein_bottle", "genus": 2, "genus_kind": "nonorientable_crosscap_genus", "is_orientable": False, "boundary_count": 0, "euler_characteristic": 0}


def make_genus_schedule():
    # Together with the classical-surface categories this yields near-uniform full-set
    # genus counts: g0=755, g1=820, g2=675, g3=750.
    values = [0] * 190 + [1] * 35 + [2] * 150 + [3] * 375
    random.Random(20260825).shuffle(values)
    return values


GENUS_SCHEDULE = make_genus_schedule()


def questions(iid: str, row: dict, rng: random.Random):
    qs = [
        {
            "question_id": f"{iid}_q1",
            "question_text": "How many holes or handles does this surface have? Answer with a number in curly brackets, e.g. {1}.",
            "question_type": "genus_count",
            "ground_truth": str(row["genus"]),
            "answer_format": "number_in_curly_brackets",
            "difficulty_level": 1,
        },
        {
            "question_id": f"{iid}_q2",
            "question_text": "Is this surface orientable (has a consistent 'inside' and 'outside') or non-orientable (a single-sided surface, like a Möbius strip)? Answer 'orientable' or 'non-orientable'.",
            "question_type": "orientability",
            "ground_truth": "orientable" if row["is_orientable"] else "non-orientable",
            "answer_format": "choice",
            "difficulty_level": 2,
        },
    ]
    if row["surface_type"] == "polyhedral_mesh" and rng.random() < 0.5:
        q3 = {
            "question_text": "How many vertices does this mesh have?",
            "question_type": "mesh_vertex_count",
            "ground_truth": str(row["vertex_count"]),
            "answer_format": "numeric",
        }
    else:
        q3 = {
            "question_text": "What is the Euler characteristic of this surface? Answer with a number in curly brackets (can be negative), e.g. {-2}.",
            "question_type": "euler_characteristic",
            "ground_truth": str(row["euler_characteristic"]),
            "answer_format": "number_in_curly_brackets",
        }
    q3.update(question_id=f"{iid}_q3", difficulty_level=3)
    qs.append(q3)

    orientation = "orientable" if row["is_orientable"] else "non-orientable"
    q4 = {
        "question_text": "Combine the depicted surface's genus/handle structure and orientability: report its Euler characteristic, followed by whether it is orientable or non-orientable. Answer as 'Euler characteristic; orientability'.",
        "question_type": "combined_euler_orientability",
        "ground_truth": f"{row['euler_characteristic']}; {orientation}",
        "answer_format": "integer; orientability",
    }
    q4.update(question_id=f"{iid}_q4", difficulty_level=4)
    qs.append(q4)
    qs.append({
        "question_id": f"{iid}_q5",
        "question_text": (
            "If a small open disk were removed from this surface, creating exactly one "
            "additional boundary component without changing its genus or orientability, "
            "what would its new Euler characteristic be? Answer with a number in curly "
            "brackets, e.g. {-1}."
        ),
        "question_type": "remove_disk_euler_characteristic",
        "ground_truth": str(row["euler_characteristic"] - 1),
        "answer_format": "number_in_curly_brackets",
        "difficulty_level": 5,
    })
    return qs


def generate_one(index: int, images_dir: Path):
    rng = random.Random(index)
    surface_type = SURFACE_TYPES[(index - 1) % 4]
    occurrence = (index - 1) // 4
    row = topology_record(surface_type, occurrence)
    size = rng.randint(500, 550)
    color = rng.choice(PALETTE)
    yaw = rng.uniform(-18, 18)
    tilt = rng.uniform(17, 31)
    iid = f"surface_topology_{index:04d}"
    canvas = Canvas(size)

    if surface_type == "sphere_handles":
        render_sphere_handles(canvas, row["genus"], color, rng)
    elif surface_type == "polyhedral_mesh":
        mesh = MESHES[row["genus"]]
        render_polyhedral(canvas, mesh, color, -34 + yaw, 24 + tilt / 3)
        row.update(
            vertex_count=len(mesh["vertices"]),
            edge_count=len(mesh["edges"]),
            face_count=len(mesh["faces"]),
            mesh_vertices=[list(p) for p in mesh["vertices"]],
            mesh_edges=[list(e) for e in mesh["edges"]],
            mesh_faces=[list(f) for f in mesh["faces"]],
        )
    elif row["surface_variant"] in ("mobius_strip", "cylindrical_band", "torus"):
        kind = {"mobius_strip": "mobius", "cylindrical_band": "cylinder", "torus": "torus"}[row["surface_variant"]]
        render_parametric(canvas, kind, color, yaw + 18, tilt + 8)
    else:
        render_klein(canvas, color, mirror=bool(index % 3 == 0))

    canvas.save(images_dir / f"{iid}.png")
    row.update(
        id=iid,
        image_path=f"images/{iid}.png",
        canvas_size=[size, size],
        surface_type=surface_type,
        viewing_angle={"yaw_degrees": round(yaw, 6), "tilt_degrees": round(tilt, 6)},
        render_color=list(color),
        seed=index,
        dataset_version="surface-topology-3.0.0",
    )
    complexity = row["genus"] / 3 + (0.15 if not row["is_orientable"] else 0) + (0.12 if surface_type == "polyhedral_mesh" else 0)
    row["difficulty_score"] = round(min(1.0, 0.24 + 0.55 * complexity), 4)
    row["questions"] = questions(iid, row, rng)
    return row


def generate_dataset(count: int, output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)
    images_dir = output_dir / "images"
    images_dir.mkdir(exist_ok=True)
    annotation_path = output_dir / "annotations.jsonl"
    distribution = Counter()
    with annotation_path.open("w", encoding="utf-8", newline="\n") as handle:
        for index in range(1, count + 1):
            row = generate_one(index, images_dir)
            distribution[(row["surface_type"], row["surface_variant"], row["genus"])] += 1
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
            if index % 250 == 0 or index == count:
                print(f"Generated {index}/{count}")
    print("Distribution:")
    for key, value in sorted(distribution.items()):
        print(f"  {key}: {value}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=3000)
    parser.add_argument("--output-dir", type=Path, default=Path("surface_topology_dataset_3000"))
    parser.add_argument("--sample", action="store_true", help="Generate five samples for mandatory visual review")
    args = parser.parse_args()
    generate_dataset(5 if args.sample else args.n, args.output_dir)


if __name__ == "__main__":
    main()
