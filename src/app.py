from __future__ import annotations

import random
import sys
from dataclasses import dataclass

import pygame

from src.config import (
    ACCENT,
    BACKGROUND_BOTTOM,
    BACKGROUND_TOP,
    BUTTON_BLUE,
    BUTTON_BLUE_HOVER,
    BUTTON_GREEN,
    BUTTON_ORANGE,
    BUTTON_PURPLE,
    BUTTON_RED,
    FONT_NAME,
    FPS,
    MAIN_TEXT,
    MENU_BUTTON_TEXT,
    PANEL_COLOR,
    PRIZE_LADDER,
    SMALL_TEXT,
    TEXT_DARK,
    TEXT_LIGHT,
    TITLE_TEXT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
)
from src.data import DataValidationError, load_questions
from src.logic import GameSession
from src.sound import SoundManager
from src.ui import (
    Button,
    draw_audience_chart,
    draw_badge,
    draw_rounded_panel,
    draw_vertical_gradient,
    render_wrapped_text,
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
        }
        self.sound = SoundManager()

        question_pool = load_questions()
        self.session = GameSession(question_pool)

        self.state = "menu"
        self.running = True
        self.message = "Выбери режим в главном меню."
        self.pending_transition: PendingTransition | None = None
        self.selected_answer: int | None = None
        self.show_audience_modal = False
        self.money_sprites: list[MoneySprite] = []
        self.answer_buttons = self._create_answer_buttons()
        self.menu_buttons = self._create_menu_buttons()
        self.rules_buttons = self._create_rules_buttons()
        self.result_buttons = self._create_result_buttons()
        self.hint_buttons = self._create_hint_buttons()
        self.audience_close_button = Button(
            pygame.Rect(835, 572, 180, 52),
            "Закрыть",
            self.fonts["small"],
            bg_color=BUTTON_BLUE,
        )
        self._restart_game()
        self.state = "menu"
        self.message = "Выбери режим в главном меню."

    def _create_answer_buttons(self) -> list[Button]:
        letters = ["А", "Б", "В", "Г"]
        buttons: list[Button] = []
        positions = [
            pygame.Rect(60, 392, 495, 112),
            pygame.Rect(585, 392, 495, 112),
            pygame.Rect(60, 528, 495, 112),
            pygame.Rect(585, 528, 495, 112),
        ]
        for index, rect in enumerate(positions):
            buttons.append(Button(rect, f"{letters[index]}", self.fonts["body"]))
        return buttons

    def _create_menu_buttons(self) -> list[Button]:
        return [
            Button(pygame.Rect(438, 270, 404, 86), "Играть", self.fonts["menu"], bg_color=BUTTON_GREEN),
            Button(pygame.Rect(438, 380, 404, 86), "Правила", self.fonts["menu"], bg_color=BUTTON_ORANGE),
            Button(pygame.Rect(438, 490, 404, 86), "Выход", self.fonts["menu"], bg_color=BUTTON_RED),
        ]

    def _create_rules_buttons(self) -> list[Button]:
        return [Button(pygame.Rect(488, 612, 304, 64), "Назад в меню", self.fonts["small"], bg_color=BUTTON_BLUE)]

    def _create_result_buttons(self) -> list[Button]:
        return [
            Button(pygame.Rect(358, 470, 260, 74), "Играть снова", self.fonts["main"], bg_color=BUTTON_GREEN),
            Button(pygame.Rect(662, 470, 260, 74), "В меню", self.fonts["main"], bg_color=BUTTON_BLUE),
        ]

    def _create_hint_buttons(self) -> dict[str, Button]:
        return {
            "fifty": Button(pygame.Rect(60, 238, 180, 62), "50:50", self.fonts["small"], bg_color=BUTTON_ORANGE),
            "remove_one": Button(pygame.Rect(260, 238, 180, 62), "Убрать 1", self.fonts["small"], bg_color=BUTTON_PURPLE),
            "audience": Button(pygame.Rect(460, 238, 220, 62), "Помощь зала", self.fonts["small"], bg_color=BUTTON_GREEN),
        }

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

            if self.state == "menu":
                self._handle_menu_event(event)
            elif self.state == "rules":
                self._handle_rules_event(event)
            elif self.state == "game":
                self._handle_game_event(event)
            elif self.state == "result":
                self._handle_result_event(event)

    def _handle_menu_event(self, event: pygame.event.Event) -> None:
        if self.menu_buttons[0].handle_event(event):
            self.sound.play("click")
            self._restart_game()
            self.state = "game"
        elif self.menu_buttons[1].handle_event(event):
            self.sound.play("click")
            self.state = "rules"
        elif self.menu_buttons[2].handle_event(event):
            self.running = False

    def _handle_rules_event(self, event: pygame.event.Event) -> None:
        if self.rules_buttons[0].handle_event(event):
            self.sound.play("click")
            self.state = "menu"

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
        if self.state != "game" or self.pending_transition is None:
            if self.state == "result" and self.session.victory:
                self._update_money_sprites()
            return

        if pygame.time.get_ticks() < self.pending_transition.ends_at:
            return

        transition = self.pending_transition
        self.pending_transition = None
        self.selected_answer = None

        if transition.answer_correct:
            self.session.handle_correct_answer()
            if self.session.game_finished:
                if self.session.victory:
                    self._create_money_sprites()
                self.state = "result"
                return
            self.message = "Верно! Переходим к следующему вопросу."
            self._sync_answer_buttons()
        else:
            self.session.handle_wrong_answer()
            self.state = "result"

    def _process_answer(self, answer_index: int) -> None:
        if not self.session.is_answer_available(answer_index):
            return

        self.selected_answer = answer_index
        is_correct = self.session.check_answer(answer_index)
        if is_correct:
            self.sound.play("correct")
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
        self.message = "Ответь на вопрос и поднимайся по лестнице призов."
        self._sync_answer_buttons()

    def _create_money_sprites(self) -> None:
        self.money_sprites = []
        for _ in range(26):
            currency = random.choice(["$", "€"])
            if currency == "$":
                color = random.choice([(128, 222, 146), (100, 204, 122), (151, 231, 163)])
                accent = (31, 113, 55)
            else:
                color = random.choice([(126, 219, 198), (103, 205, 179), (155, 236, 215)])
                accent = (24, 102, 98)

            self.money_sprites.append(
                MoneySprite(
                    x=random.randint(90, WINDOW_WIDTH - 90),
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
                sprite.x = random.randint(90, WINDOW_WIDTH - 90)
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
        bill.blit(symbol, (bill.get_width() // 2 - symbol.get_width() // 2, bill.get_height() // 2 - symbol.get_height() // 2))
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

        if self.state == "menu":
            self._draw_menu()
        elif self.state == "rules":
            self._draw_rules()
        elif self.state == "game":
            self._draw_game()
        elif self.state == "result":
            self._draw_result()

    def _draw_menu(self) -> None:
        panel = pygame.Rect(220, 80, 840, 560)
        draw_rounded_panel(self.screen, panel, radius=34)

        title = self.fonts["title"].render("Детский миллионер", True, TEXT_DARK)
        subtitle = self.fonts["body"].render("Ответь на все вопросы и доберись до 1 000 000!", True, TEXT_DARK)
        self.screen.blit(title, (WINDOW_WIDTH // 2 - title.get_width() // 2, 140))
        self.screen.blit(subtitle, (WINDOW_WIDTH // 2 - subtitle.get_width() // 2, 204))

        for button in self.menu_buttons:
            button.draw(self.screen)

        note_rect = pygame.Rect(300, 600, 680, 40)
        render_wrapped_text(
            self.screen,
            "Все вопросы и кнопки сделаны на русском языке для ребёнка.",
            self.fonts["small"],
            TEXT_DARK,
            note_rect,
            align="center",
        )

    def _draw_rules(self) -> None:
        panel = pygame.Rect(120, 56, 1040, 620)
        draw_rounded_panel(self.screen, panel, radius=34)

        title = self.fonts["title"].render("Правила игры", True, TEXT_DARK)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 26))

        rule_lines = [
            "1. На экране появляется один вопрос и четыре ответа.",
            "2. Нажми на правильный ответ.",
            "3. За каждый верный ответ ты поднимаешься выше по лестнице призов.",
            "4. Если ответ неверный, игра заканчивается.",
            "5. Подсказки можно использовать только один раз за игру.",
            "6. 50:50 убирает два неверных ответа.",
            "7. Убрать 1 прячет один неверный ответ.",
            "8. Помощь зала показывает проценты голосов.",
            "   У верного ответа процент всегда самый большой.",
            "9. После победы или проигрыша можно сыграть снова.",
        ]
        y = panel.top + 110
        for line in rule_lines:
            text = self.fonts["body"].render(line, True, TEXT_DARK)
            self.screen.blit(text, (170, y))
            y += 36 if line.startswith("   ") else 40

        info_rect = pygame.Rect(170, 540, 760, 70)
        render_wrapped_text(
            self.screen,
            "Подсказки работают вместе: игра остаётся честной и не ломается даже после любого порядка нажатий.",
            self.fonts["small"],
            TEXT_DARK,
            info_rect,
        )

        self.rules_buttons[0].draw(self.screen)

    def _draw_game(self) -> None:
        left_panel = pygame.Rect(30, 24, 1070, 670)
        right_panel = pygame.Rect(1120, 24, 130, 670)
        draw_rounded_panel(self.screen, left_panel, radius=30)
        draw_rounded_panel(self.screen, right_panel, radius=30)

        title = self.fonts["subtitle"].render(
            f"Уровень {self.session.level_number} из {len(PRIZE_LADDER)}",
            True,
            TEXT_DARK,
        )
        self.screen.blit(title, (60, 44))

        badge_rect = pygame.Rect(540, 38, 190, 52)
        draw_badge(self.screen, badge_rect, f"Сумма: {self.session.current_amount}", self.fonts["small"])

        category_rect = pygame.Rect(750, 38, 280, 52)
        draw_badge(self.screen, category_rect, f"Тема: {self.session.current_question.category}", self.fonts["small"])

        question_panel = pygame.Rect(60, 106, 980, 108)
        pygame.draw.rect(self.screen, PANEL_COLOR, question_panel, border_radius=24)
        pygame.draw.rect(self.screen, ACCENT, question_panel, width=4, border_radius=24)
        render_wrapped_text(
            self.screen,
            self.session.current_question.text,
            self.fonts["main"],
            TEXT_DARK,
            question_panel.inflate(-26, -18),
            line_gap=6,
            align="center",
        )

        hint_title = self.fonts["small"].render("Подсказки", True, TEXT_DARK)
        self.screen.blit(hint_title, (60, 206))
        for button in self.hint_buttons.values():
            button.draw(self.screen)

        message_panel = pygame.Rect(705, 230, 335, 74)
        pygame.draw.rect(self.screen, (246, 248, 255), message_panel, border_radius=22)
        pygame.draw.rect(self.screen, (218, 225, 244), message_panel, width=2, border_radius=22)
        render_wrapped_text(
            self.screen,
            self.message,
            self.fonts["small"],
            TEXT_DARK,
            message_panel.inflate(-18, -12),
            line_gap=4,
        )

        for button in self.answer_buttons:
            button.draw(self.screen)

        self._draw_prize_ladder(right_panel)

        if self.show_audience_modal and self.session.audience_votes:
            modal = pygame.Rect(160, 110, 960, 520)
            draw_audience_chart(
                self.screen,
                modal,
                self.session.audience_votes,
                self.session.current_question.options,
                self.fonts,
            )
            self.audience_close_button.draw(self.screen)

    def _draw_prize_ladder(self, panel: pygame.Rect) -> None:
        title = self.fonts["small"].render("Призы", True, TEXT_DARK)
        self.screen.blit(title, (panel.left + 26, panel.top + 18))

        item_height = 44
        start_y = panel.bottom - 24 - item_height
        for reverse_index, amount in enumerate(reversed(PRIZE_LADDER)):
            level = len(PRIZE_LADDER) - reverse_index
            y = start_y - reverse_index * (item_height + 6)
            item_rect = pygame.Rect(panel.left + 12, y, panel.width - 24, item_height)

            if level == self.session.level_number and not self.session.game_finished:
                color = ACCENT
            elif level <= self.session.level_index:
                color = (194, 234, 202)
            else:
                color = (238, 243, 255)

            pygame.draw.rect(self.screen, color, item_rect, border_radius=14)
            pygame.draw.rect(self.screen, (220, 228, 245), item_rect, width=2, border_radius=14)

            level_text = self.fonts["small"].render(str(level), True, TEXT_DARK)
            amount_text = self.fonts["small"].render(amount, True, TEXT_DARK)
            self.screen.blit(level_text, (item_rect.left + 10, item_rect.top + 8))
            self.screen.blit(amount_text, (item_rect.right - amount_text.get_width() - 10, item_rect.top + 8))

    def _draw_result(self) -> None:
        if self.session.victory:
            for sprite in self.money_sprites:
                self._draw_money_sprite(sprite)

        panel = pygame.Rect(220, 120, 840, 460)
        draw_rounded_panel(self.screen, panel, radius=34)

        if self.session.victory:
            title_text = "Ты победил!"
            subtitle_text = "Поздравляем! Ты прошёл все вопросы."
            amount = PRIZE_LADDER[-1]
            color = BUTTON_GREEN
        else:
            title_text = "Игра окончена"
            subtitle_text = "В следующий раз получится ещё лучше."
            amount = self.session.last_won_amount
            color = BUTTON_RED

        ribbon = pygame.Rect(410, 164, 460, 68)
        pygame.draw.rect(self.screen, color, ribbon, border_radius=22)
        pygame.draw.rect(self.screen, (255, 255, 255), ribbon, width=2, border_radius=22)

        title = self.fonts["title"].render(title_text, True, TEXT_LIGHT)
        self.screen.blit(title, (ribbon.centerx - title.get_width() // 2, ribbon.centery - title.get_height() // 2))

        subtitle = self.fonts["body"].render(subtitle_text, True, TEXT_DARK)
        self.screen.blit(subtitle, (panel.centerx - subtitle.get_width() // 2, 326))

        reached = self.fonts["subtitle"].render(f"Достигнутая сумма: {amount}", True, TEXT_DARK)
        self.screen.blit(reached, (panel.centerx - reached.get_width() // 2, 376))

        if self.session.victory:
            note = self.fonts["small"].render("Вокруг летят яркие доллары и евро!", True, TEXT_DARK)
            self.screen.blit(note, (panel.centerx - note.get_width() // 2, 420))

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