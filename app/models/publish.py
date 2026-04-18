from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class SocialAccount(Base, TimestampMixin):
    __tablename__ = "social_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    account_id: Mapped[str | None] = mapped_column(String(100))
    auth_data: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_publish_at: Mapped[DateTime | None] = mapped_column(DateTime)

    user: Mapped["User"] = relationship(back_populates="social_accounts")  # noqa: F821
    publish_records: Mapped[list["PublishRecord"]] = relationship(back_populates="social_account", cascade="all, delete-orphan")


class PublishRecord(Base):
    __tablename__ = "publish_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("social_accounts.id"), nullable=False)
    asset_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("assets.id"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(Text)
    platform_post_id: Mapped[str | None] = mapped_column(String(100))
    platform_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default="pending")
    published_at: Mapped[DateTime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)

    project: Mapped["Project"] = relationship(back_populates="publish_records")  # noqa: F821
    social_account: Mapped["SocialAccount"] = relationship(back_populates="publish_records")
