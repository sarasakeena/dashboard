import ezdxf
import math
import os
SPACING_TEXT_TEMPLATE = "T8@200C/C"

def update_globals(params):
    global TARGET_LAYER, GENERATED_LAYER, BEHIND_MIN_DISTANCE, BEHIND_MAX_DISTANCE, FRONT_MIN_DISTANCE
    global RATIO, PARALLEL_TOLERANCE, RAY_LENGTH, ENDPOINT_TOLERANCE, PERP_DIM_OFFSET
    global PERP_DIM_TEXT_HEIGHT, PERP_DIM_ARROW_SIZE, WALL_SIZE_TOLERANCE_PERCENT, SPACING_TEXT_TEMPLATE
    
    TARGET_LAYER = params.get("TARGET_LAYER", TARGET_LAYER)
    GENERATED_LAYER = params.get("GENERATED_LAYER", GENERATED_LAYER)
    BEHIND_MIN_DISTANCE = params.get("BEHIND_MIN_DISTANCE", BEHIND_MIN_DISTANCE)
    BEHIND_MAX_DISTANCE = params.get("BEHIND_MAX_DISTANCE", BEHIND_MAX_DISTANCE)
    FRONT_MIN_DISTANCE = params.get("FRONT_MIN_DISTANCE", FRONT_MIN_DISTANCE)
    RATIO = params.get("RATIO", RATIO)
    PARALLEL_TOLERANCE = params.get("PARALLEL_TOLERANCE", PARALLEL_TOLERANCE)
    RAY_LENGTH = params.get("RAY_LENGTH", RAY_LENGTH)
    ENDPOINT_TOLERANCE = params.get("ENDPOINT_TOLERANCE", ENDPOINT_TOLERANCE)
    PERP_DIM_OFFSET = params.get("PERP_DIM_OFFSET", PERP_DIM_OFFSET)
    PERP_DIM_TEXT_HEIGHT = params.get("PERP_DIM_TEXT_HEIGHT", PERP_DIM_TEXT_HEIGHT)
    PERP_DIM_ARROW_SIZE = params.get("PERP_DIM_ARROW_SIZE", PERP_DIM_ARROW_SIZE)
    WALL_SIZE_TOLERANCE_PERCENT = params.get("WALL_SIZE_TOLERANCE_PERCENT", WALL_SIZE_TOLERANCE_PERCENT)
    SPACING_TEXT_TEMPLATE = params.get("SPACING_TEXT_TEMPLATE", SPACING_TEXT_TEMPLATE)
    
    _spacing_text_drawn.clear()


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

def fix_linetypes(doc):
    
    existing = list(doc.linetypes)
    standard = {
        "DASHED": [3.0, -1.0],
        "HIDDEN": [6.0, -3.0],
        "DASH": [3.0, -1.0],
        "CENTER": [6.0, -2.0, 1.0, -2.0],
        "PHANTOM": [6.0, -3.0, 1.0, -3.0],
    }
    for name, pattern in standard.items():
        if name not in existing:
            try:
                doc.linetypes.new(name=name, pattern=pattern)
                print(f"Created linetype: {name}")
            except:
                pass



def length(p1, p2):
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])

def is_hidden_entity(e):
    try:
        lt = e.dxf.linetype.upper()
        return "DASH" in lt or "HIDDEN" in lt
    except:
        return False

def is_target_beam(e):
    layer = e.dxf.layer.upper().replace("_", " ")
    target = TARGET_LAYER.upper().replace("_", " ")
    return layer == target and is_hidden_entity(e)

def extract_beams(msp):
    beams = []
    for e in msp:
        if e.dxftype() == "LINE" and is_target_beam(e):
            p1 = (e.dxf.start.x, e.dxf.start.y)
            p2 = (e.dxf.end.x, e.dxf.end.y)
            beams.append((p1, p2))
        elif e.dxftype() == "LWPOLYLINE" and is_target_beam(e):
            pts = list(e.get_points())
            for i in range(len(pts) - 1):
                p1 = (pts[i][0], pts[i][1])
                p2 = (pts[i + 1][0], pts[i + 1][1])
                beams.append((p1, p2))
    return beams

def get_beam_center(p1, p2):
    return ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)

