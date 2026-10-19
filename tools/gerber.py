"""Minimal Gerber X2 reader for the Proteus CADCAM files (stdlib only).

Covers what Proteus 8.12 writes: %FSLAX45Y45*%, %MOMM*%, G01 linear interpolation only
(G02/G03 are rejected), D01 draws, D02 moves, D03 flashes, G36/G37 regions with several
contours, %LPD*% / %LPC*% polarity, standard C/R apertures, and the PPAD aperture macros
(a single outline primitive, code 4). The aperture function comes from the preceding
%TA.AperFunction,...*% attribute.

Coordinates are returned in mm in the Gerber frame (= IPC frame, Y up).

parse(path) -> Gerber with
  apertures {dcode: Aperture(shape, params, function, outline)}
  objects   [Draw | Flash | Region] in file order, each with .dark (polarity)
"""
import re
from dataclasses import dataclass, field


@dataclass
class Aperture:
    dcode: int
    shape: str            # C, R, or a macro name
    params: tuple         # C: (d,), R: (w, h)
    function: str         # e.g. "Conductor", "ViaPad", "ComponentPad", "SMDPad,CuDef"
    outline: list = None  # macro outline points (mm, relative to the flash point)

    @property
    def diameter(self):
        return self.params[0] if self.shape == "C" else None


@dataclass
class Draw:
    ap: Aperture
    x1: float
    y1: float
    x2: float
    y2: float
    dark: bool


@dataclass
class Flash:
    ap: Aperture
    x: float
    y: float
    dark: bool


@dataclass
class Region:
    contours: list        # [[(x, y), ...], ...] closed (first point == last point)
    dark: bool


@dataclass
class Gerber:
    path: str
    attributes: dict = field(default_factory=dict)
    apertures: dict = field(default_factory=dict)
    objects: list = field(default_factory=list)

    def of(self, kind):
        return [o for o in self.objects if isinstance(o, kind)]


_COORD = re.compile(r"([XYIJ])([+-]?\d+)")


def parse(path):
    with open(path) as f:
        text = f.read()
    g = Gerber(path)
    # split into extended (%...%) blocks and plain word commands
    tokens = re.findall(r"%[^%]*%|[^%*\s][^*]*\*", text)
    scale = None
    func = ""
    macros = {}
    cur_ap = None
    x = y = 0.0
    dark = True
    in_region = False
    contour = None
    region = None
    for tok in tokens:
        if tok.startswith("%"):
            body = tok[1:-1]
            if body.startswith("FS"):
                m = re.match(r"FSLAX(\d)(\d)Y(\d)(\d)\*", body)
                if not m:
                    raise ValueError(f"{path}: unsupported format {body}")
                scale = 10 ** -int(m.group(2))
            elif body.startswith("MO"):
                if body != "MOMM*":
                    raise ValueError(f"{path}: unsupported units {body}")
            elif body.startswith("TF."):
                k, _, v = body[3:-1].partition(",")
                g.attributes[k] = v
            elif body.startswith("TA.AperFunction"):
                func = body[len("TA.AperFunction,"):-1]
            elif body.startswith("TD"):
                func = ""
            elif body.startswith("LP"):
                dark = body[2] == "D"
            elif body.startswith("AM"):
                name, _, rest = body[2:].partition("*")
                nums = [float(t) for t in re.findall(r"[+-]?\d+\.?\d*", rest)]
                # primitive 4: 4, exposure, n, x0, y0, ..., xn, yn, rotation
                if not nums or nums[0] != 4:
                    raise ValueError(f"{path}: unsupported macro {name}")
                n = int(nums[2])
                pts = [(nums[3 + 2 * i], nums[4 + 2 * i]) for i in range(n + 1)]
                if nums[3 + 2 * (n + 1)] != 0:
                    raise ValueError(f"{path}: rotated macro {name}")
                macros[name] = pts
            elif body.startswith("AD"):
                m = re.match(r"ADD(\d+)([A-Za-z_][A-Za-z0-9_]*)(?:,([^*]*))?\*", body)
                d, shape = int(m.group(1)), m.group(2)
                params = tuple(float(p) for p in m.group(3).split("X")) if m.group(3) else ()
                ap = Aperture(d, shape, params, func)
                if shape not in ("C", "R"):
                    ap.outline = macros[shape]
                g.apertures[d] = ap
            continue
        w = tok[:-1]
        if w.startswith("G04") or not w:
            continue
        if w == "M02":
            break
        if w in ("G01", "G1"):
            continue
        if w in ("G02", "G03", "G75", "G74"):
            raise ValueError(f"{path}: arcs not supported ({w})")
        if w == "G36":
            in_region, region, contour = True, Region([], dark), None
            continue
        if w == "G37":
            if contour and len(contour) > 1:
                region.contours.append(contour)
            g.objects.append(region)
            in_region, region, contour = False, None, None
            continue
        m = re.fullmatch(r"D(\d+)", w)
        if m and int(m.group(1)) >= 10:
            cur_ap = g.apertures[int(m.group(1))]
            continue
        m = re.fullmatch(r"((?:[XYIJ][+-]?\d+)*)D0?([123])", w)
        if not m:
            raise ValueError(f"{path}: unsupported command {w!r}")
        nx, ny = x, y
        for c, v in _COORD.findall(m.group(1)):
            if c == "X":
                nx = round(int(v) * scale, 6)
            elif c == "Y":
                ny = round(int(v) * scale, 6)
        op = m.group(2)
        if in_region:
            if op == "2":
                if contour and len(contour) > 1:
                    region.contours.append(contour)
                contour = [(nx, ny)]
            elif op == "1":
                contour.append((nx, ny))
            else:
                raise ValueError(f"{path}: flash inside region")
        elif op == "1":
            g.objects.append(Draw(cur_ap, x, y, nx, ny, dark))
        elif op == "3":
            g.objects.append(Flash(cur_ap, nx, ny, dark))
        x, y = nx, ny
    return g
