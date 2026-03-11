from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from src.config import BASE_DIR, PLAYER_DATA_DIR, PLAYER_DATA_FILE


@dataclass
class PlayerProfile:
    name: str
    best_score: int = 0
    last_played: str | None = None


def format_score(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def parse_score(value: str) -> int:
    return int(value.replace(" ", "")) if value else 0


def _storage_file() -> Path:
    try:
        PLAYER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        return PLAYER_DATA_FILE
    except OSError:
        fallback_dir = BASE_DIR / ".player_data"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir / "players.json"


def load_profiles() -> list[PlayerProfile]:
    storage_file = _storage_file()
    if not storage_file.exists():
        return []

    raw = json.loads(storage_file.read_text(encoding="utf-8"))
    players = raw.get("players", []) if isinstance(raw, dict) else []
    result: list[PlayerProfile] = []
    for item in players:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()
        if not name:
            continue
        best_score = int(item.get("best_score", 0) or 0)
        last_played = item.get("last_played")
        result.append(PlayerProfile(name=name, best_score=best_score, last_played=last_played))

    result.sort(key=lambda player: (player.last_played or "", player.best_score, player.name.lower()), reverse=True)
    return result


def save_profiles(profiles: list[PlayerProfile]) -> None:
    storage_file = _storage_file()
    payload = {"players": [asdict(profile) for profile in profiles]}
    storage_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def ensure_player(profiles: list[PlayerProfile], name: str) -> list[PlayerProfile]:
    trimmed = name.strip()
    if not trimmed:
        return profiles
    if any(profile.name.lower() == trimmed.lower() for profile in profiles):
        return profiles
    profiles.append(PlayerProfile(name=trimmed))
    save_profiles(profiles)
    return load_profiles()


def update_player_result(profiles: list[PlayerProfile], name: str, score: int) -> list[PlayerProfile]:
    trimmed = name.strip()
    if not trimmed:
        return profiles

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    found = False
    for profile in profiles:
        if profile.name.lower() == trimmed.lower():
            profile.best_score = max(profile.best_score, score)
            profile.last_played = now
            found = True
            break

    if not found:
        profiles.append(PlayerProfile(name=trimmed, best_score=score, last_played=now))

    save_profiles(profiles)
    return load_profiles()
