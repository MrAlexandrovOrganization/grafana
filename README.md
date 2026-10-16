# Grafana

Версия образа задаётся в `makefiles/versions.mk`; `make versions` показывает её.
Make экспортирует значение в Compose. CI вызывает `make config-check`.

- `make config-check` — валидация Compose; задайте тестовый `MONITORING_DATA_DIR`.
- `make up` / `make down` / `make logs` — управление стеком.
- `make render` — сформировать provisioning из шаблонов и настроек окружения.

При проверках используйте синтетические настройки и checkout без `.env`.
Запускайте Compose через Make, чтобы не дублировать версию образа.

## Доступ через VPN

HTTPS-вход Caddy использует отдельную внутреннюю `caddy-grafana-net` с alias
`grafana-ingress`; сеть создаёт стек `infra/network/caddy`, поэтому его следует
поднять первым. Сети источников данных остаются для datasource-трафика.

Docker публикует Grafana только на `127.0.0.1:3000`. На VM настроен
Tailscale Serve: `sudo tailscale serve --bg --tcp=3000 tcp://127.0.0.1:3000`.
С телефона с подключённым Tailscale открыть `http://100.64.0.1:3000/`.
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
