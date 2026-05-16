from __future__ import annotations

from dataclasses import dataclass

RGB = dict[str, float]


def rgb(r: int, g: int, b: int) -> RGB:
    return {"red": r / 255, "green": g / 255, "blue": b / 255}


@dataclass
class Theme:
    name: str
    background: RGB
    wall: RGB
    floor: RGB
    player: RGB
    goal: RGB
    pellet: RGB
    btn_active: RGB
    btn_inactive: RGB
    btn_text: RGB
    title_text: RGB
    win_text: RGB


DARK = Theme(
    name="dark",
    background=rgb(26, 26, 46),
    wall=rgb(60, 60, 100),
    floor=rgb(40, 40, 70),
    player=rgb(255, 215, 0),
    goal=rgb(50, 200, 80),
    pellet=rgb(220, 220, 220),
    btn_active=rgb(70, 130, 200),
    btn_inactive=rgb(50, 50, 70),
    btn_text=rgb(255, 255, 255),
    title_text=rgb(255, 255, 255),
    win_text=rgb(255, 215, 0),
)

PACMAN = Theme(
    name="pacman",
    background=rgb(0, 0, 0),
    wall=rgb(0, 0, 200),
    floor=rgb(0, 0, 0),
    player=rgb(255, 215, 0),
    goal=rgb(220, 80, 80),
    pellet=rgb(255, 200, 200),
    btn_active=rgb(0, 80, 200),
    btn_inactive=rgb(25, 25, 25),
    btn_text=rgb(255, 255, 255),
    title_text=rgb(255, 215, 0),
    win_text=rgb(255, 215, 0),
)

RETRO = Theme(
    name="retro",
    background=rgb(15, 15, 15),
    wall=rgb(180, 60, 0),
    floor=rgb(30, 30, 30),
    player=rgb(0, 220, 100),
    goal=rgb(255, 230, 0),
    pellet=rgb(0, 180, 220),
    btn_active=rgb(180, 60, 0),
    btn_inactive=rgb(45, 45, 45),
    btn_text=rgb(255, 255, 255),
    title_text=rgb(0, 220, 100),
    win_text=rgb(255, 230, 0),
)
