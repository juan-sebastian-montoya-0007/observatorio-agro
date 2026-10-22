from sqlalchemy import inspect, text

EXPECTED_TABLES = {
    "agricultural_records",
    "crop_groups",
    "crop_subgroups",
    "crop_variants",
    "crops",
    "departments",
    "import_issues",
    "import_runs",
    "municipalities",
    "periods",
    "physical_states",
    "source_versions",
    "sources",
    "territorial_geometries",
}


def test_initial_migration_creates_postgis_and_all_tables(migrated_connection):
    assert migrated_connection.scalar(text("SELECT postgis_version()"))
    assert EXPECTED_TABLES <= set(inspect(migrated_connection).get_table_names())


def test_initial_migration_uses_required_storage_types(migrated_connection):
    inspector = inspect(migrated_connection)

    department_columns = {
        column["name"]: column for column in inspector.get_columns("departments")
    }
    municipality_columns = {
        column["name"]: column for column in inspector.get_columns("municipalities")
    }
    fact_columns = {
        column["name"]: column for column in inspector.get_columns("agricultural_records")
    }

    assert department_columns["code"]["type"].length == 2
    assert municipality_columns["code"]["type"].length == 5
    for metric in (
        "planted_area_ha",
        "harvested_area_ha",
        "production_t",
        "reported_yield_t_ha",
    ):
        assert fact_columns[metric]["type"].precision == 18
        assert fact_columns[metric]["type"].scale == 4

    geometry_type = migrated_connection.scalar(
        text(
            "SELECT format_type(a.atttypid, a.atttypmod) "
            "FROM pg_attribute a "
            "JOIN pg_class c ON c.oid = a.attrelid "
            "WHERE c.relname = 'territorial_geometries' AND a.attname = 'geometry'"
        )
    )
    assert geometry_type == "geometry(MultiPolygon,4326)"
