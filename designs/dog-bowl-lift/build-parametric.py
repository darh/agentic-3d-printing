import math

import FreeCAD as App
import Part
import Sketcher


DOC_NAME = globals().get("DOC_NAME", "DogBowlLiftParametric")
OUTPUT_PATH = globals().get(
    "OUTPUT_PATH",
    "/Users/darh/Work/3dPrinting/designs/dog-bowl-lift/dog-bowl-lift.FCStd",
)


def expression(obj, prop, value):
    obj.setExpression(prop, value)


def hide(obj):
    obj.Visibility = False


def add_parameter(sheet, row, name, value, alias, note):
    sheet.set("A%d" % row, name)
    sheet.set("B%d" % row, value)
    sheet.set("C%d" % row, note)
    sheet.setAlias("B%d" % row, alias)


def make_arm_sketch(doc, sheet):
    sketch = doc.addObject("Sketcher::SketchObject", "ArmProfileSketch")
    sketch.Label = "Parametric tapered arm profile"
    root_width = 38.0
    tip_width = 18.0
    arm_radius = 80.0
    points = [
        App.Vector(0, -root_width / 2),
        App.Vector(arm_radius, -tip_width / 2),
        App.Vector(arm_radius, tip_width / 2),
        App.Vector(0, root_width / 2),
    ]
    for index in range(4):
        sketch.addGeometry(
            Part.LineSegment(points[index], points[(index + 1) % 4]), False
        )
    for first, second in ((0, 1), (1, 2), (2, 3), (3, 0)):
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", first, 2, second, 1)
        )
    sketch.addConstraint(Sketcher.Constraint("Vertical", 1))
    sketch.addConstraint(Sketcher.Constraint("Vertical", 3))
    root_constraint = sketch.addConstraint(
        Sketcher.Constraint("Distance", 3, root_width)
    )
    tip_constraint = sketch.addConstraint(
        Sketcher.Constraint("Distance", 1, tip_width)
    )
    sketch.addConstraint(
        Sketcher.Constraint("Symmetric", 3, 1, 3, 2, -1, 1)
    )
    tip_center = sketch.addGeometry(
        Part.Point(App.Vector(arm_radius, 0)), True
    )
    radius_constraint = sketch.addConstraint(
        Sketcher.Constraint("DistanceX", tip_center, 1, arm_radius)
    )
    sketch.addConstraint(
        Sketcher.Constraint("DistanceY", tip_center, 1, 0)
    )
    sketch.addConstraint(
        Sketcher.Constraint("Symmetric", 1, 1, 1, 2, tip_center, 1)
    )
    expression(
        sketch,
        "Constraints[%d]" % root_constraint,
        "Parameters.ArmRootWidth",
    )
    expression(
        sketch,
        "Constraints[%d]" % tip_constraint,
        "Parameters.ArmTipWidth",
    )
    expression(
        sketch,
        "Constraints[%d]" % radius_constraint,
        "Parameters.ArmRadius",
    )
    return sketch


def make_thread_profile(
    doc,
    name,
    label,
    inner_expression,
    outer_expression,
    pitch_expression,
    initial_inner,
    initial_outer,
    initial_pitch,
    placement_x_expression=None,
    placement_z_expression=None,
):
    sketch = doc.addObject("Sketcher::SketchObject", name)
    sketch.Label = label
    points = [
        App.Vector(initial_inner, 0),
        App.Vector(initial_outer, initial_pitch / 2),
        App.Vector(initial_inner, initial_pitch),
    ]
    for index in range(3):
        sketch.addGeometry(
            Part.LineSegment(points[index], points[(index + 1) % 3]), False
        )
    for first, second in ((0, 1), (1, 2), (2, 0)):
        sketch.addConstraint(
            Sketcher.Constraint("Coincident", first, 2, second, 1)
        )
    definitions = [
        (0, 1, inner_expression, "0 mm", initial_inner, 0),
        (
            0,
            2,
            outer_expression,
            "%s / 2" % pitch_expression,
            initial_outer,
            initial_pitch / 2,
        ),
        (
            1,
            2,
            inner_expression,
            pitch_expression,
            initial_inner,
            initial_pitch,
        ),
    ]
    for geometry, point, x_expr, y_expr, x_value, y_value in definitions:
        x_constraint = sketch.addConstraint(
            Sketcher.Constraint(
                "DistanceX", geometry, point, x_value
            )
        )
        y_constraint = sketch.addConstraint(
            Sketcher.Constraint(
                "DistanceY", geometry, point, y_value
            )
        )
        expression(
            sketch, "Constraints[%d]" % x_constraint, x_expr
        )
        expression(
            sketch, "Constraints[%d]" % y_constraint, y_expr
        )
    sketch.Placement = App.Placement(
        App.Vector(0, 0, 0), App.Rotation(App.Vector(1, 0, 0), 90)
    )
    if placement_x_expression:
        expression(
            sketch, "Placement.Base.x", placement_x_expression
        )
    if placement_z_expression:
        expression(
            sketch, "Placement.Base.z", placement_z_expression
        )
    return sketch


