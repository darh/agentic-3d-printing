# 3D printing with FreeCAD

Design parts here for a Bambu Lab A1. Model them in FreeCAD.

## Printer

Figures are from the [A1 technical specifications](https://bambulab.com/en/a1/tech-specs) and the [A1 introduction](https://wiki.bambulab.com/en/a1/manual/intro-a1).

- Build volume: 256 × 256 × 256 mm
- Filament diameter: 1.75 mm
- Included nozzle: 0.4 mm stainless steel. Optional diameters: 0.2, 0.6, 0.8 mm
- Maximum temperatures: hotend 300 °C, bed 100 °C
- Plate in the box: textured PEI
- Ideal materials: PLA, PETG, TPU, PVA
- Poor fit for this open-frame machine: ABS, ASA, PC, PA, PET, and carbon- or glass-filled filament. Filled filament also needs a hardened-steel nozzle.

Work in millimeters. FreeCAD stores lengths in mm.

Ask which filament, and whether the nozzle is still the stock 0.4 mm, when the answer changes thickness, fit, or material choice. Until told otherwise, design for a 0.4 mm nozzle and a material the A1 is rated for, and name that assumption in the reply.

## Modeling

Use one Part Design Body per printed part. Draw on a sketch, Pad to add material, and Pocket to remove it. Fully constrain each sketch. Put dimensions the user may edit later on a named constraint or a spreadsheet alias.

When it takes comparable effort, make every model spreadsheet-driven:

- Add a `Parameters` sheet with units, stable aliases, and short purpose or safe-range notes.
- Drive sketch constraints, feature dimensions, placements, patterns, fits, and clearances from spreadsheet expressions. Do not create a sheet that only records values while the geometry remains static.
- Prefer native FreeCAD expressions and features so parameters still recompute after closing and reopening the `.FCStd`; do not require a rebuild macro for routine edits.
- Keep one printable master Body per unique part and use links only for repeated assembly instances.
- Before finishing, change representative primary parameters, recompute, verify every printable result remains one valid solid, then restore the approved values.
- If live spreadsheet geometry would add substantial brittleness or effort, say so and use named sketch constraints instead of silently building a fake or fragile parameter layer.

Use the Part workbench for booleans, imported solids, and shapes Part Design does not build.

After a change that the user should see: recompute, confirm the shape is a valid solid, and show a screenshot from the view that makes the change obvious.

## Printability

Check these before calling a part done:

- The bounding box fits in 256 × 256 × 256 mm. When it does not, say so and propose a split.
- Walls and pins are at least two nozzle widths (0.8 mm with the stock 0.4 mm nozzle). Call out holes under about 2 mm; they print small.
- The face that sits on the textured PEI plate is flat and is the face you intended.
- Overhangs past about 45° from vertical, and long bridges, usually need support. Name those spots, and offer an orientation that prints without support when one exists.
- State every fit clearance (press, snug, or loose) in the reply.

### Printed threads

Treat a valid helical solid as unproven until its thread form is printable. For printed male or female threads with the stock 0.4 mm nozzle:

- Prefer a coarse custom trapezoidal or buttress profile over a fine standard V-thread. Start around 3 mm pitch, 0.6-0.7 mm radial depth, and at least 0.4 mm flat crests and roots.
- In the intended orientation, the unsupported/lower flank must rise at least 1 mm for each 1 mm of radial projection (at least 45° above horizontal). Do not use a deeper profile merely because the CAD boolean succeeds.
- Start PLA mating clearance around 0.25-0.35 mm radial and state it. Add a chamfered lead-in and thread relief at the shoulder.
- Use at least four fully engaged turns. Confirm that modeled thread length divided by pitch matches the visible turn count in the exported mesh and slicer layer preview; internal turns must continue to full depth rather than merging into a smooth bore.
- Before a full print, make or offer a small coupon containing one female boss and a short male stub, preferably with several clearances. Do not call a new printed-thread fit proven from CAD validation alone.
- Check whether a tall, narrow threaded part can wobble when printed vertically. Recommend a brim and slower overhang walls; horizontal round threads generally need support or a designed flat.
- When hardware is forbidden, offer a bayonet or quarter-turn lock when it is more reliable than a printed screw thread.

Export `.3mf` or `.stl` when the user wants a file for Bambu Studio. Leave slicing and printer profiles in Bambu Studio.

## Files

Save each design under `designs/<short-name>/`:

- `designs/<short-name>/<short-name>.FCStd` — the FreeCAD document
- `designs/<short-name>/<short-name>.3mf` or `.stl` — only for the slicer

Use a short lowercase name with hyphens. Continue an existing document for that part rather than creating a second one.

## FreeCAD connection

FreeCAD is available as the `user-freecad` tools. Read a tool's schema before calling it.

If a call fails or FreeCAD seems frozen, call `get_rpc_status` before retrying. When that report says the GUI dispatch is stuck, tell the user FreeCAD needs a restart.

1. `list_documents` before creating or editing.
2. `create_document` for a new part.
3. Use `create_object`, `edit_object`, `get_object`, `get_objects`, and `delete_object` for registered types (`Part::`, `PartDesign::`, `Fem::`) and for the Draft factories that tool documents. Draft factories assign their own internal name; later calls must use the name the tool returns.
4. Use `execute_code` for sketches, constraints, Part Design features the object tools do not cover, recomputes, saving, and exports. It runs on the GUI thread and is the normal path.
5. Set `include_screenshot` to false on intermediate steps. Leave it on for the step the user should see, and pick `view_name` for that feature. Use `get_view` with `focus_object` when you only need a picture.
6. Use `execute_code_async` only for long geometry math. It must not create objects, set properties, recompute, or save. Document and view writes go through the injected `commit()`. Poll with `get_async_status`.
7. Use `execute_code_headless` for work that can crash OpenCascade: threads, lofts, sweeps, and heavy booleans. Save the `.FCStd` from that script, then `reload_document` when that file is open in the GUI.
8. Save the `.FCStd` under `designs/` before finishing, so the part is not only in the live session.
9. Library parts: `get_parts_list`, then `insert_part_from_library`.
10. Run finite-element analysis only when asked. `run_fem_analysis` needs a solid, a material, a mesh, a fixed constraint, and a load already in the analysis.
