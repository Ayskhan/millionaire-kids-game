from pathlib import Path
import sys

WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 720
WINDOW_TITLE = "Детский миллионер"
FPS = 60

if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_FILE = BASE_DIR / "questions.json"
ASSETS_DIR = BASE_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"

FONT_NAME = "Segoe UI"

PRIZE_LADDER = [
    "100",
    "200",
    "300",
    "500",
    "1 000",
    "2 000",
    "4 000",
    "8 000",
    "16 000",
    "32 000",
    "125 000",
    "1 000 000",
]

BACKGROUND_TOP = (14, 39, 96)
BACKGROUND_BOTTOM = (76, 155, 255)
PANEL_COLOR = (255, 255, 255)
PANEL_SHADOW = (17, 31, 79)
TEXT_DARK = (25, 44, 84)
TEXT_LIGHT = (255, 255, 255)
ACCENT = (255, 198, 50)
BUTTON_BLUE = (56, 118, 255)
BUTTON_BLUE_HOVER = (76, 136, 255)
BUTTON_DISABLED = (170, 180, 205)
BUTTON_GREEN = (61, 186, 104)
BUTTON_RED = (226, 94, 94)
BUTTON_ORANGE = (255, 156, 51)
BUTTON_PURPLE = (142, 109, 242)
BORDER = (215, 227, 255)
SOFT_BG = (240, 245, 255)
AUDIENCE_BAR = (104, 192, 119)
REMOVED_OVERLAY = (220, 228, 244)

MENU_BUTTON_TEXT = 34
MAIN_TEXT = 28
SMALL_TEXT = 22
TITLE_TEXT = 46
