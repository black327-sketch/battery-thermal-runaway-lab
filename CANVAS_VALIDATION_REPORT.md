# Canvas Validation Report

## What Changed
- Added semantic `LabConnection.from_ports(...)` with `from_device`, `from_port`, `to_device`, and `to_port`.
- Added automatic orthogonal SVG path generation from stable device ports.
- Added endpoint validation via `validate_connection_endpoints(...)`.
- Added hidden-by-default port debug overlay, controlled by the canvas toolbar `????` toggle.
- Added `data-from`, `data-to`, `aria-label`, and `title` attributes to connection paths.

## ARC Canvas
- Connection endpoints are generated from `ARC_LAYOUT` anchors.
- Validated chains include nitrogen to ARC, vacuum to ARC, ARC to tank, tank to bag, bag to GC, GC to MS, MS/DAQ to computer, and GC to LFL.
- Risk overlay remains above devices but can be hidden; connection lines remain below device labels.

## Literature Canvas
- Connection endpoints are generated from `LITERATURE_PORTS`.
- Validated chains include vacuum pump to chamber, nitrogen to chamber, chamber sample out to bag, bag to GC, GC to MS, MS to computer, chamber voltage/pressure/ARC monitor to DAQ/ARC.
- Literature labels that were briefly corrupted by console encoding during editing were repaired using Unicode-escaped source strings.

## Validation Results
- Canvas-specific tests: `27 passed`.
- Full test suite with backup ignored: `221 passed`.
- Screenshots:
  - `artifacts/screenshots/canvas-literature.png`
  - `artifacts/screenshots/canvas-arc.png`

## Console Notes
Directly opening Streamlit subpaths produced `_stcore/host-config` and `_stcore/health` 404s because Streamlit uses relative internal paths on direct encoded routes. Pages still rendered. Browser warnings about unsupported iframe feature flags are from Streamlit/runtime behavior, not app logic.
