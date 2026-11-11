# Grafana

Версия образа задаётся в `makefiles/versions.mk`; `make versions` показывает её.
Make экспортирует значение в Compose. CI вызывает `make config-check`.

- `make config-check` — валидация Compose; задайте тестовый `MONITORING_DATA_DIR`.
- `make up` / `make down` / `make logs` — управление стеком.
- `make render` — сформировать provisioning из шаблонов и настроек окружения.

При проверках используйте синтетические настройки и checkout без `.env`.
Запускайте Compose через Make, чтобы не дублировать версию образа.

## Доступ через VPN

Центральный экземпляр работает на WSL: `http://100.64.0.3:3000/` через VPN.
HTTPS-вход — `https://grafana.mralexandrov.duckdns.org/`: Caddy на Russia
проксирует запросы к экземпляру WSL. Требуется обычная авторизация Grafana.

Docker публикует Grafana только на `127.0.0.1:3000`. На WSL настроен
Tailscale Serve: `sudo tailscale serve --bg --tcp=3000 tcp://127.0.0.1:3000`.
С телефона с подключённым Tailscale открыть `http://100.64.0.3:3000/`.
HTTP идёт внутри зашифрованного VPN; публичный доступ к порту 3000 не включён.

## Уведомления

Telegram-уведомления отключены. Шаблон контактных точек больше не требует
токен бота; старые контактные точки в БД сохранены, но не используются политикой.
Политика маршрутизирует в штатный `grafana-default-email`, с круглосуточным mute
`notifications-disabled` на дочернем маршруте, совпадающем со всеми алертами.
Вычисление правил продолжается, отправка уведомлений отключена.
Штатная контактная точка `grafana-default-email` должна существовать.

Причина исправления 27 сентября 2026 года: контейнер циклически завершался
из-за Telegram provisioning без `TELEGRAM_BOT_TOKEN`. После изменения проверены
HTTP 200 на `/login` через loopback и VPN, применение политики и mute в БД,
отсутствие новых рестартов в период проверки. Дашборды и источники данных
отдельно не проверялись. Конфигурация применена вручную на VM и сохранена локально.

## Центральный экземпляр на WSL

Фактическое размещение, сохранённые данные, ограничения WAL и откат описаны
в [MIGRATION.md](MIGRATION.md).

При переносе сохраняются named volume с БД Grafana, вся `.monitoring` с
provisioning/dashboards и приватный `.env`. Уведомления остаются отключёнными.
Источники Prometheus/Loki используют локальные Docker aliases; `JAEGER_URL`
указывает на прежний Jaeger через tailnet. Дополнительные SQL datasources также
должны использовать tailnet endpoint вместо Docker DNS другой машины.

До проверки нового экземпляра старые volumes не удаляются.

Docker Desktop не использует маршруты Headscale внутри Ubuntu. Поэтому Grafana
разделяет network namespace с `grafana-tailnet`, отдельным Tailscale-клиентом
с постоянным named volume. `HEADSCALE_URL` обязателен. Первичная регистрация
выполняется одноразовым короткоживущим ключом через приватный временный файл
внутри контейнера; ключ не передаётся в Compose, логи или Git. После регистрации
файл удаляется, последующие старты используют сохранённое состояние.
Клиент не принимает DNS, subnet routes или exit node и меняет маршруты только
в своём namespace. Grafana по-прежнему публикуется лишь на loopback:3000.

## Автодеплой

После проверок push в `main` доставляет точный проверенный SHA на WSL через
SSH jump host Hostkey Russia. `make ci-deploy` запускает транспорт; `make deploy`
пересоздаёт сервис и выполняет `make smoke`. PR только проверяются. Ручной запуск
workflow доступен для main. `DEPLOY_ENABLED` управляет включением доставки.
Ключ репозитория ограничен этим проектом; `DEPLOY_SSH_KEY` хранится в Secrets,
проверенные SSH host keys — в переменной `DEPLOY_KNOWN_HOSTS`. Старые `VM_*`
secrets не используются. `.env` и named volumes остаются на хосте.

