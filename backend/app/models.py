import uuid
from datetime import datetime

from sqlalchemy import String, Float, ForeignKey, DateTime, Text, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    beans = relationship("Bean", back_populates="user", cascade="all, delete-orphan")
    shots = relationship("Shot", back_populates="user", cascade="all, delete-orphan")


class Bean(Base):
    __tablename__ = "beans"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_bean_name_per_user"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    roaster: Mapped[str | None] = mapped_column(String(180), nullable=True)
    bean_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    origin: Mapped[str | None] = mapped_column(String(180), nullable=True)
    roast_level: Mapped[str] = mapped_column(String(30), default="Mittel")
    cupping: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="beans")
    shots = relationship("Shot", back_populates="bean", cascade="all, delete-orphan")


class Shot(Base):
    __tablename__ = "shots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    bean_id: Mapped[str] = mapped_column(ForeignKey("beans.id", ondelete="CASCADE"), index=True)
    grind: Mapped[float] = mapped_column(Float)
    actual_time: Mapped[float] = mapped_column(Float)
    target_time: Mapped[float | None] = mapped_column(Float, nullable=True)
    dose: Mapped[float | None] = mapped_column(Float, nullable=True)
    yield_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    machine: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    features_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    timeseries_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    user = relationship("User", back_populates="shots")
    bean = relationship("Bean", back_populates="shots")
