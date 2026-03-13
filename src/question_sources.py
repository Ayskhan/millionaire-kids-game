from __future__ import annotations

import os
import socket
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from src.config import (
    ACTIVE_QUESTIONS_FILE,
    BASE_DIR,
    QUESTIONS_DATA_DIR,
    QUESTIONS_FILE,
    QUESTIONS_REMOTE_TIMEOUT,
    QUESTIONS_REMOTE_URL,
)
from src.data import DataValidationError, QuestionPool, load_questions, load_questions_from_text


@dataclass(frozen=True)
class QuestionSourceState:
    question_pool: QuestionPool
    source_label: str
    source_path: Path
    message: str


@dataclass(frozen=True)
class QuestionUpdateResult:
    success: bool
    message: str
    question_pool: QuestionPool | None = None
    source_label: str | None = None
    source_path: Path | None = None


class QuestionSourceManager:
    def __init__(
        self,
        bundled_file: Path = QUESTIONS_FILE,
        remote_url: str = QUESTIONS_REMOTE_URL,
    ) -> None:
        self.bundled_file = bundled_file
        self.remote_url = remote_url

    def _storage_file(self) -> Path:
        try:
            QUESTIONS_DATA_DIR.mkdir(parents=True, exist_ok=True)
            return ACTIVE_QUESTIONS_FILE
        except OSError:
            fallback_dir = BASE_DIR / ".question_data"
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir / "questions_active.json"

    def load_active_questions(self) -> QuestionSourceState:
        bundled_pool = load_questions(self.bundled_file)

        try:
            active_file = self._storage_file()
        except OSError:
            return QuestionSourceState(
                question_pool=bundled_pool,
                source_label="встроенные вопросы",
                source_path=self.bundled_file,
                message="Не удалось открыть папку для обновлений. Используются встроенные вопросы.",
            )

        if not active_file.exists():
            return QuestionSourceState(
                question_pool=bundled_pool,
                source_label="встроенные вопросы",
                source_path=self.bundled_file,
                message="Сейчас используются встроенные вопросы.",
            )

        try:
            active_pool = load_questions(active_file)
        except DataValidationError:
            return QuestionSourceState(
                question_pool=bundled_pool,
                source_label="встроенные вопросы",
                source_path=self.bundled_file,
                message="Сохранённый файл вопросов повреждён. Используются встроенные вопросы.",
            )
        except OSError:
            return QuestionSourceState(
                question_pool=bundled_pool,
                source_label="встроенные вопросы",
                source_path=self.bundled_file,
                message="Не получилось прочитать сохранённые вопросы. Используются встроенные вопросы.",
            )

        return QuestionSourceState(
            question_pool=active_pool,
            source_label="обновлённые вопросы",
            source_path=active_file,
            message="Сейчас используются обновлённые вопросы.",
        )

    def download_questions_update(self) -> QuestionUpdateResult:
        if not self.remote_url:
            return QuestionUpdateResult(False, "Адрес обновления вопросов не настроен.")

        try:
            target_file = self._storage_file()
        except OSError:
            return QuestionUpdateResult(
                False,
                "Не получилось открыть папку для сохранения вопросов.",
            )

        request = urllib.request.Request(
            self.remote_url,
            headers={"User-Agent": "MillionaireKidsGame/1.0"},
        )

        try:
            with urllib.request.urlopen(request, timeout=QUESTIONS_REMOTE_TIMEOUT) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return QuestionUpdateResult(
                    False,
                    "На GitHub не найден файл вопросов. Текущая база не изменена.",
                )
            return QuestionUpdateResult(
                False,
                "GitHub временно не отдал файл вопросов. Текущая база не изменена.",
            )
        except (urllib.error.URLError, TimeoutError, socket.timeout):
            return QuestionUpdateResult(
                False,
                "Нет связи с интернетом или GitHub недоступен. Используем текущие вопросы.",
            )
        except OSError:
            return QuestionUpdateResult(
                False,
                "Не удалось скачать файл вопросов. Используем текущие вопросы.",
            )

        if not payload:
            return QuestionUpdateResult(
                False,
                "Получен пустой файл вопросов. Текущая база не изменена.",
            )

        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError:
            return QuestionUpdateResult(
                False,
                "Файл вопросов имеет неверную кодировку. Текущая база не изменена.",
            )

        try:
            question_pool = load_questions_from_text(text, source_name=self.remote_url)
        except DataValidationError as exc:
            return QuestionUpdateResult(
                False,
                f"Новый файл вопросов неверный: {exc}. Текущая база сохранена.",
            )

        temp_file = target_file.with_suffix(".tmp")
        try:
            target_file.parent.mkdir(parents=True, exist_ok=True)
            temp_file.write_text(text, encoding="utf-8")
            os.replace(temp_file, target_file)
        except OSError:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError:
                    pass
            return QuestionUpdateResult(
                False,
                "Не получилось сохранить новый файл вопросов на компьютере.",
            )

        return QuestionUpdateResult(
            True,
            "Новые вопросы загружены. Они будут использоваться в следующей игре.",
            question_pool=question_pool,
            source_label="обновлённые вопросы",
            source_path=target_file,
        )
