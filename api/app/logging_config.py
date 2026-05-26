import logging
import json
from datetime import datetime, timezone

class JSONFormatter(logging.Formatter):
    """
    Formateador que convierte los logs a JSON estructurado.
    Se usa en producción para que los sistemas de monitoreo puedan indexarlos.
    """
    def format(self, record: logging.LogRecord) -> str: 
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }

        # Si el log tiene datos extra, los incluimos
        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        # Si hay una excepción, la incluimos
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry) # string JSON del log estructurado


class TextFormatter(logging.Formatter):
    """
    Formateador legible para desarrollo.
    """
    FORMAT = "%(asctime)s [%(levelname)s] %(module)s - %(message)s"

    def __init__(self):
        super().__init__(self.FORMAT, datefmt="%Y-%m-%d %H:%M:%S")


def setup_logging(environment: str = "development") -> logging.Logger:
    """
    Configura y devuelve el logger principal de la aplicación.
    environment: "development" o "production"
    """
    logger = logging.getLogger("mail_analyzer")
    logger.setLevel(logging.DEBUG if environment == "development" else logging.INFO)

    # Evitar duplicar handlers si se llama más de una vez
    if logger.handlers:
        return logger

    handler = logging.StreamHandler()

    if environment == "production":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(TextFormatter())

    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    """
    Devuelve el logger ya configurado.
    Todos los módulos llaman a esta función en vez de configurar su propio logger.
    """
    return logging.getLogger("mail_analyzer")