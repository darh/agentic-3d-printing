# FreeCAD headless script invoked by export_to_bambu.sh.
# Extracts printable PartDesign::Body solids (honoring assembly App::Link counts),
# packs them as named objects into a single .3mf (or .stl), optionally runs
# Bambu Studio CLI plate arrangement, and launches Bambu Studio GUI.

import argparse
import glob
import json
import math
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

import FreeCAD as App
import Mesh
import MeshPart


BAMBU_APP = "/Applications/BambuStudio.app"
BAMBU_BIN = "/Applications/BambuStudio.app/Contents/MacOS/BambuStudio"
A1_MAX_MM = 256.0


def parse_args():
    # Read CLI arguments from BAMBU_EXPORT_ARGS so FreeCADCmd doesn't treat them as files to open.
    raw_env = os.environ.get("BAMBU_EXPORT_ARGS")
    if raw_env:
        argv = json.loads(raw_env)
    else:
        argv = sys.argv[1:]
        if "--" in argv:
            argv = argv[argv.index("--") + 1 :]
    parser = argparse.ArgumentParser(
        prog="export_to_bambu.sh",
        description="Export a FreeCAD .FCStd design to .3mf and open in Bambu Studio.",
    )
    parser.add_argument(
        "target",
        help="Path to .FCStd file, design directory, or short design name under designs/<name>/",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output .3mf or .stl path (defaults to <fcstd-dir>/<fcstd-stem>.3mf)",
    )
    parser.add_argument(
        "--body",
        action="append",
        default=[],
        help="Specific body Name or Label to export (repeatable; defaults to all printable bodies)",
    )
    parser.add_argument(
        "--linear-deflection",
        type=float,
        default=0.05,
        help="Mesh linear deflection in mm (default: 0.05)",
    )
    parser.add_argument(
        "--angular-deflection",
        type=float,
        default=0.25,
        help="Mesh angular deflection in radians (default: 0.25)",
    )
    parser.add_argument(
        "--arrange",
        action="store_true",
        help="Run Bambu Studio CLI (--ensure-on-bed --arrange 1) before opening",
    )
    parser.add_argument(
        "--orient",
        action="store_true",
        help="Also let Bambu Studio CLI auto-orient parts (--orient 1)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Only export the file without launching Bambu Studio GUI",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List printable bodies in the .FCStd document and exit",
    )
    return parser.parse_args(argv)


def resolve_fcstd(target):
    # Support short design names ("dog-bowl-lift"), design folders, or direct .FCStd paths.
    if os.path.isfile(target) and target.endswith(".FCStd"):
        return os.path.abspath(target)
    if os.path.isdir(target):
        candidates = sorted(
            p
            for p in glob.glob(os.path.join(target, "*.FCStd"))
            if not p.endswith("-pre-parametric.FCStd")
        )
        if len(candidates) == 1:
            return os.path.abspath(candidates[0])
        base = os.path.basename(os.path.normpath(target))
        exact = os.path.join(target, f"{base}.FCStd")
        if os.path.isfile(exact):
            return os.path.abspath(exact)
        if candidates:
            return os.path.abspath(candidates[0])
    design_dir = os.path.join("designs", target)
    if os.path.isdir(design_dir):
        return resolve_fcstd(design_dir)
    direct = f"{target}.FCStd"
    if os.path.isfile(direct):
        return os.path.abspath(direct)
    raise FileNotFoundError(f"Could not find a .FCStd file for target: {target!r}")


def is_helper_body(body):
    # Helper bodies used as intermediate boolean/fillet stages shouldn't be exported as separate parts.
    label_lower = (body.Label or "").lower()
    name_lower = (body.Name or "").lower()
    if "helper" in label_lower or "helper" in name_lower:
        return True
    if not getattr(body, "Visibility", True):
        has_assembly_links = any(p.TypeId == "App::Link" for p in body.InList)
        if not has_assembly_links:
            return True
    return False


