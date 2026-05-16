"""pygame-inspired drawing API for slide-games.

Coordinates use a 1920 × 1080 virtual pixel space mapped to the full slide
canvas.  Import these helpers to build custom games with hand-drawn visuals
instead of (or on top of) the default grid renderer.

Reserved area: the bottom ~160 virtual pixels (y > 920) are used by the
automatic D-pad navigation buttons — keep game content above that line.

Example::

    from slide_games import BaseGame, Color, Rect, Surface, draw, Vector2

    class MyGame(BaseGame):
        def render(self, surface, state):
            surface.fill(Color(20, 20, 60))
            draw.circle(surface, Color(255, 215, 0),
                        (state.x * 120 + 100, state.y * 120 + 100), 50)
            draw.text(surface, f"Moves: {state.moves}",
                      Rect(10, 10, 400, 60), color=Color(255, 255, 255))
            draw.progress_bar(surface, Rect(10, 80, 300, 20),
                              state.health, 100, GREEN, DARK_GRAY)
"""

from __future__ import annotations

import math
import uuid

# Slide canvas dimensions in EMU (Google Slides 16:9 default — never changes)
_SLIDE_W_EMU = 9_144_000
_SLIDE_H_EMU = 5_143_500

# Virtual canvas — 1920 × 1080 "pixels" intuitive for game developers
SCREEN_W = 1920
SCREEN_H = 1080

# Bottom of the safe drawing area; D-pad lives below this line
NAV_RESERVED_Y = 820


def _px_x(x: float) -> int:
    return round(x * _SLIDE_W_EMU / SCREEN_W)


def _px_y(y: float) -> int:
    return round(y * _SLIDE_H_EMU / SCREEN_H)


def _px_w(w: float) -> int:
    return max(round(w * _SLIDE_W_EMU / SCREEN_W), 1)


def _px_h(h: float) -> int:
    return max(round(h * _SLIDE_H_EMU / SCREEN_H), 1)


def _uid() -> str:
    return f"g{uuid.uuid4().hex[:14]}"


# ── Color ──────────────────────────────────────────────────────────────────────


class Color:
    """RGB(A) colour, mirroring :class:`pygame.Color`.

    Usage::

        Color(255, 128, 0)              # orange
        Color(255, 128, 0, 200)         # orange, semi-transparent (alpha visual-only)
        Color.from_hex("#ff8000")       # same orange from hex string
        RED.darken(0.5)                 # dark red
        RED.lerp(BLUE, 0.5)             # purple
    """

    def __init__(self, r: int, g: int, b: int, a: int = 255):
        self.r = int(r) & 0xFF
        self.g = int(g) & 0xFF
        self.b = int(b) & 0xFF
        self.a = int(a) & 0xFF

    @classmethod
    def from_hex(cls, hex_str: str) -> Color:
        """Parse a CSS hex string like ``"#ff8000"`` or ``"ff8000"``."""
        h = hex_str.lstrip("#")
        return cls(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    # ── colour math (pygame.Color-style) ────────────────────────────────────

    def lerp(self, other: Color, t: float) -> Color:
        """Linear interpolation towards *other*.  t=0 → self, t=1 → other."""
        t = max(0.0, min(1.0, t))
        return Color(
            round(self.r + (other.r - self.r) * t),
            round(self.g + (other.g - self.g) * t),
            round(self.b + (other.b - self.b) * t),
        )

    def darken(self, factor: float) -> Color:
        """Return a darker shade.  factor 0 → black, 1 → unchanged."""
        f = max(0.0, min(1.0, factor))
        return Color(round(self.r * f), round(self.g * f), round(self.b * f))

    def lighten(self, factor: float) -> Color:
        """Return a lighter shade.  factor 0 → unchanged, 1 → white."""
        f = max(0.0, min(1.0, factor))
        return Color(
            round(self.r + (255 - self.r) * f),
            round(self.g + (255 - self.g) * f),
            round(self.b + (255 - self.b) * f),
        )

    def with_alpha(self, a: int) -> Color:
        """Return a copy with a different alpha value (0–255)."""
        return Color(self.r, self.g, self.b, int(a) & 0xFF)

    def grayscale(self) -> Color:
        """Return the luminance-weighted greyscale equivalent."""
        lum = round(0.299 * self.r + 0.587 * self.g + 0.114 * self.b)
        return Color(lum, lum, lum)

    def complementary(self) -> Color:
        """Return the complementary colour (hue rotated 180°)."""
        return Color(255 - self.r, 255 - self.g, 255 - self.b)

    # ── internals ────────────────────────────────────────────────────────────

    def _rgb(self) -> dict:
        return {"red": self.r / 255, "green": self.g / 255, "blue": self.b / 255}

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Color)
            and self.r == other.r
            and self.g == other.g
            and self.b == other.b
            and self.a == other.a
        )

    def __repr__(self) -> str:
        return f"Color({self.r}, {self.g}, {self.b})"


