# Детская игра «Кто хочет стать миллионером?»

Офлайн-игра на Python и `pygame-ce` для Windows 10 и Windows 11. Вся игра, интерфейс, вопросы и подсказки полностью на русском языке и подходят для ребёнка.

## Возможности

- 20 вопросов за одну игру
- 4 уровня сложности: `easy`, `medium`, `hard`, `very_hard`
- несгораемые суммы после 5 и 10 вопроса
- 3 подсказки: `50:50`, `Убрать 1`, `Помощь зала`
- выбор имени игрока и сохранение лучшего результата в `AppData`
- встроенный `questions.json` и безопасное обновление вопросов из GitHub
- работа без интернета: если обновление недоступно, игра использует текущие рабочие вопросы
- необязательные звуки: если файлов нет, игра всё равно запускается

## Требования

- Windows 10 или Windows 11
- Python 3.11+ рекомендуется

## Установка зависимостей

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Запуск игры

```powershell
python main.py
```

## Сборка standalone `.exe`

```powershell
pyinstaller --noconfirm --windowed --name MillionaireKids --add-data "questions.json;." --add-data "assets;assets" main.py
```

После сборки готовый файл будет лежать в `dist\MillionaireKids\` или в `dist\MillionaireKids.exe`, в зависимости от режима сборки.

## Обновление вопросов из GitHub

В главном меню есть кнопка `Обновить вопросы`.

Игра:

- скачивает новый файл вопросов по raw URL из GitHub
- проверяет JSON перед заменой локальной базы
- сохраняет рабочий файл в `AppData\Roaming\MillionaireKidsGame\questions\questions_active.json`
- если новый файл неверный, не затирает текущую рабочую базу
- если интернета нет, продолжает работать на встроенных или уже сохранённых вопросах

По умолчанию используется такой raw URL:

```text
https://raw.githubusercontent.com/Ayskhan/millionaire-kids-game/main/questions.json
```

Чтобы обновить вопросы позже, достаточно заменить `questions.json` в корне репозитория и оставить тот же путь к файлу.

## Необязательные звуки

Игра умеет использовать такие файлы:

- `assets\sounds\click.wav`
- `assets\sounds\correct.wav`
- `assets\sounds\wrong.wav`

Если этих файлов нет, ошибок не будет: игра просто запустится без звука.

## Структура проекта

```text
.
├── assets/
│   └── README.md
├── src/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── data.py
│   ├── logic.py
│   ├── profiles.py
│   ├── question_sources.py
│   ├── sound.py
│   └── ui.py
├── main.py
├── questions.json
├── README.md
└── requirements.txt
```

## Формат вопросов

Каждый вопрос в `questions.json` должен содержать:

- `difficulty`
- `question`
- `options` из 4 вариантов
- `answer_index`
- `category` по желанию

При запуске и при обновлении игра проверяет:

- что JSON читается
- что у каждого вопроса ровно 4 варианта ответа
- что правильный ответ один и его индекс верный
- что нет пустого текста вопроса
- что внутри одного вопроса нет одинаковых вариантов ответа
- что вопросов хватает для всех 4 уровней сложности