def add_link(doc, name, linked_object, angle=0):
    link = doc.addObject("App::Link", name)
    link.LinkedObject = linked_object
    link.LinkTransform = True
    link.Placement = App.Placement(
        App.Vector(0, 0, 0),
        App.Rotation(App.Vector(0, 0, 1), angle),
    )
    return link


def make_live_top_fillet(doc, sheet, name, label, source):
    body = doc.addObject("PartDesign::Body", name + "Body")
    body.Label = label + " helper body"
    base = body.newObject("PartDesign::FeatureBase", name + "Base")
    base.BaseFeature = source
    doc.recompute()
    thickness = float(sheet.get("B5").Value)
    top_face = max(
        [
            face
            for face in base.Shape.Faces
            if face.BoundBox.ZLength < 0.01
            and abs(face.BoundBox.ZMin - thickness) < 0.01
        ],
        key=lambda face: face.Area,
    )
    edge_names = []
    for edge in top_face.OuterWire.Edges:
        for global_index, global_edge in enumerate(base.Shape.Edges, 1):
            if edge.isSame(global_edge):
                edge_names.append("Edge%d" % global_index)
                break
    fillet = body.newObject("PartDesign::Fillet", name)
    fillet.Label = label
    fillet.Base = (base, edge_names)
    fillet.Radius = 1.5
    expression(fillet, "Radius", "Parameters.FilletRadius")
    doc.recompute()
    return body, base, fillet


try:
    App.closeDocument(DOC_NAME)
except Exception:
    pass

doc = App.newDocument(DOC_NAME)

parameters = doc.addObject("Spreadsheet::Sheet", "Parameters")
parameters.Label = "Editable Dog Bowl Lift Parameters"
parameters.set("A1", "Parameter")
parameters.set("B1", "Value")
parameters.set("C1", "Recommended range / purpose")

parameter_rows = [
    ("Arm radius", "80 mm", "ArmRadius", "60-95 mm"),
    ("Arm tip width", "18 mm", "ArmTipWidth", "16-24 mm"),
    ("Arm root width", "38 mm", "ArmRootWidth", "Tip width + 10 to 30 mm"),
    ("Platform thickness", "10 mm", "PlatformThickness", "8-14 mm"),
    ("Inverted arch radius", "160 mm", "InvertedArchRadius", "Must exceed 0.87 x arm radius"),
    ("Hub diameter", "36 mm", "HubDiameter", "At least center hole + 12 mm"),
    ("Tip boss diameter", "20 mm", "TipBossDiameter", "At least thread major + 8 mm"),
    ("Dome diameter", "20 mm", "DomeDiameter", "Retaining hemisphere"),
    ("Dome inset", "1 mm", "DomeInset", "0-2 mm into boss"),
    ("Upper edge fillet", "1.5 mm", "FilletRadius", "0.5-2.5 mm"),
    ("Leg diameter", "10 mm", "LegDiameter", "Also male-thread major diameter"),
    ("Leg length", "120 mm", "LegLength", "40-220 mm"),
    ("Thread length", "15 mm", "ThreadLength", "10-20 mm"),
    ("Thread pitch", "1.5 mm", "ThreadPitch", "1.25-2.0 mm"),
    ("Thread depth", "1 mm", "ThreadDepth", "0.8-1.2 mm"),
    ("Thread radial clearance", "0.30 mm", "ThreadRadialClearance", "Loose PLA fit for 0.4 mm nozzle"),
    ("Bone-hole radial start", "24 mm", "BoneHoleRadialStart", "Beyond hub radius"),
    ("Bone-hole length", "38 mm", "BoneHoleLength", "Leave at least 8 mm before boss"),
    ("Bone-hole max width", "12 mm", "BoneHoleMaxWidth", "Leave at least 5 mm side walls"),
    ("Bone-hole neck width", "5 mm", "BoneHoleNeckWidth", "4-8 mm"),
    ("Bone-hole lobe radius", "3.5 mm", "BoneHoleLobeRadius", "3-5 mm"),
    ("Center-hole diameter", "20 mm", "CenterHoleDiameter", "Leave at least 6 mm hub ring"),
]
for row, definition in enumerate(parameter_rows, 2):
    add_parameter(parameters, row, *definition)
