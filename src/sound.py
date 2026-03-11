from __future__ import annotations

from pathlib import Path

import pygame

from src.config import SOUNDS_DIR


class SoundManager:
    def __init__(self) -> None:
        self.enabled = False
        self.sounds: dict[str, pygame.mixer.Sound] = {}

        try:
            pygame.mixer.init()
            self.enabled = True
        except pygame.error:
            self.enabled = False

        if not self.enabled:
            return

        for name in ("click", "correct", "wrong"):
            self._load_sound(name, SOUNDS_DIR / f"{name}.wav")

    def _load_sound(self, name: str, path: Path) -> None:
        if not path.exists():
            return
        try:
            self.sounds[name] = pygame.mixer.Sound(str(path))
        except pygame.error:
            pass

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        sound = self.sounds.get(name)
        if sound is not None:
            sound.play()
