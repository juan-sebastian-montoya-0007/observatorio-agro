from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    publisher: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(200), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    official_url: Mapped[str | None] = mapped_column(String(500))
    reuse_terms: Mapped[str | None] = mapped_column(Text)

    versions: Mapped[list[SourceVersion]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class SourceVersion(Base):
    __tablename__ = "source_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"))
    version_label: Mapped[str] = mapped_column(String(100))
    coverage_start_year: Mapped[int] = mapped_column(Integer)
    coverage_end_year: Mapped[int] = mapped_column(Integer)
    available_date: Mapped[date | None] = mapped_column(Date)
    sha256: Mapped[str] = mapped_column(String(64), unique=True)
    file_name: Mapped[str] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), default="STAGED", server_default="STAGED")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    source: Mapped[Source] = relationship(back_populates="versions")
    import_runs: Mapped[list[ImportRun]] = relationship(
        back_populates="source_version", cascade="all, delete-orphan"
    )


class ImportRun(Base):
    __tablename__ = "import_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_version_id: Mapped[int] = mapped_column(
        ForeignKey("source_versions.id", ondelete="CASCADE"), index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="RUNNING", server_default="RUNNING")
    rows_read: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rows_inserted: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    rows_rejected: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, server_default="{}")
    importer_version: Mapped[str] = mapped_column(String(100))

    source_version: Mapped[SourceVersion] = relationship(back_populates="import_runs")
    issues: Mapped[list[ImportIssue]] = relationship(
        back_populates="import_run", cascade="all, delete-orphan"
    )


class ImportIssue(Base):
    __tablename__ = "import_issues"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_run_id: Mapped[int] = mapped_column(
        ForeignKey("import_runs.id", ondelete="CASCADE"), index=True
    )
    severity: Mapped[str] = mapped_column(String(20))
    sheet: Mapped[str | None] = mapped_column(String(100))
    row: Mapped[int | None] = mapped_column(Integer)
    field: Mapped[str | None] = mapped_column(String(200))
    code: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)

    import_run: Mapped[ImportRun] = relationship(back_populates="issues")
