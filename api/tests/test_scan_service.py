# Tests unitarios para las funciones puras de scan_service.
# "Puras" significa: misma entrada → misma salida, sin DB, sin red, sin efectos secundarios.
# Son las más fáciles de testear y las que más valor dan como base.

import pytest
from app.services.scan_service import calculate_risk_score, extract_domain


# ─── calculate_risk_score ────────────────────────────────────────────────────

class TestCalculateRiskScore:

    def test_sin_findings_score_es_100(self):
        # Sin problemas detectados, el dominio es perfecto → score máximo
        assert calculate_risk_score([]) == 100

    def test_un_finding_resta_su_penalizacion(self):
        # no_spf tiene penalty=20 → 100 - 20 = 80
        assert calculate_risk_score(["no_spf"]) == 80

    def test_multiples_findings_suman_penalizaciones(self):
        # no_spf(20) + no_dmarc(20) + no_mx(15) = 55 → 100 - 55 = 45
        assert calculate_risk_score(["no_spf", "no_dmarc", "no_mx"]) == 45

    def test_score_nunca_baja_de_cero(self):
        # Acumular todas las penalizaciones no puede dar score negativo
        todos = ["no_spf", "weak_spf", "no_dmarc", "dmarc_none", "no_mx", "domain_expiring_soon"]
        assert calculate_risk_score(todos) >= 0

    def test_finding_desconocido_se_ignora(self):
        # Una regla que no existe en RULES no suma penalización
        assert calculate_risk_score(["regla_que_no_existe"]) == 100

    def test_finding_duplicado_solo_cuenta_una_vez(self):
        # Si el mismo finding aparece dos veces, solo debería penalizar una vez.
        # Esto documenta el comportamiento actual: sum() con 'in' no deduplica.
        # El valor esperado es 60 (no 40) porque 'in' evalúa existencia, no frecuencia.
        assert calculate_risk_score(["no_spf", "no_spf"]) == 80


# ─── extract_domain ───────────────────────────────────────────────────────────

class TestExtractDomain:

    def test_email_simple(self):
        assert extract_domain("user@gmail.com") == "gmail.com"

    def test_email_con_subdominio(self):
        # El dominio es todo lo que está después del @
        assert extract_domain("user@mail.empresa.com") == "mail.empresa.com"

    def test_email_con_punto_en_usuario(self):
        assert extract_domain("nombre.apellido@gmail.com") == "gmail.com"

    def test_dominio_con_tld_compuesto(self):
        assert extract_domain("contacto@corxea.cl") == "corxea.cl"
