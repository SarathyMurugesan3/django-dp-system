import csv
import os
import re
from django.core.management.base import BaseCommand
from django.db import connection


def sanitize_column(name):
    name = name.strip()
    name = re.sub(r'\W+', '_', name)  # replace spaces & symbols
    return name.lower()


class Command(BaseCommand):
    help = "Upload CSV & CREATE PostgreSQL table dynamically (safe column names)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)
        parser.add_argument("--table", type=str, default=None)
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        table_name = options["table"]
        clear_data = options["clear"]

        if not os.path.exists(csv_file):
            self.stdout.write("❌ File not found")
            return

        if not table_name:
            base = os.path.basename(csv_file).replace(".csv", "")
            table_name = f"dataset_{base}"

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            raw_columns = reader.fieldnames

            if not raw_columns:
                self.stdout.write("❌ No columns found")
                return

            # Map original → SQL safe
            col_map = {col: sanitize_column(col) for col in raw_columns}
            sql_columns = ", ".join([f'"{col_map[col]}" TEXT' for col in raw_columns])

            with connection.cursor() as cursor:
                if clear_data:
                    cursor.execute(f'DROP TABLE IF EXISTS "{table_name}"')

                # Create table
                cursor.execute(f'''
                    CREATE TABLE IF NOT EXISTS "{table_name}" (
                        id SERIAL PRIMARY KEY,
                        {sql_columns}
                    )
                ''')

                created = 0

                for row in reader:
                    cols = [f'"{col_map[c]}"' for c in raw_columns]
                    values = [row[c] for c in raw_columns]

                    placeholders = ", ".join(["%s"] * len(values))
                    col_sql = ", ".join(cols)

                    cursor.execute(
                        f'INSERT INTO "{table_name}" ({col_sql}) VALUES ({placeholders})',
                        values
                    )

                    created += 1

        self.stdout.write("\n✅ Import completed")
        self.stdout.write(f"Table created: {table_name}")
        self.stdout.write(f"Rows inserted: {created}")
        self.stdout.write("Column mapping:")
        for original, safe in col_map.items():
            self.stdout.write(f"  {original} → {safe}")
