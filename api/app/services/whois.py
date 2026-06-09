
import whois
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

def analyze_whois(domain: str) -> dict:
    """
    Consulta información WHOIS del dominio.
    """
    try:
        w = whois.whois(domain)

        has_data = any([ # Verificar si se obtuvo información relevante
            getattr(w, "domain_name", None),
            getattr(w, "registrar", None),
            getattr(w, "creation_date", None),
            getattr(w, "expiration_date", None),
            getattr(w, "name_servers", None),
        ])

        if not has_data: # Si no se encontró información relevante, consideramos que no se encontró el dominio
            return {
                "found": False,
                "findings": ["whois_not_found"],
                "details": "No WHOIS information found"
            }

        expiration_date = _parse_date(w.expiration_date)
        creation_date = _parse_date(w.creation_date)
        findings = []

        days_until_expiry = None
        if expiration_date:
            days_until_expiry = (expiration_date - datetime.now(timezone.utc)).days
            if days_until_expiry < 30:
                findings.append("domain_expiring_soon")

        updated_date = _parse_date(getattr(w, "updated_date", None))

        return {
            "found": True,
            # quién registró el dominio y desde dónde
            "registrar":    getattr(w, "registrar", None),
            "registrant":   getattr(w, "registrant", None),  # nombre del registrante (no siempre disponible)
            "org":          getattr(w, "org", None),          # organización registrante
            "country":      getattr(w, "country", None),      # país de registro — útil para detectar dominios que fingen ser locales
            # fechas
            "creation_date":  creation_date.isoformat() if creation_date else None,
            "updated_date":   updated_date.isoformat() if updated_date else None,   # modificación reciente puede indicar domain hijacking
            "expiration_date": expiration_date.isoformat() if expiration_date else None,
            "days_until_expiry": days_until_expiry,
            # contacto y resolución
            "emails":       _parse_list(getattr(w, "emails", None)),       # email anónimo/desechable es señal de alerta
            "name_servers": _parse_nameservers(w.name_servers),
            "status":       _parse_status(w.status),
            # análisis de seguridad
            "findings": findings,
            "details":  _describe(days_until_expiry)
        }

    except Exception as e:
        return {
            "found": False,
            "findings": ["whois_error"],
            "details": f"WHOIS lookup failed: {str(e)}"
        }

def _parse_date(date) -> datetime | None:
    if not date:
        return None
    if isinstance(date, list):
        date = date[0]
    if isinstance(date, datetime):
        if date.tzinfo is None:
            return date.replace(tzinfo=timezone.utc)
        return date
    
    if isinstance(date, str):
        try:
            parsed = parsedate_to_datetime(date)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except Exception:
            pass

        # fallback manual
        try:
            return datetime.strptime(
                date.replace(" CLST", ""),
                "%Y-%m-%d %H:%M:%S"
            ).replace(tzinfo=timezone.utc)
        except Exception:
            return None

    return None

def _parse_list(val) -> list[str]:
    """Convierte cualquier valor (str, lista, None) a lista de strings."""
    if val is None:
        return []
    if isinstance(val, (list, tuple, set)):
        return [str(x) for x in val]
    return [str(val)]

def _parse_nameservers(ns) -> list[str]:
    if not ns:
        return []
    if isinstance(ns, list):
        return [n.lower() for n in ns]
    return [ns.lower()]

def _parse_status(status) -> list[str]:
    if not status:
        return []
    if isinstance(status, list):
        return status
    return [status]

def _describe(days_until_expiry: int | None) -> str:
    if days_until_expiry is None:
        return "Expiration date unknown"
    if days_until_expiry < 0:
        return "Domain has expired"
    if days_until_expiry < 30:
        return f"Domain expires in {days_until_expiry} days, renew urgently"
    return f"Domain expires in {days_until_expiry} days"