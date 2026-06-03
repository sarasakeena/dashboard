import ezdxf
import math
import os
import tkinter as tk
from tkinter import filedialog

root = tk.Tk()
root.withdraw()

input_path = filedialog.askopenfilename(
    title="Select Input DXF File",
    filetypes=[("DXF Files", "*.dxf")]
)
if not input_path:
    print("No file selected. Exiting.")
    exit()

base_name = os.path.splitext(input_path)[0]
output_path = base_name + "_output.dxf"

TARGET_LAYER = "RCC_BEAMS"
GENERATED_LAYER = "GENERATED_PERP_LINES"
BEHIND_MIN_DISTANCE = 10
BEHIND_MAX_DISTANCE = 450
FRONT_MIN_DISTANCE = 200
RATIO = 0.2
PARALLEL_TOLERANCE = 1.0
RAY_LENGTH = 100000
ENDPOINT_TOLERANCE = 20
PERP_DIM_OFFSET = 350
PERP_DIM_TEXT_HEIGHT = 2
PERP_DIM_ARROW_SIZE = 2
BAR_TEXT = "T8@200C/C"
BAR_TEXT_HEIGHT = 50
BAR_TEXT_OFFSET = 65
BAR_TEXT_COLOR = 3
WALL_SIZE_TOLERANCE_PERCENT = 0.50

_spacing_text_drawn = set()


def generated_line_attribs(color):
    return {
        "color": color,
        "layer": GENERATED_LAYER,
        "linetype": "CONTINUOUS",
    }



def add_text_for_each_bar(msp, start, end, text_value=BAR_TEXT):
    from ezdxf.enums import TextEntityAlignment

    dx = end[0] - start[0]
    dy = end[1] - start[1]
    bar_len = math.hypot(dx, dy)
    if bar_len < 1e-6:
        return

    normal = (-dy / bar_len, dx / bar_len)
    mid = (
        (start[0] + end[0]) / 2,
        (start[1] + end[1]) / 2,
    )
    insert = (
        mid[0] + normal[0] * BAR_TEXT_OFFSET,
        mid[1] + normal[1] * BAR_TEXT_OFFSET,
    )

    rotation = math.degrees(math.atan2(dy, dx))
    if rotation > 90:
        rotation -= 180
    elif rotation < -90:
        rotation += 180

    text = msp.add_text(
        text_value,
        dxfattribs={
            "height": BAR_TEXT_HEIGHT,
            "layer": GENERATED_LAYER,
            "color": BAR_TEXT_COLOR,
            "rotation": rotation,
        },
    )
    try:
        text.set_placement(insert, align=TextEntityAlignment.MIDDLE_CENTER)
    except Exception:
        text.dxf.insert = insert
def safe_read_dxf(path):
    try:
        return ezdxf.readfile(path)
    except ezdxf.DXFError as e:
        print(f"Error reading DXF: {e}")
        print("Attempting to read with ignore_missing_linetypes=True...")
        try:
            return ezdxf.readfile(path, ignore_missing_linetypes=True)
        except:
            print("Failed to read file.")
            raise
