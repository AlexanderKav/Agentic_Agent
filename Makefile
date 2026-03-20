.PHONY: help build up down logs shell test clean

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
	docker-compose -f docker/docker-compose.yml build

up:
	docker-compose -f docker/docker-compose.yml up -d
	@echo "✅ Application running at http://localhost:8000"
	@echo "📊 API docs at http://localhost:8000/api/docs"

down:
	docker-compose -f docker/docker-compose.yml down

logs:
	docker-compose -f docker/docker-compose.yml logs -f

shell:
	docker-compose -f docker/docker-compose.yml exec app /bin/bash

test:
	docker-compose -f docker/docker-compose.yml exec app pytest tests/ -v

clean:
	docker-compose -f docker/docker-compose.yml down -v
	docker system prune -f

restart: down up

status:
	docker-compose -f docker/docker-compose.yml ps