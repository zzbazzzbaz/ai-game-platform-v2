.PHONY: up down install jwt-keys run-api run-agent sandbox-assets-publish

ENV_FILE := $(CURDIR)/apps/.env

up:
	cd apps && docker compose up -d

down:
	cd apps && docker compose down

install:
	cd apps/api && uv sync
	cd apps/agent && uv sync
	cd sandbox/game-template && npm install

jwt-keys:
	cd apps/api && mkdir -p .keys \
		&& openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out .keys/jwt_private.pem \
		&& openssl rsa -pubout -in .keys/jwt_private.pem -out .keys/jwt_public.pem \
		&& echo "已生成 apps/api/.keys/jwt_{private,public}.pem"

run-api:
	cd apps/api && uv run --env-file $(ENV_FILE) fastapi run --no-reload --port 8000

run-agent:
	cd apps/agent && uv run --env-file $(ENV_FILE) langgraph dev --no-reload

sandbox-assets-publish:
	cd sandbox && uv run --env-file $(ENV_FILE) --with cos-python-sdk-v5 python publish_assets.py
