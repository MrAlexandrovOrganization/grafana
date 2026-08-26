DOCKER_COMPOSE = docker compose

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

up: render
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

logs:
	$(DOCKER_COMPOSE) logs -f

.PHONY: render up down logs
