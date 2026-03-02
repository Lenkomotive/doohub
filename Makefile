.PHONY: up down logs restart build migrate seed prod prod-build prod-down prod-logs

# --- Dev ---
up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart

build:
	docker compose up -d --build

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python seed.py $(user) $(pass)

# --- Production ---
prod:
	docker compose -f docker-compose.prod.yml up -d

prod-build:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f

prod-migrate:
	docker compose -f docker-compose.prod.yml exec backend alembic upgrade head

prod-seed:
	docker compose -f docker-compose.prod.yml exec backend python seed.py $(user) $(pass)
