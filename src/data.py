from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.config import DIFFICULTY_ORDER, QUESTION_COUNT_PER_TIER, QUESTIONS_FILE


class DataValidationError(Exception):
    pass


@dataclass(frozen=True)
class Question:
    difficulty: str
    text: str
    options: list[str]
    answer_index: int
    category: str


QuestionPool = dict[str, list[Question]]


def load_questions(path: Path | None = None) -> QuestionPool:
    return load_questions_from_path(path or QUESTIONS_FILE)


def load_questions_from_path(path: Path) -> QuestionPool:
    try:
        text = path.read_text(encoding="utf-8-sig")
    except FileNotFoundError as exc:
        raise DataValidationError(f"Файл с вопросами не найден: {path}") from exc
    except OSError as exc:
        raise DataValidationError(f"Не удалось прочитать файл вопросов: {path}") from exc

    return load_questions_from_text(text, source_name=str(path))


def load_questions_from_text(text: str, source_name: str = "строка") -> QuestionPool:
    try:
        raw_data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise DataValidationError(
            f"Файл вопросов содержит ошибку JSON: строка {exc.lineno}, столбец {exc.colno}"
        ) from exc

    return validate_questions_payload(raw_data, source_name=source_name)


def validate_questions_payload(raw_data: object, source_name: str = "данные") -> QuestionPool:
    if not isinstance(raw_data, list):
        raise DataValidationError(f"Источник {source_name} должен содержать список вопросов.")

    grouped: QuestionPool = {difficulty: [] for difficulty in DIFFICULTY_ORDER}

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
        if not isinstance(options, list) or len(options) != 4:
            raise DataValidationError(
                f"У вопроса №{index} должно быть ровно 4 варианта ответа."
            )
        if not all(isinstance(option, str) and option.strip() for option in options):
            raise DataValidationError(
                f"У вопроса №{index} все варианты ответа должны быть непустыми строками."
            )
        normalized_options = [option.strip().casefold() for option in options]
        if len(set(normalized_options)) != 4:
            raise DataValidationError(
                f"У вопроса №{index} есть повторяющиеся варианты ответа."
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

    minimum_total = len(DIFFICULTY_ORDER) * QUESTION_COUNT_PER_TIER
    if len(raw_data) < minimum_total:
        raise DataValidationError(
            f"В базе должно быть минимум {minimum_total} вопросов для всех уровней сложности."
        )

    missing = [
        difficulty for difficulty, questions in grouped.items() if len(questions) < QUESTION_COUNT_PER_TIER
    ]
    if missing:
        joined = ", ".join(missing)
        raise DataValidationError(
            f"Для сложностей {joined} недостаточно вопросов. Нужно минимум по {QUESTION_COUNT_PER_TIER}."
        )

    return grouped