parameters.setColumnWidth("A", 190)
parameters.setColumnWidth("B", 95)
parameters.setColumnWidth("C", 310)

top_group = doc.addObject("App::DocumentObjectGroup", "TopConstruction")
top_group.Label = "Top platform native construction"
leg_group = doc.addObject("App::DocumentObjectGroup", "LegConstruction")
leg_group.Label = "Leg native construction"
assembly_group = doc.addObject("App::DocumentObjectGroup", "Assembly")
assembly_group.Label = "Assembled view"

# Concave triangular web: a native triangular prism minus three R-arch cylinders.
web_triangle = doc.addObject("Part::Prism", "WebTriangle")
web_triangle.Polygon = 3
expression(web_triangle, "Circumradius", "Parameters.ArmRadius")
expression(web_triangle, "Height", "Parameters.PlatformThickness")
top_group.addObject(web_triangle)

arch_distance = (
    "Parameters.ArmRadius / 2 + "
    "sqrt(Parameters.InvertedArchRadius * Parameters.InvertedArchRadius "
    "- 3 * Parameters.ArmRadius * Parameters.ArmRadius / 4)"
)
arch_cutters = []
arch_centers = [
    ("(%s) / 2" % arch_distance, "(%s) * sqrt(3) / 2" % arch_distance),
    ("-(%s)" % arch_distance, "0 mm"),
    ("(%s) / 2" % arch_distance, "-(%s) * sqrt(3) / 2" % arch_distance),
]
for index, (x_expr, y_expr) in enumerate(arch_centers, 1):
    cutter = doc.addObject("Part::Cylinder", "ArchCutter%d" % index)
    expression(cutter, "Radius", "Parameters.InvertedArchRadius")
    expression(cutter, "Height", "Parameters.PlatformThickness + 2 mm")
    expression(cutter, "Placement.Base.x", x_expr)
    expression(cutter, "Placement.Base.y", y_expr)
    expression(cutter, "Placement.Base.z", "-1 mm")
    arch_cutters.append(cutter)
    top_group.addObject(cutter)
arch_tools = doc.addObject("Part::MultiFuse", "ArchCutters")
arch_tools.Shapes = arch_cutters
arch_tools.Refine = True
top_group.addObject(arch_tools)
web = doc.addObject("Part::Cut", "ConcaveWeb")
web.Base = web_triangle
web.Tool = arch_tools
web.Refine = True
top_group.addObject(web)
web_fillet_body, web_fillet_base, web_fillet = make_live_top_fillet(
    doc,
    parameters,
    "WebUpperFillet",
    "Live R160 web-edge fillet",
    web,
)

