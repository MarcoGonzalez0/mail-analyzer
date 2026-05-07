from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone
import uuid
from app.database import Base # importar clase base ORM desde tu configuración de SQLAlchemy

class Scan(Base):
    # Clase declarativa, aqui no se valida nada, solo se define la estructura de la tabla en la base de datos
    __tablename__ = "scans"

    scan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    status = Column(String, default="pending")
    risk_score = Column(Integer, nullable=True)
    results = Column(JSON, nullable=True)
    findings = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)