def instance_count_for_body(body):
    # Assembly links pointing directly to a master body indicate how many copies the assembly needs.
    links = [
        p
        for p in body.InList
        if p.TypeId == "App::Link" and getattr(p, "Visibility", True)
    ]
    return max(1, len(links))


def find_printable_bodies(doc, requested_filters):
    all_bodies = [o for o in doc.Objects if o.TypeId == "PartDesign::Body"]
    valid_bodies = [
        b
        for b in all_bodies
        if hasattr(b, "Shape")
        and not b.Shape.isNull()
        and b.Shape.isValid()
        and len(b.Shape.Solids) == 1
    ]
    if requested_filters:
        wanted = {f.lower() for f in requested_filters}
        selected = [
            b
            for b in valid_bodies
            if b.Name.lower() in wanted or (b.Label or "").lower() in wanted
        ]
        if not selected:
            available = ", ".join(f"{b.Name} ({b.Label!r})" for b in valid_bodies)
            raise RuntimeError(
                f"No body matched {requested_filters}. Available: {available}"
            )
        return [(b, instance_count_for_body(b)) for b in selected]

    printable = [b for b in valid_bodies if not is_helper_body(b)]
    if not printable:
        printable = valid_bodies
    return [(b, instance_count_for_body(b)) for b in printable]


def pack_shapes_on_plate(body_entries, spacing=12.0):
    # Place each exported solid flat on Z=0 and spaced along a grid so multi-part
    # exports don't overlap inside Bambu Studio before arrangement.
    items = []
    for body, count in body_entries:
        for idx in range(count):
            shape = body.Shape.copy()
            # Reset to master body's local orientation (ignore assembly Z-lifts) and sit on Z=0.
            bb = shape.BoundBox
            shape.translate(
                App.Vector(
                    -(bb.XMin + bb.XMax) / 2.0,
                    -(bb.YMin + bb.YMax) / 2.0,
                    -bb.ZMin,
                )
            )
            label = body.Label or body.Name
            if count > 1:
                label = f"{label} #{idx + 1}"
            items.append((body.Name, label, shape))

    if len(items) == 1:
        return items

    cols = max(1, math.ceil(math.sqrt(len(items))))
    col_widths = [0.0] * cols
    row_Count = math.ceil(len(items) / cols)
    row_heights = [0.0] * row_Count

    for i, (_, _, shape) in enumerate(items):
        r, c = divmod(i, cols)
        bb = shape.BoundBox
        col_widths[c] = max(col_widths[c], bb.XLength)
        row_heights[r] = max(row_heights[r], bb.YLength)

    total_w = sum(col_widths) + spacing * (cols - 1)
    total_h = sum(row_heights) + spacing * (row_Count - 1)

    placed = []
    y_cursor = -total_h / 2.0
    for r in range(row_Count):
        x_cursor = -total_w / 2.0
        for c in range(cols):
            idx = r * cols + c
            if idx >= len(items):
                break
            name, label, shape = items[idx]
            cx = x_cursor + col_widths[c] / 2.0
            cy = y_cursor + row_heights[r] / 2.0
            moved = shape.copy()
            moved.translate(App.Vector(cx, cy, 0.0))
            placed.append((name, label, moved))
            x_cursor += col_widths[c] + spacing
        y_cursor += row_heights[r] + spacing

    return placed