# One live tapered arm profile, extruded and linked at 120 degree intervals.
arm_sketch = make_arm_sketch(doc, parameters)
top_group.addObject(arm_sketch)
arm_extrusion = doc.addObject("Part::Extrusion", "ArmPad")
arm_extrusion.Label = "Parametric tapered arm pad"
arm_extrusion.Base = arm_sketch
arm_extrusion.Solid = True
arm_extrusion.Dir = App.Vector(0, 0, 10)
expression(arm_extrusion, "Dir.z", "Parameters.PlatformThickness")
top_group.addObject(arm_extrusion)
arm_fillet_body, arm_fillet_base, arm_fillet = make_live_top_fillet(
    doc,
    parameters,
    "ArmUpperFillet",
    "Live tapered arm-edge fillet",
    arm_extrusion,
)
arm_link_2 = add_link(doc, "ArmPad120", arm_fillet, 120)
arm_link_3 = add_link(doc, "ArmPad240", arm_fillet, 240)
top_group.addObject(arm_link_2)
top_group.addObject(arm_link_3)

hub = doc.addObject("Part::Cylinder", "HubPad")
expression(hub, "Radius", "Parameters.HubDiameter / 2")
expression(hub, "Height", "Parameters.PlatformThickness")
top_group.addObject(hub)

boss = doc.addObject("Part::Cylinder", "TipBossPad")
expression(boss, "Radius", "Parameters.TipBossDiameter / 2")
expression(boss, "Height", "Parameters.PlatformThickness")
expression(boss, "Placement.Base.x", "Parameters.ArmRadius")
top_group.addObject(boss)
boss_link_2 = add_link(doc, "TipBossPad120", boss, 120)
boss_link_3 = add_link(doc, "TipBossPad240", boss, 240)
top_group.addObject(boss_link_2)
top_group.addObject(boss_link_3)

raw_top = doc.addObject("Part::MultiFuse", "RawTopPlatform")
raw_top.Shapes = [
    web_fillet,
    arm_fillet,
    arm_link_2,
    arm_link_3,
    hub,
    boss,
    boss_link_2,
    boss_link_3,
]
raw_top.Refine = True
top_group.addObject(raw_top)
doc.recompute()

# The printable body receives the finished native boolean tree below.
top_body = doc.addObject("PartDesign::Body", "TopPlatformBody")
top_body.Label = "CONFIGURABLE top platform (print once)"

# Lowered hemispheres remain native spheres linked around the platform.
dome = doc.addObject("Part::Sphere", "RetainingDome")
dome.Angle1 = 0
dome.Angle2 = 90
expression(dome, "Radius", "Parameters.DomeDiameter / 2")
expression(dome, "Placement.Base.x", "Parameters.ArmRadius")
expression(
    dome,
    "Placement.Base.z",
    "Parameters.PlatformThickness - Parameters.DomeInset",
)
top_group.addObject(dome)
dome_link_2 = add_link(doc, "RetainingDome120", dome, 120)
dome_link_3 = add_link(doc, "RetainingDome240", dome, 240)
top_group.addObject(dome_link_2)
top_group.addObject(dome_link_3)
dome_fuse = doc.addObject("Part::MultiFuse", "PlatformWithDomes")
dome_fuse.Shapes = [raw_top, dome, dome_link_2, dome_link_3]
dome_fuse.Refine = True
top_group.addObject(dome_fuse)

