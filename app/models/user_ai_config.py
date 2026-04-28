from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class UserAIConfig(Base, TimestampMixin):
    __tablename__ = "user_ai_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True
    )
    config_name: Mapped[str] = mapped_column(String(100), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_id: Mapped[str] = mapped_column(String(100), nullable=False)
    service_type: Mapped[str] = mapped_column(String(30), nullable=False)
    api_base_url: Mapped[str | None] = mapped_column(String(500))
    encrypted_api_key: Mapped[str | None] = mapped_column(String(500))
    api_key_hint: Mapped[str | None] = mapped_column(String(100))
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_config: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="ai_configs")  # noqa: F821

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )
