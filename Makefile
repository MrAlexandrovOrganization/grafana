DOCKER_COMPOSE = docker compose
DOCKER ?= docker
NETS = prometheus-net loki-net jaeger-net grafana-datasources-net

TEMPLATE_VARS = $${TELEGRAM_BOT_TOKEN} $${TELEGRAM_CHAT_ID}

-include .env
export

render:
	@find templates -name '*.tpl.yml' | while read tpl; do \
		out="provisioning/$${tpl#templates/}"; \
		out="$${out%.tpl.yml}.yml"; \
		mkdir -p "$$(dirname "$$out")"; \
		envsubst '$(TEMPLATE_VARS)' < "$$tpl" > "$$out"; \
		echo "rendered $$out"; \
		done

up: render init
	$(DOCKER_COMPOSE) up -d

init: network directories

network:
	@for n in $(NETS); do \
		if $(DOCKER) network inspect $$n >/dev/null 2>&1; then \
			echo "network $$n already exists"; \
		else \
			$(DOCKER) network create $$n --opt com.docker.network.driver.mtu=1376; \
		fi; \
	done

directories:
	@mkdir -p $(MONITORING_DATA_DIR)/grafana-dashboards
	@mkdir -p $(MONITORING_DATA_DIR)/grafana-datasources
	@cp ./provisioning/datasources/*.yaml $(MONITORING_DATA_DIR)/grafana-datasources/

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

.PHONY: render up down logs init network directories
