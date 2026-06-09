# Tests unitarios para los helpers internos de whois.py.
# No testeamos analyze_whois() directamente porque hace una llamada de red real.
# Eso va en tests de integración. Acá testeamos la lógica pura de normalización.

import pytest
from datetime import datetime, timezone
from app.services.whois import _parse_date, _parse_list, _parse_nameservers, _parse_status


class TestParseList:
    """_parse_list convierte cualquier valor a lista de strings."""

    def test_none_devuelve_lista_vacia(self):
        assert _parse_list(None) == []

    def test_string_devuelve_lista_con_un_elemento(self):
        assert _parse_list("admin@example.com") == ["admin@example.com"]

    def test_lista_de_strings_se_mantiene(self):
        emails = ["admin@example.com", "tech@example.com"]
        assert _parse_list(emails) == emails

    def test_lista_con_no_strings_se_convierte(self):
        # Por si la librería devuelve tipos inesperados
        assert _parse_list([1, 2, 3]) == ["1", "2", "3"]

    def test_tupla_se_convierte_a_lista(self):
        result = _parse_list(("a@b.com", "c@d.com"))
        assert isinstance(result, list)
        assert len(result) == 2


class TestParseNameservers:
    """_parse_nameservers normaliza nameservers a lista de strings en minúscula."""

    def test_none_devuelve_lista_vacia(self):
        assert _parse_nameservers(None) == []

    def test_string_unico_devuelve_lista(self):
        result = _parse_nameservers("NS1.EXAMPLE.COM")
        assert result == ["ns1.example.com"]

    def test_lista_se_pasa_a_minusculas(self):
        result = _parse_nameservers(["NS1.CLOUDFLARE.COM", "NS2.CLOUDFLARE.COM"])
        assert result == ["ns1.cloudflare.com", "ns2.cloudflare.com"]

    def test_ya_en_minusculas_no_cambia(self):
        ns = ["ignat.ns.cloudflare.com", "tricia.ns.cloudflare.com"]
        assert _parse_nameservers(ns) == ns


class TestParseStatus:
    """_parse_status normaliza el campo status de WHOIS."""

    def test_none_devuelve_lista_vacia(self):
        assert _parse_status(None) == []

    def test_string_devuelve_lista_con_un_elemento(self):
        result = _parse_status("clientTransferProhibited")
        assert result == ["clientTransferProhibited"]

    def test_lista_se_mantiene(self):
        statuses = ["clientTransferProhibited", "clientUpdateProhibited"]
        assert _parse_status(statuses) == statuses


class TestParseDate:
    """_parse_date normaliza fechas de distintos formatos a datetime con timezone."""

    def test_none_devuelve_none(self):
        assert _parse_date(None) is None

    def test_string_vacio_devuelve_none(self):
        assert _parse_date("") is None

    def test_datetime_con_timezone_se_mantiene(self):
        dt = datetime(2023, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
        result = _parse_date(dt)
        assert result == dt

    def test_datetime_sin_timezone_agrega_utc(self):
        # python-whois a veces devuelve datetime naive (sin timezone)
        dt = datetime(2023, 6, 21, 12, 0, 0)
        result = _parse_date(dt)
        assert result.tzinfo is not None
        assert result.tzinfo == timezone.utc

    def test_lista_toma_el_primer_elemento(self):
        # python-whois puede devolver una lista de fechas para el mismo campo
        dt1 = datetime(2023, 1, 1, tzinfo=timezone.utc)
        dt2 = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = _parse_date([dt1, dt2])
        assert result == dt1

    def test_resultado_siempre_tiene_timezone(self):
        dt = datetime(2026, 6, 22, 12, 57, 46)
        result = _parse_date(dt)
        assert result.tzinfo is not None
