from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Script(Base, TimestampMixin):
    __tablename__ = "scripts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    theme: Mapped[str | None] = mapped_column(String(100))
    sub_theme: Mapped[str | None] = mapped_column(String(100))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    narrative_type: Mapped[str | None] = mapped_column(String(50))
    content: Mapped[str] = mapped_column(Text, nullable=False)
    viral_elements: Mapped[str | None] = mapped_column(Text)
    source_case_id: Mapped[int | None] = mapped_column(Integer)
    script_path: Mapped[str | None] = mapped_column(String(500))  # Markdown file path
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)

    project: Mapped["Project"] = relationship(back_populates="scripts")  # noqa: F821
    storyboard: Mapped["Storyboard | None"] = relationship(
        back_populates="script", uselist=False, cascade="all, delete-orphan", lazy="selectin",
    )


class Storyboard(Base, TimestampMixin):
    __tablename__ = "storyboards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    script_id: Mapped[int] = mapped_column(Integer, ForeignKey("scripts.id"), nullable=False)
    total_shots: Mapped[int] = mapped_column(Integer, nullable=False)
    total_duration: Mapped[int | None] = mapped_column(Integer)
    tone_mapping: Mapped[str | None] = mapped_column(Text)

    script: Mapped["Script"] = relationship(back_populates="storyboard")
    shots: Mapped[list["Shot"]] = relationship(
        back_populates="storyboard", order_by="Shot.shot_number",
        cascade="all, delete-orphan", lazy="selectin",
    )


class Shot(Base, TimestampMixin):
    __tablename__ = "shots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    storyboard_id: Mapped[int] = mapped_column(Integer, ForeignKey("storyboards.id"), nullable=False)
    shot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    act_name: Mapped[str | None] = mapped_column(String(100))
    time_range: Mapped[str | None] = mapped_column(String(30))
    shot_type: Mapped[str | None] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str | None] = mapped_column(String(50))
    mood: Mapped[str | None] = mapped_column(String(50))

    # Image generation
    image_prompt: Mapped[str | None] = mapped_column(Text)
    image_path: Mapped[str | None] = mapped_column(String(500))
    image_status: Mapped[str] = mapped_column(String(20), default="pending")
    image_task_id: Mapped[str | None] = mapped_column(String(100))

    # Video generation
    video_prompt: Mapped[str | None] = mapped_column(Text)
    video_path: Mapped[str | None] = mapped_column(String(500))
    video_status: Mapped[str] = mapped_column(String(20), default="pending")
    video_task_id: Mapped[str | None] = mapped_column(String(100))
    video_duration: Mapped[float] = mapped_column(Float, default=3.0)
    video_provider: Mapped[str | None] = mapped_column(String(30))
    video_model: Mapped[str | None] = mapped_column(String(50))

    storyboard: Mapped["Storyboard"] = relationship(back_populates="shots")
