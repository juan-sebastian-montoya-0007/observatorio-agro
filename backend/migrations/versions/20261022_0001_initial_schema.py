"""Create the initial EVA Explorer relational schema.

Revision ID: 20261022_0001
Revises:
Create Date: 2026-10-22
"""

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261022_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    period_type = postgresql.ENUM(
        "ANNUAL",
        "SEMESTER_A",
        "SEMESTER_B",
        name="period_type",
    )
    period_type.create(op.get_bind(), checkfirst=True)
    period_type_column = postgresql.ENUM(
        "ANNUAL",
        "SEMESTER_A",
        "SEMESTER_B",
        name="period_type",
        create_type=False,
    )

    op.create_table(
        "sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("publisher", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("official_url", sa.String(length=500), nullable=True),
        sa.Column("reuse_terms", sa.Text(), nullable=True),
        sa.UniqueConstraint("name", name="uq_sources_name"),
    )
    op.create_table(
        "source_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), nullable=False),
        sa.Column("version_label", sa.String(length=100), nullable=False),
        sa.Column("coverage_start_year", sa.Integer(), nullable=False),
        sa.Column("coverage_end_year", sa.Integer(), nullable=False),
        sa.Column("available_date", sa.Date(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="STAGED", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"], name="fk_source_versions_source_id_sources"
        ),
        sa.UniqueConstraint("sha256", name="uq_source_versions_sha256"),
    )
    op.create_table(
        "import_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_version_id", sa.Integer(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="RUNNING", nullable=False),
        sa.Column("rows_read", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_inserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rows_rejected", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary", sa.JSON(), server_default=sa.text("'{}'::json"), nullable=False),
        sa.Column("importer_version", sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["source_versions.id"],
            name="fk_import_runs_source_version_id_source_versions",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_import_runs_source_version_id", "import_runs", ["source_version_id"])
    op.create_table(
        "import_issues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("import_run_id", sa.Integer(), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("sheet", sa.String(length=100), nullable=True),
        sa.Column("row", sa.Integer(), nullable=True),
        sa.Column("field", sa.String(length=200), nullable=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["import_run_id"],
            ["import_runs.id"],
            name="fk_import_issues_import_run_id_import_runs",
            ondelete="CASCADE",
        ),
    )
    op.create_index("ix_import_issues_import_run_id", "import_issues", ["import_run_id"])

    op.create_table(
        "departments",
        sa.Column("code", sa.String(length=2), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )
    op.create_table(
        "municipalities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=5), nullable=False),
        sa.Column("department_code", sa.String(length=2), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.ForeignKeyConstraint(
            ["department_code"],
            ["departments.code"],
            name="fk_municipalities_department_code_departments",
        ),
        sa.UniqueConstraint("code", name="uq_municipalities_code"),
    )
    op.create_index("ix_municipalities_department_code", "municipalities", ["department_code"])
    op.create_table(
        "territorial_geometries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("territorial_level", sa.String(length=20), nullable=False),
        sa.Column("divipola_code", sa.String(length=5), nullable=False),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry(
                geometry_type="MULTIPOLYGON",
                srid=4326,
                spatial_index=False,
            ),
            nullable=False,
        ),
        sa.Column("srid", sa.Integer(), server_default="4326", nullable=False),
        sa.Column("version", sa.String(length=100), nullable=False),
        sa.Column("is_simplified", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("license", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "territorial_level IN ('DEPARTMENT', 'MUNICIPALITY')",
            name="ck_territorial_geometries_level",
        ),
        sa.UniqueConstraint(
            "territorial_level",
            "divipola_code",
            "version",
            "is_simplified",
            name="uq_territorial_geometries_identity",
        ),
    )
    op.create_index(
        "ix_territorial_geometries_divipola_code",
        "territorial_geometries",
        ["divipola_code"],
    )
    op.create_index(
        "ix_territorial_geometries_geometry",
        "territorial_geometries",
        ["geometry"],
        postgresql_using="gist",
    )

    op.create_table(
        "crop_groups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.UniqueConstraint("name", name="uq_crop_groups_name"),
    )
    op.create_table(
        "crop_subgroups",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["crop_groups.id"],
            name="fk_crop_subgroups_group_id_crop_groups",
        ),
        sa.UniqueConstraint("group_id", "name", name="uq_crop_subgroups_group_id_name"),
    )
    op.create_table(
        "crops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("base_code", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("cycle", sa.String(length=100), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("subgroup_id", sa.Integer(), nullable=False),
        sa.Column("general_classification", sa.String(length=150), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"], ["crop_groups.id"], name="fk_crops_group_id_crop_groups"
        ),
        sa.ForeignKeyConstraint(
            ["subgroup_id"],
            ["crop_subgroups.id"],
            name="fk_crops_subgroup_id_crop_subgroups",
        ),
        sa.UniqueConstraint("base_code", name="uq_crops_base_code"),
    )
    op.create_table(
        "crop_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("crop_id", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.String(length=30), nullable=False),
        sa.Column("disaggregation", sa.String(length=250), nullable=False),
        sa.Column("scientific_name", sa.String(length=250), server_default="", nullable=False),
        sa.ForeignKeyConstraint(
            ["crop_id"], ["crops.id"], name="fk_crop_variants_crop_id_crops"
        ),
        sa.UniqueConstraint(
            "crop_id",
            "source_code",
            "disaggregation",
            "scientific_name",
            name="uq_crop_variants_identity",
        ),
    )
    op.create_table(
        "physical_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.UniqueConstraint("name", name="uq_physical_states_name"),
    )
    op.create_table(
        "periods",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("period_type", period_type_column, nullable=False),
        sa.Column("original_label", sa.String(length=20), nullable=False),
        sa.Column("chronological_order", sa.Integer(), nullable=False),
        sa.UniqueConstraint("year", "period_type", name="uq_periods_year_period_type"),
    )
    op.create_index("ix_periods_chronological_order", "periods", ["chronological_order"])

    op.create_table(
        "agricultural_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_version_id", sa.Integer(), nullable=False),
        sa.Column("municipality_id", sa.Integer(), nullable=False),
        sa.Column("crop_variant_id", sa.Integer(), nullable=False),
        sa.Column("period_id", sa.Integer(), nullable=False),
        sa.Column("physical_state_id", sa.Integer(), nullable=False),
        sa.Column("planted_area_ha", sa.Numeric(18, 4), nullable=False),
        sa.Column("harvested_area_ha", sa.Numeric(18, 4), nullable=False),
        sa.Column("production_t", sa.Numeric(18, 4), nullable=False),
        sa.Column("reported_yield_t_ha", sa.Numeric(18, 4), nullable=True),
        sa.Column("source_row", sa.Integer(), nullable=False),
        sa.Column(
            "trace_metadata",
            sa.JSON(),
            server_default=sa.text("'{}'::json"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["source_version_id"],
            ["source_versions.id"],
            name="fk_agricultural_records_source_version_id_source_versions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["municipality_id"],
            ["municipalities.id"],
            name="fk_agricultural_records_municipality_id_municipalities",
        ),
        sa.ForeignKeyConstraint(
            ["crop_variant_id"],
            ["crop_variants.id"],
            name="fk_agricultural_records_crop_variant_id_crop_variants",
        ),
        sa.ForeignKeyConstraint(
            ["period_id"],
            ["periods.id"],
            name="fk_agricultural_records_period_id_periods",
        ),
        sa.ForeignKeyConstraint(
            ["physical_state_id"],
            ["physical_states.id"],
            name="fk_agricultural_records_physical_state_id_physical_states",
        ),
        sa.UniqueConstraint(
            "source_version_id",
            "municipality_id",
            "crop_variant_id",
            "period_id",
            "physical_state_id",
            name="uq_agricultural_record_fact_key",
        ),
    )
    op.create_index(
        "ix_agricultural_records_version_period_territory_crop",
        "agricultural_records",
        ["source_version_id", "period_id", "municipality_id", "crop_variant_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agricultural_records_version_period_territory_crop",
        table_name="agricultural_records",
    )
    op.drop_table("agricultural_records")
    op.drop_index("ix_periods_chronological_order", table_name="periods")
    op.drop_table("periods")
    op.drop_table("physical_states")
    op.drop_table("crop_variants")
    op.drop_table("crops")
    op.drop_table("crop_subgroups")
    op.drop_table("crop_groups")
    op.drop_index("ix_territorial_geometries_geometry", table_name="territorial_geometries")
    op.drop_index("ix_territorial_geometries_divipola_code", table_name="territorial_geometries")
    op.drop_table("territorial_geometries")
    op.drop_index("ix_municipalities_department_code", table_name="municipalities")
    op.drop_table("municipalities")
    op.drop_table("departments")
    op.drop_index("ix_import_issues_import_run_id", table_name="import_issues")
    op.drop_table("import_issues")
    op.drop_index("ix_import_runs_source_version_id", table_name="import_runs")
    op.drop_table("import_runs")
    op.drop_table("source_versions")
    op.drop_table("sources")
    postgresql.ENUM(name="period_type").drop(op.get_bind(), checkfirst=True)