# ── Named colours ──────────────────────────────────────────────────────────────
# Core set (matching common pygame names)
BLACK = Color(0, 0, 0)
WHITE = Color(255, 255, 255)
RED = Color(220, 30, 30)
GREEN = Color(0, 200, 0)
BLUE = Color(30, 30, 220)
YELLOW = Color(255, 220, 0)
CYAN = Color(0, 220, 220)
MAGENTA = Color(220, 0, 220)
ORANGE = Color(255, 140, 0)
PURPLE = Color(128, 0, 128)
GRAY = Color(128, 128, 128)
LIGHT_GRAY = Color(200, 200, 200)
DARK_GRAY = Color(64, 64, 64)

# Extended palette (CSS / pygame extended colours)
GOLD = Color(255, 215, 0)
SILVER = Color(192, 192, 192)
BROWN = Color(139, 69, 19)
PINK = Color(255, 182, 193)
HOT_PINK = Color(255, 105, 180)
DEEP_PINK = Color(255, 20, 147)
NAVY = Color(0, 0, 128)
TEAL = Color(0, 128, 128)
MAROON = Color(128, 0, 0)
OLIVE = Color(128, 128, 0)
LIME = Color(0, 255, 0)
AQUA = Color(0, 255, 255)
FUCHSIA = Color(255, 0, 255)
CORAL = Color(255, 127, 80)
SALMON = Color(250, 128, 114)
TOMATO = Color(255, 99, 71)
VIOLET = Color(238, 130, 238)
INDIGO = Color(75, 0, 130)
CRIMSON = Color(220, 20, 60)
KHAKI = Color(240, 230, 140)
ORCHID = Color(218, 112, 214)
TURQUOISE = Color(64, 224, 208)
CHOCOLATE = Color(210, 105, 30)
TAN = Color(210, 180, 140)
SKY_BLUE = Color(135, 206, 235)
SLATE_GRAY = Color(112, 128, 144)
MINT = Color(152, 255, 152)


# ── Rect ───────────────────────────────────────────────────────────────────────