def get_beam_angle(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.degrees(math.atan2(dy, dx))

def is_horizontal_beam(p1, p2):
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return abs(dx) > abs(dy)


def get_perpendicular_dim_base(start, end, perp_dir, offset=PERP_DIM_OFFSET):

    mid = (
        (start[0] + end[0]) / 2,
        (start[1] + end[1]) / 2
    )

    if abs(perp_dir[0]) > abs(perp_dir[1]):

        if perp_dir[0] > 0:
            normal = (0, 1)

        else:
            normal = (0, 1)

    else:

        if perp_dir[1] > 0:
            normal = (-1, 0)

        else:
            normal = (-1, 0)

    return (
        mid[0] + normal[0] * offset,
        mid[1] + normal[1] * offset,
    )

def _ray_intersect_basic(px, py, rx, ry, x1, y1, x2, y2):
    
    dxl = x2 - x1
    dyl = y2 - y1
    denom = rx * dyl - ry * dxl
    if abs(denom) < 1e-6:
        return None
    t = ((x1 - px) * dyl - (y1 - py) * dxl) / denom
    u = ((x1 - px) * ry - (y1 - py) * rx) / denom
    if t < 0 or not (0 <= u <= 1):
        return None
    return t


def collect_nearest_behind_hits(beam_p1, beam_p2, msp, line_filter,
                                min_distance=10, max_distance=450,
                                size_tolerance_percent=None,
                                use_size_filter=True, label="LINE",
                                layer_filter=None,
                                debug=False):
    
    if size_tolerance_percent is None:
        size_tolerance_percent = WALL_SIZE_TOLERANCE_PERCENT

    dx = beam_p2[0] - beam_p1[0]
    dy = beam_p2[1] - beam_p1[1]
    beam_length = math.hypot(dx, dy)
    size_tolerance = beam_length * size_tolerance_percent
    is_horizontal = abs(dx) > abs(dy)

    directions = (
        {"ABOVE": (0, 1), "BELOW": (0, -1)}
        if is_horizontal
        else {"RIGHT": (1, 0), "LEFT": (-1, 0)}
    )

    NUM_SAMPLES = 5
    sample_origins = [
        (beam_p1[0] + (i + 1) / (NUM_SAMPLES + 1) * dx,
         beam_p1[1] + (i + 1) / (NUM_SAMPLES + 1) * dy)
        for i in range(NUM_SAMPLES)
    ]

    raw_hits = {}
    scanned_count = size_rejected = distance_rejected = 0

    for e in msp:
        if e.dxftype() != "LINE":
            continue
        try:
            if e.dxf.layer.upper() == GENERATED_LAYER.upper():
                continue
        except:
            pass
        if layer_filter is not None:
            try:
                if not layer_filter(e.dxf.layer):
                    continue
            except:
                continue
        lt = e.dxf.linetype.upper()
        if not line_filter(lt):
            continue

        scanned_count += 1
        x1, y1 = e.dxf.start.x, e.dxf.start.y
        x2, y2 = e.dxf.end.x, e.dxf.end.y
        line_length = math.hypot(x2 - x1, y2 - y1)

        if use_size_filter:
            size_diff = abs(line_length - beam_length)
            if size_diff > size_tolerance:
                size_rejected += 1
                if debug:
                    print(f"      [SIZE] Reject {label}: line={line_length:.1f}mm, "
                          f"beam={beam_length:.1f}mm, diff={size_diff:.1f}mm > {size_tolerance:.1f}mm")
                continue

        for ox, oy in sample_origins:
            for side, (rx, ry) in directions.items():
                dist = _ray_intersect_basic(ox, oy, rx, ry, x1, y1, x2, y2)
                if dist is None:
                    continue
                if not (min_distance <= dist <= max_distance):
                    distance_rejected += 1
                    continue

                seg_key = (
                    side,
                    round(min(x1, x2), 1), round(min(y1, y2), 1),
                    round(max(x1, x2), 1), round(max(y1, y2), 1),
                )
                if seg_key not in raw_hits or dist < raw_hits[seg_key]["dist"]:
                    raw_hits[seg_key] = {
                        "side": side,
                        "dist": dist,
                        "coords": (x1, y1, x2, y2),
                        "line_length": line_length,
                        "linetype": lt,
                    }

    if debug:
        print(f"      [SCAN] Scanned {scanned_count} {label} lines, "
              f"{size_rejected} rejected by size, "
              f"{distance_rejected} sample-ray/dist rejects, "
              f"{len(raw_hits)} unique segments hit")

    if not raw_hits:
        return []

    hits = list(raw_hits.values())

    if debug:
        for h in hits:
            print(f"      HIT {label} {h['side']}: dist={h['dist']:.1f}mm, "
                  f"line_len={h['line_length']:.1f}mm")
        print(f"      Returning {len(hits)} {label} hit(s) â€” all distinct segments")

    return hits


def get_perpendicular_start_and_direction(beam_p1, beam_p2, behind_hit, debug=False):
    
    mx = (beam_p1[0] + beam_p2[0]) / 2
    my = (beam_p1[1] + beam_p2[1]) / 2
    dx = beam_p2[0] - beam_p1[0]
    dy = beam_p2[1] - beam_p1[1]
    is_horizontal = abs(dx) > abs(dy)

    bx1, by1, bx2, by2 = behind_hit["coords"]
    behind_side = behind_hit["side"]

    if is_horizontal:
        perp_dir = (0, -1) if behind_side == "ABOVE" else (0, 1)
        beam_min = min(beam_p1[0], beam_p2[0])
        beam_max = max(beam_p1[0], beam_p2[0])
        behind_min = min(bx1, bx2)
        behind_max = max(bx1, bx2)
        overlap_min = max(beam_min, behind_min)
        overlap_max = min(beam_max, behind_max)
        if overlap_min > overlap_max:
            return None, None
        start = ((overlap_min + overlap_max) / 2, my)
        if debug:
            print(f"         Beam X: {beam_min:.1f}â€“{beam_max:.1f}  "
                  f"Behind X: {behind_min:.1f}â€“{behind_max:.1f}  "
                  f"Overlap X: {overlap_min:.1f}â€“{overlap_max:.1f}  "
                  f"Start X: {start[0]:.1f}")
    else:
        perp_dir = (-1, 0) if behind_side == "RIGHT" else (1, 0)
        beam_min = min(beam_p1[1], beam_p2[1])
        beam_max = max(beam_p1[1], beam_p2[1])
        behind_min = min(by1, by2)
        behind_max = max(by1, by2)
        overlap_min = max(beam_min, behind_min)
        overlap_max = min(beam_max, behind_max)
        if overlap_min > overlap_max:
            return None, None
        start = (mx, (overlap_min + overlap_max) / 2)
        if debug:
            print(f"         Beam Y: {beam_min:.1f}â€“{beam_max:.1f}  "
                  f"Behind Y: {behind_min:.1f}â€“{behind_max:.1f}  "
                  f"Overlap Y: {overlap_min:.1f}â€“{overlap_max:.1f}  "
                  f"Start Y: {start[1]:.1f}")

    return start, perp_dir


def has_l_pline_in_front(beam_p1, beam_p2, behind_hit, msp,
                         min_distance=10, max_distance=300,
                         layer_name="L_PLINE", debug=False):
    
    dx = beam_p2[0] - beam_p1[0]
    dy = beam_p2[1] - beam_p1[1]
    is_horizontal = abs(dx) > abs(dy)
    behind_side = behind_hit["side"]

    if is_horizontal:
        if behind_side == "ABOVE":
            front_dir = (0, -1)
        elif behind_side == "BELOW":
            front_dir = (0, 1)
        else:
            return False
    else:
        if behind_side == "RIGHT":
            front_dir = (-1, 0)
        elif behind_side == "LEFT":
            front_dir = (1, 0)
        else:
            return False

    num_samples = 5
    sample_origins = [
        (
            beam_p1[0] + (i + 1) / (num_samples + 1) * dx,
            beam_p1[1] + (i + 1) / (num_samples + 1) * dy,
        )
        for i in range(num_samples)
    ]

    target_layer = layer_name.upper()
    for e in msp:
        if e.dxftype() != "LINE":
            continue
        try:
            if e.dxf.layer.upper() != target_layer:
                continue
        except:
            continue

        x1, y1 = e.dxf.start.x, e.dxf.start.y
        x2, y2 = e.dxf.end.x, e.dxf.end.y
        for ox, oy in sample_origins:
            dist = _ray_intersect_basic(
                ox, oy, front_dir[0], front_dir[1],
                x1, y1, x2, y2,
            )
            if dist is not None and min_distance <= dist <= max_distance:
                if debug:
                    print(f"      [SKIP] Found {layer_name} in front at {dist:.1f}mm")
                return True

    return False


def draw_perpendicular_for_behind_hit(beam_p1, beam_p2, beams, beam_idx, msp,
                                      behind_hit, color=6, debug=False,
                                      label="Behind"):
    
    if has_l_pline_in_front(beam_p1, beam_p2, behind_hit, msp, debug=debug):
        return 0

    start, perp_dir = get_perpendicular_start_and_direction(
        beam_p1, beam_p2, behind_hit, debug=debug
    )
    if start is None:
        if debug:
            print(f"      [SKIP] {label} line has no overlap with main beam")
        return 0

    is_horizontal = is_horizontal_beam(beam_p1, beam_p2)
    behind_dist = behind_hit["dist"]

    front_dist, _ = find_front_line_in_direction(
        beam_p1, beam_p2, beams, beam_idx, perp_dir, debug=False
    )
    perp_length = 0.2 * front_dist if front_dist else 0.2 * behind_dist

    end = (
        start[0] + perp_dir[0] * perp_length,
        start[1] + perp_dir[1] * perp_length,
    )
    msp.add_line(start, end, dxfattribs=generated_line_attribs(color))
    add_text_for_each_bar(msp, start, end)

    angle_45_len = 100
    if is_horizontal:
        angle_end = (
            end[0] + angle_45_len * 0.707,
            end[1] + angle_45_len * 0.707 if perp_dir[1] > 0 else end[1] - angle_45_len * 0.707,
        )
    else:
        angle_end = (
            end[0] + angle_45_len * 0.707 if perp_dir[0] > 0 else end[0] - angle_45_len * 0.707,
            end[1] - angle_45_len * 0.707,
        )
    msp.add_line(end, angle_end, dxfattribs=generated_line_attribs(color))

    back_len = max(behind_dist - 75, 0)
    back_dir = (-perp_dir[0], -perp_dir[1])
    back_start = (
        start[0] + back_dir[0] * back_len,
        start[1] + back_dir[1] * back_len,
    )
    msp.add_line(back_start, start, dxfattribs=generated_line_attribs(color))

    angle_90_len = 100
    if is_horizontal:
        x_offset = angle_90_len if perp_dir[1] > 0 else angle_90_len
        angle_90_end = (
            back_start[0] + x_offset,
            back_start[1],
        )
    else:
        y_offset = -angle_90_len if perp_dir[0] > 0 else -angle_90_len
        angle_90_end = (
            back_start[0],
            back_start[1] + y_offset,
        )
    msp.add_line(back_start, angle_90_end, dxfattribs=generated_line_attribs(color))


    base = get_perpendicular_dim_base(
    start,
    end,
    perp_dir
)
    

    perp_angle = math.degrees(math.atan2(perp_dir[1], perp_dir[0])) % 180

    dim_perp = msp.add_linear_dim(
        base=base,
        p1=start,
        p2=end,
        angle=perp_angle,
        dxfattribs={"dimstyle": "PERP_DIM"},
    )
    dim_perp.set_tick(50)
    dim_perp.set_dimline_format(color=1)
    dim_perp.set_extline_format(color=1, extension=25, offset=10)
    dim_perp.set_extline1(disable=False)
    dim_perp.set_extline2(disable=False)
    dim_perp.update({"dimclrt": 3})
    dim_perp.render()

    add_beam_spacing_text(
        beams, beam_idx, beam_p1, beam_p2, perp_dir, start, msp,
        perpendicular_length=perp_length,
        perpendicular_ratio=0.2,
    )

    return 1

def generate_perpendiculars_from_behind_hits(beam_p1, beam_p2, beams, beam_idx,
                                             msp, behind_hits, color=6,
                                             debug=False, label="Behind"):
    
    count = 0
    generated_keys = set()

    for behind_hit in behind_hits:
        start, perp_dir = get_perpendicular_start_and_direction(
            beam_p1, beam_p2, behind_hit, debug=False
        )
        if start is None:
            continue

        bx1, by1, bx2, by2 = behind_hit["coords"]
        key = (
            round(start[0], 3),
            round(start[1], 3),
            round(perp_dir[0], 3),
            round(perp_dir[1], 3),
            round(bx1, 1),
            round(by1, 1),
            round(bx2, 1),
            round(by2, 1),
        )
        if key in generated_keys:
            if debug:
                print(f"      [SKIP] Duplicate {label} perpendicular at "
                      f"({start[0]:.1f}, {start[1]:.1f})")
            continue
        generated_keys.add(key)

        if debug:
            print(f"      [PERP {count + 1}] {label}: Side={behind_hit['side']}, "
                  f"Dist={behind_hit['dist']:.1f}mm, "
                  f"Length={behind_hit['line_length']:.1f}mm")

        count += draw_perpendicular_for_behind_hit(
            beam_p1, beam_p2, beams, beam_idx, msp,
            behind_hit, color=color, debug=debug, label=label
        )

    return count


def generate_hidden_perpendiculars_like_find_hidden(beam_p1, beam_p2, beams,
                                                    beam_idx, msp,
                                                    nearest_hits=None,
                                                    debug=False):
    
    if nearest_hits is None:
        nearest_hits = collect_nearest_behind_hits(
            beam_p1, beam_p2, msp,
            line_filter=lambda lt: "HIDDEN" in lt or "DASH" in lt,
            min_distance=BEHIND_MIN_DISTANCE,
            max_distance=BEHIND_MAX_DISTANCE,
            use_size_filter=False,
            label="HIDDEN",
            debug=debug,
        )

    if not nearest_hits:
        return 0

    count = 0
    generated_keys = set()
    is_horizontal = is_horizontal_beam(beam_p1, beam_p2)

    hit_pos = None
    hit_neg = None
    for hit in nearest_hits:
        if hit["side"] in ["ABOVE", "RIGHT"]:
            if hit_pos is None or hit["dist"] < hit_pos["dist"]:
                hit_pos = hit
        if hit["side"] in ["BELOW", "LEFT"]:
            if hit_neg is None or hit["dist"] < hit_neg["dist"]:
                hit_neg = hit

    for behind_hit in nearest_hits:
        if has_l_pline_in_front(beam_p1, beam_p2, behind_hit, msp, debug=debug):
            continue

        start, perp_dir = get_perpendicular_start_and_direction(
            beam_p1, beam_p2, behind_hit, debug=debug
        )
        if start is None:
            continue

        bx1, by1, bx2, by2 = behind_hit["coords"]
        key = (
            round(start[0], 3),
            round(start[1], 3),
            round(perp_dir[0], 3),
            round(perp_dir[1], 3),
            round(bx1, 1),
            round(by1, 1),
            round(bx2, 1),
            round(by2, 1),
        )
        if key in generated_keys:
            if debug:
                print(f"      [SKIP] Duplicate hidden perpendicular at "
                      f"({start[0]:.1f}, {start[1]:.1f})")
            continue
        generated_keys.add(key)

        front_dist, _ = find_front_line_in_direction(
            beam_p1, beam_p2, beams, beam_idx, perp_dir, debug=False
        )
        perp_length = 0.3 * front_dist if front_dist else 0.3 * behind_hit["dist"]

        end = (
            start[0] + perp_dir[0] * perp_length,
            start[1] + perp_dir[1] * perp_length,
        )
        msp.add_line(start, end, dxfattribs=generated_line_attribs(6))
        add_text_for_each_bar(msp, start, end)

        if hit_pos:
            if is_horizontal:
                conn_pos = (start[0], start[1] + hit_pos["dist"])
            else:
                conn_pos = (start[0] + hit_pos["dist"], start[1])
            msp.add_line(start, conn_pos, dxfattribs=generated_line_attribs(6))

        if hit_neg:
            if is_horizontal:
                conn_neg = (start[0], start[1] - hit_neg["dist"])
            else:
                conn_neg = (start[0] - hit_neg["dist"], start[1])
            msp.add_line(start, conn_neg, dxfattribs=generated_line_attribs(6))

        angle_len = 100
        if is_horizontal:
            if perp_dir[1] > 0:
                angle_end = (end[0] + angle_len * 0.707, end[1] + angle_len * 0.707)
            else:
                angle_end = (end[0] + angle_len * 0.707, end[1] - angle_len * 0.707)
        else:
            if perp_dir[0] > 0:
                angle_end = (end[0] + angle_len * 0.707, end[1] - angle_len * 0.707)
            else:
                angle_end = (end[0] - angle_len * 0.707, end[1] - angle_len * 0.707)
        msp.add_line(end, angle_end, dxfattribs=generated_line_attribs(6))

        dim_perp = msp.add_linear_dim(
            base=get_perpendicular_dim_base(start, end, perp_dir),
            p1=start,
            p2=end,
            angle=math.degrees(math.atan2(perp_dir[1], perp_dir[0])) % 180,
            dxfattribs={"dimstyle": "PERP_DIM"},
        )
        dim_perp.set_tick(50)
        dim_perp.set_dimline_format(color=1)
        dim_perp.set_extline_format(color=1, extension=25, offset=10)
        dim_perp.set_extline1(disable=False)
        dim_perp.set_extline2(disable=False)
        dim_perp.update({"dimclrt": 3})
        dim_perp.render()

        add_beam_spacing_text(
            beams, beam_idx, beam_p1, beam_p2, perp_dir, start, msp,
            perpendicular_length=perp_length,
            perpendicular_ratio=0.3,
        )

        count += 1
        if debug:
            print(f"      Generated hidden perpendicular {count} "
                  f"for line length {behind_hit['line_length']:.1f}mm")

    return count


def generate_perpendiculars_for_multiple_mismatched_behind_lines(
        beam_p1, beam_p2, beams, beam_idx, msp,
        min_distance=10, max_distance=450, debug=False):
    
    nearest_hits = collect_nearest_behind_hits(
        beam_p1, beam_p2, msp,
        line_filter=lambda lt: "HIDDEN" in lt or "DASH" in lt,
        min_distance=min_distance,
        max_distance=max_distance,
        use_size_filter=False,
        label="HIDDEN",
        debug=debug,
    )

    if not nearest_hits:
        if debug:
            print(f"      No HIDDEN lines found for mismatched fallback")
        return 0

    perpendicular_count = generate_hidden_perpendiculars_like_find_hidden(
        beam_p1, beam_p2, beams, beam_idx, msp,
        nearest_hits=nearest_hits,
        debug=debug,
    )

    if debug:
        print(f"      Generated {perpendicular_count} perpendicular(s) "
              f"from mismatched hidden behind line(s)")
    return perpendicular_count


def find_hidden_and_generate(p1, p2, beams, beam_idx, msp,
                             min_distance=10, max_distance=450,
                             size_tolerance_percent=0.20):
    
    mx = (p1[0] + p2[0]) / 2
    my = (p1[1] + p2[1]) / 2
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    beam_length = math.hypot(dx, dy)
    size_tolerance = beam_length * size_tolerance_percent
    is_horizontal = abs(dx) > abs(dy)

    if is_horizontal:
        directions = {"ABOVE": (0, 1), "BELOW": (0, -1)}
    else:
        directions = {"RIGHT": (1, 0), "LEFT": (-1, 0)}

    def ray_intersect(px, py, rx, ry, x1, y1, x2, y2):
        dxl = x2 - x1
        dyl = y2 - y1
        denom = rx * dyl - ry * dxl
        if abs(denom) < 1e-6:
            return None
        t = ((x1 - px) * dyl - (y1 - py) * dxl) / denom
        u = ((x1 - px) * ry - (y1 - py) * rx) / denom
        if t < 0 or not (0 <= u <= 1):
            return None
        ix = px + t * rx
        iy = py + t * ry
        if (ix - px) * rx + (iy - py) * ry <= 0:
            return None
        if t < 1e-6:
            return None
        return t

    nearest_side = nearest_dist = nearest_line = None
    hit_pos = hit_neg = None

    for e in msp:
        if e.dxftype() != "LINE":
            continue
        lt = e.dxf.linetype.upper()
        if "HIDDEN" not in lt:
            continue

        x1, y1 = e.dxf.start.x, e.dxf.start.y
        x2, y2 = e.dxf.end.x, e.dxf.end.y
        line_length = math.hypot(x2 - x1, y2 - y1)
        if abs(line_length - beam_length) > size_tolerance:
            continue

        for side, (rx, ry) in directions.items():
            dist = ray_intersect(mx, my, rx, ry, x1, y1, x2, y2)
            if dist is None or not (min_distance <= dist <= max_distance):
                continue
            if side in ["ABOVE", "RIGHT"]:
                if hit_pos is None or dist < hit_pos[0]:
                    hit_pos = (dist, (x1, y1, x2, y2))
            if side in ["BELOW", "LEFT"]:
                if hit_neg is None or dist < hit_neg[0]:
                    hit_neg = (dist, (x1, y1, x2, y2))
            if nearest_dist is None or dist < nearest_dist:
                nearest_dist = dist
                nearest_side = side
                nearest_line = (x1, y1, x2, y2)

    if nearest_side is None:
        return 0

    if is_horizontal:
        perp_dir = (0, -1) if nearest_side == "ABOVE" else (0, 1)
    else:
        perp_dir = (-1, 0) if nearest_side == "RIGHT" else (1, 0)

    front_dist, _ = find_front_line_in_direction(
        p1, p2, beams, beam_idx, perp_dir, debug=False
    )
    perp_length = 0.3 * front_dist if front_dist else 0.3 * nearest_dist

    x1, y1, x2, y2 = nearest_line
    if is_horizontal:
        mx1, mx2 = sorted([p1[0], p2[0]])
        hx1, hx2 = sorted([x1, x2])
        overlap_start = max(mx1, hx1)
        overlap_end = min(mx2, hx2)
        cx = (overlap_start + overlap_end) / 2
        start = (cx, my)
    else:
        my1, my2 = sorted([p1[1], p2[1]])
        hy1, hy2 = sorted([y1, y2])
        overlap_start = max(my1, hy1)
        overlap_end = min(my2, hy2)
        cy = (overlap_start + overlap_end) / 2
        start = (mx, cy)

    end = (start[0] + perp_dir[0] * perp_length,
           start[1] + perp_dir[1] * perp_length)
    msp.add_line(start, end, dxfattribs=generated_line_attribs(6))
    add_text_for_each_bar(msp, start, end)

    if hit_pos:
        pos_dist, _ = hit_pos
        conn_pos = (
            (start[0], start[1] + pos_dist) if is_horizontal
            else (start[0] + pos_dist, start[1])
        )
        msp.add_line(start, conn_pos, dxfattribs=generated_line_attribs(6))

    if hit_neg:
        neg_dist, _ = hit_neg
        conn_neg = (
            (start[0], start[1] - neg_dist) if is_horizontal
            else (start[0] - neg_dist, start[1])
        )
        msp.add_line(start, conn_neg, dxfattribs=generated_line_attribs(6))

    angle_len = 100
    if is_horizontal:
        angle_end = (
            end[0] + angle_len * 0.707,
            end[1] + angle_len * 0.707 if perp_dir[1] > 0 else end[1] - angle_len * 0.707,
        )
    else:
        angle_end = (
            end[0] + angle_len * 0.707 if perp_dir[0] > 0 else end[0] - angle_len * 0.707,
            end[1] - angle_len * 0.707,
        )
    msp.add_line(end, angle_end, dxfattribs=generated_line_attribs(6))
    return 1


def find_front_line_in_direction(beam_p1, beam_p2, beams, beam_idx, perp_dir,
                                 debug=True):
    
    mx, my = get_beam_center(beam_p1, beam_p2)
    is_horizontal = is_horizontal_beam(beam_p1, beam_p2)

    if debug:
        print(f"  Searching for front line in direction: {perp_dir}")

    ray_length = 100000
    ray_end = (mx + perp_dir[0] * ray_length, my + perp_dir[1] * ray_length)

    nearest_dist = nearest_coords = None

    for other_idx, (op1, op2) in enumerate(beams):
        if other_idx == beam_idx:
            continue
        if is_horizontal:
            if abs(op2[1] - op1[1]) > PARALLEL_TOLERANCE:
                continue
        else:
            if abs(op2[0] - op1[0]) > PARALLEL_TOLERANCE:
                continue

        x1, y1 = mx, my
        x2, y2 = ray_end
        x3, y3 = op1
        x4, y4 = op2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 0.0001:
            continue

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

        if t >= 0 and 0 <= u <= 1:
            ix = x1 + t * (x2 - x1)
            iy = y1 + t * (y2 - y1)
            dist = math.hypot(ix - mx, iy - my)
            if dist > 0:
                if nearest_dist is None or dist < nearest_dist:
                    nearest_dist = dist
                    nearest_coords = (op1, op2)
                    if debug:
                        print(f"    Nearest front line: {dist:.1f}mm")

    if debug and nearest_dist is None:
        print(f"  No front line found in direction {perp_dir}")

    return (nearest_dist, nearest_coords)


def get_perpendicular_length_at_endpoint(beam_idx, is_start, beams, ratio=RATIO):
    beam_p = beams[beam_idx]
    beam_length = length(beam_p[0], beam_p[1])
    endpoint = beam_p[0] if is_start else beam_p[1]

    connected_lengths = []
    for other_idx, (ob1, ob2) in enumerate(beams):
        if other_idx == beam_idx:
            continue
        if math.hypot(endpoint[0] - ob1[0], endpoint[1] - ob1[1]) < ENDPOINT_TOLERANCE:
            connected_lengths.append(length(ob1, ob2))
        elif math.hypot(endpoint[0] - ob2[0], endpoint[1] - ob2[1]) < ENDPOINT_TOLERANCE:
            connected_lengths.append(length(ob1, ob2))

    return ratio * max(connected_lengths) if connected_lengths else ratio * beam_length


def get_perpendicular_length_at_endpoint_by_direction(beam_idx, beams,
                                                       is_horizontal,
                                                       ratio=RATIO):
    len1 = get_perpendicular_length_at_endpoint(beam_idx, True, beams, ratio)
    len2 = get_perpendicular_length_at_endpoint(beam_idx, False, beams, ratio)
    return (len1, len2)


def find_nearest_parallel_beam_with_direction(beam_p1, beam_p2, beams,
                                               beam_idx, debug=True):
    mx, my = get_beam_center(beam_p1, beam_p2)
    is_horizontal = is_horizontal_beam(beam_p1, beam_p2)

    beams_pos = []
    beams_neg = []

    for other_idx, (op1, op2) in enumerate(beams):
        if other_idx == beam_idx:
            continue
        if is_horizontal:
            if abs(op2[1] - op1[1]) > PARALLEL_TOLERANCE:
                continue
            other_c = (op1[1] + op2[1]) / 2
            dist = abs(other_c - my)
            (beams_pos if other_c > my else beams_neg).append(
                (dist, other_c, (op1, op2), other_idx)
            )
        else:
            if abs(op2[0] - op1[0]) > PARALLEL_TOLERANCE:
                continue
            other_c = (op1[0] + op2[0]) / 2
            dist = abs(other_c - mx)
            (beams_pos if other_c > mx else beams_neg).append(
                (dist, other_c, (op1, op2), other_idx)
            )

    beams_pos.sort(key=lambda x: x[0])
    beams_neg.sort(key=lambda x: x[0])

    pos_label = "ABOVE" if is_horizontal else "RIGHT"
    neg_label = "BELOW" if is_horizontal else "LEFT"

    if beams_pos and beams_neg:
        if beams_pos[0][0] <= beams_neg[0][0]:
            nd, _, nc, _ = beams_pos[0]
            return (nd, pos_label, nc, False)
        else:
            nd, _, nc, _ = beams_neg[0]
            return (nd, neg_label, nc, False)
    elif beams_pos:
        nd, _, nc, _ = beams_pos[0]
        return (nd, pos_label, nc, True)
    elif beams_neg:
        nd, _, nc, _ = beams_neg[0]
        return (nd, neg_label, nc, True)
    else:
        return (None, None, None, True)


def generate_perpendiculars(beams, msp):
    
    perp_count = 0
    with_behind_count = 0
    without_behind_count = 0
    front_line_count = 0
    fallback_front_line_count = 0

    for beam_idx, (p1, p2) in enumerate(beams):
        mx, my = get_beam_center(p1, p2)
        is_horizontal = is_horizontal_beam(p1, p2)
        beam_length = length(p1, p2)

        print(f"\n{'='*60}")
        print(f"BEAM {beam_idx}")
        print(f"  Center: ({mx:.1f}, {my:.1f})  Length: {beam_length:.1f}mm  "
              f"{'HORIZONTAL' if is_horizontal else 'VERTICAL'}")

        behind_hits = find_behind_line(p1, p2, beams, beam_idx, msp, debug=True)

        if behind_hits:
            with_behind_count += 1
            beam_perp_count = 0

            for behind_hit in behind_hits:
                behind_side = behind_hit["side"]
                behind_dist = behind_hit["dist"]

                if is_horizontal:
                    perp_dir = (0, -1) if behind_side == "ABOVE" else (0, 1)
                else:
                    perp_dir = (-1, 0) if behind_side == "RIGHT" else (1, 0)

                front_dist, _ = find_front_line_in_direction(
                    p1, p2, beams, beam_idx, perp_dir, debug=False
                )
                if front_dist:
                    tick_len = RATIO * front_dist
                    front_line_count += 1
                else:
                    t1, t2 = get_perpendicular_length_at_endpoint_by_direction(
                        beam_idx, beams, is_horizontal
                    )
                    tick_len = (t1 + t2) / 2

                drawn = draw_perpendicular_for_behind_hit(
                    p1, p2, beams, beam_idx, msp,
                    behind_hit, color=6, debug=False, label="WALL"
                )
                perp_count += drawn
                beam_perp_count += drawn

            print(f"  Drew {beam_perp_count} perpendicular(s) from {len(behind_hits)} behind hit(s)")

        else:
            without_behind_count += 1
            print(f"  No behind line found â€” using fallback")

            nearest_dist, nearest_side, nearest_coords, is_outer = \
                find_nearest_parallel_beam_with_direction(p1, p2, beams, beam_idx, debug=False)

            if nearest_side:
                if is_horizontal:
                    perp_dir = (0, 1) if nearest_side == "ABOVE" else (0, -1)
                else:
                    perp_dir = (1, 0) if nearest_side == "RIGHT" else (-1, 0)

                front_dist, _ = find_front_line_in_direction(
                    p1, p2, beams, beam_idx, perp_dir, debug=False
                )
                tick_len = (RATIO * front_dist if front_dist
                            else RATIO * nearest_dist)
                if front_dist:
                    fallback_front_line_count += 1
                color = 3
            else:
                perp_dir = (0, 1) if is_horizontal else (1, 0)
                front_dist, _ = find_front_line_in_direction(
                    p1, p2, beams, beam_idx, perp_dir, debug=False
                )
                if front_dist:
                    tick_len = RATIO * front_dist
                else:
                    t1, t2 = get_perpendicular_length_at_endpoint_by_direction(
                        beam_idx, beams, is_horizontal
                    )
                    tick_len = (t1 + t2) / 2
                color = 3

            p_start = (mx, my)
            p_end = (mx + perp_dir[0] * tick_len, my + perp_dir[1] * tick_len)
            msp.add_line(p_start, p_end, dxfattribs=generated_line_attribs(color))
            add_text_for_each_bar(msp, p_start, p_end)

            angle_45_len = 100
            if is_horizontal:
                p_angle_end = (
                    p_end[0] + angle_45_len * 0.707,
                    p_end[1] + angle_45_len * 0.707 if perp_dir[1] > 0
                    else p_end[1] - angle_45_len * 0.707,
                )
            else:
                p_angle_end = (
                    p_end[0] + angle_45_len * 0.707 if perp_dir[0] > 0
                    else p_end[0] - angle_45_len * 0.707,
                    p_end[1] - angle_45_len * 0.707,
                )
            msp.add_line(p_end, p_angle_end, dxfattribs=generated_line_attribs(color))

            back_len = 100
            back_dir = (-perp_dir[0], -perp_dir[1])
            p_back_start = (mx + back_dir[0] * back_len, my + back_dir[1] * back_len)
            msp.add_line(p_back_start, p_start, dxfattribs=generated_line_attribs(color))

            angle_90_len = 100
            if is_horizontal:
                p_90_end = (
                    p_back_start[0] - angle_90_len if perp_dir[1] > 0
                    else p_back_start[0] + angle_90_len,
                    p_back_start[1],
                )
            else:
                p_90_end = (
                    p_back_start[0],
                    p_back_start[1] - angle_90_len if perp_dir[0] > 0
                    else p_back_start[1] + angle_90_len,
                )
            msp.add_line(p_back_start, p_90_end, dxfattribs=generated_line_attribs(color))

            dim_perp = msp.add_linear_dim(
                base=get_perpendicular_dim_base(p_start, p_end, perp_dir),
                p1=p_start,
                p2=p_end,
                angle=math.degrees(math.atan2(perp_dir[1], perp_dir[0])) % 180,
                dxfattribs={"dimstyle": "PERP_DIM"},
            )
            dim_perp.set_tick(50)
            dim_perp.set_dimline_format(color=1)
            dim_perp.set_extline_format(color=1, extension=25, offset=10)
            dim_perp.set_extline1(disable=False)
            dim_perp.set_extline2(disable=False)
            dim_perp.update({"dimclrt": 3})
            dim_perp.render()
            perp_count += 1

    print(f"\n{'='*60}")
    print(f"SUMMARY (generate_perpendiculars)")
    print(f"  Total perpendiculars: {perp_count}")
    print(f"  With behind line: {with_behind_count}")
    print(f"  Without behind line (fallback): {without_behind_count}")
    print(f"{'='*60}")
    return perp_count


def find_behind_line(beam_p1, beam_p2, beams, beam_idx, msp,
                     min_distance=10, max_distance=450,
                     size_tolerance_percent=None,
                     debug=False):
    
    if size_tolerance_percent is None:
        size_tolerance_percent = WALL_SIZE_TOLERANCE_PERCENT

    return collect_nearest_behind_hits(
        beam_p1, beam_p2, msp,
        line_filter=lambda lt: lt in ["BYLAYER", "CONTINUOUS"],
        min_distance=min_distance,
        max_distance=max_distance,
        size_tolerance_percent=size_tolerance_percent,
        use_size_filter=True,
        layer_filter=lambda layer: layer.upper().replace("_", " ") == TARGET_LAYER.upper().replace("_", " "),
        label="WALL",
        debug=debug,
    )


def setup_dimstyle(doc):
    
   
    if "EZDXF" not in doc.dimstyles:
        dimstyle = doc.dimstyles.new("EZDXF")
    else:
        dimstyle = doc.dimstyles.get("EZDXF")

    dimstyle.dxf.dimtxt = 50
    dimstyle.dxf.dimasz = 50
    dimstyle.dxf.dimexe = 0
    dimstyle.dxf.dimse1 = 0
    dimstyle.dxf.dimse2 = 0
    dimstyle.dxf.dimexo = 2
    dimstyle.dxf.dimgap = 8
    dimstyle.dxf.dimclrd = 1
    dimstyle.dxf.dimclre = 1
    dimstyle.dxf.dimclrt = 1

    if "PERP_DIM" not in doc.dimstyles:
        perp_dimstyle = doc.dimstyles.new("PERP_DIM")
    else:
        perp_dimstyle = doc.dimstyles.get("PERP_DIM")

    perp_dimstyle.dxf.dimtsz = 50
    perp_dimstyle.dxf.dimasz = 50

    perp_dimstyle.dxf.dimse1 = 0
    perp_dimstyle.dxf.dimse2 = 0
    perp_dimstyle.dxf.dimexo = 10
    perp_dimstyle.dxf.dimexe = 25

    perp_dimstyle.dxf.dimtxt  = 50
    perp_dimstyle.dxf.dimgap  = 8
    perp_dimstyle.dxf.dimtad  = 1
    perp_dimstyle.dxf.dimjust = 0

    perp_dimstyle.dxf.dimclrd = 1
    perp_dimstyle.dxf.dimclre = 1
    perp_dimstyle.dxf.dimclrt = 3

    return dimstyle

def add_beam_spacing_text(
        beams,
        beam_idx,
        p1,
        p2,
        perp_dir,
        start,
        msp,
        perpendicular_length=None,
        perpendicular_ratio=None,
        text_template="T8@200C/C"
):
    
    
    from ezdxf.enums import TextEntityAlignment

    is_horizontal = is_horizontal_beam(p1, p2)
    rx, ry = perp_dir

    if is_horizontal:
        main_min  = min(p1[0], p2[0])
        main_max  = max(p1[0], p2[0])
        main_axis = (p1[1] + p2[1]) / 2
    else:
        main_min  = min(p1[1], p2[1])
        main_max  = max(p1[1], p2[1])
        main_axis = (p1[0] + p2[0]) / 2

    beam_span = main_max - main_min
    if beam_span < 1.0:
        return

    max_spacing_distance = None
    if perpendicular_length is not None and perpendicular_ratio:
        max_spacing_distance = perpendicular_length / perpendicular_ratio

    sample_min = main_min
    sample_max = main_max

    candidates = []
    for other_idx, (op1, op2) in enumerate(beams):
        if other_idx == beam_idx:
            continue

        if is_horizontal:
            if abs(op2[1] - op1[1]) > PARALLEL_TOLERANCE:
                continue
            other_axis = (op1[1] + op2[1]) / 2
            if ry > 0 and other_axis <= main_axis:
                continue
            if ry < 0 and other_axis >= main_axis:
                continue
            other_min = min(op1[0], op2[0])
            other_max = max(op1[0], op2[0])
        else:
            if abs(op2[0] - op1[0]) > PARALLEL_TOLERANCE:
                continue
            other_axis = (op1[0] + op2[0]) / 2
            if rx > 0 and other_axis <= main_axis:
                continue
            if rx < 0 and other_axis >= main_axis:
                continue
            other_min = min(op1[1], op2[1])
            other_max = max(op1[1], op2[1])

        if other_max <= sample_min or other_min >= sample_max:
            continue

        spacing = abs(other_axis - main_axis)
        if max_spacing_distance is not None and spacing > max_spacing_distance + 1.0:
            continue

        candidates.append({
            "idx":        other_idx,
            "other_min":  other_min,
            "other_max":  other_max,
            "other_axis": other_axis,
            "spacing":    spacing,
        })

    if not candidates:
        return

    sample_span = sample_max - sample_min
    NUM_SAMPLES = max(20, int(sample_span / 5))
    step        = sample_span / NUM_SAMPLES

    sample_hits   = []
    sample_coords = []

    for i in range(NUM_SAMPLES + 1):
        along = sample_min + i * step
        sample_coords.append(along)

        best_idx     = None
        best_spacing = None
        for c in candidates:
            if tuple(sorted((beam_idx, c["idx"]))) in _spacing_text_drawn:
                continue
            if along < c["other_min"] - 1.0 or along > c["other_max"] + 1.0:
                continue
            if best_spacing is None or c["spacing"] < best_spacing:
                best_idx     = c["idx"]
                best_spacing = c["spacing"]

        sample_hits.append(best_idx)

    groups = []
    i = 0
    n = len(sample_hits)
    while i < n:
        other_idx = sample_hits[i]
        if other_idx is None:
            i += 1
            continue
        j = i
        while j < n and sample_hits[j] == other_idx:
            j += 1
        groups.append({
            "other_idx": other_idx,
            "range_min": sample_coords[i],
            "range_max": sample_coords[j - 1],
        })
        i = j

    if not groups:
        return

    idx_to_c = {c["idx"]: c for c in candidates}
    for g in groups:
        c = idx_to_c.get(g["other_idx"])
        if c:
            g["spacing"]    = c["spacing"]
            g["other_axis"] = c["other_axis"]

    DIM_OFFSET = 120
    ARROW_INSET = 100

    for g in groups:
        if "spacing" not in g:
            continue

        other_idx = g["other_idx"]
        dedup_key = tuple(sorted((beam_idx, other_idx)))
        if dedup_key in _spacing_text_drawn:
            continue

        spacing   = g["spacing"]
        range_min = g["range_min"]
        range_max = g["range_max"]
        range_mid = (range_min + range_max) / 2

        if is_horizontal:
            p_main    = (range_mid, main_axis)
            p_opp     = (range_mid, g["other_axis"])
            dim_base  = (range_mid + DIM_OFFSET, (main_axis + g["other_axis"]) / 2)
            dim_angle = 90

            arrow_inset = min(ARROW_INSET, max((spacing / 2) - 1, 0))
            axis_sign = 1 if g["other_axis"] > main_axis else -1
            dim_p1 = (p_main[0], p_main[1] + axis_sign * arrow_inset)
            dim_p2 = (p_opp[0], p_opp[1] - axis_sign * arrow_inset)
        else:
            p_main    = (main_axis, range_mid)
            p_opp     = (g["other_axis"], range_mid)
            dim_base  = ((main_axis + g["other_axis"]) / 2, range_mid + DIM_OFFSET)
            dim_angle = 0

            arrow_inset = min(ARROW_INSET, max((spacing / 2) - 1, 0))
            axis_sign = 1 if g["other_axis"] > main_axis else -1
            dim_p1 = (p_main[0] + axis_sign * arrow_inset, p_main[1])
            dim_p2 = (p_opp[0] - axis_sign * arrow_inset, p_opp[1])

        _spacing_text_drawn.add(dedup_key)

        try:
            dim = msp.add_linear_dim(
                base  = dim_base,
                p1    = dim_p1,
                p2    = dim_p2,
                angle = dim_angle,
                text  = text_template,
                dxfattribs={"dimstyle": "SPACING_DIM"},
            )
            dim.set_dimline_format(color=1)
            dim.set_extline_format(color=1, extension=25, offset=10)
            dim.set_extline1(disable=False)
            dim.set_extline2(disable=False)
            dim.update({"dimclrt": 3})
            dim.render()
        except Exception as exc:
            print(f"      [SPACING DIM] Could not add dimension with text: {exc}")

def setup_dimstyle(doc):
    
    if "EZDXF" not in doc.dimstyles:
        dimstyle = doc.dimstyles.new("EZDXF")
    else:
        dimstyle = doc.dimstyles.get("EZDXF")

    dimstyle.dxf.dimtxt = 50
    dimstyle.dxf.dimasz = 50
    dimstyle.dxf.dimexe = 0
    dimstyle.dxf.dimse1 = 0
    dimstyle.dxf.dimse2 = 0
    dimstyle.dxf.dimexo = 2
    dimstyle.dxf.dimgap = 8
    dimstyle.dxf.dimclrd = 1
    dimstyle.dxf.dimclre = 1
    dimstyle.dxf.dimclrt = 1

    if "PERP_DIM" not in doc.dimstyles:
        perp_dimstyle = doc.dimstyles.new("PERP_DIM")
    else:
        perp_dimstyle = doc.dimstyles.get("PERP_DIM")

    perp_dimstyle.dxf.dimtsz = 50
    perp_dimstyle.dxf.dimasz = 50
    perp_dimstyle.dxf.dimse1 = 0
    perp_dimstyle.dxf.dimse2 = 0
    perp_dimstyle.dxf.dimexo = 10
    perp_dimstyle.dxf.dimexe = 25
    perp_dimstyle.dxf.dimtxt = 50
    perp_dimstyle.dxf.dimgap = 8
    perp_dimstyle.dxf.dimtad = 1
    perp_dimstyle.dxf.dimjust = 0
    perp_dimstyle.dxf.dimclrd = 1
    perp_dimstyle.dxf.dimclre = 1
    perp_dimstyle.dxf.dimclrt = 3

    if "SPACING_DIM" not in doc.dimstyles:
        spacing_dimstyle = doc.dimstyles.new("SPACING_DIM")
    else:
        spacing_dimstyle = doc.dimstyles.get("SPACING_DIM")

    spacing_dimstyle.dxf.dimtsz = 0
    spacing_dimstyle.dxf.dimasz = 50
    
    spacing_dimstyle.dxf.dimse1 = 0
    spacing_dimstyle.dxf.dimse2 = 0
    spacing_dimstyle.dxf.dimexo = 10
    spacing_dimstyle.dxf.dimexe = 25
    
    spacing_dimstyle.dxf.dimtxt = 50
    spacing_dimstyle.dxf.dimgap = 8
    spacing_dimstyle.dxf.dimtad = 1
    spacing_dimstyle.dxf.dimjust = 0
    
    spacing_dimstyle.dxf.dimclrd = 1
    spacing_dimstyle.dxf.dimclre = 1
    spacing_dimstyle.dxf.dimclrt = 3

    return dimstyle
def run_dxf_processing(doc, params):
    # Update configuration from streamlit params
    update_globals(params)
    
    print("=" * 60)
    print("DXF BEAM PERPENDICULAR GENERATOR (RUNNING)")
    print("=" * 60)
    
    dimstyle = setup_dimstyle(doc)
    msp = doc.modelspace()
    beams = extract_beams(msp)
    print(f"\nDetected {len(beams)} target beam segments on layer '{TARGET_LAYER}'")

    if len(beams) == 0:
        print("No beams found! Check layer name and linetype (DASH/HIDDEN).")
        return doc, {
            "total_beams": 0,
            "total_perps": 0,
            "bylayer_count": 0,
            "hidden_count": 0,
            "skipped_count": 0
        }

    perp_count = 0
    bylayer_count = 0
    hidden_count = 0

    for beam_idx, (p1, p2) in enumerate(beams):
        mx, my = get_beam_center(p1, p2)
        is_horizontal = is_horizontal_beam(p1, p2)
        beam_length = length(p1, p2)

        show_debug = beam_idx < 5

        if beam_idx < 10 or beam_idx % 50 == 0:
            print(f"\nBEAM {beam_idx} / {len(beams)}")
            if show_debug:
                print(f"   Center: ({mx:.1f}, {my:.1f}), "
                      f"Length: {beam_length:.1f}mm, "
                      f"Horizontal: {is_horizontal}")

        wall_hits = collect_nearest_behind_hits(
            p1, p2, msp,
            line_filter=lambda lt: lt in ["BYLAYER", "CONTINUOUS"],
            min_distance=BEHIND_MIN_DISTANCE,
            max_distance=BEHIND_MAX_DISTANCE,
            use_size_filter=False,
            layer_filter=lambda layer: layer.upper().replace("_", " ") == TARGET_LAYER.upper().replace("_", " "),
            label="WALL",
            debug=show_debug,
        )

        walls_generated = 0
        if wall_hits:
            walls_generated = generate_perpendiculars_from_behind_hits(
                p1, p2, beams, beam_idx, msp,
                wall_hits, color=6, debug=show_debug, label="WALL"
            )
            if walls_generated > 0:
                perp_count += walls_generated
                bylayer_count += 1
                if show_debug:
                    print(f"   Generated {walls_generated} perpendicular(s) from WALLS")

        hidden_hits = collect_nearest_behind_hits(
            p1, p2, msp,
            line_filter=lambda lt: "HIDDEN" in lt or "DASH" in lt,
            min_distance=BEHIND_MIN_DISTANCE,
            max_distance=BEHIND_MAX_DISTANCE,
            use_size_filter=False,
            label="HIDDEN",
            debug=show_debug,
        )

        if hidden_hits:
            hidden_generated = generate_hidden_perpendiculars_like_find_hidden(
                p1, p2, beams, beam_idx, msp,
                nearest_hits=hidden_hits,
                debug=show_debug,
            )
            if hidden_generated > 0:
                perp_count += hidden_generated
                hidden_count += 1
                if show_debug:
                    print(f"   Generated {hidden_generated} perpendicular(s) from HIDDEN lines")
        else:
            if show_debug:
                print(f"   No hidden lines found — trying legacy find_hidden_and_generate")
            legacy_generated = find_hidden_and_generate(p1, p2, beams, beam_idx, msp)
            if legacy_generated > 0:
                perp_count += legacy_generated
                hidden_count += 1

    skipped = len(beams) - bylayer_count - hidden_count
    
    print(f"\n{'='*60}")
    print(f"FINAL SUMMARY")
    print(f"{'='*60}")
    print(f"  Total beams processed:          {len(beams)}")
    print(f"  Total perpendiculars generated: {perp_count}")
    print(f"  From BYLAYER walls:             {bylayer_count} beams")
    print(f"  From HIDDEN lines:              {hidden_count} beams")
    print(f"  Skipped (no hits):              {skipped} beams")
    print(f"{'='*60}")
    print("\nDONE!")
    
    return doc, {
        "total_beams": len(beams),
        "total_perps": perp_count,
        "bylayer_count": bylayer_count,
        "hidden_count": hidden_count,
        "skipped_count": skipped
    }

if __name__ == "__main__":
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

    print("=" * 60)
    print("DXF BEAM PERPENDICULAR GENERATOR (CLI)")
    print("=" * 60)
    print(f"Input file:  {input_path}")
    print(f"Output file: {output_path}")
    print("=" * 60)

    try:
        doc = safe_read_dxf(input_path)
    except Exception as e:
        print(f"Failed to read DXF file: {e}")
        exit()

    fix_linetypes(doc)
    processed_doc, stats = run_dxf_processing(doc, {})
    processed_doc.saveas(output_path)
    print(f"\nDONE! Saved to: {output_path}")


