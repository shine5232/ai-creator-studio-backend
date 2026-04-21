from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base, TimestampMixin


class KBCase(Base, TimestampMixin):
    __tablename__ = "kb_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_video_path: Mapped[str | None] = mapped_column(String(500))
    view_count: Mapped[int | None] = mapped_column(Integer)
    like_count: Mapped[int | None] = mapped_column(Integer)
    like_rate: Mapped[float | None] = mapped_column(Float)
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    uploader: Mapped[str | None] = mapped_column(String(100))
    upload_date: Mapped[str | None] = mapped_column(String)

    theme: Mapped[str | None] = mapped_column(String(100))
    narrative_type: Mapped[str | None] = mapped_column(String(50))
    narrative_structure: Mapped[str | None] = mapped_column(Text)
    story_summary: Mapped[str | None] = mapped_column(Text)
    emotion_curve: Mapped[str | None] = mapped_column(Text)
    emotion_triggers: Mapped[str | None] = mapped_column(Text)
    visual_style: Mapped[str | None] = mapped_column(Text)
    visual_contrast: Mapped[str | None] = mapped_column(Text)

    viral_elements: Mapped[str | None] = mapped_column(Text)
    visual_symbols: Mapped[str | None] = mapped_column(Text)
    audience_profile: Mapped[str | None] = mapped_column(Text)
    reusable_elements: Mapped[str | None] = mapped_column(Text)
    success_factors: Mapped[str | None] = mapped_column(Text)
    title_formula: Mapped[str | None] = mapped_column(String(200))

    characters_ethnicity: Mapped[str | None] = mapped_column(Text)
    analysis_report_path: Mapped[str | None] = mapped_column(String(500))
    frames_dir: Mapped[str | None] = mapped_column(String(500))
    analysis_status: Mapped[str | None] = mapped_column(String(20), default="pending")
    analysis_progress: Mapped[int | None] = mapped_column(Integer, default=0)
    celery_task_id: Mapped[str | None] = mapped_column(String(100))


class KBElement(Base, TimestampMixin):
    __tablename__ = "kb_elements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    element_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    impact_score: Mapped[float | None] = mapped_column(Float)
    examples: Mapped[str | None] = mapped_column(Text)


class KBFramework(Base, TimestampMixin):
    __tablename__ = "kb_frameworks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    framework_type: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    impact_data: Mapped[str | None] = mapped_column(Text)
    examples: Mapped[str | None] = mapped_column(Text)


class KBScriptTemplate(Base, TimestampMixin):
    __tablename__ = "kb_script_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    theme: Mapped[str | None] = mapped_column(String(100))
    narrative_type: Mapped[str | None] = mapped_column(String(50))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    template_content: Mapped[str] = mapped_column(Text, nullable=False)
    reference_case_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("kb_cases.id"))
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
