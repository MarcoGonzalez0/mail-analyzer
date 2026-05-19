def analyze_spf(txt_records: list[str]) -> dict:
    """
    Analiza los registros TXT buscando y evaluando la política SPF.
    """
    spf_record = None
    for record in txt_records:
        if record.startswith("v=spf1"):
            spf_record = record
            break

    # Si no se encuentra un registro SPF, se reporta como tal
    if not spf_record:
        return {
            "found": False,
            "record": None,
            "policy": None,
            "findings": ["no_spf"],
            "details": "No SPF record found"
        }

    findings = []
    policy = None

    if "+all" in spf_record:
        policy = "+all"
        findings.append("weak_spf")
    elif "-all" in spf_record:
        policy = "-all"       # estricto, rechaza todo lo no autorizado
    elif "~all" in spf_record:
        policy = "~all"       # softfail, marca pero no rechaza
        findings.append("soft_spf")
    elif "?all" in spf_record:
        policy = "?all"       # neutral, no hace nada
        findings.append("neutral_spf")

    return {
        "found": True,
        "record": spf_record,
        "policy": policy,
        "findings": findings,
        "details": _describe_policy(policy)
    }

def _describe_policy(policy: str | None) -> str:
    descriptions = {
        "+all": "Cualquier servidor puede enviar emails, configuración peligrosa",
        "-all": "Solo servidores autorizados pueden enviar emails, configuración estricta",
        "~all": "Servidores no autorizados son marcados pero no rechazados, configuración débil",
        "?all": "No hay política definida para servidores no autorizados, configuración neutral",
    }
    return descriptions.get(policy, "Política desconocida")