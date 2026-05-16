"""Tests for the pygame-like gfx module and the BaseGame.render() hook."""

import pytest

from slide_games.games.base import BaseGame
from slide_games.games.maze import MazeGame
from slide_games.gfx import (
    _SLIDE_H_EMU,
    _SLIDE_W_EMU,
    BLACK,
    BLUE,
    DARK_GRAY,
    GREEN,
    RED,
    SCREEN_H,
    SCREEN_W,
    WHITE,
    Color,
    Rect,
    Surface,
    Vector2,
    _px_h,
    _px_w,
    _px_x,
    _px_y,
    draw,
)
from slide_games.models import Level
from slide_games.renderer import Renderer
from slide_games.themes import DARK

# ── Color ─────────────────────────────────────────────────────────────────────


class TestColor:
    def test_construction(self):
        c = Color(100, 150, 200)
        assert (c.r, c.g, c.b) == (100, 150, 200)
        assert c.a == 255

    def test_construction_with_alpha(self):
        c = Color(10, 20, 30, 128)
        assert c.a == 128

    def test_wraps_via_bitmask(self):
        c = Color(300, -10, 256)
        assert c.r == (300 & 0xFF)
        assert c.g == (-10 & 0xFF)
        assert c.b == (256 & 0xFF)

    def test_from_hex(self):
        c = Color.from_hex("#ff8000")
        assert (c.r, c.g, c.b) == (255, 128, 0)

    def test_from_hex_no_hash(self):
        c = Color.from_hex("00ff80")
        assert (c.r, c.g, c.b) == (0, 255, 128)

    def test_rgb_dict_range(self):
        c = Color(255, 0, 128)
        d = c._rgb()
        assert d["red"] == pytest.approx(1.0)
        assert d["green"] == pytest.approx(0.0)
        assert d["blue"] == pytest.approx(128 / 255)

    def test_equality(self):
        assert Color(1, 2, 3) == Color(1, 2, 3)
        assert Color(1, 2, 3) != Color(1, 2, 4)

    def test_named_colors_are_color_instances(self):
        for c in (BLACK, WHITE, RED, GREEN, BLUE):
            assert isinstance(c, Color)


# ── Rect ──────────────────────────────────────────────────────────────────────


class TestRect:
    def test_construction(self):
        r = Rect(10, 20, 300, 150)
        assert (r.x, r.y, r.width, r.height) == (10, 20, 300, 150)

    def test_edges(self):
        r = Rect(10, 20, 300, 150)
        assert r.left == 10
        assert r.top == 20
        assert r.right == 310
        assert r.bottom == 170

    def test_center(self):
        r = Rect(0, 0, 200, 100)
        assert r.centerx == 100
        assert r.centery == 50
        assert r.center == (100, 50)

    def test_corners(self):
        r = Rect(10, 20, 100, 50)
        assert r.topleft == (10, 20)
        assert r.topright == (110, 20)
        assert r.bottomleft == (10, 70)
        assert r.bottomright == (110, 70)

    def test_move(self):
        r = Rect(10, 20, 100, 50)
        r2 = r.move(5, -5)
        assert r2.x == 15 and r2.y == 15
        assert r2.width == 100 and r2.height == 50

    def test_inflate(self):
        r = Rect(100, 100, 200, 100)
        r2 = r.inflate(20, 10)
        assert r2.width == 220
        assert r2.height == 110
        assert r2.center == r.center

    def test_collidepoint_inside(self):
        assert Rect(0, 0, 100, 100).collidepoint(50, 50)

    def test_collidepoint_outside(self):
        assert not Rect(0, 0, 100, 100).collidepoint(150, 50)

    def test_colliderect(self):
        r1 = Rect(0, 0, 100, 100)
        r2 = Rect(50, 50, 100, 100)
        assert r1.colliderect(r2)
        assert not r1.colliderect(Rect(200, 200, 50, 50))

    def test_equality(self):
        assert Rect(1, 2, 3, 4) == Rect(1, 2, 3, 4)
        assert Rect(1, 2, 3, 4) != Rect(1, 2, 3, 5)


