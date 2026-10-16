.PHONY: ci-deploy deploy recreate smoke test
ci-deploy:
	python3 scripts/ci-deploy.py

deploy:
	$(MAKE) recreate
	$(MAKE) smoke

smoke:
	python3 scripts/smoke.py

test:
	python3 -m unittest discover -s tests -v

recreate: render init
	chmod a+r provisioning/alerting/rules.yml
	$(DOCKER_COMPOSE) up -d --force-recreate grafana-tailnet grafana
