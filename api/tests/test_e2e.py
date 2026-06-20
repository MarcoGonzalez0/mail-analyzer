"""
Tests end-to-end: flujo completo sin mocks.

A diferencia de test_endpoints.py (que mockea call_scanner y analyze_whois),
estos tests ejecutan el flujo real:

  POST /v1/scans → Python → Go scanner (HTTP real) → DNS real → WHOIS real → DB

Verifican el CONTRATO entre servicios: que el JSON que Go produce
sea exactamente el que Python espera. Si Go cambia un campo (ej. has_mx → hasMx),
los tests de integración siguen pasando (usan mock), pero este test lo detecta.

Requieren:
  - Scanner Go corriendo    (docker compose up scanner)
  - DB de test corriendo    (docker compose up db-test)
  - Red disponible          (DNS y WHOIS hacen queries reales)

Ejecución:
  docker compose run --rm -e TEST_DATABASE_URL=postgresql+asyncpg://test_user:test_pass@db-test:5432/mailanalyzer_test api pytest tests/ -v -m e2e
"""

import pytest


@pytest.mark.e2e
class TestFlujoCompleto:

    async def test_scan_dominio_real(self, client):
        """
        Flujo completo con gmail.com — sin mocks.
        Verifica que Python llama al scanner Go real, Go hace DNS real,
        Python hace WHOIS real, y todo se ensambla correctamente.
        """
        response = await client.post("/v1/scans", json={"email": "test@gmail.com"})

        assert response.status_code == 200
        data = response.json()

        # ── Estado general ────────────────────────────────────────────────────
        assert data["status"] == "completed"
        assert data["domain"] == "gmail.com"
        assert data["email"] == "test@gmail.com"
        assert data["scan_id"] is not None

        # ── DNS (viene del scanner Go via HTTP) ──────────────────────────────
        # Estas assertions validan el contrato: si Go cambia la estructura
        # del JSON, este test falla y te avisa antes de que llegue a producción.
        dns = data["results"]["dns"]
        assert dns["has_mx"] is True
        assert dns["has_spf"] is True
        assert dns["has_dmarc"] is True
        assert len(dns["mx_records"]) > 0
        assert len(dns["txt_records"]) > 0

        # ── Risk score (calculado por Python con datos reales) ────────────────
        assert isinstance(data["risk_score"], int)
        assert 0 <= data["risk_score"] <= 100

        # ── WHOIS (query real desde Python) ───────────────────────────────────
        whois_data = data["results"]["analysis"]["whois"]
        assert whois_data["found"] is True
