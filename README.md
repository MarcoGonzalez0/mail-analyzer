# Mail Analyzer

API REST que recibe un email y devuelve un análisis de seguridad de su dominio: DNS, SPF, DMARC, MX, WHOIS y score de riesgo.

## Stack

| Capa | Tecnología |
|---|---|
| API | Python + FastAPI (async) |
| Escaneo DNS | Go (microservicio) |
| Base de datos | PostgreSQL + JSONB |
| Infraestructura | Docker + GitHub Actions |

## Levantar el proyecto

### Desarrollo

```bash
cp .env.example .env  # completar credenciales
docker compose up --build
```

### Producción

```bash
export POSTGRES_USER=admin
export POSTGRES_PASSWORD=una_password_segura
export POSTGRES_DB=mailanalyzer
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

API disponible en `http://localhost:8000` — documentación en `http://localhost:8000/docs`

## Endpoints

```
POST /v1/scans          # analizar un dominio a partir de un email
GET  /v1/scans          # listar todos los análisis
GET  /v1/scans/{id}     # obtener un análisis por ID
GET  /health            # health check
```

### Ejemplo

```bash
curl -X POST http://localhost:8000/v1/scans \
  -H "Content-Type: application/json" \
  -d '{"email": "test@gmail.com"}'
```

```json
{
  "scan_id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "test@gmail.com",
  "domain": "gmail.com",
  "status": "completed",
  "risk_score": 90,
  "dns": { "has_mx": true, "has_spf": true, "has_dmarc": true },
  "whois": { "registrar": "MarkMonitor Inc.", "country": "US" }
}
```

## Tests

```bash
# Unitarios (sin DB)
docker compose run --no-deps --rm api pytest tests/ -v -m "not integration"

# Integración Python (requiere db-test corriendo)
docker compose up -d db-test
docker compose run --rm \
  -e TEST_DATABASE_URL=postgresql+asyncpg://test_user:test_pass@db-test:5432/mailanalyzer_test \
  api pytest tests/ -v -m integration

# Unitarios Go
docker run --rm -v "${PWD}/scanner:/app" -w /app golang:1.23 go test ./... -v -short

# Integración Go (DNS real)
docker run --rm -v "${PWD}/scanner:/app" -w /app golang:1.23 go test ./... -v
```

## CI

GitHub Actions corre 3 jobs en paralelo en cada push a `main`:
- Tests unitarios Python
- Tests de integración Python (con PostgreSQL)
- Tests Go
