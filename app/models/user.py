from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(20), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    projects: Mapped[list["Project"]] = relationship(back_populates="user", lazy="selectin")  # noqa: F821
    quotas: Mapped[list["UserQuota"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    social_accounts: Mapped[list["SocialAccount"]] = relationship(back_populates="user", cascade="all, delete-orphan")  # noqa: F821


class UserQuota(Base, TimestampMixin):
    __tablename__ = "user_quotas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    quota_type: Mapped[str] = mapped_column(String(50), nullable=False)
    used_count: Mapped[int] = mapped_column(Integer, default=0)
    limit_count: Mapped[int] = mapped_column(Integer, default=100)
    period: Mapped[str] = mapped_column(String(20), default="monthly")
    reset_at: Mapped[DateTime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="quotas")
