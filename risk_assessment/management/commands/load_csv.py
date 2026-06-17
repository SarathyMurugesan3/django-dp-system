import csv
import os
import re
from django.core.management.base import BaseCommand
from django.db import connection, transaction


def sanitize_column(name):
    name = name.strip()
    name = re.sub(r'\W+', '_', name)  # replace spaces & symbols with underscore
    return name.lower()


class Command(BaseCommand):
    help = "Upload CSV & CREATE MySQL table dynamically (safe column names)"

    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)
        parser.add_argument("--table", type=str, default=None)
        parser.add_argument("--clear", action="store_true")

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        table_name = options["table"]
        clear_data = options["clear"]

        if not os.path.exists(csv_file):
            self.stdout.write("[ERROR] File not found")
            return

        if not table_name:
            base = os.path.basename(csv_file).replace(".csv", "")
            # Sanitize the table name (remove spaces/special chars)
            base = re.sub(r'\W+', '_', base).lower()
            table_name = f"dataset_{base}"

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            raw_columns = reader.fieldnames

            if not raw_columns:
                self.stdout.write("[ERROR] No columns found")
                return

            # Map original column names -> MySQL-safe names (backtick-escaped)
            col_map = {col: sanitize_column(col) for col in raw_columns}
            # Build column definitions using backticks (MySQL syntax)
            sql_columns = ", ".join([f"`{col_map[col]}` TEXT" for col in raw_columns])

            with connection.cursor() as cursor:
                if clear_data:
                    # MySQL-compatible DROP TABLE uses backticks
                    cursor.execute(f"DROP TABLE IF EXISTS `{table_name}`")

                # Create table -- MySQL syntax: INT AUTO_INCREMENT, backtick identifiers
                cursor.execute(f"""
                    CREATE TABLE IF NOT EXISTS `{table_name}` (
                        `id` INT AUTO_INCREMENT PRIMARY KEY,
                        {sql_columns}
                    )
                """)

                # Build INSERT template once
                cols_sql = ", ".join([f"`{col_map[c]}`" for c in raw_columns])
                placeholders = ", ".join(["%s"] * len(raw_columns))
                insert_sql = f"INSERT INTO `{table_name}` ({cols_sql}) VALUES ({placeholders})"

                # Batch insert for speed (2000 rows per round-trip)
                BATCH_SIZE = 2000
                batch = []
                created = 0

                with transaction.atomic():
                    for row in reader:
                        batch.append(tuple(row[c] for c in raw_columns))
                        if len(batch) >= BATCH_SIZE:
                            cursor.executemany(insert_sql, batch)
                            created += len(batch)
                            batch = []
                            self.stdout.write(f"  -> {created} rows inserted...", ending="\r")

                    # Insert any remaining rows
                    if batch:
                        cursor.executemany(insert_sql, batch)
                        created += len(batch)

        self.stdout.write("")
        self.stdout.write("[OK] Import completed")
        self.stdout.write(f"Table created: {table_name}")
        self.stdout.write(f"Rows inserted: {created}")
        self.stdout.write("Column mapping:")
        for original, safe in col_map.items():
            self.stdout.write(f"  {original} -> {safe}")
