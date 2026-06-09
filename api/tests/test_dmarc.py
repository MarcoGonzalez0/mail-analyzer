# Tests unitarios para analyze_dmarc.
# DMARC tiene más combinaciones que SPF: política + pct + subdominio.
# Cada test cubre una dimensión distinta del análisis.

import pytest
from app.services.dmarc import analyze_dmarc


DOMAIN = "example.com"


class TestAnalyzeDmarc:

    # ── caso: sin registros ───────────────────────────────────────────────────

    def test_lista_vacia_no_encontrado(self):
        result = analyze_dmarc(DOMAIN, [])
        assert result["found"] is False
        assert "no_dmarc" in result["findings"]

    def test_none_como_records_no_encontrado(self):
        # Go puede devolver null en dmarc_records → Python lo recibe como None
        result = analyze_dmarc(DOMAIN, None)
        assert result["found"] is False
        assert "no_dmarc" in result["findings"]

    def test_registros_sin_dmarc_no_encontrado(self):
        result = analyze_dmarc(DOMAIN, ["v=spf1 -all", "otro registro"])
        assert result["found"] is False

    # ── caso: política reject (la más estricta) ───────────────────────────────

    def test_politica_reject_sin_findings_de_seguridad(self):
        # reject = rechaza emails no autorizados → configuración ideal
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=reject; pct=100"])
        assert result["found"] is True
        assert result["policy"] == "reject"
        assert "dmarc_none" not in result["findings"]
        assert "dmarc_quarantine" not in result["findings"]

    # ── caso: política quarantine ─────────────────────────────────────────────

    def test_politica_quarantine_agrega_finding(self):
        # quarantine = va a spam pero no se rechaza → penalización leve
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=quarantine; pct=100"])
        assert result["found"] is True
        assert result["policy"] == "quarantine"
        assert "dmarc_quarantine" in result["findings"]

    # ── caso: política none (solo monitoreo) ──────────────────────────────────

    def test_politica_none_agrega_finding(self):
        # none = solo recolecta reportes, no protege → penalización alta
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=none"])
        assert result["found"] is True
        assert result["policy"] == "none"
        assert "dmarc_none" in result["findings"]

    # ── caso: porcentaje parcial ──────────────────────────────────────────────

    def test_pct_menor_a_100_agrega_dmarc_partial(self):
        # pct=50 = la política solo aplica al 50% de los emails → protección incompleta
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=reject; pct=50"])
        assert "dmarc_partial" in result["findings"]
        assert result["pct"] == 50

    def test_pct_igual_a_100_no_agrega_dmarc_partial(self):
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=reject; pct=100"])
        assert "dmarc_partial" not in result["findings"]

    def test_pct_por_defecto_es_100(self):
        # Si no se especifica pct en el registro, el estándar asume 100
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=reject"])
        assert result["pct"] == 100

    # ── caso: política de subdominio ──────────────────────────────────────────

    def test_sp_hereda_politica_principal_si_no_se_define(self):
        # Si no hay 'sp', el subdominio hereda la política de 'p'
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=reject"])
        assert result["subdomain_policy"] == "reject"

    def test_sp_independiente_si_se_define(self):
        result = analyze_dmarc(DOMAIN, ["v=DMARC1; p=reject; sp=none"])
        assert result["policy"] == "reject"
        assert result["subdomain_policy"] == "none"

    # ── estructura del resultado ──────────────────────────────────────────────

    def test_resultado_siempre_tiene_claves_esperadas(self):
        result = analyze_dmarc(DOMAIN, [])
        for clave in ["found", "record", "policy", "subdomain_policy", "pct", "findings", "details"]:
            assert clave in result
