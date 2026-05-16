import pytest

from slide_games.models import Level, Position


class TestPosition:
    def test_move(self):
        p = Position(2, 3)
        assert p.move(1, 0) == Position(3, 3)
        assert p.move(0, -1) == Position(2, 2)
        assert p.move(-1, 1) == Position(1, 4)

    def test_immutable(self):
        p = Position(1, 1)
        with pytest.raises((AttributeError, TypeError)):
            p.x = 99  # type: ignore[misc]

    def test_hashable_deduplication(self):
        s = {Position(1, 1), Position(1, 1), Position(2, 2)}
        assert len(s) == 2

    def test_equality(self):
        assert Position(3, 4) == Position(3, 4)
        assert Position(3, 4) != Position(4, 3)


class TestLevel:
    GRID = "#####\n#S..#\n#.###\n#..G#\n#####"

    def test_from_string_dimensions(self):
        level = Level.from_string(self.GRID)
        assert level.width == 5
        assert level.height == 5

    def test_get_in_bounds(self):
        level = Level.from_string(self.GRID)
        assert level.get(Position(1, 1)) == "S"
        assert level.get(Position(0, 0)) == "#"
        assert level.get(Position(3, 3)) == "G"

    def test_get_out_of_bounds_returns_wall(self):
        level = Level.from_string(self.GRID)
        assert level.get(Position(-1, 0)) == "#"
        assert level.get(Position(99, 99)) == "#"

    def test_is_passable_floor(self):
        level = Level.from_string(self.GRID)
        assert level.is_passable(Position(1, 1))  # S
        assert level.is_passable(Position(2, 1))  # .
        assert level.is_passable(Position(3, 3))  # G

    def test_is_passable_wall(self):
        level = Level.from_string(self.GRID)
        assert not level.is_passable(Position(0, 0))  # #
        assert not level.is_passable(Position(2, 2))  # #

    def test_find_present(self):
        level = Level.from_string(self.GRID)
        assert level.find("S") == Position(1, 1)
        assert level.find("G") == Position(3, 3)

    def test_find_absent(self):
        level = Level.from_string(self.GRID)
        assert level.find("X") is None

    def test_find_all(self):
        level = Level.from_string("#p#\n#p#")
        pellets = level.find_all("p")
        assert len(pellets) == 2
        assert Position(1, 0) in pellets
        assert Position(1, 1) in pellets

    def test_find_all_empty(self):
        level = Level.from_string("###\n###")
        assert level.find_all("p") == []
