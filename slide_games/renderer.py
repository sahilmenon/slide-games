"""Google Slides API request builders.

Slide layout  (10" × 5.625"  — Google Slides 16:9 default)
------------
  ┌─────────────────────────────────────────┐  0"
  │                                         │
  │   ┌─── game grid (centred) ──────────┐  │  0.20"
  │   │  # # # # # # # # # #             │  │
  │   │  # S . . . . . . . #             │  │
  │   │  # . # # # # # # . #             │  │
  │   │  # . . . . . . . G #             │  │
  │   │  # # # # # # # # # #             │  │
  │   └──────────────────────────────────┘  │  3.60"
  │                                         │
  │              [▲]                        │  4.65" (D-pad centre)
  │         [◄]     [►]                     │
  │              [▼]                        │
  └─────────────────────────────────────────┘  5.625"

All coordinates in EMU (1 inch = 914 400 EMU).
"""

from __future__ import annotations

import uuid
from typing import Any

from .games.base import ARROWS, BaseGame
from .gfx import Surface
from .models import Level, Position
from .themes import Theme

SLIDE_W = 9_144_000  # 10 inches
SLIDE_H = 5_143_500  # 5.625 inches — Google Slides 16:9 default
INCH = 914_400

# Layout
_GRID_TOP = round(0.20 * INCH)  # top of game grid
_GRID_BOTTOM = round(3.60 * INCH)  # bottom of game grid
_SIDE_MARGIN = round(0.35 * INCH)  # left/right margin for grid
_NAV_CY = round(4.65 * INCH)  # vertical centre of D-pad
_BTN_SZ = round(0.55 * INCH)  # square button size
_BTN_GAP = round(0.06 * INCH)  # gap between D-pad buttons


# ── helpers ───────────────────────────────────────────────────────────────────


def _uid() -> str:
    return f"o{uuid.uuid4().hex[:15]}"


def _emu(inches: float) -> int:
    return round(inches * INCH)


def _ep(page_id: str, x: int, y: int, w: int, h: int) -> dict:
    return {
        "pageObjectId": page_id,
        "size": {
            "width": {"magnitude": max(w, 1), "unit": "EMU"},
            "height": {"magnitude": max(h, 1), "unit": "EMU"},
        },
        "transform": {
            "scaleX": 1,
            "scaleY": 1,
            "translateX": x,
            "translateY": y,
            "unit": "EMU",
        },
    }


def _create(oid: str, shape: str, page_id: str, x: int, y: int, w: int, h: int) -> dict:
    return {
        "createShape": {
            "objectId": oid,
            "shapeType": shape,
            "elementProperties": _ep(page_id, x, y, w, h),
        }
    }


def _fill(oid: str, rgb: dict) -> dict:
    """Solid fill + no border."""
    return {
        "updateShapeProperties": {
            "objectId": oid,
            "fields": "shapeBackgroundFill,outline",
            "shapeProperties": {
                "shapeBackgroundFill": {"solidFill": {"color": {"rgbColor": rgb}}},
                "outline": {"propertyState": "NOT_RENDERED"},
            },
        }
    }


def _insert(oid: str, text: str) -> dict:
    return {"insertText": {"objectId": oid, "text": text, "insertionIndex": 0}}


def _style(oid: str, pt: float, rgb: dict, bold: bool = False) -> dict:
    """Text style: size, colour, bold, and explicitly no underline."""
    return {
        "updateTextStyle": {
            "objectId": oid,
            "textRange": {"type": "ALL"},
            "style": {
                "fontSize": {"magnitude": pt, "unit": "PT"},
                "bold": bold,
                "foregroundColor": {"opaqueColor": {"rgbColor": rgb}},
                "underline": False,
            },
            "fields": "fontSize,bold,foregroundColor,underline",
        }
    }


def _center(oid: str) -> dict:
    return {
        "updateParagraphStyle": {
            "objectId": oid,
            "style": {"alignment": "CENTER"},
            "fields": "alignment",
        }
    }


