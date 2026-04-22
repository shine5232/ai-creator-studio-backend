from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class ContentAnalytics(Base):
    __tablename__ = "content_analytics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    publish_record_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("publish_records.id"))
    platform: Mapped[str | None] = mapped_column(String(30))
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    like_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)
    share_count: Mapped[int] = mapped_column(Integer, default=0)
    favorite_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_watch_time: Mapped[float | None] = mapped_column(Float)
    engagement_rate: Mapped[float | None] = mapped_column(Float)
    recorded_at: Mapped[str | None] = mapped_column(String(50))


class GenerationCost(Base, TimestampMixin):
    __tablename__ = "generation_costs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("projects.id"))
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    service_type: Mapped[str] = mapped_column(String(30), nullable=False)
    shot_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("shots.id"))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    api_calls: Mapped[int] = mapped_column(Integer, default=1)
    cost_amount: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="CNY")
    duration_ms: Mapped[int | None] = mapped_column(Integer)
