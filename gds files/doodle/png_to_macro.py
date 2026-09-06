#!/usr/bin/env python3
"""Convert a monochrome PNG into a GDSII layout and a LEF abstract view for

Tiny Tapeout hard-macro placement.
"""

from pathlib import Path
import gdstk
from PIL import Image

# -------------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------------
PNG_FILE = "entc.png"  # Input PNG
CELL_NAME = "my_logo"  # Macro cell name (must match config.json and Verilog)
TARGET_WIDTH_UM = 30.0  # Desired width on silicon in micrometers (µm)

# Target PDK layer definitions (Defaults below are for SkyWater 130 met4)
# - met1: (68, 20), met2: (69, 20), met3: (70, 20), met4: (71, 20), met5: (72, 20)
ART_LAYER = 71  # met4 drawing
ART_DATATYPE = 20

# PR boundary layer: 235/4 for sky130
PR_BOUNDARY_LAYER = 235
PR_BOUNDARY_DATATYPE = 4

OUTPUT_GDS = f"{CELL_NAME}.gds"
OUTPUT_LEF = f"{CELL_NAME}.lef"
# -------------------------------------------------------------------------


def generate_macro():
    # 1. Load and threshold image
    img = Image.open(PNG_FILE).convert("L")
    w_px, h_px = img.size

    # Scale factor: pixels -> micrometers (µm)
    pixel_size_um = TARGET_WIDTH_UM / w_px
    target_height_um = h_px * pixel_size_um

    print(
        f"Processing '{PNG_FILE}': {w_px}x{h_px} px -> "
        f"{TARGET_WIDTH_UM:.2f} x {target_height_um:.2f} µm on chip."
    )

    # 2. Create GDS Library and Cell
    lib = gdstk.Library(unit=1e-6, precision=1e-9)  # 1 µm units, 1 nm database
    cell = lib.new_cell(CELL_NAME)

    # 3. Vectorize pixels into horizontal scanline rectangles (RLE)
    #    (Groups consecutive black pixels into single polygons to reduce file size)
    polygons_added = 0
    threshold = 128  # Pixels < threshold are treated as metal/drawn

    for y in range(h_px):
        # Flip vertically so image renders right-side up in layout coords
        y_coord_um = (h_px - 1 - y) * pixel_size_um
        in_run = False
        start_x = 0

        for x in range(w_px):
            is_black = img.getpixel((x, y)) < threshold

            if is_black and not in_run:
                in_run = True
                start_x = x
            elif not is_black and in_run:
                # End of a continuous black segment
                rect = gdstk.rectangle(
                    (start_x * pixel_size_um, y_coord_um),
                    (x * pixel_size_um, y_coord_um + pixel_size_um),
                    layer=ART_LAYER,
                    datatype=ART_DATATYPE,
                )
                cell.add(rect)
                polygons_added += 1
                in_run = False

        if in_run:
            rect = gdstk.rectangle(
                (start_x * pixel_size_um, y_coord_um),
                (w_px * pixel_size_um, y_coord_um + pixel_size_um),
                layer=ART_LAYER,
                datatype=ART_DATATYPE,
            )
            cell.add(rect)
            polygons_added += 1

    # 4. Add Place-and-Route (PR) Boundary
    # Defines the bounding box area so the router knows to stay clear
    pr_box = gdstk.rectangle(
        (0.0, 0.0),
        (TARGET_WIDTH_UM, target_height_um),
        layer=PR_BOUNDARY_LAYER,
        datatype=PR_BOUNDARY_DATATYPE,
    )
    cell.add(pr_box)

    # 5. Write GDSII file
    lib.write_gds(OUTPUT_GDS)
    print(f"Generated GDS: {OUTPUT_GDS} ({polygons_added} polygons created)")

    # 6. Write Abstract LEF file
    # A minimal LEF containing only the cell footprint (no electrical pins)
    lef_content = f"""VERSION 5.7 ;
NOWIREEXTENSIONATPIN ON ;
DIVIDERCHAR "/" ;
BUSBITCHARS "[]" ;

MACRO {CELL_NAME}
  CLASS BLOCK ;
  ORIGIN 0.000 0.000 ;
  FOREIGN {CELL_NAME} 0.000 0.000 ;
  SIZE {TARGET_WIDTH_UM:.3f} BY {target_height_um:.3f} ;
  SYMMETRY X Y R90 ;
  OBS
    LAYER met4 ;
      RECT 0.000 0.000 {TARGET_WIDTH_UM:.3f} {target_height_um:.3f} ;
  END
END {CELL_NAME}

END LIBRARY
"""
    with open(OUTPUT_LEF, "w") as f:
        f.write(lef_content)

    print(f"Generated LEF: {OUTPUT_LEF}")


if __name__ == "__main__":
    generate_macro()