# ── Surface ───────────────────────────────────────────────────────────────────


class TestSurface:
    def test_fill_adds_update_page_properties(self):
        s = Surface("slide1")
        s.fill(Color(0, 0, 0))
        reqs = s.get_requests()
        assert len(reqs) == 1
        assert "updatePageProperties" in reqs[0]

    def test_fill_uses_slide_id(self):
        s = Surface("my_slide")
        s.fill(WHITE)
        reqs = s.get_requests()
        assert len(reqs) == 1
        assert reqs[0]["updatePageProperties"]["objectId"] == "my_slide"

    def test_fill_tuple_color(self):
        s = Surface("s1")
        s.fill((255, 0, 0))
        reqs = s.get_requests()
        rgb = reqs[0]["updatePageProperties"]["pageProperties"]["pageBackgroundFill"]["solidFill"][
            "color"
        ]["rgbColor"]
        assert rgb["red"] == pytest.approx(1.0)

    def test_get_requests_returns_copy(self):
        s = Surface("s1")
        s.fill(BLACK)
        r1 = s.get_requests()
        r1.clear()
        assert len(s.get_requests()) == 1  # original not mutated


# ── coordinate conversion ─────────────────────────────────────────────────────


class TestCoordConversion:
    def test_full_width_maps_to_slide_width(self):
        assert _px_w(SCREEN_W) == _SLIDE_W_EMU

    def test_full_height_maps_to_slide_height(self):
        assert _px_h(SCREEN_H) == _SLIDE_H_EMU

    def test_origin_maps_to_zero(self):
        assert _px_x(0) == 0
        assert _px_y(0) == 0

    def test_minimum_one_emu(self):
        assert _px_w(0) == 1
        assert _px_h(0) == 1


# ── draw.rect ─────────────────────────────────────────────────────────────────


class TestDrawRect:
    def _reqs(self, **kw):
        s = Surface("s")
        draw.rect(s, RED, Rect(10, 10, 200, 100), **kw)
        return s.get_requests()

    def test_creates_rectangle(self):
        reqs = self._reqs()
        creates = [r for r in reqs if "createShape" in r]
        assert len(creates) == 1
        assert creates[0]["createShape"]["shapeType"] == "RECTANGLE"

    def test_creates_round_rectangle_with_border_radius(self):
        s = Surface("s")
        draw.rect(s, RED, Rect(10, 10, 200, 100), border_radius=10)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert creates[0]["createShape"]["shapeType"] == "ROUND_RECTANGLE"

    def test_fill_request_included(self):
        reqs = self._reqs()
        fills = [r for r in reqs if "updateShapeProperties" in r]
        assert len(fills) == 1

    def test_outline_mode_when_width_gt_0(self):
        reqs = self._reqs(width=2)
        fill = next(r for r in reqs if "updateShapeProperties" in r)
        outline = fill["updateShapeProperties"]["shapeProperties"]["outline"]
        assert "propertyState" not in outline  # NOT_RENDERED only for filled

    def test_no_outline_when_width_0(self):
        reqs = self._reqs(width=0)
        fill = next(r for r in reqs if "updateShapeProperties" in r)
        outline = fill["updateShapeProperties"]["shapeProperties"]["outline"]
        assert outline.get("propertyState") == "NOT_RENDERED"

    def test_tuple_rect_accepted(self):
        s = Surface("s")
        draw.rect(s, RED, (10, 10, 200, 100))
        assert any("createShape" in r for r in s.get_requests())

    def test_tuple_color_accepted(self):
        s = Surface("s")
        draw.rect(s, (255, 0, 0), Rect(0, 0, 100, 100))
        assert any("createShape" in r for r in s.get_requests())


# ── draw.circle ───────────────────────────────────────────────────────────────