class Rect:
    """Axis-aligned rectangle in virtual pixel coordinates, mirroring :class:`pygame.Rect`.

    Usage::

        Rect(100, 200, 400, 300)            # x, y, width, height
        Rect(100, 200, 400, 300).center     # → (300, 350)
        Rect(0, 0, 200, 100).scale_by(0.5) # → Rect(50, 25, 100, 50)
    """

    def __init__(self, x: float, y: float, width: float, height: float):
        self.x = x
        self.y = y
        self.width = width
        self.height = height

    # ── positional properties (pygame.Rect-compatible) ───────────────────────
    @property
    def left(self) -> float:
        return self.x

    @property
    def top(self) -> float:
        return self.y

    @property
    def right(self) -> float:
        return self.x + self.width

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @property
    def centerx(self) -> float:
        return self.x + self.width / 2

    @property
    def centery(self) -> float:
        return self.y + self.height / 2

    @property
    def center(self) -> tuple[float, float]:
        return (self.centerx, self.centery)

    @property
    def size(self) -> tuple[float, float]:
        return (self.width, self.height)

    @property
    def topleft(self) -> tuple[float, float]:
        return (self.x, self.y)

    @property
    def topright(self) -> tuple[float, float]:
        return (self.right, self.y)

    @property
    def bottomleft(self) -> tuple[float, float]:
        return (self.x, self.bottom)

    @property
    def bottomright(self) -> tuple[float, float]:
        return (self.right, self.bottom)

    @property
    def midleft(self) -> tuple[float, float]:
        return (self.x, self.centery)

    @property
    def midright(self) -> tuple[float, float]:
        return (self.right, self.centery)

    @property
    def midtop(self) -> tuple[float, float]:
        return (self.centerx, self.y)

    @property
    def midbottom(self) -> tuple[float, float]:
        return (self.centerx, self.bottom)

    # ── transform methods ────────────────────────────────────────────────────

    def move(self, dx: float, dy: float) -> Rect:
        """Return this rect shifted by (dx, dy)."""
        return Rect(self.x + dx, self.y + dy, self.width, self.height)

    def inflate(self, dw: float, dh: float) -> Rect:
        """Return this rect grown by (dw, dh), centred on the same point."""
        return Rect(self.x - dw / 2, self.y - dh / 2, self.width + dw, self.height + dh)

    def scale_by(self, factor_x: float, factor_y: float | None = None) -> Rect:
        """Scale around the centre.  *factor_y* defaults to *factor_x*."""
        fy = factor_y if factor_y is not None else factor_x
        nw = self.width * factor_x
        nh = self.height * fy
        return Rect(self.centerx - nw / 2, self.centery - nh / 2, nw, nh)

    def padded(self, px: float, py: float | None = None) -> Rect:
        """Return this rect inset by *px* horizontally and *py* vertically.

        Pass negative values to expand instead of shrink.
        """
        py = py if py is not None else px
        return Rect(self.x + px, self.y + py, self.width - 2 * px, self.height - 2 * py)

    def normalized(self) -> Rect:
        """Return a copy with positive width and height."""
        x = self.x if self.width >= 0 else self.x + self.width
        y = self.y if self.height >= 0 else self.y + self.height
        return Rect(x, y, abs(self.width), abs(self.height))

    # ── set-like operations ──────────────────────────────────────────────────

    def clip(self, other: Rect) -> Rect:
        """Return the intersection of this rect and *other* (zero-size if no overlap)."""
        lx = max(self.left, other.left)
        ty = max(self.top, other.top)
        rx = min(self.right, other.right)
        by = min(self.bottom, other.bottom)
        if rx <= lx or by <= ty:
            return Rect(lx, ty, 0, 0)
        return Rect(lx, ty, rx - lx, by - ty)

    def union(self, other: Rect) -> Rect:
        """Return the smallest rect that contains both this rect and *other*."""
        lx = min(self.left, other.left)
        ty = min(self.top, other.top)
        rx = max(self.right, other.right)
        by = max(self.bottom, other.bottom)
        return Rect(lx, ty, rx - lx, by - ty)

    def fit(self, other: Rect) -> Rect:
        """Scale and centre this rect to fill *other* while preserving aspect ratio."""
        if self.width == 0 or self.height == 0:
            return Rect(other.x, other.y, 0, 0)
        scale = min(other.width / self.width, other.height / self.height)
        nw, nh = self.width * scale, self.height * scale
        return Rect(other.centerx - nw / 2, other.centery - nh / 2, nw, nh)

    def clamp(self, other: Rect) -> Rect:
        """Return this rect moved so it lies entirely within *other*."""
        x = max(other.left, min(self.x, other.right - self.width))
        y = max(other.top, min(self.y, other.bottom - self.height))
        return Rect(x, y, self.width, self.height)

    # ── collision helpers ────────────────────────────────────────────────────

    def collidepoint(self, x: float, y: float) -> bool:
        return self.left <= x < self.right and self.top <= y < self.bottom

    def colliderect(self, other: Rect) -> bool:
        return (
            self.left < other.right
            and self.right > other.left
            and self.top < other.bottom
            and self.bottom > other.top
        )

    def contains(self, other: Rect) -> bool:
        """Return True if *other* lies entirely within this rect."""
        return (
            self.left <= other.left
            and self.right >= other.right
            and self.top <= other.top
            and self.bottom >= other.bottom
        )

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Rect)
            and self.x == other.x
            and self.y == other.y
            and self.width == other.width
            and self.height == other.height
        )

    def __repr__(self) -> str:
        return f"Rect({self.x}, {self.y}, {self.width}, {self.height})"


# ── Vector2 ────────────────────────────────────────────────────────────────────