# One native female thread cutter, linked to all three arm tips.
female_inner = (
    "Parameters.LegDiameter / 2 - Parameters.ThreadDepth "
    "+ Parameters.ThreadRadialClearance"
)
female_outer = (
    "Parameters.LegDiameter / 2 + Parameters.ThreadRadialClearance"
)
female_profile = make_thread_profile(
    doc,
    "FemaleThreadProfile",
    "Live female thread profile",
    "(%s) - 0.1 mm" % female_inner,
    female_outer,
    "Parameters.ThreadPitch",
    4.2,
    5.3,
    1.5,
    "Parameters.ArmRadius",
    "-0.5 mm",
)
top_group.addObject(female_profile)
female_helix = doc.addObject("Part::Helix", "FemaleThreadHelix")
expression(female_helix, "Pitch", "Parameters.ThreadPitch")
expression(
    female_helix,
    "Height",
    "Parameters.ThreadLength + 1 mm - Parameters.ThreadPitch",
)
expression(female_helix, "Radius", "(%s) - 0.1 mm" % female_inner)
expression(female_helix, "Placement.Base.x", "Parameters.ArmRadius")
expression(female_helix, "Placement.Base.z", "-0.5 mm")
top_group.addObject(female_helix)
female_sweep = doc.addObject("Part::Sweep", "FemaleThreadSweep")
female_sweep.Sections = [female_profile]
female_sweep.Spine = (female_helix, ["Edge1"])
female_sweep.Solid = True
female_sweep.Frenet = True
top_group.addObject(female_sweep)
female_pilot = doc.addObject("Part::Cylinder", "FemalePilotBore")
expression(female_pilot, "Radius", female_inner)
expression(female_pilot, "Height", "Parameters.ThreadLength + 1 mm")
expression(female_pilot, "Placement.Base.x", "Parameters.ArmRadius")
expression(female_pilot, "Placement.Base.z", "-0.5 mm")
top_group.addObject(female_pilot)
female_cutter = doc.addObject("Part::MultiFuse", "FemaleThreadCutter")
female_cutter.Shapes = [female_pilot, female_sweep]
female_cutter.Refine = False
top_group.addObject(female_cutter)
female_link_2 = add_link(doc, "FemaleThreadCutter120", female_cutter, 120)
female_link_3 = add_link(doc, "FemaleThreadCutter240", female_cutter, 240)
top_group.addObject(female_link_2)
top_group.addObject(female_link_3)
female_cutters = doc.addObject("Part::MultiFuse", "AllFemaleThreadCutters")
female_cutters.Shapes = [female_cutter, female_link_2, female_link_3]
female_cutters.Refine = True
top_group.addObject(female_cutters)
threaded_top = doc.addObject("Part::Cut", "ThreadedTopPlatform")
threaded_top.Base = dome_fuse
threaded_top.Tool = female_cutters
threaded_top.Refine = True
top_group.addObject(threaded_top)

# Native dog-bone cutter built from a neck box and four circular lobes.
bone_box = doc.addObject("Part::Box", "BoneHoleNeck")
expression(
    bone_box,
    "Length",
    "Parameters.BoneHoleLength - 2 * Parameters.BoneHoleLobeRadius",
)
expression(bone_box, "Width", "Parameters.BoneHoleNeckWidth")
expression(bone_box, "Height", "Parameters.PlatformThickness + 1 mm")
expression(
    bone_box,
    "Placement.Base.x",
    "Parameters.BoneHoleRadialStart + Parameters.BoneHoleLobeRadius",
)
expression(
    bone_box,
    "Placement.Base.y",
    "-Parameters.BoneHoleNeckWidth / 2",
)
expression(bone_box, "Placement.Base.z", "-0.5 mm")
top_group.addObject(bone_box)
bone_lobes = []
for end_index, x_expr in enumerate(
    [
        "Parameters.BoneHoleRadialStart + Parameters.BoneHoleLobeRadius",
        "Parameters.BoneHoleRadialStart + Parameters.BoneHoleLength "
        "- Parameters.BoneHoleLobeRadius",
    ]
):
    for side_index, sign in enumerate((-1, 1)):
        lobe = doc.addObject(
            "Part::Cylinder",
            "BoneLobe%d%d" % (end_index + 1, side_index + 1),
        )
        expression(lobe, "Radius", "Parameters.BoneHoleLobeRadius")
        expression(lobe, "Height", "Parameters.PlatformThickness + 1 mm")
        expression(lobe, "Placement.Base.x", x_expr)
        y_expr = (
            "%d * (Parameters.BoneHoleMaxWidth / 2 "
            "- Parameters.BoneHoleLobeRadius)" % sign
        )
        expression(lobe, "Placement.Base.y", y_expr)
        expression(lobe, "Placement.Base.z", "-0.5 mm")
        bone_lobes.append(lobe)
        top_group.addObject(lobe)
bone_cutter = doc.addObject("Part::MultiFuse", "DogBoneHoleCutter")
bone_cutter.Shapes = [bone_box] + bone_lobes
bone_cutter.Refine = True
top_group.addObject(bone_cutter)
bone_link_2 = add_link(doc, "DogBoneHoleCutter120", bone_cutter, 120)
bone_link_3 = add_link(doc, "DogBoneHoleCutter240", bone_cutter, 240)
top_group.addObject(bone_link_2)
top_group.addObject(bone_link_3)
bone_cutters = doc.addObject("Part::MultiFuse", "AllDogBoneHoleCutters")
bone_cutters.Shapes = [bone_cutter, bone_link_2, bone_link_3]
bone_cutters.Refine = True
top_group.addObject(bone_cutters)
lightened_top = doc.addObject("Part::Cut", "DogBoneLightenedPlatform")
lightened_top.Base = threaded_top
lightened_top.Tool = bone_cutters
lightened_top.Refine = True
top_group.addObject(lightened_top)