class TestDrawCircle:
    def test_creates_ellipse(self):
        s = Surface("s")
        draw.circle(s, BLUE, (100, 100), 50)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert creates[0]["createShape"]["shapeType"] == "ELLIPSE"

    def test_circle_is_square_bounding_box(self):
        s = Surface("s")
        draw.circle(s, BLUE, (960, 540), 100)
        create = next(r for r in s.get_requests() if "createShape" in r)
        size = create["createShape"]["elementProperties"]["size"]
        assert size["width"]["magnitude"] == size["height"]["magnitude"]


# ── draw.ellipse ──────────────────────────────────────────────────────────────


class TestDrawEllipse:
    def test_creates_ellipse(self):
        s = Surface("s")
        draw.ellipse(s, GREEN, Rect(100, 100, 400, 200))
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert creates[0]["createShape"]["shapeType"] == "ELLIPSE"

    def test_bounding_box_preserved(self):
        s = Surface("s")
        draw.ellipse(s, GREEN, Rect(0, 0, SCREEN_W, SCREEN_H))
        create = next(r for r in s.get_requests() if "createShape" in r)
        size = create["createShape"]["elementProperties"]["size"]
        assert size["width"]["magnitude"] == _SLIDE_W_EMU
        assert size["height"]["magnitude"] == _SLIDE_H_EMU


# ── draw.line ─────────────────────────────────────────────────────────────────


class TestDrawLine:
    def test_creates_rectangle(self):
        s = Surface("s")
        draw.line(s, WHITE, (0, 540), (1920, 540), 4)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 1
        assert creates[0]["createShape"]["shapeType"] == "RECTANGLE"

    def test_zero_length_creates_nothing(self):
        s = Surface("s")
        draw.line(s, WHITE, (100, 100), (100, 100))
        assert s.get_requests() == []

    def test_horizontal_line_has_transform(self):
        s = Surface("s")
        draw.line(s, WHITE, (0, 540), (1920, 540), 4)
        create = next(r for r in s.get_requests() if "createShape" in r)
        t = create["createShape"]["elementProperties"]["transform"]
        assert "scaleX" in t and "shearX" in t

    def test_diagonal_line_has_nonzero_shear(self):
        s = Surface("s")
        draw.line(s, WHITE, (0, 0), (1920, 1080), 4)
        create = next(r for r in s.get_requests() if "createShape" in r)
        t = create["createShape"]["elementProperties"]["transform"]
        assert abs(t["shearX"]) > 0.1
        assert abs(t["shearY"]) > 0.1


# ── draw.text ─────────────────────────────────────────────────────────────────


class TestDrawText:
    def test_creates_text_box(self):
        s = Surface("s")
        draw.text(s, "Hello", Rect(0, 0, 400, 60), color=WHITE, font_size=24)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert creates[0]["createShape"]["shapeType"] == "TEXT_BOX"

    def test_insert_text_request(self):
        s = Surface("s")
        draw.text(s, "Score: 42", Rect(0, 0, 400, 60))
        inserts = [r for r in s.get_requests() if "insertText" in r]
        assert len(inserts) == 1
        assert inserts[0]["insertText"]["text"] == "Score: 42"

    def test_style_request_included(self):
        s = Surface("s")
        draw.text(s, "Hi", Rect(0, 0, 200, 50), font_size=32, bold=True)
        styles = [r for r in s.get_requests() if "updateTextStyle" in r]
        assert len(styles) == 1
        assert styles[0]["updateTextStyle"]["style"]["fontSize"]["magnitude"] == 32
        assert styles[0]["updateTextStyle"]["style"]["bold"] is True

    def test_alignment_request(self):
        s = Surface("s")
        draw.text(s, "X", Rect(0, 0, 200, 50), align="CENTER")
        para = [r for r in s.get_requests() if "updateParagraphStyle" in r]
        assert para[0]["updateParagraphStyle"]["style"]["alignment"] == "CENTER"

    def test_tuple_rect_accepted(self):
        s = Surface("s")
        draw.text(s, "Hi", (0, 0, 200, 50))
        assert any("createShape" in r for r in s.get_requests())