Доступ/установка receiver, блокировки, отказы и повторный запуск описаны в
[инструкции доставки Alloy](https://github.com/MrAlexandrovOrganization/alloy/blob/main/DEPLOY.md).
Для тестов использовать `make test`; `make check` также валидирует конфигурацию.

## Container names

Compose uses explicit service names without replica numbers. Set
`CONTAINER_NAME_PREFIX` (for example `dev-`) for an additional local or CI stack
on the same Docker host. Keep Compose project/service labels and volume names
unchanged; clients address services or explicit network aliases.

`make recreate` recreates Grafana and its tailnet sidecar together, retaining
their existing volumes. This also refreshes Docker namespace references after
a container rename.

## Структура Compose

Файлы Docker Compose находятся в `compose/`; основной файл — `compose/docker-compose.yml`.
Команды запускайте из корня проекта через Makefile: он задаёт `--project-directory`
на корень checkout. Build contexts, bind mounts, `env_file` и секреты остаются
относительными к этому корню; имена Compose project, сервисов, сетей и томов сохранены.
При явном вызове Docker используйте `docker compose --project-directory . -f compose/docker-compose.yml ...`.
Если в приватной `.env` или окружении задан `COMPOSE_FILE`, добавьте `compose/`
к прежним именам файлов, сохранив прежний набор overlays и порядок. Для плавного
перехода Make также распознаёт прежние короткие имена, если файлы уже перенесены.
Не меняйте project name и не удаляйте прежние тома для переноса файлов.


## Дашборды сервисов

Специальные дашборды поставляются пакетами их владельцев через закрытую
конфигурацию доставки. UID, каталоги провайдера и существующие файлы сохраняются;
этот репозиторий содержит только общие дашборды платформы.

## Доступность сервисов

`dashboards/service-availability.json`, UID `service-availability`, —
[«Сервисы · доступность»](https://grafana.mralexandrov.duckdns.org/d/service-availability).
Устанавливается `make directories`/`make init` Grafana; также включён в
закреплённый пакет платформы для сборщика Alloy.
Существующие JSON других проектов сохраняются. Datasource — `prometheus`,
сторонние panel plugins не требуются. Push в main доставляет файл через CI/CD.

По умолчанию выбраны Finland, Russia, WSL и ASUS; Mac и другие наблюдаемые хосты
можно включить фильтром. Отдельно показаны registration, VPN/вход и notes-bot,
проблемные контейнеры, история healthcheck, успешность и покрытие наблюдений,
сбор системных метрик и доступность metrics endpoints.

Состояния контейнеров определяются по `container_health_state`,
`container_last_seen` и `up{job="cadvisor"}`. Healthy означает успешный Docker
healthcheck; контейнер без него имеет отдельное состояние. Samples старше 90 с
и отказ cAdvisor означают отсутствие телеметрии. При работающем сборе пропавший
контейнер отмечается как не обнаруженный. Список ожидаемых пар host/service
строится по Compose-контейнерам с меткой проекта за последние 24 часа: он включает
недавно выключенные контейнеры и забывает их через сутки. Разовые standalone
контейнеры без Compose-меток в этот список не входят. Это не постоянный inventory желаемых
сервисов; контейнер, ни разу не наблюдавшийся, автоматически в список не попадёт.
После планового удаления он может оставаться в проблемных до суток.

История healthcheck отображается на минутной сетке с разрывами при отсутствии
данных. Процент успешных минут исключает пропуски; рядом приведена доля минут
периода с доступными проверками. Для `up` успешность рассчитана по полученным
samples, покрытие — по интервалу scrape 15 с. Новые targets и отключённые хосты
дают неполное покрытие. Retention Prometheus — 15 дней; короткие сбои между
точками минутной сетки могут быть не видны. Для текущих состояний используются
instant queries, а не последнее ненулевое значение за весь период.

Дашборд не выполняет внешние HTTP/TCP-пробы, Telegram-диалоги или VPN-соединения;
проценты не являются SLA пользовательских сценариев. `up=0` в блоке endpoints
говорит об отказе `/metrics`, а не обязательно об отказе приложения. Чтобы
измерять доступность снаружи, потребуется отдельный проверяющий клиент/blackbox
exporter; в рамках этого дашборда сборщики и приложения не перенастраивались.

## Настройки наблюдаемости

`monitoring/observability.json` описывает только компоненты и ресурсы этого
проекта: правила разбора логов, targets метрик и дашборды. Стандартные JSON/logfmt
логи и метрики контейнеров собираются общими средствами; пустой список ресурсов
не отключает общий сбор.

`make observability-check` проверяет пакет без сети, Docker и соседних checkout
(Python 3.9+). `make observability-export` создаёт `.observability/package.tar`;
CI публикует его как artifact. Экспорт содержит явно перечисленные файлы,
ревизию и SHA-256. Незакоммиченные ресурсы помечаются `source_state=worktree`.
Приватные `.env`, credentials и карта инфраструктуры в экспорт не входят.

В ресурсах задаётся логическое размещение `local` (сбор метрик рядом с сервисом)
или `central` (центральные провайдеры). Физическое размещение и набор других
пакетов задаются закрытой конфигурацией доставки. Сборщик строит итоговый файл
из закреплённых экспортов; обычная сборка этого проекта не зависит от них.
Копия Python-инструмента закреплена SHA-256 в `monitoring/tool.lock.json`.