center_cutter = doc.addObject("Part::Cylinder", "CenterHoleCutter")
expression(center_cutter, "Radius", "Parameters.CenterHoleDiameter / 2")
expression(center_cutter, "Height", "Parameters.PlatformThickness + 1 mm")
expression(center_cutter, "Placement.Base.z", "-0.5 mm")
top_group.addObject(center_cutter)
finished_top = doc.addObject("Part::Cut", "FinishedTopPlatform")
finished_top.Base = lightened_top
finished_top.Tool = center_cutter
finished_top.Refine = True
top_group.addObject(finished_top)

top_final = top_body.newObject("PartDesign::FeatureBase", "ConfigurableTopResult")
top_final.Label = "LIVE CONFIGURABLE TOP RESULT"
top_final.BaseFeature = finished_top
top_body.Tip = top_final

# Parametric leg and integral male thread.
leg_cylinder = doc.addObject("Part::Cylinder", "StraightLegPad")
expression(leg_cylinder, "Radius", "Parameters.LegDiameter / 2")
expression(leg_cylinder, "Height", "Parameters.LegLength")
leg_group.addObject(leg_cylinder)

male_root = (
    "Parameters.LegDiameter / 2 - Parameters.ThreadDepth"
)
male_outer = "Parameters.LegDiameter / 2"
male_profile = make_thread_profile(
    doc,
    "MaleThreadProfile",
    "Live male thread profile",
    "(%s) - 0.1 mm" % male_root,
    male_outer,
    "Parameters.ThreadPitch",
    3.9,
    5.0,
    1.5,
    None,
    "Parameters.LegLength",
)
leg_group.addObject(male_profile)
male_helix = doc.addObject("Part::Helix", "MaleThreadHelix")
expression(male_helix, "Pitch", "Parameters.ThreadPitch")
expression(
    male_helix,
    "Height",
    "Parameters.ThreadLength - Parameters.ThreadPitch",
)
expression(male_helix, "Radius", "(%s) - 0.1 mm" % male_root)
expression(male_helix, "Placement.Base.z", "Parameters.LegLength")
leg_group.addObject(male_helix)
male_sweep = doc.addObject("Part::Sweep", "MaleThreadSweep")
male_sweep.Sections = [male_profile]
male_sweep.Spine = (male_helix, ["Edge1"])
male_sweep.Solid = True
male_sweep.Frenet = True
leg_group.addObject(male_sweep)
male_root_cylinder = doc.addObject("Part::Cylinder", "MaleThreadRoot")
expression(
    male_root_cylinder,
    "Radius",
    "%s + 0.05 mm" % male_root,
)
expression(male_root_cylinder, "Height", "Parameters.ThreadLength")
expression(
    male_root_cylinder,
    "Placement.Base.z",
    "Parameters.LegLength",
)
leg_group.addObject(male_root_cylinder)
finished_leg = doc.addObject("Part::MultiFuse", "FinishedLeg")
finished_leg.Shapes = [leg_cylinder, male_root_cylinder, male_sweep]
finished_leg.Refine = True
leg_group.addObject(finished_leg)

leg_body = doc.addObject("PartDesign::Body", "LegBody")
leg_body.Label = "CONFIGURABLE leg with integral thread (print x3)"
leg_final = leg_body.newObject("PartDesign::FeatureBase", "ConfigurableLegResult")
leg_final.Label = "LIVE CONFIGURABLE LEG RESULT"
leg_final.BaseFeature = finished_leg
leg_body.Tip = leg_final

# Assembly links keep the printable master bodies at their local origins.
top_assembly = add_link(doc, "TopAssembly", top_body)
top_assembly.Label = "Top platform assembly instance"
expression(top_assembly, "Placement.Base.z", "Parameters.LegLength")
assembly_group.addObject(top_assembly)

