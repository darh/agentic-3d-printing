---
name: bambu-studio
description: Export FreeCAD (.FCStd) designs to .3mf or .stl and import/open them in Bambu Studio on macOS. Use when the user asks to export to Bambu, import to Bambu, send a model or .FCStd to Bambu Studio, slice a FreeCAD part, or open a design in Bambu Studio.
---

# Export FreeCAD to Bambu Studio

Exports printable `PartDesign::Body` solids (including repeated assembly `App::Link` instances) from a `.FCStd` document into a single `.3mf` file with named objects on the build plate, checks the Bambu Lab A1 `256 × 256 × 256 mm` envelope, and opens the `.3mf` in Bambu Studio.

## Quick Usage

Run the helper script from the repository root. Note that `freecadcmd` on macOS requires running outside the Cursor sandbox (`required_permissions: ["all"]`) because the sandbox blocks ARM64 CPU feature detection (`neon crc32`) inside Qt.

```bash
.cursor/skills/bambu-studio/scripts/export_to_bambu.sh <design-name-or-fcstd-path>
```

### Examples

```bash
# Export by short design name under designs/<name>/ and open in Bambu Studio
.cursor/skills/bambu-studio/scripts/export_to_bambu.sh bedside-ipad-holder

# Export a multi-part / assembly .FCStd (places all printable bodies & link instances into one .3mf)
.cursor/skills/bambu-studio/scripts/export_to_bambu.sh designs/dog-bowl-lift/dog-bowl-lift.FCStd

# Export + run Bambu Studio CLI plate arrangement before opening GUI
.cursor/skills/bambu-studio/scripts/export_to_bambu.sh garmin-venu-stand --arrange

# Export only a specific body without opening Bambu Studio GUI
.cursor/skills/bambu-studio/scripts/export_to_bambu.sh garmin-venu-stand --body PlugTestSlug -o designs/garmin-venu-stand/meshes/plug-test-slug.3mf --no-open

# List printable bodies and instance counts in a .FCStd file
.cursor/skills/bambu-studio/scripts/export_to_bambu.sh dog-bowl-lift --list
```

## CLI Flags

- `<target>`: Short name (`dog-bowl-lift`), folder (`designs/dog-bowl-lift`), or `.FCStd` path.
- `-o, --output <path>`: Custom `.3mf` or `.stl` path (defaults to `designs/<name>/<name>.3mf`).
- `--body <NameOrLabel>`: Export only specific body/bodies (repeatable).
- `--arrange`: Run `/Applications/BambuStudio.app/Contents/MacOS/BambuStudio --ensure-on-bed --arrange 1` on the `.3mf` before opening.
- `--orient`: Also pass `--orient 1` to Bambu Studio CLI.
- `--no-open`: Export the `.3mf`/`.stl` without launching the Bambu Studio app.
- `--list`: Print detected printable bodies, instance counts, and dimensions without exporting.
- `--linear-deflection <mm>`: Mesh linear deflection (default `0.05`).
- `--angular-deflection <rad>`: Mesh angular deflection (default `0.25`).

## Direct Bambu Studio CLI Reference

When you already have a `.3mf` or `.stl` and only want to import/open or CLI-process it:

```bash
# Open existing .3mf or .stl in Bambu Studio GUI
open -a "/Applications/BambuStudio.app" designs/<name>/<name>.3mf

# Headless CLI arrange + export
/Applications/BambuStudio.app/Contents/MacOS/BambuStudio \
  --ensure-on-bed --arrange 1 \
  --export-3mf designs/<name>/<name>.3mf \
  designs/<name>/<name>.3mf
```
