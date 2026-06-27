import os
import unittest
from unittest.mock import patch

from services.query_service import build_db_connect_kwargs


class TestBuildDbConnectKwargs(unittest.TestCase):
    def test_adds_sslmode_for_supabase_hosts(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PGHOST": "db.example.supabase.co",
                "PGPORT": "5432",
                "PGDATABASE": "postgres",
                "PGUSER": "postgres",
                "PGPASSWORD": "secret",
            },
            clear=False,
        ):
            kwargs = build_db_connect_kwargs()
            self.assertEqual(kwargs["sslmode"], "require")

    def test_respects_explicit_sslmode_override(self) -> None:
        with patch.dict(
            os.environ,
            {
                "PGHOST": "localhost",
                "PGPORT": "5432",
                "PGDATABASE": "northwind",
                "PGUSER": "postgres",
                "PGPASSWORD": "secret",
                "PGSSLMODE": "disable",
            },
            clear=False,
        ):
            kwargs = build_db_connect_kwargs()
            self.assertEqual(kwargs["sslmode"], "disable")


if __name__ == "__main__":
    unittest.main()