def inject_3mf_object_names(three_mf_path, labels):
    # FreeCAD's Mesh.export omits object names in 3D/3dmodel.model; adding them
    # makes part names readable in Bambu Studio's object list.
    ET.register_namespace("", "http://schemas.microsoft.com/3dmanufacturing/core/2015/02")
    with zipfile.ZipFile(three_mf_path, "r") as zin:
        entries = {name: zin.read(name) for name in zin.namelist()}

    model_key = "3D/3dmodel.model"
    if model_key not in entries:
        return

    root = ET.fromstring(entries[model_key])
    objects = root.findall(".//{*}object")
    for obj, label in zip(objects, labels):
        obj.set("name", label)

    entries[model_key] = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    with zipfile.ZipFile(three_mf_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
        for name, data in entries.items():
            zout.writestr(name, data)


def export_items(doc, placed_items, output_path, lin_defl, ang_defl):
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    temp_features = []
    labels = []
    try:
        for idx, (name, label, shape) in enumerate(placed_items, 1):
            mesh_obj = doc.addObject("Mesh::Feature", f"ExportMesh_{idx}")
            mesh_obj.Label = label
            mesh_obj.Mesh = MeshPart.meshFromShape(
                Shape=shape,
                LinearDeflection=lin_defl,
                AngularDeflection=ang_defl,
                Relative=False,
            )
            temp_features.append(mesh_obj)
            labels.append(label)

        Mesh.export(temp_features, output_path)
        if output_path.lower().endswith(".3mf"):
            inject_3mf_object_names(output_path, labels)
    finally:
        for feat in temp_features:
            doc.removeObject(feat.Name)


def run_bambu_cli_arrange(output_path, auto_orient=False):
    if not os.path.isfile(BAMBU_BIN):
        print(f"Warning: Bambu Studio CLI not found at {BAMBU_BIN}", file=sys.stderr)
        return
    tmp_out = output_path + ".arranged.3mf"
    cmd = [
        BAMBU_BIN,
        "--ensure-on-bed",
        "--arrange",
        "1",
        "--orient",
        "1" if auto_orient else "0",
        "--export-3mf",
        tmp_out,
        output_path,
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and os.path.isfile(tmp_out):
        os.replace(tmp_out, output_path)
        print("Bambu Studio CLI: arranged on bed.")
    else:
        if os.path.isfile(tmp_out):
            os.remove(tmp_out)
        print(
            f"Warning: Bambu Studio CLI arrange returned {res.returncode}: {res.stderr.strip()}",
            file=sys.stderr,
        )


def main():
    args = parse_args()
    fcstd_path = resolve_fcstd(args.target)
    doc = App.openDocument(fcstd_path)
    doc.recompute()

    body_entries = find_printable_bodies(doc, args.body)
    if args.list:
        print(f"Document: {fcstd_path}")
        for body, count in body_entries:
            bb = body.Shape.BoundBox
            print(
                f"  - {body.Name} ({body.Label!r}) x{count}: "
                f"{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm"
            )
        return

    stem = os.path.splitext(os.path.basename(fcstd_path))[0]
    out_path = os.path.abspath(
        args.output or os.path.join(os.path.dirname(fcstd_path), f"{stem}.3mf")
    )

    placed_items = pack_shapes_on_plate(body_entries)
    print(f"Source: {fcstd_path}")
    for name, label, shape in placed_items:
        bb = shape.BoundBox
        fits = (
            bb.XLength <= A1_MAX_MM
            and bb.YLength <= A1_MAX_MM
            and bb.ZLength <= A1_MAX_MM
        )
        status = "OK (fits A1 256^3)" if fits else "WARN: exceeds A1 256x256x256 mm!"
        print(
            f"  Part: {label} [{name}] -> "
            f"{bb.XLength:.1f} x {bb.YLength:.1f} x {bb.ZLength:.1f} mm ({status})"
        )

    export_items(
        doc,
        placed_items,
        out_path,
        args.linear_deflection,
        args.angular_deflection,
    )
    print(f"Exported: {out_path} ({len(placed_items)} object(s))")

    if (args.arrange or args.orient) and out_path.lower().endswith(".3mf"):
        run_bambu_cli_arrange(out_path, auto_orient=args.orient)

    if not args.no_open:
        subprocess.run(["open", "-a", BAMBU_APP, out_path], check=True)
        print(f"Opened in Bambu Studio: {out_path}")


main()
