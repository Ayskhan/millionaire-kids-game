from __future__ import annotations

import random
from dataclasses import dataclass, field

from src.config import DIFFICULTY_ORDER, MILESTONE_LEVELS, PRIZE_LADDER, QUESTION_COUNT_PER_TIER
from src.data import Question, QuestionPool


@dataclass
class GameSession:
    question_pool: QuestionPool
    rng: random.Random = field(default_factory=random.Random)
    level_index: int = 0
    selected_questions: list[Question] = field(default_factory=list)
    available_answers: set[int] = field(default_factory=lambda: {0, 1, 2, 3})
    used_fifty: bool = False
    used_remove_one: bool = False
    used_audience: bool = False
    audience_votes: dict[int, int] | None = None
    last_won_amount: str = "0"
    game_finished: bool = False
    victory: bool = False

    def _pick_question(self, question: Question) -> Question:
        indexed_options = list(enumerate(question.options))
        self.rng.shuffle(indexed_options)
        new_options = [option for _, option in indexed_options]
        new_answer_index = next(
            idx
            for idx, (original_index, _) in enumerate(indexed_options)
            if original_index == question.answer_index
        )
        return Question(
            difficulty=question.difficulty,
            text=question.text,
            options=new_options,
            answer_index=new_answer_index,
            category=question.category,
        )

    def start_new_game(self) -> None:
        self.level_index = 0
        self.last_won_amount = "0"
        self.game_finished = False
        self.victory = False
        self.used_fifty = False
        self.used_remove_one = False
        self.used_audience = False
        self.audience_votes = None

        stage_questions: list[Question] = []
        for difficulty in DIFFICULTY_ORDER:
            stage_questions.extend(
                self._pick_question(question)
                for question in self.rng.sample(self.question_pool[difficulty], QUESTION_COUNT_PER_TIER)
            )
        self.selected_questions = stage_questions
        self._reset_question_state()

    @property
    def current_question(self) -> Question:
        return self.selected_questions[self.level_index]

    @property
    def current_amount(self) -> str:
        return PRIZE_LADDER[self.level_index]

    @property
    def current_difficulty(self) -> str:
        return self.current_question.difficulty

    @property
    def level_number(self) -> int:
        return self.level_index + 1

    @property
    def correct_answer(self) -> int:
        return self.current_question.answer_index

    @property
    def is_last_question(self) -> bool:
        return self.level_index == len(self.selected_questions) - 1

    @property
    def secured_amount(self) -> str:
        completed = self.level_index
        secured = "0"
        for milestone in sorted(MILESTONE_LEVELS):
            if completed >= milestone:
                secured = PRIZE_LADDER[milestone - 1]
        return secured

    def _reset_question_state(self) -> None:
        self.available_answers = {0, 1, 2, 3}
        self.audience_votes = None

    def is_answer_available(self, answer_index: int) -> bool:
        return answer_index in self.available_answers

    def use_fifty(self) -> str:
        if self.used_fifty:
            return "Подсказка 50:50 уже использована."

        wrong_answers = [index for index in range(4) if index != self.correct_answer]
        keep_wrong = self.rng.choice(wrong_answers)
        self.available_answers = {self.correct_answer, keep_wrong}
        self.used_fifty = True
        self.audience_votes = None
        return "50:50 убрала два неверных ответа."

    def use_remove_one(self) -> str:
        if self.used_remove_one:
            return "Подсказка «Убрать 1» уже использована."

        wrong_answers = {index for index in range(4) if index != self.correct_answer}
        visible_wrong = sorted(wrong_answers & self.available_answers)
        hidden_wrong = sorted(wrong_answers - self.available_answers)

        if len(visible_wrong) >= 2:
            to_hide = self.rng.choice(visible_wrong)
            self.available_answers.remove(to_hide)
        elif len(visible_wrong) == 1 and hidden_wrong:
            to_hide = visible_wrong[0]
            replacement = self.rng.choice(hidden_wrong)
            self.available_answers.remove(to_hide)
            self.available_answers.add(replacement)

        self.used_remove_one = True
        self.audience_votes = None
        return "Подсказка убрала один неверный вариант."

    def use_audience(self) -> dict[int, int]:
        if self.used_audience and self.audience_votes is not None:
            return self.audience_votes

        visible_answers = sorted(self.available_answers)
        hidden_answers = [index for index in range(4) if index not in self.available_answers]
        wrong_visible = [index for index in visible_answers if index != self.correct_answer]
        votes = {index: 0 for index in range(4)}

        if not wrong_visible:
            votes[self.correct_answer] = 100
        else:
            difficulty_bonus = {
                "easy": 74,
                "medium": 66,
                "hard": 58,
                "very_hard": 52,
            }[self.current_difficulty]
            correct_percent = self.rng.randint(difficulty_bonus - 6, difficulty_bonus + 4)
            remaining = 100 - correct_percent
            weights = [self.rng.randint(1, 9) for _ in wrong_visible]
            total_weight = sum(weights)
            assigned = 0

            for idx, answer_index in enumerate(wrong_visible):
                if idx == len(wrong_visible) - 1:
                    part = remaining - assigned
                else:
                    part = max(1, remaining * weights[idx] // total_weight)
                    assigned += part
                votes[answer_index] = part

            overflow = sum(votes[index] for index in wrong_visible) - remaining
            if overflow > 0:
                votes[wrong_visible[-1]] = max(0, votes[wrong_visible[-1]] - overflow)
            elif overflow < 0:
                votes[wrong_visible[-1]] += -overflow

            highest_wrong = max(votes[index] for index in wrong_visible)
            if correct_percent <= highest_wrong:
                correct_percent = highest_wrong + 1
                needed = correct_percent + sum(votes[index] for index in wrong_visible) - 100
                for answer_index in reversed(wrong_visible):
                    if needed <= 0:
                        break
                    cut = min(needed, votes[answer_index])
                    votes[answer_index] -= cut
                    needed -= cut

            votes[self.correct_answer] = 100 - sum(
                votes[index] for index in range(4) if index != self.correct_answer
            )

        for hidden in hidden_answers:
            votes[hidden] = 0

        self.used_audience = True
        self.audience_votes = votes
        return votes

    def check_answer(self, answer_index: int) -> bool:
        return answer_index == self.correct_answer

    def handle_correct_answer(self) -> None:
        self.last_won_amount = self.current_amount
        if self.is_last_question:
            self.game_finished = True
            self.victory = True
            return

        self.level_index += 1
        self._reset_question_state()

    def handle_wrong_answer(self) -> None:
        self.last_won_amount = self.secured_amount
        self.game_finished = True
        self.victory = False

    def is_milestone_question(self) -> bool:
        return self.level_number in MILESTONE_LEVELS
