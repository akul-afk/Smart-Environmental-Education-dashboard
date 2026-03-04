"""Compress world_geo.json — regex-shortens decimals, fixes nesting, verifies."""
import json
import re
import os

INPUT = os.path.join("assets", "world_geo.json")
OUTPUT = os.path.join("assets", "world_geo_min.json")

with open(INPUT, "r", encoding="utf-8") as f:
    raw = f.read()

def shorten(m):
    return str(round(float(m.group()), 3))

shortened = re.sub(r'-?\d+\.\d{4,}', shorten, raw)
data = json.loads(shortened)

def fix_and_validate(feature):
    geom = feature["geometry"]
    gtype = geom["type"]
    coords = geom["coordinates"]

    def is_point(v):
        return isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)

    def is_ring(v):
        return isinstance(v, list) and len(v) > 0 and is_point(v[0])

    if gtype == "Polygon":
        # coords should be list of rings, each ring = list of points
        if not is_ring(coords[0]):
            # Possibly extra nesting — unwrap
            geom["coordinates"] = coords[0] if is_ring(coords[0][0] if coords[0] else []) else coords
    elif gtype == "MultiPolygon":
        # coords should be list of polygons, each polygon = list of rings
        fixed_polys = []
        for poly in coords:
            if isinstance(poly, list) and len(poly) > 0:
                if is_ring(poly):
                    # This is actually a single ring, wrap it as polygon
                    fixed_polys.append([poly])
                elif isinstance(poly[0], list) and is_ring(poly[0]):
                    # Correct: list of rings
                    fixed_polys.append(poly)
                elif is_point(poly[0]):
                    # This is a bare ring, wrap twice
                    fixed_polys.append([poly])
                else:
                    fixed_polys.append(poly)
            else:
                fixed_polys.append(poly)
        geom["coordinates"] = fixed_polys

fixed = 0
for ft in data["features"]:
    try:
        fix_and_validate(ft)
    except Exception as e:
        print(f"  Warning: {ft.get('id', '?')}: {e}")
        fixed += 1

# Write minified
with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))

orig = os.path.getsize(INPUT)
mini = os.path.getsize(OUTPUT)
print(f"Original: {orig:,} bytes ({orig/1024/1024:.1f} MB)")
print(f"Minified: {mini:,} bytes ({mini/1024/1024:.1f} MB)")
print(f"Reduction: {(1 - mini/orig)*100:.1f}%")

# Final integrity check
errors = 0
for ft in data["features"]:
    geom = ft["geometry"]
    gtype = geom["type"]
    coords = geom["coordinates"]
    try:
        if gtype == "Polygon":
            for ring in coords:
                for pt in ring:
                    assert isinstance(pt, list) and len(pt) == 2 and all(isinstance(x, (int, float)) for x in pt), f"Bad pt: {pt}"
        elif gtype == "MultiPolygon":
            for poly in coords:
                for ring in poly:
                    for pt in ring:
                        assert isinstance(pt, list) and len(pt) == 2 and all(isinstance(x, (int, float)) for x in pt), f"Bad pt: {pt}"
    except AssertionError as e:
        print(f"  FAIL {ft.get('id','?')}: {e}")
        errors += 1

if errors == 0:
    print("Structure integrity: OK ✓")
else:
    print(f"Structure errors: {errors}")