class Vector2:
    """2-D float vector, mirroring :class:`pygame.math.Vector2`.

    All angle values are in *degrees*.  Rotation is clockwise in screen
    coordinates (y-axis points down), matching pygame's screen-space convention.

    Usage::

        v = Vector2(3, 4)
        v.magnitude           # → 5.0
        v.normalize()         # → Vector2(0.6, 0.8)
        Vector2(1, 0).rotate(90)   # → Vector2(0, 1)  (clockwise in screen space)
        Vector2(0, 0).lerp(Vector2(10, 20), 0.5)  # → Vector2(5, 10)
        v.as_tuple()          # → (3.0, 4.0)  — pass directly to draw functions
    """

    __slots__ = ("x", "y")

    def __init__(self, x: float, y: float = 0.0):
        self.x = float(x)
        self.y = float(y)

    # ── arithmetic ───────────────────────────────────────────────────────────

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> Vector2:
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector2:
        return Vector2(self.x / scalar, self.y / scalar)

    def __neg__(self) -> Vector2:
        return Vector2(-self.x, -self.y)

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Vector2) and self.x == other.x and self.y == other.y

    def __repr__(self) -> str:
        return f"Vector2({self.x}, {self.y})"

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, idx: int) -> float:
        return (self.x, self.y)[idx]

    # ── properties ───────────────────────────────────────────────────────────

    @property
    def magnitude(self) -> float:
        """Length of the vector."""
        return math.hypot(self.x, self.y)

    @property
    def magnitude_squared(self) -> float:
        return self.x * self.x + self.y * self.y

    # ── vector operations ────────────────────────────────────────────────────

    def normalize(self) -> Vector2:
        """Return a unit vector in the same direction (zero vector → zero vector)."""
        m = self.magnitude
        return Vector2(self.x / m, self.y / m) if m else Vector2(0.0, 0.0)

    def dot(self, other: Vector2) -> float:
        return self.x * other.x + self.y * other.y

    def cross(self, other: Vector2) -> float:
        """2-D cross product (scalar z-component)."""
        return self.x * other.y - self.y * other.x

    def distance_to(self, other: Vector2) -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def lerp(self, other: Vector2, t: float) -> Vector2:
        """Linearly interpolate towards *other*.  t=0 → self, t=1 → other."""
        t = max(0.0, min(1.0, t))
        return Vector2(self.x + (other.x - self.x) * t, self.y + (other.y - self.y) * t)

    def rotate(self, degrees: float) -> Vector2:
        """Return this vector rotated *degrees* clockwise in screen coordinates."""
        rad = math.radians(degrees)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        return Vector2(self.x * cos_a - self.y * sin_a, self.x * sin_a + self.y * cos_a)

    def angle_to(self, other: Vector2) -> float:
        """Signed CW angle in degrees from *self* to *other* (screen coords)."""
        return math.degrees(
            math.atan2(other.x * self.y - other.y * self.x, self.x * other.x + self.y * other.y)
        )

    def reflect(self, normal: Vector2) -> Vector2:
        """Reflect this vector across *normal* (normal should be unit length)."""
        d = 2 * self.dot(normal)
        return Vector2(self.x - d * normal.x, self.y - d * normal.y)

    def project(self, other: Vector2) -> Vector2:
        """Project this vector onto *other*."""
        denom = other.magnitude_squared
        if denom == 0:
            return Vector2(0.0, 0.0)
        t = self.dot(other) / denom
        return Vector2(other.x * t, other.y * t)

    # ── convenience ──────────────────────────────────────────────────────────

    def as_tuple(self) -> tuple[float, float]:
        """Convert to ``(x, y)`` tuple for use with :class:`draw` functions."""
        return (self.x, self.y)

    def copy(self) -> Vector2:
        return Vector2(self.x, self.y)

    @classmethod
    def from_polar(cls, magnitude: float, angle_degrees: float) -> Vector2:
        """Create from polar coordinates.  Angle is CW from the positive-x axis."""
        rad = math.radians(angle_degrees)
        return cls(magnitude * math.cos(rad), magnitude * math.sin(rad))


# ── Surface ────────────────────────────────────────────────────────────────────


