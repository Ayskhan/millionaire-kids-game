from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import DIFFICULTY_ORDER, QUESTIONS_FILE


class DataValidationError(Exception):
    pass


@dataclass(frozen=True)
class Question:
    difficulty: str
    text: str
    options: list[str]
    answer_index: int
    category: str


def load_questions(path: Path | None = None) -> dict[str, list[Question]]:
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

    grouped: dict[str, list[Question]] = {difficulty: [] for difficulty in DIFFICULTY_ORDER}

    for index, item in enumerate(raw_data, start=1):
        if not isinstance(item, dict):
            raise DataValidationError(f"Вопрос №{index} имеет неверный формат.")

        difficulty = item.get("difficulty")
        text = item.get("question")
        options = item.get("options")
        answer_index = item.get("answer_index")
        category = item.get("category", "Общее")

        if difficulty not in grouped:
            raise DataValidationError(f"У вопроса №{index} указана неверная сложность.")
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

        grouped[difficulty].append(
            Question(
                difficulty=difficulty,
                text=text.strip(),
                options=[option.strip() for option in options],
                answer_index=answer_index,
                category=str(category).strip() or "Общее",
            )
        )

    if len(raw_data) < 45:
        raise DataValidationError("В базе должно быть минимум 45 вопросов.")

    missing = [difficulty for difficulty, questions in grouped.items() if len(questions) < 10]
    if missing:
        joined = ", ".join(missing)
        raise DataValidationError(f"Для сложностей {joined} недостаточно вопросов.")

    return grouped