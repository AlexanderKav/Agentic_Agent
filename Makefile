.PHONY: help build up down logs shell test clean

ENV_FILE := .env

help:
	@echo "Available commands:"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make shell    - Open shell in app container"
	@echo "  make test     - Run tests in Docker"
	@echo "  make clean    - Remove containers and volumes"

build:
	cd docker && docker-compose build

up:
	cd docker && docker-compose --env-file ../.env up -d
	@echo "✅ Application running at http://localhost:8000"
	@echo "📊 API docs at http://localhost:8000/api/docs"

down:
	cd docker && docker-compose down

logs:
	cd docker && docker-compose logs -f

shell:
	cd docker && docker-compose exec app /bin/bash

test:
	cd docker && docker-compose exec app pytest tests/ -v

clean:
	cd docker && docker-compose down -v
	docker system prune -f

restart: down up

status:
	cd docker && docker-compose ps