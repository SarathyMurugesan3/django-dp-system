# Generated manually to fix production database schema mismatch

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proj', '0005_remove_noise_deterministic'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE privacy_budget_transactions DROP COLUMN IF EXISTS noise_seed_window;",
            reverse_sql="ALTER TABLE privacy_budget_transactions ADD COLUMN noise_seed_window TEXT;",
        ),
    ]
