from __future__ import annotations

import pygame

from src.config import (
    ACCENT,
    AUDIENCE_BAR,
    BORDER,
    BUTTON_BLUE,
    BUTTON_BLUE_HOVER,
    BUTTON_DISABLED,
    PANEL_COLOR,
    PANEL_SHADOW,
    REMOVED_OVERLAY,
    SOFT_BG,
    TEXT_DARK,
    TEXT_LIGHT,
)


def draw_vertical_gradient(surface: pygame.Surface, top_color: tuple[int, int, int], bottom_color: tuple[int, int, int]) -> None:
    width, height = surface.get_size()
    for y in range(height):
        blend = y / max(1, height - 1)
        color = tuple(
            int(top_color[i] + (bottom_color[i] - top_color[i]) * blend)
            for i in range(3)
        )
        pygame.draw.line(surface, color, (0, y), (width, y))


def draw_rounded_panel(surface: pygame.Surface, rect: pygame.Rect, radius: int = 24) -> None:
    shadow_rect = rect.move(6, 8)
    pygame.draw.rect(surface, PANEL_SHADOW, shadow_rect, border_radius=radius)
    pygame.draw.rect(surface, PANEL_COLOR, rect, border_radius=radius)
    pygame.draw.rect(surface, BORDER, rect, width=2, border_radius=radius)


def render_wrapped_text(
    surface: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: tuple[int, int, int],
    rect: pygame.Rect,
    line_gap: int = 6,
    align: str = "left",
) -> None:
    words = text.split()
    lines: list[str] = []
    current_line = ""
    for word in words:
        trial = word if not current_line else f"{current_line} {word}"
        if font.size(trial)[0] <= rect.width:
            current_line = trial
        else:
            if current_line:
                lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    y = rect.top
    for line in lines:
        rendered = font.render(line, True, color)
        if align == "center":
            x = rect.centerx - rendered.get_width() // 2
        else:
            x = rect.left
        surface.blit(rendered, (x, y))
        y += rendered.get_height() + line_gap


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        font: pygame.font.Font,
        bg_color: tuple[int, int, int] = BUTTON_BLUE,
        hover_color: tuple[int, int, int] = BUTTON_BLUE_HOVER,
        text_color: tuple[int, int, int] = TEXT_LIGHT,
    ) -> None:
        self.rect = rect
        self.text = text
        self.font = font
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.disabled = False
        self.visible = True
        self.removed = False
        self.keep_color_when_disabled = False

    def draw(self, surface: pygame.Surface) -> None:
        if not self.visible:
            return

        mouse_pos = pygame.mouse.get_pos()
        hovered = self.rect.collidepoint(mouse_pos)
        color = self.bg_color
        if self.disabled and not self.removed and not self.keep_color_when_disabled:
            color = BUTTON_DISABLED
        elif hovered and not self.disabled:
            color = self.hover_color

        pygame.draw.rect(surface, color, self.rect, border_radius=20)
        pygame.draw.rect(surface, BORDER, self.rect, width=2, border_radius=20)

        label = self.text
        label_color = self.text_color
        if self.removed:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((*REMOVED_OVERLAY, 210))
            surface.blit(overlay, self.rect.topleft)
            label = "Убрано"
            label_color = TEXT_DARK

        render_wrapped_text(
            surface,
            label,
            self.font,
            label_color,
            self.rect.inflate(-26, -18),
            line_gap=4,
            align="center",
        )

    def handle_event(self, event: pygame.event.Event) -> bool:
        if not self.visible or self.disabled:
            return False
        return event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and self.rect.collidepoint(event.pos)


def draw_audience_chart(
    surface: pygame.Surface,
    rect: pygame.Rect,
    votes: dict[int, int],
    labels: list[str],
    fonts: dict[str, pygame.font.Font],
) -> None:
    draw_rounded_panel(surface, rect, radius=28)
    title = fonts["subtitle"].render("Помощь зала", True, TEXT_DARK)
    surface.blit(title, (rect.left + 24, rect.top + 20))

    chart_top = rect.top + 78
    bar_height = 36
    gap = 18

    for index, label in enumerate(labels):
        y = chart_top + index * (bar_height + gap)
        short_label = label if len(label) < 28 else f"{label[:25]}..."
        text = fonts["small"].render(short_label, True, TEXT_DARK)
        surface.blit(text, (rect.left + 24, y + 5))

        bar_rect = pygame.Rect(rect.left + 310, y, rect.width - 430, bar_height)
        pygame.draw.rect(surface, SOFT_BG, bar_rect, border_radius=14)
        fill_width = int(bar_rect.width * votes.get(index, 0) / 100)
        fill_rect = pygame.Rect(bar_rect.left, bar_rect.top, max(0, fill_width), bar_rect.height)
        pygame.draw.rect(surface, AUDIENCE_BAR, fill_rect, border_radius=14)
        pygame.draw.rect(surface, BORDER, bar_rect, width=2, border_radius=14)

        percent = fonts["small"].render(f"{votes.get(index, 0)}%", True, TEXT_DARK)
        surface.blit(percent, (bar_rect.right + 14, y + 5))

    info = fonts["small"].render("У правильного ответа всегда самый высокий процент.", True, TEXT_DARK)
    surface.blit(info, (rect.left + 24, rect.bottom - 46))


def draw_badge(surface: pygame.Surface, rect: pygame.Rect, text: str, font: pygame.font.Font) -> None:
    pygame.draw.rect(surface, ACCENT, rect, border_radius=18)
    pygame.draw.rect(surface, BORDER, rect, width=2, border_radius=18)
    render_wrapped_text(surface, text, font, TEXT_DARK, rect.inflate(-12, -10), align="center")