# ── draw.polygon ──────────────────────────────────────────────────────────────


class TestDrawPolygon:
    def test_triangle_creates_three_lines(self):
        s = Surface("s")
        draw.polygon(s, RED, [(100, 100), (200, 100), (150, 200)])
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 3  # 3 edges

    def test_fewer_than_two_points_does_nothing(self):
        s = Surface("s")
        draw.polygon(s, RED, [(100, 100)])
        assert s.get_requests() == []


# ── render hook integration ───────────────────────────────────────────────────

TINY = Level.from_string("###\n#S#\n#G#\n###")


class TestRenderHook:
    def test_default_game_does_not_use_custom_render(self):
        game = MazeGame(TINY)
        assert type(game).render is BaseGame.render

    def test_custom_render_overrides_grid(self):
        """A game that overrides render should NOT produce the default grid rects."""

        class CustomGame(MazeGame):
            def render(self, surface, state):
                surface.fill(Color(10, 20, 30))
                draw.circle(surface, Color(255, 0, 0), (960, 400), 100)

        game = CustomGame(TINY)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = {s: f"sl{i}" for i, s in enumerate(game.get_all_states())}
        reqs = r.render_state(s2s[state], state, s2s)

        # Should have updatePageProperties (from fill) and an ELLIPSE (from circle)
        assert any("updatePageProperties" in req for req in reqs)
        ellipses = [
            req
            for req in reqs
            if "createShape" in req and req["createShape"]["shapeType"] == "ELLIPSE"
        ]
        assert len(ellipses) >= 1

    def test_custom_render_still_has_dpad(self):
        """D-pad nav buttons are always added, even with custom render."""

        class CustomGame(MazeGame):
            def render(self, surface, state):
                surface.fill(Color(0, 0, 0))

        game = CustomGame(TINY)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = {s: f"sl{i}" for i, s in enumerate(game.get_all_states())}
        reqs = r.render_state(s2s[state], state, s2s)

        round_rects = [
            req
            for req in reqs
            if "createShape" in req and req["createShape"]["shapeType"] == "ROUND_RECTANGLE"
        ]
        assert len(round_rects) == 4

    def test_default_game_still_has_grid_rects(self):
        """Non-overriding game still uses the default grid renderer."""
        game = MazeGame(TINY)
        r = Renderer(game, DARK)
        state = game.get_initial_state()
        s2s = {s: f"sl{i}" for i, s in enumerate(game.get_all_states())}
        reqs = r.render_state(s2s[state], state, s2s)

        rects = [
            req
            for req in reqs
            if "createShape" in req and req["createShape"]["shapeType"] == "RECTANGLE"
        ]
        assert len(rects) >= 1  # at least the floor background


# ── Color helpers ─────────────────────────────────────────────────────────────


