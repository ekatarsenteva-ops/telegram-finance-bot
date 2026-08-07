# Как запушить бота на GitHub

Локально уже подготовлена отдельная ветка `finance-bot-only` — это чистая история
только кода бота (без посторонних файлов из соседнего проекта). Осталось её
отправить на GitHub.

## Шаг 1. Создать токен доступа на GitHub

1. Открой в браузере: https://github.com/settings/tokens
2. Нажми **"Generate new token"** → выбери **"Generate new token (classic)"**
3. В поле "Note" впиши любое название, например `finance-bot-push`
4. В "Expiration" выбери, например, 30 дней (токен нужен разово, можно и меньше)
5. В списке прав (scopes) поставь галочку только на **`repo`**
6. Прокрути вниз, нажми **"Generate token"**
7. GitHub покажет строку вида `ghp_xxxxxxxxxxxxxxxxxxxx` — **скопируй её сразу**,
   второй раз показать не даст

## Шаг 2. Запушить из терминала VSCode

1. В VSCode открой терминал: меню Terminal → New Terminal (или Ctrl+`)
2. Перейди в папку проекта:
   ```
   cd /home/coder/workspace
   ```
3. Выполни:
   ```
   git push -u origin finance-bot-only:main
   ```
4. На запрос **Username** — впиши логин GitHub: `ekatarsenteva-ops`
5. На запрос **Password** — вставь **токен** из шага 1 (не обычный пароль)
6. Enter — должно пойти "Writing objects...", "Total..."

## Шаг 3. Проверить результат

Открой https://github.com/ekatarsenteva-ops/telegram-finance-bot — должны
появиться файлы бота (`main.py`, `bot/`, `README.md` и т.д.).

## Если что-то пошло не так

- `remote: Repository not found` — проверь, что репозиторий
  `telegram-finance-bot` действительно существует под аккаунтом
  `ekatarsenteva-ops` на GitHub.
- `Authentication failed` — токен скопирован неверно или устарел, создай новый
  по шагу 1.
- Любая другая ошибка — скопируй текст ошибки целиком и разберём вместе.

## Как пушить в будущем (после новых изменений кода)

Каждый раз, когда будут новые правки в `telegram-finance-bot/`, нужно:
1. Закоммитить изменения в основной ветке `master` (как обычно)
2. Пересобрать чистую ветку кода бота:
   ```
   git branch -D finance-bot-only
   git subtree split --prefix=telegram-finance-bot -b finance-bot-only
   ```
3. Запушить:
   ```
   git push origin finance-bot-only:main
   ```
