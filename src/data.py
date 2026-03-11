from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import PRIZE_LADDER, QUESTIONS_FILE


class DataValidationError(Exception):
    pass


@dataclass(frozen=True)
class Question:
    level: int
    text: str
    options: list[str]
    answer_index: int
    category: str


def load_questions(path: Path | None = None) -> dict[int, list[Question]]:
    file_path = path or QUESTIONS_FILE
    try:
        raw_data = json.loads(file_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise DataValidationError(f"Файл с вопросами не найден: {file_path}") from exc
    except json.JSONDecodeError as exc:
        raise DataValidationError(
            f"Файл вопросов содержит ошибку JSON: строка {exc.lineno}, столбец {exc.colno}"
        ) from exc

    if not isinstance(raw_data, list):
        raise DataValidationError("Файл вопросов должен содержать список вопросов.")

    if len(raw_data) < 50:
        raise DataValidationError("В базе должно быть минимум 50 вопросов.")

    grouped: dict[int, list[Question]] = {level: [] for level in range(1, len(PRIZE_LADDER) + 1)}

    for index, item in enumerate(raw_data, start=1):
        if not isinstance(item, dict):
            raise DataValidationError(f"Вопрос №{index} имеет неверный формат.")

        level = item.get("level")
        text = item.get("question")
        options = item.get("options")
        answer_index = item.get("answer_index")
        category = item.get("category", "Общее")

        if not isinstance(level, int) or level not in grouped:
            raise DataValidationError(f"У вопроса №{index} указан неверный уровень.")
        if not isinstance(text, str) or not text.strip():
            raise DataValidationError(f"У вопроса №{index} нет текста вопроса.")
        if not isinstance(options, list) or len(options) != 4 or not all(
            isinstance(option, str) and option.strip() for option in options
        ):
            raise DataValidationError(
                f"У вопроса №{index} должно быть ровно 4 непустых варианта ответа."
            )
        if not isinstance(answer_index, int) or answer_index not in range(4):
            raise DataValidationError(
                f"У вопроса №{index} неверно указан правильный ответ."
            )

        grouped[level].append(
            Question(
                level=level,
                text=text.strip(),
                options=[option.strip() for option in options],
                answer_index=answer_index,
                category=str(category).strip() or "Общее",
            )
        )

    empty_levels = [str(level) for level, questions in grouped.items() if not questions]
    if empty_levels:
        joined = ", ".join(empty_levels)
        raise DataValidationError(f"Для уровней {joined} нет ни одного вопроса.")

    return grouped
