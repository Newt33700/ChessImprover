"""Tests unitaires — nettoyage pur des migrations SQL (migration CockroachDB).

Aucune I/O ici : `strip_unsupported_statements`/`split_statements` opèrent
sur du texte SQL en mémoire, sans connexion Postgres réelle.
"""

from __future__ import annotations

from scripts.apply_migrations import (
    split_statements,
    strip_unsupported_statements,
)


class TestStripUnsupportedStatements:
    def test_removes_enable_row_level_security(self):
        sql = "ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;\n"
        assert strip_unsupported_statements(sql).strip() == ""

    def test_removes_single_line_create_policy(self):
        sql = (
            "CREATE POLICY profiles_own_row ON profiles\n"
            "FOR ALL\n"
            "USING (id = auth.uid()::UUID);\n"
        )
        assert strip_unsupported_statements(sql).strip() == ""

    def test_removes_multiple_policies_on_same_table(self):
        sql = (
            "CREATE POLICY tactical_sprints_read_all ON tactical_sprints\n"
            "FOR SELECT\n"
            "USING (true);\n\n"
            "CREATE POLICY tactical_sprints_insert_own ON tactical_sprints\n"
            "FOR INSERT\n"
            "WITH CHECK (user_id = auth.uid()::UUID);\n"
        )
        assert strip_unsupported_statements(sql).strip() == ""

    def test_removes_trigger_function_and_trigger(self):
        sql = (
            "CREATE OR REPLACE FUNCTION set_updated_at()\n"
            "RETURNS TRIGGER AS $$\n"
            "BEGIN\n"
            "  NEW.updated_at = now();\n"
            "  RETURN NEW;\n"
            "END;\n"
            "$$ LANGUAGE plpgsql;\n\n"
            "DROP TRIGGER IF EXISTS trg_user_data_updated_at ON user_data;\n"
            "CREATE TRIGGER trg_user_data_updated_at\n"
            "BEFORE UPDATE ON user_data\n"
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at();\n"
        )
        assert strip_unsupported_statements(sql).strip() == ""

    def test_keeps_create_table_and_index_statements(self):
        sql = (
            "CREATE TABLE IF NOT EXISTS profiles (\n"
            "    id UUID PRIMARY KEY DEFAULT gen_random_uuid()\n"
            ");\n\n"
            "CREATE INDEX IF NOT EXISTS idx_profiles_id ON profiles (id);\n"
        )
        result = strip_unsupported_statements(sql)
        assert "CREATE TABLE IF NOT EXISTS profiles" in result
        assert "CREATE INDEX IF NOT EXISTS idx_profiles_id" in result

    def test_full_init_auth_migration_yields_only_table_and_index_ddl(self):
        sql = (
            "CREATE TABLE IF NOT EXISTS profiles (\n"
            "    id UUID PRIMARY KEY DEFAULT gen_random_uuid()\n"
            ");\n\n"
            "ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;\n\n"
            "CREATE POLICY profiles_own_row ON profiles\n"
            "FOR ALL\n"
            "USING (id = auth.uid()::UUID);\n\n"
            "CREATE OR REPLACE FUNCTION set_updated_at()\n"
            "RETURNS TRIGGER AS $$\n"
            "BEGIN\n"
            "  NEW.updated_at = now();\n"
            "  RETURN NEW;\n"
            "END;\n"
            "$$ LANGUAGE plpgsql;\n\n"
            "CREATE TRIGGER trg_user_data_updated_at\n"
            "BEFORE UPDATE ON user_data\n"
            "FOR EACH ROW EXECUTE FUNCTION set_updated_at();\n"
        )
        statements = split_statements(strip_unsupported_statements(sql))
        assert len(statements) == 1
        assert statements[0].startswith("CREATE TABLE IF NOT EXISTS profiles")
        assert "auth.uid()" not in statements[0]


class TestSplitStatements:
    def test_splits_on_semicolon(self):
        sql = "CREATE TABLE a (id INT);\nCREATE TABLE b (id INT);"
        assert split_statements(sql) == [
            "CREATE TABLE a (id INT)",
            "CREATE TABLE b (id INT)",
        ]

    def test_ignores_comment_only_fragments(self):
        sql = "-- juste un commentaire\n\nCREATE TABLE a (id INT);"
        assert split_statements(sql) == ["CREATE TABLE a (id INT)"]

    def test_empty_sql_yields_no_statements(self):
        assert split_statements("   \n  ") == []
