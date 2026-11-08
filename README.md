# Dzencode Comments

Веб-приложение для обсуждений: список комментариев с вложенными ответами,
CAPTCHA, загрузкой файлов, обновлениями в реальном времени и уведомлениями об
ответах. Backend написан на Django 6 + Django REST Framework, интерфейс — на Vue.

## Возможности

### Комментарии
- Главные комментарии и ответы на них (ответить можно и на ответ). Структура:
  `related_comment` — корневой комментарий ветки, `target_comment` — тот, на
  кого отвечают.
- Постраничный список главных комментариев (по 25 на страницу), ответы
  подгружаются через API.
- Сортировка списка по имени пользователя, e-mail и дате создания
  (`?field=username|email|created&orderingType=asc|desc`).
- Текст до 2000 символов. Разрешены только теги `a` (`href`, `title`), `code`,
  `i`, `strong`; остальной HTML вырезается (nh3). Незакрытые теги приводят к
  ошибке валидации.
- Кнопки быстрой вставки тегов в форме.

### Авторы
- Автор задаётся именем (только латинские буквы и цифры), уникальным e-mail и
  необязательной домашней страницей.
- После первого комментария автор получает JWT, который хранится в
  `localStorage`; форма автоматически заполняется сохранёнными данными.
- Если в форме указать другое имя, e-mail или сайт, будет создан или получен
  другой автор, и токен обновится.

### Вложения
- К комментарию можно приложить изображение (`jpg`, `gif`, `png`) или `txt`
  файл (до 100 КБ).
- Изображения проверяются и уменьшаются до 320×240; просмотр в lightbox.

### CAPTCHA
- Используется `django-simple-captcha` с кнопкой обновления без перезагрузки.
- Капча проверяется один раз через `POST /api/commenting/captcha/verify/`,
  который возвращает одноразовый `captcha_token` (живёт 5 минут) и список
  методов, для которых он действует (поле `methods` через `;`, например
  `author_get_create;comment_create`). Каждый успешный запрос тратит свой метод
  из списка, а когда список пуст, токен удаляется.

### Реальное время и уведомления
- Новые комментарии и ответы рассылаются всем открытым страницам по WebSocket
  (Django Channels, `/ws/comments/`).
- Ответ на комментарий другого автора отправляет автору исходного комментария
  письмо через Celery. Используется консольный e-mail backend: письма выводятся
  в лог процесса Celery.
- События публикуются в Redis-список и обрабатываются отдельным процессом
  `listen_events`, который сбрасывает кеш и запускает задачи.

### Производительность
- Кеш Redis для списка комментариев, ответов и авторов с инвалидацией по
  событиям.

## API

Все эндпоинты находятся под `/api/commenting/`.

| Метод и путь | Назначение |
|---|---|
| `POST captcha/verify/` | Проверить CAPTCHA, получить `captcha_token` |
| `POST authors/` | Получить или создать автора, вернуть JWT |
| `GET get-author/` | Получить автора по JWT |
| `POST comments/` | Создать комментарий или ответ (`multipart/form-data`) |
| `GET comments/replies/?comment_id=` | Ответы на комментарий |

Для `authors/` и `comments/` обязателен `captcha_token`, полученный в
`captcha/verify/`.

## Стек

Python 3.14, Django, Django REST Framework, SimpleJWT, Channels + Daphne,
Celery, Redis, PostgreSQL (SQLite по умолчанию при локальной разработке),
Gunicorn, Nginx, Docker Compose, Pillow, nh3.

## Структура

```
comments/
  comments/    настройки проекта, ASGI, Celery
  commenting/  модели, API, сервисы, шаблоны, статика (JS/CSS), WebSocket
  events/      отправка и обработка событий через Redis
  core/        общий кеш, валидаторы, базовые модели
  api/         JWT-аутентификация и корневые API-маршруты
frontend/
  src/         Vue-интерфейс и компоненты
nginx/         конфигурация Nginx
scripts/       генерация локального TLS-сертификата
```

## Запуск

### Docker Compose (рекомендуется)

Требуются Docker Engine и Docker Compose. Для локального запуска достаточно:

```sh
docker compose up --build
```

Команда собирает Vue-интерфейс и Docker-образы, создаёт таблицы и запускает
веб-сервер, WebSocket, PostgreSQL, Redis, Celery и обработчик событий.
Откройте [http://localhost](http://localhost) (порт можно изменить через
`HTTP_PORT`). Для запуска в фоне используйте `docker compose up --build -d`,
затем `docker compose ps` для проверки состояния. Создание администратора
необязательно:

```sh
docker compose exec web python manage.py createsuperuser
```

Для локальной разработки можно скопировать `.env.example` в `.env` и изменить
порт или параметры подключения. Значения по умолчанию в Compose предназначены
только для локального запуска и не подходят для публичного сервера. Настройка
production и локального HTTPS описана в [DEPLOYMENT.md](DEPLOYMENT.md).

### Локально

Для запуска Django вне Docker нужны Python 3.14, Node.js 22.12+ и Redis,
доступный на `127.0.0.1:6379`. Этот вариант предназначен для разработки
backend; для полного сценария с WebSocket используйте Docker Compose.
Сначала соберите интерфейс:

```sh
cd frontend
npm ci
npm run build
cd ..
```

Затем запустите backend из отдельных терминалов:

```sh
python -m venv venv
venv\Scripts\activate            # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt
cd comments
python manage.py migrate
python manage.py runserver
```

Для очередей и обработки событий запустите ещё два процесса из каталога
`comments`:

```sh
celery -A comments worker -l info
python manage.py listen_events
```

Локальный Redis можно запустить через Compose:

```sh
docker compose up -d redis
```

Его порт опубликован только на loopback-интерфейсе.

## Тесты

```sh
cd comments
python manage.py test
```