def _vmiddle(oid: str) -> dict:
    return {
        "updateShapeProperties": {
            "objectId": oid,
            "fields": "contentAlignment",
            "shapeProperties": {"contentAlignment": "MIDDLE"},
        }
    }


def _text_link(oid: str, target_slide_id: str) -> dict:
    """Hyperlink all text in a shape to another slide.

    Text-level links are more reliably clickable in Presentation mode than
    shape-level links (updateShapeProperties.link).
    """
    return {
        "updateTextStyle": {
            "objectId": oid,
            "textRange": {"type": "ALL"},
            "style": {"link": {"pageObjectId": target_slide_id}},
            "fields": "link",
        }
    }


def _create_image(oid: str, url: str, page_id: str, x: int, y: int, w: int, h: int) -> dict:
    return {
        "createImage": {
            "objectId": oid,
            "url": url,
            "elementProperties": _ep(page_id, x, y, w, h),
        }
    }


def _slide_bg(page_id: str, rgb: dict) -> dict:
    return {
        "updatePageProperties": {
            "objectId": page_id,
            "pageProperties": {"pageBackgroundFill": {"solidFill": {"color": {"rgbColor": rgb}}}},
            "fields": "pageBackgroundFill",
        }
    }


# ── layout helpers ────────────────────────────────────────────────────────────


