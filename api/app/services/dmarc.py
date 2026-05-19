def analyze_dmarc(domain: str, txt_records: list[str] | None = None) -> dict:
    """
    Analiza el registro DMARC del dominio.
    Los registros DMARC viven en _dmarc.dominio.com
    Go ya los detectó, pero aquí los analizamos en detalle.
    """

    dmarc_record = None
    if txt_records:
        for record in txt_records:
            if record.startswith("v=DMARC1"):
                dmarc_record = record
                break

    if not dmarc_record:
        return {
            "found": False,
            "record": None,
            "policy": None,
            "subdomain_policy": None,
            "pct": None,
            "findings": ["no_dmarc"],
            "details": "No DMARC record found"
        }

    findings = []
    tags = _parse_dmarc_tags(dmarc_record)

    policy = tags.get("p", "none")
    subdomain_policy = tags.get("sp", policy)
    pct = int(tags.get("pct", 100))

    if policy == "none":
        findings.append("dmarc_none")
    elif policy == "quarantine":
        findings.append("dmarc_quarantine")

    if pct < 100:
        findings.append("dmarc_partial")

    return {
        "found": True,
        "record": dmarc_record,
        "policy": policy,
        "subdomain_policy": subdomain_policy,
        "pct": pct,
        "findings": findings,
        "details": _describe_policy(policy, pct)
    }

def _parse_dmarc_tags(record: str) -> dict:
    """
    Parsea el registro DMARC en un diccionario de tags.
    Ejemplo: "v=DMARC1; p=reject; pct=100" → {"v": "DMARC1", "p": "reject", "pct": "100"}
    """
    tags = {}
    parts = record.split(";")
    for part in parts:
        part = part.strip()
        if "=" in part:
            key, value = part.split("=", 1)
            tags[key.strip()] = value.strip()
    return tags

def _describe_policy(policy: str, pct: int) -> str:
    descriptions = {
        "none":       "Solo monitoreo, no se toman acciones contra emails no autorizados",
        "quarantine": "Emails no autorizados van a spam",
        "reject":     "Emails no autorizados son rechazados completamente",
    }
    base = descriptions.get(policy, "Política desconocida")
    if pct < 100:
        base += f" (aplicado al {pct}% de los emails)"
    return base