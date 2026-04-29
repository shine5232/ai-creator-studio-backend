from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, TimestampMixin


class Character(Base, TimestampMixin):
    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    role_type: Mapped[str | None] = mapped_column(String(30))
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(10))
    nationality: Mapped[str | None] = mapped_column(String(50))
    skin_tone: Mapped[str | None] = mapped_column(String(50))
    ethnic_features: Mapped[str | None] = mapped_column(Text)
    appearance: Mapped[str | None] = mapped_column(Text)
    personality: Mapped[str | None] = mapped_column(Text)
    clothing: Mapped[str | None] = mapped_column(Text)
    symbol_meaning: Mapped[str | None] = mapped_column(String(200))

    reference_image_path: Mapped[str | None] = mapped_column(String(500))
    reference_prompt_cn: Mapped[str | None] = mapped_column(Text)
    reference_prompt_en: Mapped[str | None] = mapped_column(Text)
    detailed_description: Mapped[str | None] = mapped_column(Text)

    project: Mapped["Project"] = relationship(back_populates="characters")  # noqa: F821
    periods: Mapped[list["CharacterPeriod"]] = relationship(
        back_populates="character", order_by="CharacterPeriod.sort_order",
        cascade="all, delete-orphan", lazy="selectin",
    )
    reference_images: Mapped[list["CharacterReferenceImage"]] = relationship(
        back_populates="character", cascade="all, delete-orphan", lazy="selectin",
    )


class CharacterReferenceImage(Base, TimestampMixin):
    __tablename__ = "character_reference_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("characters.id", ondelete="CASCADE"), nullable=False,
    )
    angle: Mapped[str] = mapped_column(String(20), nullable=False)  # "front"|"left"|"right"|"back"
    image_path: Mapped[str | None] = mapped_column(String(500))
    prompt_cn: Mapped[str | None] = mapped_column(Text)
    prompt_en: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|completed|failed

    character: Mapped["Character"] = relationship(back_populates="reference_images")


class CharacterPeriod(Base):
    __tablename__ = "character_periods"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    character_id: Mapped[int] = mapped_column(Integer, ForeignKey("characters.id"), nullable=False)
    period_name: Mapped[str] = mapped_column(String(50), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer)
    appearance_delta: Mapped[str | None] = mapped_column(Text)
    clothing_delta: Mapped[str | None] = mapped_column(Text)
    expression: Mapped[str | None] = mapped_column(String(100))
    tone: Mapped[str | None] = mapped_column(String(50))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str | None] = mapped_column(String(50))

    character: Mapped["Character"] = relationship(back_populates="periods")