class Surface:
    """A drawable slide canvas that collects Google Slides API requests.

    Passed to :meth:`~slide_games.BaseGame.render` for each game-state slide.
    Use :class:`draw` functions to add shapes and text.  Coordinates use the
    1920 × 1080 virtual pixel space.
    """

    #: Virtual canvas width — always 1920 virtual pixels.
    width = SCREEN_W
    #: Virtual canvas height — always 1080 virtual pixels.
    height = SCREEN_H

    @property
    def size(self) -> tuple[int, int]:
        return (self.width, self.height)

    @property
    def get_rect(self) -> Rect:
        """Return a :class:`Rect` covering the full canvas."""
        return Rect(0, 0, self.width, self.height)

    def __init__(self, slide_id: str):
        self._slide_id = slide_id
        self._requests: list[dict] = []

    def fill(self, color: Color | tuple) -> None:
        """Set the slide background to a solid colour."""
        c = _coerce_color(color)
        self._requests.append(
            {
                "updatePageProperties": {
                    "objectId": self._slide_id,
                    "pageProperties": {
                        "pageBackgroundFill": {"solidFill": {"color": {"rgbColor": c._rgb()}}}
                    },
                    "fields": "pageBackgroundFill",
                }
            }
        )

    def get_requests(self) -> list[dict]:
        return list(self._requests)


# ── internal helpers ──────────────────────────────────────────────────────────


def _coerce_color(color: Color | tuple) -> Color:
    return color if isinstance(color, Color) else Color(*color)


def _coerce_rect(rect: Rect | tuple) -> Rect:
    return rect if isinstance(rect, Rect) else Rect(*rect)


def _make_shape(
    slide_id: str,
    shape_type: str,
    x_emu: int,
    y_emu: int,
    w_emu: int,
    h_emu: int,
    transform: dict | None = None,
) -> tuple[str, dict]:
    oid = _uid()
    t = transform or {
        "scaleX": 1,
        "scaleY": 1,
        "translateX": x_emu,
        "translateY": y_emu,
        "unit": "EMU",
    }
    return oid, {
        "createShape": {
            "objectId": oid,
            "shapeType": shape_type,
            "elementProperties": {
                "pageObjectId": slide_id,
                "size": {
                    "width": {"magnitude": max(w_emu, 1), "unit": "EMU"},
                    "height": {"magnitude": max(h_emu, 1), "unit": "EMU"},
                },
                "transform": t,
            },
        }
    }


def _apply_fill(oid: str, color: Color, outline: bool = False) -> list[dict]:
    rgb = color._rgb()
    outline_props = (
        {
            "outlineFill": {"solidFill": {"color": {"rgbColor": rgb}}},
            "weight": {"magnitude": 12_700, "unit": "EMU"},
            "dashStyle": "SOLID",
        }
        if outline
        else {"propertyState": "NOT_RENDERED"}
    )
    return [
        {
            "updateShapeProperties": {
                "objectId": oid,
                "fields": "shapeBackgroundFill,outline",
                "shapeProperties": {
                    "shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": rgb}}},
                    "outline": outline_props,
                },
            }
        }
    ]


# ── draw ──────────────────────────────────────────────────────────────────────


