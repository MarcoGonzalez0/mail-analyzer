# Tests unitarios para analyze_spf.
# Cada caso testea una política distinta del estándar SPF.
# No hay red, no hay DNS real — solo listas de strings como las que devuelve Go.

import pytest
from app.services.spf import analyze_spf


class TestAnalyzeSpf:

    # ── caso: sin registros ───────────────────────────────────────────────────

    def test_lista_vacia_no_encontrado(self):
        result = analyze_spf([])
        assert result["found"] is False
        assert "no_spf" in result["findings"]

    def test_registros_sin_spf_no_encontrado(self):
        # Hay TXT records pero ninguno es SPF — situación real y común
        result = analyze_spf(["google-site-verification=abc123", "v=DKIM1 k=rsa p=..."])
        assert result["found"] is False
        assert "no_spf" in result["findings"]

    # ── caso: política estricta (-all) ────────────────────────────────────────

    def test_politica_estricta_sin_findings(self):
        # -all = solo servidores autorizados pueden enviar → configuración correcta
        result = analyze_spf(["v=spf1 include:_spf.google.com -all"])
        assert result["found"] is True
        assert result["policy"] == "-all"
        assert result["findings"] == []  # sin problemas de seguridad

    # ── caso: política débil (+all) ───────────────────────────────────────────

    def test_politica_debil_agrega_weak_spf(self):
        # +all = cualquier servidor puede enviar → el más peligroso
        result = analyze_spf(["v=spf1 +all"])
        assert result["found"] is True
        assert result["policy"] == "+all"
        assert "weak_spf" in result["findings"]

    # ── caso: soft fail (~all) ────────────────────────────────────────────────

    def test_soft_fail_agrega_soft_spf(self):
        # ~all = marca como sospechoso pero no rechaza → política intermedia
        result = analyze_spf(["v=spf1 include:_spf.google.com ~all"])
        assert result["found"] is True
        assert result["policy"] == "~all"
        assert "soft_spf" in result["findings"]

    # ── caso: neutral (?all) ──────────────────────────────────────────────────

    def test_neutral_agrega_neutral_spf(self):
        # ?all = no hay política definida → equivale a no tener SPF
        result = analyze_spf(["v=spf1 ?all"])
        assert result["found"] is True
        assert result["policy"] == "?all"
        assert "neutral_spf" in result["findings"]

    # ── casos de estructura del resultado ─────────────────────────────────────

    def test_resultado_siempre_tiene_claves_esperadas(self):
        # Contrato: la función siempre devuelve estas claves, sin importar el input
        result = analyze_spf([])
        assert "found" in result
        assert "record" in result
        assert "policy" in result
        assert "findings" in result
        assert "details" in result

    def test_solo_toma_el_primer_registro_spf(self):
        # Tener más de un registro SPF es técnicamente inválido, pero puede pasar.
        # La función debe tomar el primero y no duplicar findings.
        result = analyze_spf(["v=spf1 -all", "v=spf1 +all"])
        assert result["policy"] == "-all"
        assert "weak_spf" not in result["findings"]
