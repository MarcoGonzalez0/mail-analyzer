"""
Tests de integración de los endpoints HTTP.

Por qué son de integración y no unitarios:
  - Usan la DB real (PostgreSQL, via conftest.db_session)
  - Pasan por FastAPI completo: routing → validación Pydantic → servicio → DB
  - Mocks solo para dependencias EXTERNAS (Go scanner y WHOIS):
      call_scanner → evita llamadas HTTP al contenedor Go (no disponible en CI)
      analyze_whois → evita llamadas reales a servidores WHOIS (lentas, frágiles)

Lo que SÍ se testea sin mocks:
  - Routing de FastAPI (/v1/scans → create_scan)
  - Validación de Pydantic (email inválido → 422)
  - calculate_risk_score y extract_domain (lógica de negocio)
  - Escritura y lectura en PostgreSQL
  - Serialización de la respuesta (ScanResponse)
"""

import pytest
from unittest.mock import patch, AsyncMock # patch para reemplazar funciones con mocks, AsyncMock para mocks de funciones async

# ─── Datos de prueba ──────────────────────────────────────────────────────────

# Respuesta simulada del scanner Go (lo que call_scanner devolvería en producción)
SCANNER_MOCK = {
    "domain": "gmail.com",
    "dns": {
        "a_records": ["142.250.80.37"],
        "mx_records": ["gmail-smtp-in.l.google.com."],
        "txt_records": ["v=spf1 include:_spf.google.com ~all"],
        "dmarc_records": ["v=DMARC1; p=reject; pct=100"],
        "has_mx": True,
        "has_spf": True,
        "has_dmarc": True,
        "errors": [],
    },
}

# Respuesta simulada de analyze_whois
WHOIS_MOCK = {
    "registrar": "MarkMonitor Inc.",
    "creation_date": "1995-08-13",
    "expiration_date": "2028-09-14",
    "registrant": "Google LLC",
    "org": "Google LLC",
    "country": "US",
    "updated_date": "2019-09-09",
    "emails": [],
    "findings": [],  # sin penalizaciones WHOIS
}


# ─── POST /v1/scans ───────────────────────────────────────────────────────────

@pytest.mark.integration
class TestCrearScan:

    async def test_crea_scan_y_devuelve_completed(self, client):
        """Flujo completo: request llega, se analiza, se guarda en DB, se devuelve."""
        with (
            # sobreescribimos la funcion call_scanner y analyze_whois para que devuelvan datos predecibles de los mocks definidos arriba
            patch("app.services.scan_service.call_scanner", new=AsyncMock(return_value=SCANNER_MOCK)),
            patch("app.services.scan_service.analyze_whois", return_value=WHOIS_MOCK),
        ):
            response = await client.post("/v1/scans", json={"email": "test@gmail.com"}) # si le doy esto me deberia dar el mismo response de MOCK

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@gmail.com"
        assert data["domain"] == "gmail.com"
        assert data["status"] == "completed"
        assert data["scan_id"] is not None
        assert isinstance(data["risk_score"], int)
        assert 0 <= data["risk_score"] <= 100

    async def test_email_inválido_devuelve_422(self, client):
        """Pydantic valida el email antes de llegar al servicio. Sin mocks necesarios."""
        response = await client.post("/v1/scans", json={"email": "no-es-un-email"})
        assert response.status_code == 422

    async def test_body_vacío_devuelve_422(self, client):
        response = await client.post("/v1/scans", json={})
        assert response.status_code == 422

    async def test_scanner_caído_guarda_scan_como_failed(self, client):
        """
        Si el scanner Go no responde, la app NO debe devolver 500.
        El scan se guarda en DB con status='failed' y el endpoint devuelve 200.
        Esto protege al cliente: sabe que falló pero la API no se cae.
        """
        with patch(
            "app.services.scan_service.call_scanner",
            new=AsyncMock(side_effect=Exception("connection refused")),
        ):
            response = await client.post("/v1/scans", json={"email": "test@gmail.com"})

        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    async def test_score_refleja_las_reglas(self, client):
        """
        Con SPF ~all (soft_spf, -10) y DMARC reject (sin penalización),
        el score debe ser menor que 100.
        """
        with (
            patch("app.services.scan_service.call_scanner", new=AsyncMock(return_value=SCANNER_MOCK)),
            patch("app.services.scan_service.analyze_whois", return_value=WHOIS_MOCK),
        ):
            response = await client.post("/v1/scans", json={"email": "test@gmail.com"})

        score = response.json()["risk_score"]
        # SCANNER_MOCK usa ~all (soft_spf, penalidad 10) → score < 100
        assert score < 100


# ─── GET /v1/scans ────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestListarScans:

    async def test_lista_vacía_sin_scans(self, client):
        response = await client.get("/v1/scans")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["scans"] == []

    async def test_total_coincide_con_cantidad_creada(self, client):
        with (
            patch("app.services.scan_service.call_scanner", new=AsyncMock(return_value=SCANNER_MOCK)),
            patch("app.services.scan_service.analyze_whois", return_value=WHOIS_MOCK),
        ):
            await client.post("/v1/scans", json={"email": "a@gmail.com"})
            await client.post("/v1/scans", json={"email": "b@gmail.com"})

        response = await client.get("/v1/scans")
        data = response.json()
        assert data["total"] == 2
        assert len(data["scans"]) == 2


# ─── GET /v1/scans/{scan_id} ──────────────────────────────────────────────────

@pytest.mark.integration
class TestObtenerScan:

    async def test_obtiene_scan_por_id(self, client):
        """Crea un scan y lo recupera por ID — verifica que la DB persiste correctamente."""
        with (
            patch("app.services.scan_service.call_scanner", new=AsyncMock(return_value=SCANNER_MOCK)),
            patch("app.services.scan_service.analyze_whois", return_value=WHOIS_MOCK),
        ):
            create_resp = await client.post("/v1/scans", json={"email": "test@gmail.com"}) # client es un servidor de pruebas simulado

        scan_id = create_resp.json()["scan_id"]

        response = await client.get(f"/v1/scans/{scan_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["scan_id"] == scan_id
        assert data["email"] == "test@gmail.com"

    async def test_id_inexistente_devuelve_404(self, client):
        response = await client.get("/v1/scans/00000000-0000-0000-0000-000000000000")
        assert response.status_code == 404

    async def test_id_no_uuid_devuelve_422(self, client):
        """Un entero como "13" no es UUID válido — FastAPI debe rechazarlo antes del servicio."""
        response = await client.get("/v1/scans/13")
        assert response.status_code == 422


# ─── GET /health ──────────────────────────────────────────────────────────────

@pytest.mark.integration
class TestHealth:

    async def test_health_con_db_ok(self, client):
        """Con DB disponible, health devuelve status ok."""
        response = await client.get("/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "ok"
        assert "version" in data

    async def test_health_con_db_caída(self, client):
        """Si la DB falla, health devuelve degraded (no 500) — la app sigue respondiendo."""
        from app.database import get_db
        from app.main import app
        # Sobrescribimos la dependencia get_db para simular una falla de DB (ej. conexión rechazada).

        async def _db_rota():
            mock_session = AsyncMock()
            mock_session.execute.side_effect = Exception("connection refused")
            yield mock_session

        app.dependency_overrides[get_db] = _db_rota

        # Al hacer esto, la dependencia get_db ahora usará _db_rota, que simula una falla de DB. Esto nos permite probar cómo responde el endpoint de health cuando la DB no está disponible.
        response = await client.get("/v1/health")

        assert response.status_code == 200
        assert response.json()["status"] == "degraded"
        assert response.json()["db"] == "error"
        