class draw:
    """Drawing functions, mirroring :mod:`pygame.draw`.

    All coordinates use the 1920 × 1080 virtual pixel space.

    Filled shapes: pass ``width=0`` (default).
    Outlined shapes: pass ``width > 0``.

    New in this release compared to vanilla pygame:
      * :meth:`triangle` — filled directional triangle
      * :meth:`lines` — multi-segment polyline
      * :meth:`progress_bar` — game HUD progress/health bar
      * :meth:`shape` — any Google Slides built-in shape (diamond, star, etc.)
      * :meth:`text` now supports ``italic`` and ``vertical_align``
    """

    # ── basic shapes ─────────────────────────────────────────────────────────

    @staticmethod
    def rect(
        surface: Surface,
        color: Color | tuple,
        rect: Rect | tuple,
        width: int = 0,
        border_radius: int = 0,
    ) -> None:
        """Draw a filled (or outlined) rectangle."""
        c = _coerce_color(color)
        r = _coerce_rect(rect)
        shape = "ROUND_RECTANGLE" if border_radius > 0 else "RECTANGLE"
        oid, create = _make_shape(
            surface._slide_id, shape, _px_x(r.x), _px_y(r.y), _px_w(r.width), _px_h(r.height)
        )
        surface._requests.append(create)
        surface._requests.extend(_apply_fill(oid, c, outline=(width > 0)))

    @staticmethod
    def circle(
        surface: Surface, color: Color | tuple, center: tuple, radius: float, width: int = 0
    ) -> None:
        """Draw a filled (or outlined) circle."""
        c = _coerce_color(color)
        cx, cy = center
        oid, create = _make_shape(
            surface._slide_id,
            "ELLIPSE",
            _px_x(cx - radius),
            _px_y(cy - radius),
            _px_w(radius * 2),
            _px_h(radius * 2),
        )
        surface._requests.append(create)
        surface._requests.extend(_apply_fill(oid, c, outline=(width > 0)))

    @staticmethod
    def ellipse(surface: Surface, color: Color | tuple, rect: Rect | tuple, width: int = 0) -> None:
        """Draw a filled (or outlined) ellipse inside the bounding *rect*."""
        c = _coerce_color(color)
        r = _coerce_rect(rect)
        oid, create = _make_shape(
            surface._slide_id, "ELLIPSE", _px_x(r.x), _px_y(r.y), _px_w(r.width), _px_h(r.height)
        )
        surface._requests.append(create)
        surface._requests.extend(_apply_fill(oid, c, outline=(width > 0)))

    @staticmethod
    def line(
        surface: Surface, color: Color | tuple, start_pos: tuple, end_pos: tuple, width: int = 3
    ) -> None:
        """Draw a line from *start_pos* to *end_pos*."""
        c = _coerce_color(color)
        x1, y1 = start_pos
        x2, y2 = end_pos
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 1:
            return

        angle = math.atan2(y2 - y1, x2 - x1)
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        L_emu = _px_w(length)
        h_emu = _px_h(width)

        cx_emu = _px_x((x1 + x2) / 2)
        cy_emu = _px_y((y1 + y2) / 2)

        tx = round(cx_emu - cos_a * L_emu / 2 + sin_a * h_emu / 2)
        ty = round(cy_emu - sin_a * L_emu / 2 - cos_a * h_emu / 2)

        transform = {
            "scaleX": cos_a,
            "shearX": -sin_a,
            "shearY": sin_a,
            "scaleY": cos_a,
            "translateX": tx,
            "translateY": ty,
            "unit": "EMU",
        }
        oid, create = _make_shape(
            surface._slide_id, "RECTANGLE", tx, ty, L_emu, h_emu, transform=transform
        )
        surface._requests.append(create)
        surface._requests.extend(_apply_fill(oid, c))

    @staticmethod
    def lines(
        surface: Surface,
        color: Color | tuple,
        points: list[tuple],
        width: int = 3,
        closed: bool = False,
    ) -> None:
        """Draw a series of connected line segments.

        Unlike :meth:`polygon`, does **not** close the path unless
        ``closed=True``.  Equivalent to ``pygame.draw.lines``.

        Args:
            points:  Sequence of ``(x, y)`` positions.
            closed:  If True, connects the last point back to the first.
        """
        if len(points) < 2:
            return
        c = _coerce_color(color)
        pts = list(points)
        if closed:
            pts = pts + [pts[0]]
        for a, b in zip(pts, pts[1:]):
            draw.line(surface, c, a, b, max(width, 1))

    @staticmethod
    def polygon(
        surface: Surface, color: Color | tuple, points: list[tuple], width: int = 2
    ) -> None:
        """Draw a closed polygon outline by connecting *points* with lines.

        .. note::
            The Google Slides API does not support arbitrary filled polygons.
            Use :meth:`triangle`, :meth:`shape`, or overlapping
            :meth:`rect` / :meth:`circle` calls to approximate filled shapes.
            For a filled outline, set ``width=0`` and use :meth:`shape`.
        """
        if len(points) < 2:
            return
        draw.lines(surface, color, points, width=max(width, 1), closed=True)

    @staticmethod
    def triangle(
        surface: Surface,
        color: Color | tuple,
        rect: Rect | tuple,
        direction: str = "up",
        width: int = 0,
    ) -> None:
        """Draw a filled isosceles triangle inside the bounding *rect*.

        Args:
            direction: Which way the apex points.
                ``"up"`` (default), ``"down"``, ``"left"``, or ``"right"``.
            width: 0 → filled (default); > 0 → outlined only.

        Uses the Google Slides ``TRIANGLE`` shape type, which is an isosceles
        triangle.  A rotation transform is applied for ``"down"``, ``"left"``,
        and ``"right"`` directions.

        Example — draw a right-pointing arrow indicator::

            draw.triangle(surface, Color(255, 200, 0),
                          Rect(900, 400, 80, 60), direction="right")
        """
        c = _coerce_color(color)
        r = _coerce_rect(rect)

        cx_emu = _px_x(r.centerx)
        cy_emu = _px_y(r.centery)
        rw_emu = _px_w(r.width)
        rh_emu = _px_h(r.height)

        # Rotation transforms for each direction.
        # w_loc, h_loc: local shape dimensions (may be transposed for 90° rotations).
        # tx, ty: transform translateX/Y so the shape centre lands at (cx_emu, cy_emu).
        # Derivation: tx = cx - scaleX*(w/2) - shearX*(h/2),
        #             ty = cy - shearY*(w/2) - scaleY*(h/2)
        if direction == "down":
            # 180° rotation: scaleX=-1, scaleY=-1
            w_loc, h_loc = rw_emu, rh_emu
            transform = {
                "scaleX": -1,
                "scaleY": -1,
                "shearX": 0,
                "shearY": 0,
                "translateX": cx_emu + rw_emu // 2,
                "translateY": cy_emu + rh_emu // 2,
                "unit": "EMU",
            }
        elif direction == "left":
            # 90° CW screen-space: scaleX=0, shearX=1, shearY=-1, scaleY=0
            w_loc, h_loc = rh_emu, rw_emu  # transposed
            transform = {
                "scaleX": 0,
                "scaleY": 0,
                "shearX": 1,
                "shearY": -1,
                "translateX": cx_emu - rw_emu // 2,
                "translateY": cy_emu + rh_emu // 2,
                "unit": "EMU",
            }
        elif direction == "right":
            # 270° CW (90° CCW) screen-space: scaleX=0, shearX=-1, shearY=1, scaleY=0
            w_loc, h_loc = rh_emu, rw_emu  # transposed
            transform = {
                "scaleX": 0,
                "scaleY": 0,
                "shearX": -1,
                "shearY": 1,
                "translateX": cx_emu + rw_emu // 2,
                "translateY": cy_emu - rh_emu // 2,
                "unit": "EMU",
            }
        else:  # "up" — identity
            w_loc, h_loc = rw_emu, rh_emu
            transform = {
                "scaleX": 1,
                "scaleY": 1,
                "shearX": 0,
                "shearY": 0,
                "translateX": cx_emu - rw_emu // 2,
                "translateY": cy_emu - rh_emu // 2,
                "unit": "EMU",
            }

        oid, create = _make_shape(
            surface._slide_id, "TRIANGLE", 0, 0, w_loc, h_loc, transform=transform
        )
        surface._requests.append(create)
        surface._requests.extend(_apply_fill(oid, c, outline=(width > 0)))

    @staticmethod
    def shape(
        surface: Surface, color: Color | tuple, shape_type: str, rect: Rect | tuple, width: int = 0
    ) -> None:
        """Draw any Google Slides built-in shape type.

        This exposes the full Slides shape library: polygons, stars, arrows,
        and more — all as first-class filled drawing primitives.

        Useful ``shape_type`` values::

            "DIAMOND"        "PENTAGON"       "HEXAGON"
            "HEPTAGON"       "OCTAGON"        "DECAGON"
            "STAR_4"         "STAR_5"         "STAR_6"
            "STAR_8"         "STAR_10"        "STAR_12"
            "RIGHT_TRIANGLE" "PARALLELOGRAM"  "TRAPEZOID"
            "LEFT_ARROW"     "RIGHT_ARROW"    "UP_ARROW"
            "DOWN_ARROW"     "CHEVRON"        "RING"

        Args:
            shape_type: Any ``PredefinedLayout`` string from the Slides API.
            rect: Bounding rectangle for the shape.
            width: 0 → filled; > 0 → outlined.

        Example — draw a gold star::

            draw.shape(surface, GOLD, "STAR_5", Rect(800, 300, 100, 100))
        """
        c = _coerce_color(color)
        r = _coerce_rect(rect)
        oid, create = _make_shape(
            surface._slide_id, shape_type, _px_x(r.x), _px_y(r.y), _px_w(r.width), _px_h(r.height)
        )
        surface._requests.append(create)
        surface._requests.extend(_apply_fill(oid, c, outline=(width > 0)))

    # ── HUD helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def progress_bar(
        surface: Surface,
        rect: Rect | tuple,
        value: float,
        max_value: float,
        fg_color: Color | tuple,
        bg_color: Color | tuple | None = None,
        border_radius: int = 8,
    ) -> None:
        """Draw a progress bar — common in game HUDs for health, score, etc.

        Draws a background track in *bg_color* (default: ``DARK_GRAY``) and a
        filled section whose width is proportional to ``value / max_value``.

        Args:
            rect:          Bounding box of the bar.
            value:         Current value (clamped to 0 … max_value).
            max_value:     Maximum value.  Must be > 0.
            fg_color:      Fill colour of the filled section.
            bg_color:      Background track colour.  Defaults to ``DARK_GRAY``.
            border_radius: Rounding of the track and fill corners.

        Example::

            draw.progress_bar(surface, Rect(60, 750, 500, 24),
                              state.health, 100, GREEN)
        """
        c_fg = _coerce_color(fg_color)
        c_bg = _coerce_color(bg_color) if bg_color is not None else DARK_GRAY
        r = _coerce_rect(rect)

        # Background track
        draw.rect(surface, c_bg, r, border_radius=border_radius)

        # Filled portion
        if max_value > 0:
            frac = max(0.0, min(1.0, value / max_value))
            fill_w = max(border_radius, r.width * frac)
            draw.rect(surface, c_fg, Rect(r.x, r.y, fill_w, r.height), border_radius=border_radius)

    # ── text ─────────────────────────────────────────────────────────────────

    @staticmethod
    def text(
        surface: Surface,
        message: str,
        rect: Rect | tuple,
        color: Color | tuple = WHITE,
        font_size: int = 24,
        bold: bool = False,
        italic: bool = False,
        align: str = "LEFT",
        vertical_align: str = "TOP",
    ) -> None:
        """Render text within a bounding rectangle.

        Args:
            rect:           ``Rect`` or ``(x, y, w, h)`` bounding box.
            color:          Text colour.
            font_size:      Point size.
            bold:           Bold weight.
            italic:         Italic style.
            align:          Horizontal: ``"LEFT"``, ``"CENTER"``, or ``"RIGHT"``.
            vertical_align: Vertical: ``"TOP"`` (default), ``"MIDDLE"``, or ``"BOTTOM"``.
        """
        c = _coerce_color(color)
        r = _coerce_rect(rect)
        oid, create = _make_shape(
            surface._slide_id, "TEXT_BOX", _px_x(r.x), _px_y(r.y), _px_w(r.width), _px_h(r.height)
        )
        surface._requests.append(create)
        surface._requests.append(
            {"insertText": {"objectId": oid, "text": message, "insertionIndex": 0}}
        )
        surface._requests.append(
            {
                "updateTextStyle": {
                    "objectId": oid,
                    "textRange": {"type": "ALL"},
                    "style": {
                        "bold": bold,
                        "italic": italic,
                        "fontSize": {"magnitude": font_size, "unit": "PT"},
                        "foregroundColor": {"opaqueColor": {"rgbColor": c._rgb()}},
                        "underline": False,
                    },
                    "fields": "bold,italic,fontSize,foregroundColor,underline",
                }
            }
        )
        surface._requests.append(
            {
                "updateParagraphStyle": {
                    "objectId": oid,
                    "textRange": {"type": "ALL"},
                    "style": {"alignment": align.upper()},
                    "fields": "alignment",
                }
            }
        )
        va = vertical_align.upper()
        if va in ("MIDDLE", "BOTTOM"):
            surface._requests.append(
                {
                    "updateShapeProperties": {
                        "objectId": oid,
                        "fields": "contentAlignment",
                        "shapeProperties": {
                            "contentAlignment": va if va == "BOTTOM" else "MIDDLE",
                        },
                    }
                }
            )
