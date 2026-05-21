
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

        return {
            "found": True,
            "registrar": w.registrar,
            "creation_date": creation_date.isoformat() if creation_date else None,
            "expiration_date": expiration_date.isoformat() if expiration_date else None,
            "days_until_expiry": days_until_expiry,
            "name_servers": _parse_nameservers(w.name_servers),
            "status": _parse_status(w.status),
            "findings": findings,
            "details": _describe(days_until_expiry)
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