def _grid_cell_size(level: Level) -> int:
    """Return the largest integer cell size (EMU) that fits the grid in the
    designated grid zone with side margins."""
    avail_w = SLIDE_W - 2 * _SIDE_MARGIN
    avail_h = _GRID_BOTTOM - _GRID_TOP
    return max(min(avail_w // level.width, avail_h // level.height), 1)


def _grid_origin(level: Level, cell: int) -> tuple[int, int]:
    """Return (x, y) top-left corner of the grid, centred in the grid zone."""
    grid_w = cell * level.width
    grid_h = cell * level.height
    avail_h = _GRID_BOTTOM - _GRID_TOP
    ox = (SLIDE_W - grid_w) // 2
    oy = _GRID_TOP + (avail_h - grid_h) // 2
    return ox, oy


# ── renderer ──────────────────────────────────────────────────────────────────


class Renderer:
    """Converts game states into Google Slides batchUpdate request lists."""

    def __init__(self, game: Any, theme: Theme):
        self.game = game
        self.theme = theme

    # ── title slide ───────────────────────────────────────────────────────────

    def render_title(self, slide_id: str, first_state_slide_id: str, title: str) -> list[dict]:
        T = self.theme
        r: list[dict] = [_slide_bg(slide_id, T.background)]

        tid = _uid()
        r += [
            _create(tid, "TEXT_BOX", slide_id, _emu(0.5), _emu(0.7), _emu(9.0), _emu(1.5)),
            _insert(tid, title),
            _style(tid, 54, T.title_text, bold=True),
            _center(tid),
        ]

        sid = _uid()
        r += [
            _create(sid, "TEXT_BOX", slide_id, _emu(1.0), _emu(2.5), _emu(8.0), _emu(0.6)),
            _insert(sid, "Click the arrow buttons to navigate  •  Reach the goal to win"),
            _style(sid, 16, T.btn_text),
            _center(sid),
        ]

        bid = _uid()
        r += [
            _create(bid, "ROUND_RECTANGLE", slide_id, _emu(3.75), _emu(3.7), _emu(2.5), _emu(0.75)),
            _fill(bid, T.btn_active),
            _insert(bid, "PLAY"),
            _text_link(bid, first_state_slide_id),
            _style(bid, 30, T.btn_text, bold=True),
            _center(bid),
            _vmiddle(bid),
        ]
        return r

    # ── shared internals ──────────────────────────────────────────────────────

    def _render_content(
        self, slide_id: str, state: Any, next_level_slide_id: str | None
    ) -> list[dict]:
        """Game-specific render + win banner. No D-pad buttons."""
        T = self.theme
        has_custom_render = type(self.game).render is not BaseGame.render

        if has_custom_render:
            surf = Surface(slide_id)
            self.game.render(surf, state)
            r: list[dict] = surf.get_requests()
        else:
            r = [_slide_bg(slide_id, T.background)]

            level: Level = self.game.level
            player_pos: Position = state if isinstance(state, Position) else state.position
            eaten: frozenset = getattr(state, "eaten", frozenset())

            cell = _grid_cell_size(level)
            ox, oy = _grid_origin(level, cell)
            pad = max(2, cell // 50)

            bg_id = _uid()
            r += [
                _create(
                    bg_id, "RECTANGLE", slide_id, ox, oy, cell * level.width, cell * level.height
                ),
                _fill(bg_id, T.floor),
            ]

            for row_i, row in enumerate(level.grid):
                for col_i, ch in enumerate(row):
                    pos = Position(col_i, row_i)
                    cx = ox + col_i * cell
                    cy = oy + row_i * cell
                    is_player = pos == player_pos

                    if is_player:
                        color = T.player
                    elif ch == "#":
                        color = T.wall
                    elif ch == "G":
                        color = T.goal
                    else:
                        color = T.floor

                    color = self.game.get_cell_color(state, ch, is_player) or color
                    img_url = self.game.get_cell_image_url(state, ch, is_player)

                    inner = max(cell - 2 * pad, pad)
                    if color != T.floor or img_url:
                        cid = _uid()
                        r += [
                            _create(cid, "RECTANGLE", slide_id, cx + pad, cy + pad, inner, inner),
                            _fill(cid, color),
                        ]
                    if img_url:
                        iid = _uid()
                        r.append(
                            _create_image(iid, img_url, slide_id, cx + pad, cy + pad, inner, inner)
                        )

                    if ch == "p" and pos not in eaten:
                        dot = max(cell // 5, _emu(0.04))
                        did = _uid()
                        r += [
                            _create(
                                did,
                                "ELLIPSE",
                                slide_id,
                                cx + (cell - dot) // 2,
                                cy + (cell - dot) // 2,
                                dot,
                                dot,
                            ),
                            _fill(did, T.pellet),
                        ]

            for sh in self.game.get_extra_shapes(state):
                gx = ox + round(sh["x"] * cell)
                gy = oy + round(sh["y"] * cell)
                gw = max(round(sh["w"] * cell), 1)
                gh = max(round(sh["h"] * cell), 1)
                eid = _uid()
                if sh.get("type") == "text":
                    r += [
                        _create(eid, "TEXT_BOX", slide_id, gx, gy, gw, gh),
                        _insert(eid, sh.get("text", "")),
                        _style(eid, sh.get("font_size", 14), sh["color"]),
                        _center(eid),
                        _vmiddle(eid),
                    ]
                else:
                    stype = "ELLIPSE" if sh.get("type") == "ellipse" else "RECTANGLE"
                    r += [
                        _create(
                            eid,
                            stype,
                            slide_id,
                            gx + pad,
                            gy + pad,
                            max(gw - 2 * pad, 1),
                            max(gh - 2 * pad, 1),
                        ),
                        _fill(eid, sh["color"]),
                    ]

        if self.game.show_win_banner(state):
            wid = _uid()
            r += [
                _create(wid, "TEXT_BOX", slide_id, _emu(0.5), _emu(1.2), _emu(9.0), _emu(1.4)),
                _insert(wid, "YOU WIN!"),
                _style(wid, 72, T.win_text, bold=True),
                _center(wid),
            ]
            if next_level_slide_id:
                nxt_id = _uid()
                r += [
                    _create(
                        nxt_id,
                        "ROUND_RECTANGLE",
                        slide_id,
                        _emu(3.3),
                        _emu(2.85),
                        _emu(3.4),
                        _emu(0.70),
                    ),
                    _fill(nxt_id, T.btn_active),
                    _insert(nxt_id, "Next Level ►"),
                    _text_link(nxt_id, next_level_slide_id),
                    _style(nxt_id, 24, T.btn_text, bold=True),
                    _center(nxt_id),
                    _vmiddle(nxt_id),
                ]

        return r

    def _nav_offsets(self) -> dict[str, tuple[int, int]]:
        step = _BTN_SZ + _BTN_GAP
        return {
            "up": (0, -step),
            "down": (0, step),
            "left": (-step, 0),
            "right": (step, 0),
        }

    def _resolve_btn(
        self,
        d: str,
        state: Any,
        state_to_slide: dict,
        error_slide_id: str | None,
        initial_slide_id: str | None,
    ) -> tuple[bool, str | None]:
        """Return (active, link_target) for a direction button."""
        is_loss = self.game.is_terminal(state) and not self.game.show_win_banner(state)
        if is_loss:
            return initial_slide_id is not None, initial_slide_id
        next_state = self.game.get_transitions(state).get(d)
        active = next_state is not None and next_state in state_to_slide
        link = state_to_slide[next_state] if active else error_slide_id
        return active, link

    # ── game state slide ──────────────────────────────────────────────────────

    def render_state(
        self,
        slide_id: str,
        state: Any,
        state_to_slide: dict[Any, str],
        error_slide_id: str | None = None,
        next_level_slide_id: str | None = None,
        initial_slide_id: str | None = None,
    ) -> list[dict]:
        r = self._render_content(slide_id, state, next_level_slide_id)
        T = self.theme
        for d, (dox, doy) in self._nav_offsets().items():
            active, link_target = self._resolve_btn(
                d, state, state_to_slide, error_slide_id, initial_slide_id
            )
            oid = _uid()
            bx = SLIDE_W // 2 + dox - _BTN_SZ // 2
            by = _NAV_CY + doy - _BTN_SZ // 2
            r += [
                _create(oid, "ROUND_RECTANGLE", slide_id, bx, by, _BTN_SZ, _BTN_SZ),
                _fill(oid, T.btn_active if active else T.btn_inactive),
                _insert(oid, ARROWS[d]),
            ]
            if link_target is not None:
                r.append(_text_link(oid, link_target))
            r += [
                _style(oid, 26, T.btn_text, bold=True),
                _center(oid),
                _vmiddle(oid),
            ]
        return r

    # ── template-based rendering (duplicateObject optimisation) ───────────────

    def render_nav_template(self, slide_id: str, btn_ids: dict[str, str]) -> list[dict]:
        """Populate template slide with static D-pad shapes — no links yet.

        Saves 19 API reqs per state slide vs building buttons from scratch.
        btn_ids maps direction → pre-assigned shape object ID.
        """
        T = self.theme
        r: list[dict] = []
        for d, oid in btn_ids.items():
            dox, doy = self._nav_offsets()[d]
            bx = SLIDE_W // 2 + dox - _BTN_SZ // 2
            by = _NAV_CY + doy - _BTN_SZ // 2
            r += [
                _create(oid, "ROUND_RECTANGLE", slide_id, bx, by, _BTN_SZ, _BTN_SZ),
                _fill(oid, T.btn_inactive),
                _insert(oid, ARROWS[d]),
                _style(oid, 26, T.btn_text, bold=True),
                _center(oid),
                _vmiddle(oid),
            ]
        return r

    def render_nav_delta(
        self,
        btn_ids: dict[str, str],
        state: Any,
        state_to_slide: dict,
        error_slide_id: str | None,
        initial_slide_id: str | None,
    ) -> list[dict]:
        """Fill + link updates for duplicated D-pad buttons (1–2 reqs each)."""
        T = self.theme
        r: list[dict] = []
        for d, oid in btn_ids.items():
            active, link_target = self._resolve_btn(
                d, state, state_to_slide, error_slide_id, initial_slide_id
            )
            r.append(_fill(oid, T.btn_active if active else T.btn_inactive))
            if link_target is not None:
                r.append(_text_link(oid, link_target))
        return r

    def render_state_delta(
        self,
        slide_id: str,
        state: Any,
        btn_ids: dict[str, str],
        state_to_slide: dict[Any, str],
        error_slide_id: str | None = None,
        next_level_slide_id: str | None = None,
        initial_slide_id: str | None = None,
    ) -> list[dict]:
        """Game content + button deltas for a slide created via duplicateObject."""
        r = self._render_content(slide_id, state, next_level_slide_id)
        r += self.render_nav_delta(btn_ids, state, state_to_slide, error_slide_id, initial_slide_id)
        return r

    def render_error_template(self, slide_id: str, btn_id: str) -> list[dict]:
        """Error slide content without the try-again link (17 reqs, reused N times)."""
        T = self.theme
        _RED = {"red": 0.78, "green": 0.10, "blue": 0.10}
        _WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}

        r: list[dict] = [_slide_bg(slide_id, T.background)]
        ban_id = _uid()
        r += [
            _create(ban_id, "RECTANGLE", slide_id, _emu(0.4), _emu(1.3), _emu(9.2), _emu(2.3)),
            _fill(ban_id, _RED),
        ]
        head_id = _uid()
        r += [
            _create(head_id, "TEXT_BOX", slide_id, _emu(0.4), _emu(1.4), _emu(9.2), _emu(1.3)),
            _insert(head_id, "BLOCKED!"),
            _style(head_id, 72, _WHITE, bold=True),
            _center(head_id),
        ]
        sub_id = _uid()
        r += [
            _create(sub_id, "TEXT_BOX", slide_id, _emu(1.0), _emu(2.85), _emu(8.0), _emu(0.55)),
            _insert(sub_id, "No passage in that direction"),
            _style(sub_id, 18, _WHITE),
            _center(sub_id),
        ]
        r += [
            _create(
                btn_id, "ROUND_RECTANGLE", slide_id, _emu(0.5), _emu(3.9), _emu(9.0), _emu(1.3)
            ),
            _fill(btn_id, T.btn_active),
            _insert(btn_id, "Try Again"),
            _style(btn_id, 36, T.btn_text, bold=True),
            _center(btn_id),
            _vmiddle(btn_id),
        ]
        return r

    def render_error_delta(self, btn_id: str, main_slide_id: str) -> list[dict]:
        """Try-again link for a duplicated error slide (1 req)."""
        return [_text_link(btn_id, main_slide_id)]

    # ── error overlay slide (legacy — used when not using duplicateObject) ────

    def render_error_state(self, slide_id: str, main_slide_id: str) -> list[dict]:
        """Render the 'BLOCKED!' slide shown when a walled direction is pressed.

        Shows a red error banner and a large full-width 'Try Again' button that
        always links back to ``main_slide_id`` — the exact state the player came from.
        """
        T = self.theme
        _RED = {"red": 0.78, "green": 0.10, "blue": 0.10}
        _WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}

        r: list[dict] = [_slide_bg(slide_id, T.background)]

        # Red banner
        ban_id = _uid()
        r += [
            _create(ban_id, "RECTANGLE", slide_id, _emu(0.4), _emu(1.3), _emu(9.2), _emu(2.3)),
            _fill(ban_id, _RED),
        ]

        head_id = _uid()
        r += [
            _create(head_id, "TEXT_BOX", slide_id, _emu(0.4), _emu(1.4), _emu(9.2), _emu(1.3)),
            _insert(head_id, "BLOCKED!"),
            _style(head_id, 72, _WHITE, bold=True),
            _center(head_id),
        ]

        sub_id = _uid()
        r += [
            _create(sub_id, "TEXT_BOX", slide_id, _emu(1.0), _emu(2.85), _emu(8.0), _emu(0.55)),
            _insert(sub_id, "No passage in that direction"),
            _style(sub_id, 18, _WHITE),
            _center(sub_id),
        ]

        # Large full-width 'Try Again' button — hard to miss, always correct
        btn_id = _uid()
        r += [
            _create(
                btn_id, "ROUND_RECTANGLE", slide_id, _emu(0.5), _emu(3.9), _emu(9.0), _emu(1.3)
            ),
            _fill(btn_id, T.btn_active),
            _insert(btn_id, "Try Again"),
            _text_link(btn_id, main_slide_id),
            _style(btn_id, 36, T.btn_text, bold=True),
            _center(btn_id),
            _vmiddle(btn_id),
        ]

        return r
