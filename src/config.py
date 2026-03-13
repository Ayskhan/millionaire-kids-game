from pathlib import Path
import os
import sys

APP_NAME = "Детский миллионер"
APP_VERSION = "1.3.0"
BUILD_NAME = f"MillionaireKids-v{APP_VERSION}"
WINDOW_WIDTH = 1360
WINDOW_HEIGHT = 768
WINDOW_TITLE = f"{APP_NAME} v{APP_VERSION}"
FPS = 60

if getattr(sys, "frozen", False):
    BASE_DIR = Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
else:
    BASE_DIR = Path(__file__).resolve().parent.parent

QUESTIONS_FILE = BASE_DIR / "questions.json"
ASSETS_DIR = BASE_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
APP_DATA_DIR = Path(os.getenv("APPDATA", str(BASE_DIR))) / "MillionaireKidsGame"
PLAYER_DATA_DIR = APP_DATA_DIR
PLAYER_DATA_FILE = PLAYER_DATA_DIR / "players.json"
QUESTIONS_DATA_DIR = APP_DATA_DIR / "questions"
ACTIVE_QUESTIONS_FILE = QUESTIONS_DATA_DIR / "questions_active.json"
QUESTIONS_REMOTE_URL = os.getenv(
    "MILLIONAIRE_QUESTIONS_URL",
    "https://raw.githubusercontent.com/Ayskhan/millionaire-kids-game/main/questions.json",
)
QUESTIONS_REMOTE_TIMEOUT = 12

FONT_NAME = "Segoe UI"
MAX_NAME_LENGTH = 18
QUESTION_COUNT_PER_TIER = 5

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
    "64 000",
    "125 000",
    "200 000",
    "300 000",
    "400 000",
    "500 000",
    "650 000",
    "800 000",
    "900 000",
    "1 000 000",
]

MILESTONE_LEVELS = {5, 10}
DIFFICULTY_ORDER = ("easy", "medium", "hard", "very_hard")
DIFFICULTY_LABELS = {
    "easy": "Лёгкий",
    "medium": "Средний",
    "hard": "Сложный",
    "very_hard": "Очень сложный",
}

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
BUTTON_TEAL = (28, 173, 170)
BUTTON_TEAL_HOVER = (48, 191, 186)
BORDER = (215, 227, 255)
SOFT_BG = (240, 245, 255)
AUDIENCE_BAR = (104, 192, 119)
REMOVED_OVERLAY = (220, 228, 244)
INPUT_BG = (249, 251, 255)
SCROLL_TRACK = (228, 235, 251)
SCROLL_THUMB = (109, 141, 232)
MILESTONE_GLOW = (255, 224, 131)
PROFILE_CARD = (247, 250, 255)

MENU_BUTTON_TEXT = 34
MAIN_TEXT = 28
SMALL_TEXT = 22
TITLE_TEXT = 46