class TestColorHelpers:
    def test_lerp_midpoint(self):
        c = BLACK.lerp(WHITE, 0.5)
        assert c.r == 127 or c.r == 128
        assert c.g == c.r and c.b == c.r

    def test_lerp_t0_returns_self(self):
        c = RED.lerp(BLUE, 0.0)
        assert (c.r, c.g, c.b) == (RED.r, RED.g, RED.b)

    def test_lerp_t1_returns_other(self):
        c = RED.lerp(BLUE, 1.0)
        assert (c.r, c.g, c.b) == (BLUE.r, BLUE.g, BLUE.b)

    def test_lerp_clamps_below_0(self):
        c = RED.lerp(BLUE, -5.0)
        assert (c.r, c.g, c.b) == (RED.r, RED.g, RED.b)

    def test_lerp_clamps_above_1(self):
        c = RED.lerp(BLUE, 99.0)
        assert (c.r, c.g, c.b) == (BLUE.r, BLUE.g, BLUE.b)

    def test_darken_halves_components(self):
        c = Color(200, 100, 50).darken(0.5)
        assert c.r == 100
        assert c.g == 50
        assert c.b == 25

    def test_darken_zero_gives_black(self):
        c = WHITE.darken(0.0)
        assert (c.r, c.g, c.b) == (0, 0, 0)

    def test_lighten_towards_white(self):
        c = BLACK.lighten(0.5)
        assert c.r == 127 or c.r == 128

    def test_lighten_full_gives_white(self):
        c = BLACK.lighten(1.0)
        assert (c.r, c.g, c.b) == (255, 255, 255)

    def test_with_alpha(self):
        c = RED.with_alpha(128)
        assert c.r == RED.r and c.a == 128

    def test_grayscale_white_stays_white(self):
        c = WHITE.grayscale()
        assert c.r == c.g == c.b == 255

    def test_grayscale_black_stays_black(self):
        c = BLACK.grayscale()
        assert c.r == c.g == c.b == 0

    def test_grayscale_uses_luminance_weights(self):
        c = Color(255, 0, 0).grayscale()
        assert c.r == round(0.299 * 255)

    def test_complementary_white_gives_black(self):
        c = WHITE.complementary()
        assert (c.r, c.g, c.b) == (0, 0, 0)

    def test_complementary_red_gives_cyan(self):
        c = Color(255, 0, 0).complementary()
        assert (c.r, c.g, c.b) == (0, 255, 255)

    def test_complementary_is_involutory(self):
        c = Color(100, 150, 200).complementary().complementary()
        assert (c.r, c.g, c.b) == (100, 150, 200)


# ── Rect helpers ──────────────────────────────────────────────────────────────


class TestRectHelpers:
    def test_midleft(self):
        r = Rect(10, 20, 100, 60)
        assert r.midleft == (10, 50)

    def test_midright(self):
        r = Rect(10, 20, 100, 60)
        assert r.midright == (110, 50)

    def test_midtop(self):
        r = Rect(10, 20, 100, 60)
        assert r.midtop == (60, 20)

    def test_midbottom(self):
        r = Rect(10, 20, 100, 60)
        assert r.midbottom == (60, 80)

    def test_scale_by_doubles(self):
        r = Rect(0, 0, 100, 50)
        r2 = r.scale_by(2.0, 2.0)
        assert r2.width == 200 and r2.height == 100

    def test_padded_shrinks(self):
        r = Rect(0, 0, 100, 60)
        r2 = r.padded(10, 5)
        assert r2.width == 80 and r2.height == 50
        assert r2.x == 10 and r2.y == 5

    def test_clip_intersection(self):
        r1 = Rect(0, 0, 100, 100)
        r2 = Rect(50, 50, 100, 100)
        c = r1.clip(r2)
        assert c == Rect(50, 50, 50, 50)

    def test_clip_no_overlap_gives_zero_size(self):
        r1 = Rect(0, 0, 50, 50)
        r2 = Rect(100, 100, 50, 50)
        c = r1.clip(r2)
        assert c.width == 0 or c.height == 0

    def test_union_bounding_box(self):
        r1 = Rect(0, 0, 50, 50)
        r2 = Rect(60, 60, 50, 50)
        u = r1.union(r2)
        assert u.left == 0 and u.top == 0
        assert u.right == 110 and u.bottom == 110

    def test_contains_smaller_rect(self):
        outer = Rect(0, 0, 200, 200)
        inner = Rect(10, 10, 50, 50)
        assert outer.contains(inner)

    def test_not_contains_overlapping(self):
        r1 = Rect(0, 0, 100, 100)
        r2 = Rect(50, 50, 100, 100)
        assert not r1.contains(r2)


# ── Vector2 ───────────────────────────────────────────────────────────────────


