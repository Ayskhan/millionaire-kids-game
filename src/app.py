from __future__ import annotations

import random
import sys
from dataclasses import dataclass

import pygame

from src.config import (
    ACCENT,
    BACKGROUND_BOTTOM,
    BACKGROUND_TOP,
    BORDER,
    BUTTON_BLUE,
    BUTTON_BLUE_HOVER,
    BUTTON_GREEN,
    BUTTON_ORANGE,
    BUTTON_PURPLE,
    BUTTON_RED,
    BUTTON_TEAL,
    BUTTON_TEAL_HOVER,
    DIFFICULTY_LABELS,
    FONT_NAME,
    FPS,
    INPUT_BG,
    MAIN_TEXT,
    MAX_NAME_LENGTH,
    MENU_BUTTON_TEXT,
    MILESTONE_GLOW,
    MILESTONE_LEVELS,
    PANEL_COLOR,
    PRIZE_LADDER,
    PROFILE_CARD,
    SMALL_TEXT,
    TEXT_DARK,
    TEXT_LIGHT,
    TITLE_TEXT,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from src.data import DataValidationError
from src.logic import GameSession
from src.profiles import ensure_player, format_score, load_profiles, parse_score, update_player_result
from src.question_sources import QuestionSourceManager, QuestionSourceState
from src.sound import SoundManager
from src.ui import (
    Button,
    draw_audience_chart,
    draw_badge,
    draw_rounded_panel,
    draw_scrollbar,
    draw_vertical_gradient,
    render_wrapped_text,
    wrap_text_lines,
)


@dataclass
class PendingTransition:
    ends_at: int
    answer_correct: bool


@dataclass
class MoneySprite:
    x: float
    y: float
    width: int
    height: int
    speed: float
    sway: float
    angle: float
    currency: str
    color: tuple[int, int, int]
    accent: tuple[int, int, int]


class MillionaireApp:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption(WINDOW_TITLE)
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.fonts = {
            "title": pygame.font.SysFont(FONT_NAME, TITLE_TEXT, bold=True),
            "menu": pygame.font.SysFont(FONT_NAME, MENU_BUTTON_TEXT, bold=True),
            "main": pygame.font.SysFont(FONT_NAME, MAIN_TEXT, bold=True),
            "body": pygame.font.SysFont(FONT_NAME, 26),
            "small": pygame.font.SysFont(FONT_NAME, SMALL_TEXT),
            "subtitle": pygame.font.SysFont(FONT_NAME, 30, bold=True),
            "tiny": pygame.font.SysFont(FONT_NAME, 18),
        }
        self.sound = SoundManager()

        self.question_manager = QuestionSourceManager()
        self.question_source_state = self.question_manager.load_active_questions()
        self.session = GameSession(self.question_source_state.question_pool)
        self.session.start_new_game()

        self.profiles = load_profiles()
        self.current_player_name: str | None = None
        self.profile_input = ""
        self.profile_input_active = True
        self.profile_message = "Выбери имя игрока или напиши новое."
        self.profile_buttons: list[tuple[str, Button]] = []
        self.profile_input_rect = pygame.Rect(410, 470, 540, 62)
        self.profile_continue_button = Button(
            pygame.Rect(530, 550, 300, 70),
            "Продолжить",
            self.fonts["main"],
            bg_color=BUTTON_GREEN,
        )
        self._refresh_profile_buttons()

        self.rules_scroll = 0
        self.rules_paragraphs = [
            "1. В игре тебя ждут 20 вопросов и 4 варианта ответа на каждом шаге.",
            "2. Вопросы 1-5 лёгкие. После 5 вопроса у тебя появляется первая несгораемая сумма.",
            "3. Вопросы 6-10 средние. После 10 вопроса сохраняется вторая несгораемая сумма.",
            "4. Вопросы 11-15 сложные, а вопросы 16-20 очень сложные и требуют больше внимания.",
            "5. Если ответ неверный, игра заканчивается, но несгораемые суммы остаются у тебя.",
            "6. Подсказка 50:50 убирает два неправильных ответа.",
            "7. Подсказка Убрать 1 прячет один неправильный ответ.",
            "8. Подсказка Помощь зала показывает голоса. У правильного ответа процент всегда самый высокий.",
            "9. В меню есть кнопка Обновить вопросы. Если есть интернет, игра скачает новый questions.json из GitHub.",
            "10. Если новый файл неверный или интернета нет, игра спокойно продолжит работать на текущих вопросах.",
            "11. Имя игрока и лучший результат сохраняются на компьютере.",
            "12. Если правила длинные, прокручивай колёсиком мыши или клавишами вверх и вниз.",
        ]
        self.rules_lines = self._build_rules_lines()

        self.state = "profile"
        self.running = True
        self.message = "Выбери игрока и начинай игру."
        self.menu_message = self.question_source_state.message
        self.pending_transition: PendingTransition | None = None
        self.selected_answer: int | None = None
        self.show_audience_modal = False
        self.money_sprites: list[MoneySprite] = []
        self.result_saved = False
        self.answer_buttons = self._create_answer_buttons()
        self.menu_buttons = self._create_menu_buttons()
        self.rules_buttons = self._create_rules_buttons()
        self.result_buttons = self._create_result_buttons()
        self.hint_buttons = self._create_hint_buttons()
        self.audience_close_button = Button(
            pygame.Rect(930, 596, 180, 52),
            "Закрыть",
            self.fonts["small"],
            bg_color=BUTTON_BLUE,
        )
        self._sync_answer_buttons()

    def _create_answer_buttons(self) -> list[Button]:
        letters = ["А", "Б", "В", "Г"]
        positions = [
            pygame.Rect(60, 458, 440, 110),
            pygame.Rect(530, 458, 440, 110),
            pygame.Rect(60, 592, 440, 110),
            pygame.Rect(530, 592, 440, 110),
        ]
        return [Button(rect, letters[index], self.fonts["body"]) for index, rect in enumerate(positions)]

    def _create_menu_buttons(self) -> dict[str, Button]:
        return {
            "play": Button(
                pygame.Rect(280, 370, 340, 86),
                "Играть",
                self.fonts["menu"],
                bg_color=BUTTON_GREEN,
            ),
            "rules": Button(
                pygame.Rect(740, 370, 340, 86),
                "Правила",
                self.fonts["menu"],
                bg_color=BUTTON_ORANGE,
            ),
            "update": Button(
                pygame.Rect(280, 484, 340, 86),
                "Обновить вопросы",
                self.fonts["menu"],
                bg_color=BUTTON_TEAL,
                hover_color=BUTTON_TEAL_HOVER,
            ),
            "exit": Button(
                pygame.Rect(740, 484, 340, 86),
                "Выход",
                self.fonts["menu"],
                bg_color=BUTTON_RED,
            ),
        }

    def _create_rules_buttons(self) -> list[Button]:
        return [
            Button(
                pygame.Rect(528, 664, 304, 60),
                "Назад в меню",
                self.fonts["small"],
                bg_color=BUTTON_BLUE,
            )
        ]

    def _create_result_buttons(self) -> list[Button]:
        return [
            Button(
                pygame.Rect(390, 566, 260, 74),
                "Играть снова",
                self.fonts["main"],
                bg_color=BUTTON_GREEN,
            ),
            Button(
                pygame.Rect(710, 566, 260, 74),
                "В меню",
                self.fonts["main"],
                bg_color=BUTTON_BLUE,
            ),
        ]

    def _create_hint_buttons(self) -> dict[str, Button]:
        return {
            "fifty": Button(
                pygame.Rect(60, 240, 180, 62),
                "50:50",
                self.fonts["small"],
                bg_color=BUTTON_ORANGE,
            ),
            "remove_one": Button(
                pygame.Rect(260, 240, 180, 62),
                "Убрать 1",
                self.fonts["small"],
                bg_color=BUTTON_PURPLE,
            ),
            "audience": Button(
                pygame.Rect(460, 240, 220, 62),
                "Помощь зала",
                self.fonts["small"],
                bg_color=BUTTON_GREEN,
            ),
        }

    def _build_rules_lines(self) -> list[str]:
        lines: list[str] = []
        for paragraph in self.rules_paragraphs:
            lines.extend(wrap_text_lines(paragraph, self.fonts["body"], 800))
            lines.append("")
        return lines[:-1] if lines else []

    def _refresh_profile_buttons(self) -> None:
        self.profile_buttons = []
        for index, profile in enumerate(self.profiles[:6]):
            col = index % 2
            row = index // 2
            rect = pygame.Rect(225 + col * 470, 180 + row * 88, 440, 70)
            label = f"{profile.name}  |  лучший: {format_score(profile.best_score)}"
            button = Button(rect, label, self.fonts["small"], bg_color=BUTTON_BLUE)
            self.profile_buttons.append((profile.name, button))

    def _current_player_best_score(self) -> int:
        if not self.current_player_name:
            return 0
        for profile in self.profiles:
            if profile.name.lower() == self.current_player_name.lower():
                return profile.best_score
        return 0

    def _select_player(self, name: str) -> None:
        trimmed = name.strip()[:MAX_NAME_LENGTH]
        if not trimmed:
            self.profile_message = "Напиши имя игрока, чтобы продолжить."
            return

        self.current_player_name = trimmed
        self.profile_input = trimmed
        self.profiles = ensure_player(self.profiles, trimmed)
        self._refresh_profile_buttons()
        self.state = "menu"
        self.message = f"Привет, {trimmed}! Готов к игре?"

    def _store_result_for_player(self) -> None:
        if self.result_saved or not self.current_player_name:
            return

        amount = PRIZE_LADDER[-1] if self.session.victory else self.session.last_won_amount
        self.profiles = update_player_result(
            self.profiles,
            self.current_player_name,
            parse_score(amount),
        )
        self._refresh_profile_buttons()
        self.result_saved = True

    def _render_fit_text(self, text: str, max_width: int, size: int, bold: bool = True) -> pygame.Surface:
        current_size = size
        while current_size >= 12:
            font = pygame.font.SysFont(FONT_NAME, current_size, bold=bold)
            rendered = font.render(text, True, TEXT_DARK)
            if rendered.get_width() <= max_width:
                return rendered
            current_size -= 1
        return pygame.font.SysFont(FONT_NAME, 12, bold=bold).render(text, True, TEXT_DARK)

    def _scroll_rules(self, delta: int) -> None:
        viewport_height = 460
        content_height = len(self.rules_lines) * (self.fonts["body"].get_height() + 8)
        max_scroll = max(0, content_height - viewport_height + 12)
        self.rules_scroll = max(0, min(max_scroll, self.rules_scroll + delta))

    def _apply_question_source(self, source_state: QuestionSourceState, message: str | None = None) -> None:
        self.question_source_state = source_state
        self.session.question_pool = source_state.question_pool
        self.menu_message = message or source_state.message

    def _update_questions(self) -> None:
        if self.state == "game":
            self.menu_message = "Сначала закончи текущую игру, потом обновляй вопросы."
            return

        self.menu_message = "Пробуем скачать новый файл вопросов..."
        self._draw()
        pygame.display.flip()
        pygame.event.pump()

        result = self.question_manager.download_questions_update()
        if result.success:
            source_state = self.question_manager.load_active_questions()
            self._apply_question_source(source_state, result.message)
            return

        self.menu_message = result.message

    def run(self) -> None:
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            pygame.display.flip()
            self.clock.tick(FPS)
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return

            if self.state == "profile":
                self._handle_profile_event(event)
            elif self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "rules":
                self._handle_rules_event(event)
            elif self.state == "game":
                self._handle_game_event(event)
            elif self.state == "result":
                self._handle_result_event(event)

    def _handle_profile_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.profile_input_active = self.profile_input_rect.collidepoint(event.pos)

        for profile_name, button in self.profile_buttons:
            if button.handle_event(event):
                self.sound.play("click")
                self._select_player(profile_name)
                return

        if self.profile_continue_button.handle_event(event):
            self.sound.play("click")
            self._select_player(self.profile_input)
            return

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self._select_player(self.profile_input)
            elif event.key == pygame.K_BACKSPACE and self.profile_input_active:
                self.profile_input = self.profile_input[:-1]
            elif self.profile_input_active and event.unicode:
                allowed = event.unicode.isalnum() or event.unicode in " -_АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯабвгдеёжзийклмнопрстуфхцчшщъыьэюя"
                if allowed and len(self.profile_input) < MAX_NAME_LENGTH:
                    self.profile_input += event.unicode

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if self.menu_buttons["play"].handle_event(event):
            self.sound.play("click")
            self._restart_game()
            self.state = "game"
        elif self.menu_buttons["rules"].handle_event(event):
            self.sound.play("click")
            self.rules_scroll = 0
            self.state = "rules"
        elif self.menu_buttons["update"].handle_event(event):
            self.sound.play("click")
            self._update_questions()
        elif self.menu_buttons["exit"].handle_event(event):
            self.running = False

    def _handle_rules_event(self, event: pygame.event.Event) -> None:
        if self.rules_buttons[0].handle_event(event):
            self.sound.play("click")
            self.state = "menu"
            return

        if event.type == pygame.MOUSEWHEEL:
            self._scroll_rules(-event.y * 36)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_DOWN:
                self._scroll_rules(36)
            elif event.key == pygame.K_UP:
                self._scroll_rules(-36)
            elif event.key == pygame.K_PAGEDOWN:
                self._scroll_rules(160)
            elif event.key == pygame.K_PAGEUP:
                self._scroll_rules(-160)

    def _handle_game_event(self, event: pygame.event.Event) -> None:
        if self.show_audience_modal:
            if self.audience_close_button.handle_event(event):
                self.sound.play("click")
                self.show_audience_modal = False
            return

        if self.pending_transition is not None:
            return

        if self.hint_buttons["fifty"].handle_event(event):
            self.sound.play("click")
            self.message = self.session.use_fifty()
            self._sync_answer_buttons()
            return

        if self.hint_buttons["remove_one"].handle_event(event):
            self.sound.play("click")
            self.message = self.session.use_remove_one()
            self._sync_answer_buttons()
            return

        if self.hint_buttons["audience"].handle_event(event):
            self.sound.play("click")
            self.session.use_audience()
            self.show_audience_modal = True
            self.message = "Зал проголосовал. Посмотри на проценты."
            self._sync_hint_buttons()
            return

        for index, button in enumerate(self.answer_buttons):
            if button.handle_event(event):
                self.sound.play("click")
                self._process_answer(index)
                break

    def _handle_result_event(self, event: pygame.event.Event) -> None:
        if self.result_buttons[0].handle_event(event):
            self.sound.play("click")
            self._restart_game()
            self.state = "game"
        elif self.result_buttons[1].handle_event(event):
            self.sound.play("click")
            self.state = "menu"
    def _update(self) -> None:
        if self.state == "result" and self.session.victory:
            self._update_money_sprites()
            return

        if self.state != "game" or self.pending_transition is None:
            return

        if pygame.time.get_ticks() < self.pending_transition.ends_at:
            return

        transition = self.pending_transition
        self.pending_transition = None
        self.selected_answer = None

        if transition.answer_correct:
            self.session.handle_correct_answer()
            if self.session.game_finished:
                self._create_money_sprites()
                self._store_result_for_player()
                self.state = "result"
                return
            self.message = "Верно! Переходим к следующему вопросу."
            self._sync_answer_buttons()
        else:
            self.session.handle_wrong_answer()
            self._store_result_for_player()
            self.state = "result"

    def _process_answer(self, answer_index: int) -> None:
        if not self.session.is_answer_available(answer_index):
            return

        self.selected_answer = answer_index
        is_correct = self.session.check_answer(answer_index)
        if is_correct:
            self.sound.play("correct")
            if self.session.is_milestone_question():
                self.message = "Правильно! Это несгораемая сумма."
            else:
                self.message = "Правильно! Молодец!"
        else:
            self.sound.play("wrong")
            correct_text = self.session.current_question.options[self.session.correct_answer]
            self.message = f"Неверно. Правильный ответ: {correct_text}."

        self.pending_transition = PendingTransition(
            ends_at=pygame.time.get_ticks() + 1200,
            answer_correct=is_correct,
        )
        self._sync_answer_buttons(show_feedback=True, answered_correctly=is_correct)

    def _restart_game(self) -> None:
        self.session.start_new_game()
        self.pending_transition = None
        self.selected_answer = None
        self.show_audience_modal = False
        self.money_sprites = []
        self.result_saved = False
        player_name = self.current_player_name or "игрок"
        self.message = f"{player_name}, ответь на вопрос и пройди все 20 шагов."
        self._sync_answer_buttons()

    def _create_money_sprites(self) -> None:
        self.money_sprites = []
        for _ in range(28):
            currency = random.choice(["$", "€"])
            if currency == "$":
                color = random.choice([(128, 222, 146), (100, 204, 122), (151, 231, 163)])
                accent = (31, 113, 55)
            else:
                color = random.choice([(126, 219, 198), (103, 205, 179), (155, 236, 215)])
                accent = (24, 102, 98)

            self.money_sprites.append(
                MoneySprite(
                    x=random.randint(100, WINDOW_WIDTH - 100),
                    y=random.randint(-640, -30),
                    width=random.randint(88, 124),
                    height=random.randint(42, 58),
                    speed=random.uniform(1.6, 3.4),
                    sway=random.uniform(-1.2, 1.2),
                    angle=random.uniform(-16, 16),
                    currency=currency,
                    color=color,
                    accent=accent,
                )
            )

    def _update_money_sprites(self) -> None:
        for sprite in self.money_sprites:
            sprite.y += sprite.speed
            sprite.x += sprite.sway
            sprite.angle += sprite.sway * 0.45
            if sprite.y > WINDOW_HEIGHT + 70:
                sprite.y = random.randint(-260, -40)
                sprite.x = random.randint(100, WINDOW_WIDTH - 100)
                sprite.speed = random.uniform(1.6, 3.4)

    def _draw_money_sprite(self, sprite: MoneySprite) -> None:
        bill = pygame.Surface((sprite.width, sprite.height), pygame.SRCALPHA)
        bill_rect = bill.get_rect()
        pygame.draw.rect(bill, sprite.color, bill_rect, border_radius=14)
        pygame.draw.rect(bill, (255, 255, 255), bill_rect.inflate(-10, -10), width=2, border_radius=10)
        pygame.draw.circle(
            bill,
            sprite.accent,
            (sprite.width // 2, sprite.height // 2),
            min(sprite.width, sprite.height) // 4,
        )
        symbol = self.fonts["subtitle"].render(sprite.currency, True, (255, 255, 255))
        bill.blit(
            symbol,
            (
                bill.get_width() // 2 - symbol.get_width() // 2,
                bill.get_height() // 2 - symbol.get_height() // 2,
            ),
        )
        shine = pygame.Surface((sprite.width // 4, sprite.height - 16), pygame.SRCALPHA)
        shine.fill((255, 255, 255, 60))
        bill.blit(shine, (10, 8))
        rotated = pygame.transform.rotate(bill, sprite.angle)
        rect = rotated.get_rect(center=(int(sprite.x), int(sprite.y)))
        self.screen.blit(rotated, rect)

    def _sync_hint_buttons(self) -> None:
        self.hint_buttons["fifty"].disabled = self.session.used_fifty or self.pending_transition is not None
        self.hint_buttons["remove_one"].disabled = self.session.used_remove_one or self.pending_transition is not None
        self.hint_buttons["audience"].disabled = self.session.used_audience or self.pending_transition is not None

    def _sync_answer_buttons(self, show_feedback: bool = False, answered_correctly: bool = False) -> None:
        letters = ["А", "Б", "В", "Г"]
        current_question = self.session.current_question
        for index, button in enumerate(self.answer_buttons):
            button.text = f"{letters[index]}. {current_question.options[index]}"
            button.disabled = not self.session.is_answer_available(index) or self.pending_transition is not None
            button.removed = not self.session.is_answer_available(index)
            button.bg_color = BUTTON_BLUE
            button.hover_color = BUTTON_BLUE_HOVER
            button.keep_color_when_disabled = False

            if show_feedback and index == self.selected_answer:
                button.bg_color = BUTTON_GREEN if answered_correctly else BUTTON_RED
                button.hover_color = button.bg_color
                button.removed = False
                button.disabled = True
                button.keep_color_when_disabled = True

            if show_feedback and not answered_correctly and index == self.session.correct_answer:
                button.bg_color = BUTTON_GREEN
                button.hover_color = BUTTON_GREEN
                button.removed = False
                button.disabled = True
                button.keep_color_when_disabled = True

        self._sync_hint_buttons()

    def _draw(self) -> None:
        draw_vertical_gradient(self.screen, BACKGROUND_TOP, BACKGROUND_BOTTOM)

        if self.state == "profile":
            self._draw_profile_screen()
        elif self.state == "menu":
            self._draw_menu()
        elif self.state == "rules":
            self._draw_rules()
        elif self.state == "game":
            self._draw_game()
        elif self.state == "result":
            self._draw_result()

    def _draw_profile_screen(self) -> None:
        panel = pygame.Rect(120, 46, 1120, 676)
        draw_rounded_panel(self.screen, panel, radius=34)

        title = self.fonts["title"].render("Кто сегодня играет?", True, TEXT_DARK)
        subtitle = self.fonts["body"].render("Выбери имя из списка или напиши новое.", True, TEXT_DARK)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, 84))
        self.screen.blit(subtitle, (panel.centerx - subtitle.get_width() // 2, 140))

        if self.profile_buttons:
            label = self.fonts["subtitle"].render("Игроки, которые уже играли", True, TEXT_DARK)
            self.screen.blit(label, (240, 172))
            for profile_name, button in self.profile_buttons:
                button.draw(self.screen)
                for profile in self.profiles:
                    if profile.name == profile_name:
                        extra = self.fonts["tiny"].render(
                            f"Последний раз: {profile.last_played or 'ещё не играл'}",
                            True,
                            TEXT_DARK,
                        )
                        self.screen.blit(extra, (button.rect.left + 18, button.rect.bottom - 22))
                        break
        else:
            empty = self.fonts["body"].render("Пока нет игроков. Напиши своё имя ниже.", True, TEXT_DARK)
            self.screen.blit(empty, (panel.centerx - empty.get_width() // 2, 270))

        input_label = self.fonts["subtitle"].render("Новое имя", True, TEXT_DARK)
        self.screen.blit(input_label, (panel.centerx - input_label.get_width() // 2, 420))

        pygame.draw.rect(self.screen, INPUT_BG, self.profile_input_rect, border_radius=20)
        pygame.draw.rect(
            self.screen,
            ACCENT if self.profile_input_active else BORDER,
            self.profile_input_rect,
            width=3,
            border_radius=20,
        )
        input_text = self.profile_input or "Напиши имя"
        input_color = TEXT_DARK if self.profile_input else (115, 130, 170)
        rendered = self.fonts["body"].render(input_text, True, input_color)
        self.screen.blit(
            rendered,
            (self.profile_input_rect.left + 20, self.profile_input_rect.centery - rendered.get_height() // 2),
        )

        self.profile_continue_button.draw(self.screen)

        info_rect = pygame.Rect(220, 628, 920, 30)
        render_wrapped_text(
            self.screen,
            f"База вопросов: {self.question_source_state.source_label}.",
            self.fonts["small"],
            TEXT_DARK,
            info_rect,
            align="center",
        )

        message_rect = pygame.Rect(250, 662, 860, 30)
        render_wrapped_text(
            self.screen,
            self.profile_message,
            self.fonts["small"],
            TEXT_DARK,
            message_rect,
            align="center",
        )
    def _draw_menu(self) -> None:
        panel = pygame.Rect(180, 70, 1000, 620)
        draw_rounded_panel(self.screen, panel, radius=34)

        title = self.fonts["title"].render("Детский миллионер", True, TEXT_DARK)
        subtitle = self.fonts["body"].render("Ответь на 20 вопросов и доберись до 1 000 000!", True, TEXT_DARK)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 120))
        self.screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 180))

        player_name = self.current_player_name or "Игрок"
        best_score = format_score(self._current_player_best_score())
        player_badge = pygame.Rect(320, 228, 720, 52)
        draw_badge(
            self.screen,
            player_badge,
            f"Игрок: {player_name} | Лучший результат: {best_score}",
            self.fonts["small"],
        )

        source_badge = pygame.Rect(360, 292, 640, 46)
        draw_badge(
            self.screen,
            source_badge,
            f"База вопросов: {self.question_source_state.source_label}",
            self.fonts["small"],
        )

        for button in self.menu_buttons.values():
            button.draw(self.screen)

        status_rect = pygame.Rect(260, 600, 840, 54)
        pygame.draw.rect(self.screen, PROFILE_CARD, status_rect, border_radius=20)
        pygame.draw.rect(self.screen, BORDER, status_rect, width=2, border_radius=20)
        render_wrapped_text(
            self.screen,
            self.menu_message,
            self.fonts["small"],
            TEXT_DARK,
            status_rect.inflate(-20, -12),
            align="center",
        )

    def _draw_rules(self) -> None:
        panel = pygame.Rect(90, 30, 1180, 708)
        draw_rounded_panel(self.screen, panel, radius=34)

        title = self.fonts["title"].render("Правила игры", True, TEXT_DARK)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 24))

        viewport_rect = pygame.Rect(140, 118, 860, 470)
        pygame.draw.rect(self.screen, PROFILE_CARD, viewport_rect, border_radius=24)
        pygame.draw.rect(self.screen, BORDER, viewport_rect, width=2, border_radius=24)

        previous_clip = self.screen.get_clip()
        self.screen.set_clip(viewport_rect)
        y = viewport_rect.top + 14 - self.rules_scroll
        line_height = self.fonts["body"].get_height() + 8
        for line in self.rules_lines:
            rendered = self.fonts["body"].render(line, True, TEXT_DARK)
            self.screen.blit(rendered, (viewport_rect.left + 18, y))
            y += line_height
        self.screen.set_clip(previous_clip)

        content_height = len(self.rules_lines) * line_height
        draw_scrollbar(
            self.screen,
            pygame.Rect(1014, 130, 16, 446),
            viewport_rect.height,
            content_height,
            self.rules_scroll,
        )

        scroll_hint = pygame.Rect(140, 606, 860, 30)
        render_wrapped_text(
            self.screen,
            "Прокрутка: колёсико мыши, стрелки вверх и вниз, Page Up и Page Down.",
            self.fonts["small"],
            TEXT_DARK,
            scroll_hint,
            align="center",
        )

        self.rules_buttons[0].draw(self.screen)

    def _draw_game(self) -> None:
        left_panel = pygame.Rect(30, 24, 1000, 720)
        right_panel = pygame.Rect(1050, 24, 280, 720)
        draw_rounded_panel(self.screen, left_panel, radius=30)
        draw_rounded_panel(self.screen, right_panel, radius=30)

        title = self.fonts["subtitle"].render(
            f"Вопрос {self.session.level_number} из {len(PRIZE_LADDER)}",
            True,
            TEXT_DARK,
        )
        self.screen.blit(title, (60, 44))

        badge_rect = pygame.Rect(520, 38, 180, 52)
        draw_badge(self.screen, badge_rect, f"Сумма: {self.session.current_amount}", self.fonts["small"])

        category_rect = pygame.Rect(720, 38, 270, 52)
        draw_badge(
            self.screen,
            category_rect,
            f"Тема: {self.session.current_question.category}",
            self.fonts["small"],
        )

        player_rect = pygame.Rect(60, 92, 300, 34)
        render_wrapped_text(
            self.screen,
            f"Игрок: {self.current_player_name or 'гость'}",
            self.fonts["small"],
            TEXT_DARK,
            player_rect,
        )

        question_panel = pygame.Rect(60, 140, 930, 120)
        pygame.draw.rect(self.screen, PANEL_COLOR, question_panel, border_radius=24)
        pygame.draw.rect(self.screen, ACCENT, question_panel, width=4, border_radius=24)
        render_wrapped_text(
            self.screen,
            self.session.current_question.text,
            self.fonts["main"],
            TEXT_DARK,
            question_panel.inflate(-26, -16),
            line_gap=6,
            align="center",
        )

        hint_title = self.fonts["small"].render("Подсказки", True, TEXT_DARK)
        self.screen.blit(hint_title, (60, 286))
        for button in self.hint_buttons.values():
            button.draw(self.screen)

        message_panel = pygame.Rect(690, 272, 300, 92)
        pygame.draw.rect(self.screen, PROFILE_CARD, message_panel, border_radius=22)
        pygame.draw.rect(self.screen, BORDER, message_panel, width=2, border_radius=22)
        render_wrapped_text(
            self.screen,
            self.message,
            self.fonts["tiny"],
            TEXT_DARK,
            message_panel.inflate(-16, -10),
            line_gap=4,
        )

        milestone_text = f"Несгораемая сумма сейчас: {self.session.secured_amount}"
        if self.session.is_milestone_question():
            milestone_text = "Этот вопрос ведёт к несгораемой сумме!"
        milestone_rect = pygame.Rect(60, 382, 560, 32)
        render_wrapped_text(
            self.screen,
            milestone_text,
            self.fonts["small"],
            TEXT_DARK,
            milestone_rect,
        )

        difficulty_rect = pygame.Rect(640, 382, 350, 32)
        render_wrapped_text(
            self.screen,
            f"Сложность: {DIFFICULTY_LABELS[self.session.current_difficulty]}",
            self.fonts["small"],
            TEXT_DARK,
            difficulty_rect,
            align="right",
        )

        for button in self.answer_buttons:
            button.draw(self.screen)

        self._draw_prize_ladder(right_panel)

        if self.show_audience_modal and self.session.audience_votes:
            modal = pygame.Rect(180, 110, 980, 540)
            draw_audience_chart(
                self.screen,
                modal,
                self.session.audience_votes,
                self.session.current_question.options,
                self.fonts,
            )
            self.audience_close_button.draw(self.screen)

    def _draw_prize_ladder(self, panel: pygame.Rect) -> None:
        title = self.fonts["subtitle"].render("Призы", True, TEXT_DARK)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 18))

        gap = 5
        available_height = panel.height - 110
        item_height = max(24, min(34, (available_height - gap * (len(PRIZE_LADDER) - 1)) // len(PRIZE_LADDER)))
        start_y = panel.bottom - 28 - item_height

        for reverse_index, amount in enumerate(reversed(PRIZE_LADDER)):
            level = len(PRIZE_LADDER) - reverse_index
            y = start_y - reverse_index * (item_height + gap)
            item_rect = pygame.Rect(panel.left + 12, y, panel.width - 24, item_height)

            if level == self.session.level_number and not self.session.game_finished:
                color = ACCENT
            elif level < self.session.level_number:
                color = (194, 234, 202)
            else:
                color = (238, 243, 255)

            pygame.draw.rect(self.screen, color, item_rect, border_radius=12)
            border_color = MILESTONE_GLOW if level in MILESTONE_LEVELS else BORDER
            border_width = 3 if level in MILESTONE_LEVELS else 2
            pygame.draw.rect(self.screen, border_color, item_rect, width=border_width, border_radius=12)

            level_text = self._render_fit_text(str(level), 26, 16)
            amount_text = self._render_fit_text(amount, item_rect.width - 80, 20)
            self.screen.blit(
                level_text,
                (item_rect.left + 10, item_rect.centery - level_text.get_height() // 2),
            )
            self.screen.blit(
                amount_text,
                (item_rect.right - amount_text.get_width() - 10, item_rect.centery - amount_text.get_height() // 2),
            )

            if level in MILESTONE_LEVELS:
                mark = self.fonts["tiny"].render("НС", True, TEXT_DARK)
                self.screen.blit(
                    mark,
                    (item_rect.left + 40, item_rect.centery - mark.get_height() // 2),
                )
    def _draw_result(self) -> None:
        if self.session.victory:
            for sprite in self.money_sprites:
                self._draw_money_sprite(sprite)

        panel = pygame.Rect(250, 120, 860, 540)
        draw_rounded_panel(self.screen, panel, radius=34)

        if self.session.victory:
            title_text = "Ты победил!"
            subtitle_text = "Поздравляем! Ты прошёл все 20 вопросов."
            amount = PRIZE_LADDER[-1]
            color = BUTTON_GREEN
        else:
            title_text = "Игра окончена"
            subtitle_text = f"Несгораемая сумма: {self.session.last_won_amount}"
            amount = self.session.last_won_amount
            color = BUTTON_RED

        ribbon = pygame.Rect(445, 164, 470, 68)
        pygame.draw.rect(self.screen, color, ribbon, border_radius=22)
        pygame.draw.rect(self.screen, (255, 255, 255), ribbon, width=2, border_radius=22)

        title = self.fonts["title"].render(title_text, True, TEXT_LIGHT)
        self.screen.blit(title, (ribbon.centerx - title.get_width() // 2, ribbon.centery - title.get_height() // 2))

        subtitle = self.fonts["body"].render(subtitle_text, True, TEXT_DARK)
        self.screen.blit(subtitle, (panel.centerx - subtitle.get_width() // 2, 324))

        reached = self.fonts["subtitle"].render(f"Результат игрока: {amount}", True, TEXT_DARK)
        self.screen.blit(reached, (panel.centerx - reached.get_width() // 2, 374))

        best_line = self.fonts["small"].render(
            f"Лучший результат {self.current_player_name or 'игрока'}: {format_score(self._current_player_best_score())}",
            True,
            TEXT_DARK,
        )
        self.screen.blit(best_line, (panel.centerx - best_line.get_width() // 2, 426))

        if self.session.victory:
            note = self.fonts["small"].render("Вокруг летят яркие доллары и евро!", True, TEXT_DARK)
            self.screen.blit(note, (panel.centerx - note.get_width() // 2, 470))

        for button in self.result_buttons:
            button.draw(self.screen)


def run_game() -> int:
    try:
        app = MillionaireApp()
    except DataValidationError as exc:
        print(f"Ошибка данных: {exc}")
        return 1
    except pygame.error as exc:
        print(f"Ошибка pygame: {exc}")
        return 1

    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(run_game())
