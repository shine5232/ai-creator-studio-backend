from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Project(Base, TimestampMixin):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    source_url: Mapped[str | None] = mapped_column(String(500))
    source_platform: Mapped[str | None] = mapped_column(String(30))
    reference_case_id: Mapped[int | None] = mapped_column(Integer)
    output_duration: Mapped[int | None] = mapped_column(Integer)
    output_video_path: Mapped[str | None] = mapped_column(String(500))
    settings: Mapped[str | None] = mapped_column(Text)

    user: Mapped["User"] = relationship(back_populates="projects")  # noqa: F821
    workflow_steps: Mapped[list["WorkflowStep"]] = relationship(
        back_populates="project", order_by="WorkflowStep.step_order",
        cascade="all, delete-orphan", lazy="selectin",
    )
    scripts: Mapped[list["Script"]] = relationship(back_populates="project", cascade="all, delete-orphan", lazy="selectin")  # noqa: F821
    characters: Mapped[list["Character"]] = relationship(back_populates="project", cascade="all, delete-orphan", lazy="selectin")  # noqa: F821
    assets: Mapped[list["Asset"]] = relationship(back_populates="project", cascade="all, delete-orphan", lazy="selectin")  # noqa: F821
    publish_records: Mapped[list["PublishRecord"]] = relationship(back_populates="project", cascade="all, delete-orphan", lazy="selectin")  # noqa: F821


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    step_name: Mapped[str] = mapped_column(String(50), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    celery_task_id: Mapped[str | None] = mapped_column(String(100))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime)
    created_at: Mapped[DateTime | None] = mapped_column(DateTime)

    project: Mapped["Project"] = relationship(back_populates="workflow_steps")
