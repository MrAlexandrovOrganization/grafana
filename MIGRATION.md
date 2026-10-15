# Перенос наблюдаемости на WSL — 15 октября 2026

## Размещение

| Хост | Сервисы наблюдаемости | Метка host |
| --- | --- | --- |
| server, 100.64.0.1 | Alloy; прежний Jaeger (1000 трейсов в памяти) | yc-server-big |
| hostkey-russia, 100.64.0.5 | Alloy | hostkey-russia |
| hostkey-finland, 100.64.0.6 | Alloy | hostkey-finland |
| private-test-server, 100.64.0.4 | Alloy | private-test-server |
| WSL, 100.64.0.3 | Prometheus, Loki, Grafana, Alloy | wsl |

Проекты расположены в `/home/maxim/projects/infra/observability`. Каждый —
отдельный Git-репозиторий. Make читает приватный `.env`; версии находятся
в `makefiles/versions.mk`. Alloy собирает локально каждые 15 секунд и отправляет
метрики через remote_write. Prometheus больше не опрашивает удалённые targets.
На WSL отдельный каталог `.monitoring-wsl/prometheus-targets` не содержит
Docker aliases приложений старого сервера.

Prometheus и Loki хранят 15 дней. WAL метрик Alloy хранит недоставленные samples
до 24 часов; подтверждённые данные очищаются сегментами (проверка каждый час,
минимальный возраст 5 минут). Это не локальная queryable TSDB. Полный диск и
отказы дольше суток не покрываются. **Alloy 1.20.1 не прошёл тест досылки старых
samples после собственного перезапуска**: WAL не даёт такой гарантии.
При недоступности WSL следует сохранять работающие collectors.
Проверено на Russia: отключение сетей только контейнера Alloy на 45 секунд,
затем восстановление связи. Накопленный sample дошёл с исходной timestamp.
Для гарантии после перезапуска нужен отдельный выбор устойчивого агента/очереди.

Позиции Docker-логов и WAL находятся в `observability_alloy_data`, storage path
`/var/lib/alloy/data`. Старое неявное `/data-alloy` на server полностью перенесено
до пересоздания контейнера. Component IDs сохранены. Очередь логов на сутки
не добавлена; прежний фильтр удаляет записи старше часа.

## Доступ

Через Headscale: Grafana `http://100.64.0.3:3000`, Loki `:3100`, Prometheus `:9090`.
Docker публикует эти порты только на loopback WSL; наружу их предоставляет
Tailscale Serve внутри tailnet. Прежний HTTPS Caddy на server направляет
Grafana на WSL. Loopback forwarders server на 3000/3100/9090 сохраняют старых
локальных клиентов и прежний VPN-вход Grafana `http://100.64.0.1:3000`.

Docker Desktop не наследует маршруты Ubuntu Tailscale. Поэтому Grafana использует
постоянный Tailscale sidecar `wsl-grafana` (100.64.0.10), без exit node/subnet
routes/DNS. Состояние — `observability_grafana_tailnet`. Одноразовый ключ
регистрации удалён после использования. На server Tailscale Serve предоставляет
Grafana доступ к Jaeger `:16686` и SQL datasources `:15434`/`:15432`.
Сетевые маршруты Hostkey Finland относятся к отдельной настройке VPN.

Alloy WSL использует `cgroup: host`, `ALLOY_PROCFS_PATH=/proc` и
`ALLOY_DOCKER_DESKTOP=true`. Startup wrapper находит текущий dockerd по его
Desktop PID file, отсоединяет только собственные Ubuntu bind mounts и читает
runtime root/image store через `/proc/PID/root`. Хостовые файлы, mounts и Docker
daemon не меняются; PID не закреплён. Это уже привилегированный collector,
procfs-ссылки не являются ограничением прав записи к runtime filesystem.

Grafana перенесена целиком: БД, 18 записей dashboard/folder, 6 datasources,
пользователь, 4 alert rules, provisioning и dashboards из `.monitoring`.
Уведомления остаются выключенными. Проверены Prometheus, Loki, Jaeger и обе SQL
datasources; существующий Elasticsearch datasource не проверялся и не изменялся.
Два недоступных application targets на server оставлены намеренно.

## Резервные копии и доставка

На server и WSL: `/home/maxim/backups/observability-migration-20261015/`.
Архивы `prometheus.tar.gz`, `loki.tar.gz`, `grafana.tar.gz`, `monitoring.tar.gz`
и приватный Grafana env скопированы с проверкой SHA-256. Владение файлами
сохранено при импорте в пустые named volumes. Исходные серверные volumes не
удалены; прежние три контейнера остановлены, restart policy выключена.

На каждом из пяти хостов в том же backup-каталоге находится холодная копия
`alloy-v1.7-state.tar` перед обновлением. Исходное состояние старого Alloy server
также сохранено в `/home/maxim/.local/state/alloy-migration/legacy-state-kaz6iimo.tar`.
Архивы содержат приватные данные; не публиковать их и не добавлять в Git.

После завершения миграции настроен SSH CD через Hostkey Russia: центральные
сервисы доставляются только на WSL, Alloy — на все пять хостов. `DEPLOY_ENABLED`
управляет включением; старые VM secrets больше не используются. Применяется
проверенный SHA, результат подтверждается runtime-проверкой и receipt.
Подробности: [DEPLOY.md Alloy](https://github.com/MrAlexandrovOrganization/alloy/blob/main/DEPLOY.md).
На Hostkey запускать `sudo -n make up`: sudo перед docker отдельно теряет
экспортированные Make переменные версий. На server/WSL sudo для Docker не нужен.

## Проверка и откат

`make smoke` в Alloy проверяет node/cAdvisor/self, метрики именованных контейнеров
и логи за последние 15 минут. На WSL для проверки из shell передать
`PROMETHEUS_REMOTE_WRITE_URL=http://127.0.0.1:9090/api/v1/write`, поскольку
runtime Docker alias `prometheus` не разрешается в Ubuntu shell.
Проверки конфигураций и миграции state запускаются через `make check` Alloy.
Полные сутки отключения и перезагрузка Windows не проверялись.

Перед откатом остановить центральный стек WSL и сохранить его актуальные данные,
чтобы не потерять историю после переключения. Затем восстановить выбранные
архивы в отдельные volumes либо осознанно использовать сохранённые старые volumes
server. Остановить loopback forwarders server 3000/3100/9090 перед запуском
сервисов на прежних портах. Вернуть Caddy upstream и Alloy receiver URLs,
проверить доставку, только затем включать restart policies. Не запускать два
писателя в один volume. Обновлённый Alloy не откатывать поверх прежнего WAL:
сначала сохранить новый volume и восстановить согласованную холодную копию.
