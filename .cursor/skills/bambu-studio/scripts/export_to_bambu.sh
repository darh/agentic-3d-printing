#!/usr/bin/env bash
# Exports printable PartDesign::Body objects (and assembly instances) from a FreeCAD
# .FCStd file into a single .3mf file (or .stl) and opens it in Bambu Studio.

set -euo pipefail

FREECAD_CMD="${FREECAD_CMD:-/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd}"
BAMBU_CLI="${BAMBU_CLI:-/Applications/BambuStudio.app/Contents/MacOS/BambuStudio}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ ! -x "$FREECAD_CMD" ]]; then
  echo "Error: FreeCAD CLI not found at $FREECAD_CMD" >&2
  exit 1
fi

# Pass CLI arguments via environment variable because FreeCADCmd attempts to open
# every positional argument on its command line as a CAD file.
export BAMBU_EXPORT_ARGS="$(python3 -c 'import json, sys; print(json.dumps(sys.argv[1:]))' "$@")"
exec "$FREECAD_CMD" "$SCRIPT_DIR/_freecad_export_to_bambu.py"