class TestVector2:
    def test_construction(self):
        v = Vector2(3.0, 4.0)
        assert v.x == 3.0 and v.y == 4.0

    def test_magnitude(self):
        assert Vector2(3, 4).magnitude == pytest.approx(5.0)

    def test_magnitude_zero(self):
        assert Vector2(0, 0).magnitude == pytest.approx(0.0)

    def test_normalize(self):
        v = Vector2(3, 4).normalize()
        assert v.magnitude == pytest.approx(1.0)
        assert v.x == pytest.approx(0.6)
        assert v.y == pytest.approx(0.8)

    def test_normalize_zero_returns_zero(self):
        v = Vector2(0, 0).normalize()
        assert v.x == 0.0 and v.y == 0.0

    def test_add(self):
        v = Vector2(1, 2) + Vector2(3, 4)
        assert (v.x, v.y) == (4.0, 6.0)

    def test_sub(self):
        v = Vector2(5, 7) - Vector2(2, 3)
        assert (v.x, v.y) == (3.0, 4.0)

    def test_mul_scalar(self):
        v = Vector2(2, 3) * 2
        assert (v.x, v.y) == (4.0, 6.0)

    def test_rmul_scalar(self):
        v = 3 * Vector2(1, 2)
        assert (v.x, v.y) == (3.0, 6.0)

    def test_neg(self):
        v = -Vector2(1, -2)
        assert (v.x, v.y) == (-1.0, 2.0)

    def test_dot(self):
        assert Vector2(1, 0).dot(Vector2(0, 1)) == pytest.approx(0.0)
        assert Vector2(1, 0).dot(Vector2(1, 0)) == pytest.approx(1.0)

    def test_cross(self):
        assert Vector2(1, 0).cross(Vector2(0, 1)) == pytest.approx(1.0)
        assert Vector2(0, 1).cross(Vector2(1, 0)) == pytest.approx(-1.0)

    def test_distance_to(self):
        assert Vector2(0, 0).distance_to(Vector2(3, 4)) == pytest.approx(5.0)

    def test_lerp_midpoint(self):
        v = Vector2(0, 0).lerp(Vector2(10, 20), 0.5)
        assert (v.x, v.y) == pytest.approx((5.0, 10.0))

    def test_rotate_90_cw_screen(self):
        # CW in screen space: right → down
        v = Vector2(1, 0).rotate(90)
        assert v.x == pytest.approx(0.0, abs=1e-9)
        assert v.y == pytest.approx(1.0, abs=1e-9)

    def test_rotate_180(self):
        v = Vector2(1, 0).rotate(180)
        assert v.x == pytest.approx(-1.0, abs=1e-9)
        assert v.y == pytest.approx(0.0, abs=1e-9)

    def test_rotate_360_identity(self):
        orig = Vector2(3, 4)
        v = orig.rotate(360)
        assert v.x == pytest.approx(orig.x, abs=1e-9)
        assert v.y == pytest.approx(orig.y, abs=1e-9)

    def test_as_tuple(self):
        assert Vector2(3, 4).as_tuple() == (3.0, 4.0)

    def test_iter(self):
        x, y = Vector2(7, 8)
        assert x == 7.0 and y == 8.0

    def test_copy(self):
        v = Vector2(1, 2)
        v2 = v.copy()
        assert v == v2 and v is not v2

    def test_equality(self):
        assert Vector2(1, 2) == Vector2(1, 2)
        assert Vector2(1, 2) != Vector2(1, 3)

    def test_repr_contains_x_y(self):
        r = repr(Vector2(1.5, 2.5))
        assert "1.5" in r and "2.5" in r

    def test_from_polar(self):
        v = Vector2.from_polar(1.0, 0)
        assert v.x == pytest.approx(1.0, abs=1e-9)
        assert v.y == pytest.approx(0.0, abs=1e-9)


# ── draw.lines ────────────────────────────────────────────────────────────────