leg_assembly_1 = add_link(doc, "LegAssembly1", leg_body)
leg_assembly_1.Label = "Leg assembly instance 1"
expression(leg_assembly_1, "Placement.Base.x", "Parameters.ArmRadius")
assembly_group.addObject(leg_assembly_1)
leg_assembly_2 = add_link(doc, "LegAssembly2", leg_body)
leg_assembly_2.Label = "Leg assembly instance 2"
expression(
    leg_assembly_2, "Placement.Base.x", "-Parameters.ArmRadius / 2"
)
expression(
    leg_assembly_2,
    "Placement.Base.y",
    "Parameters.ArmRadius * sqrt(3) / 2",
)
assembly_group.addObject(leg_assembly_2)
leg_assembly_3 = add_link(doc, "LegAssembly3", leg_body)
leg_assembly_3.Label = "Leg assembly instance 3"
expression(
    leg_assembly_3, "Placement.Base.x", "-Parameters.ArmRadius / 2"
)
expression(
    leg_assembly_3,
    "Placement.Base.y",
    "-Parameters.ArmRadius * sqrt(3) / 2",
)
assembly_group.addObject(leg_assembly_3)

notes = doc.addObject("App::FeaturePython", "DesignNotes")
notes.Label = "Parametric design and print notes"
notes.addProperty("App::PropertyString", "Material", "Print")
notes.Material = "PLA"
notes.addProperty("App::PropertyString", "Nozzle", "Print")
notes.Nozzle = "0.4 mm stock nozzle"
notes.addProperty("App::PropertyString", "ThreadFit", "Print")
notes.ThreadFit = "Radial clearance is spreadsheet-driven; current value 0.30 mm is loose/easy"
notes.addProperty("App::PropertyString", "TopOrientation", "Print")
notes.TopOrientation = "Print flat underside down; no support expected"
notes.addProperty("App::PropertyString", "LegOrientation", "Print")
notes.LegOrientation = "Vertical gives the cleanest thread; use a brim"
notes.addProperty("App::PropertyString", "SafeEditing", "Parameters")
notes.SafeEditing = "Stay within spreadsheet recommendations; R-arch must exceed 0.87 x arm radius"

doc.recompute()

# Hide all construction. Only assembly links are visible.
for obj in top_group.Group + leg_group.Group:
    hide(obj)
hide(web_fillet_base)
hide(web_fillet)
hide(web_fillet_body)
hide(arm_fillet_base)
hide(arm_fillet)
hide(arm_fillet_body)
hide(top_body)
hide(leg_body)
top_final.Visibility = True
leg_final.Visibility = True
top_assembly.Visibility = True
leg_assembly_1.Visibility = True
leg_assembly_2.Visibility = True
leg_assembly_3.Visibility = True

top_final.ViewObject.ShapeColor = (0.30, 0.72, 0.64)
leg_final.ViewObject.ShapeColor = (0.38, 0.58, 0.88)

doc.recompute()

assert arm_sketch.FullyConstrained
assert female_profile.FullyConstrained
assert male_profile.FullyConstrained
assert not top_final.Shape.isNull()
assert top_final.Shape.isValid()
assert len(top_final.Shape.Solids) == 1
assert not leg_final.Shape.isNull()
assert leg_final.Shape.isValid()
assert len(leg_final.Shape.Solids) == 1

print(
    "Top:",
    round(top_final.Shape.BoundBox.XLength, 2),
    round(top_final.Shape.BoundBox.YLength, 2),
    round(top_final.Shape.BoundBox.ZLength, 2),
)
print(
    "Leg:",
    round(leg_final.Shape.BoundBox.XLength, 2),
    round(leg_final.Shape.BoundBox.YLength, 2),
    round(leg_final.Shape.BoundBox.ZLength, 2),
)
print(
    "Sketches fully constrained:",
    arm_sketch.FullyConstrained,
    female_profile.FullyConstrained,
    male_profile.FullyConstrained,
)

doc.recompute()
doc.saveAs(OUTPUT_PATH)
print("Saved:", OUTPUT_PATH)