class TestDrawLines:
    def test_two_points_creates_one_segment(self):
        s = Surface("s")
        draw.lines(s, RED, [(0, 0), (100, 100)], width=2)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 1

    def test_three_points_creates_two_segments(self):
        s = Surface("s")
        draw.lines(s, RED, [(0, 0), (100, 0), (100, 100)], width=2)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 2

    def test_closed_adds_extra_segment(self):
        s = Surface("s")
        draw.lines(s, RED, [(0, 0), (100, 0), (100, 100)], width=2, closed=True)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 3

    def test_fewer_than_two_points_does_nothing(self):
        s = Surface("s")
        draw.lines(s, RED, [(0, 0)], width=2)
        assert s.get_requests() == []

    def test_empty_points_does_nothing(self):
        s = Surface("s")
        draw.lines(s, RED, [], width=2)
        assert s.get_requests() == []


# ── draw.triangle ─────────────────────────────────────────────────────────────


class TestDrawTriangle:
    def test_creates_a_shape(self):
        s = Surface("s")
        draw.triangle(s, RED, Rect(100, 100, 80, 80), direction="up")
        assert len(s.get_requests()) > 0

    def test_shape_type_is_triangle(self):
        for direction in ("up", "down", "left", "right"):
            s = Surface("s")
            draw.triangle(s, RED, Rect(0, 0, 100, 100), direction=direction)
            creates = [r for r in s.get_requests() if "createShape" in r]
            assert len(creates) >= 1

    def test_has_transform(self):
        s = Surface("s")
        draw.triangle(s, RED, Rect(0, 0, 100, 100), direction="right")
        create = next(r for r in s.get_requests() if "createShape" in r)
        assert "elementProperties" in create["createShape"]


# ── draw.shape ────────────────────────────────────────────────────────────────


class TestDrawShape:
    def test_diamond_shape_type(self):
        s = Surface("s")
        draw.shape(s, RED, "DIAMOND", Rect(100, 100, 200, 200))
        create = next(r for r in s.get_requests() if "createShape" in r)
        assert create["createShape"]["shapeType"] == "DIAMOND"

    def test_star_5_shape_type(self):
        s = Surface("s")
        draw.shape(s, RED, "STAR_5", Rect(0, 0, 100, 100))
        create = next(r for r in s.get_requests() if "createShape" in r)
        assert create["createShape"]["shapeType"] == "STAR_5"

    def test_fill_request_included(self):
        s = Surface("s")
        draw.shape(s, GREEN, "HEXAGON", Rect(0, 0, 100, 100))
        assert any("updateShapeProperties" in r for r in s.get_requests())

    def test_outline_mode_when_width_gt_0(self):
        s = Surface("s")
        draw.shape(s, RED, "DIAMOND", Rect(0, 0, 100, 100), width=3)
        fill = next(r for r in s.get_requests() if "updateShapeProperties" in r)
        outline = fill["updateShapeProperties"]["shapeProperties"]["outline"]
        assert "propertyState" not in outline


# ── draw.progress_bar ─────────────────────────────────────────────────────────


class TestDrawProgressBar:
    def test_normal_creates_two_rects(self):
        s = Surface("s")
        draw.progress_bar(s, Rect(0, 0, 300, 20), 50, 100, GREEN, DARK_GRAY)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 2

    def test_zero_max_creates_only_background(self):
        s = Surface("s")
        draw.progress_bar(s, Rect(0, 0, 300, 20), 0, 0, GREEN, DARK_GRAY)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 1

    def test_full_value_creates_two_rects(self):
        s = Surface("s")
        draw.progress_bar(s, Rect(0, 0, 300, 20), 100, 100, GREEN, DARK_GRAY)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 2

    def test_zero_value_still_creates_two_rects(self):
        s = Surface("s")
        draw.progress_bar(s, Rect(0, 0, 300, 20), 0, 100, GREEN, DARK_GRAY)
        creates = [r for r in s.get_requests() if "createShape" in r]
        assert len(creates) == 2
