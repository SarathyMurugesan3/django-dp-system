# Generated manually to fix production database schema mismatch

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('proj', '0004_team_teammembership'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE privacy_budget_transactions DROP COLUMN IF EXISTS noise_deterministic;",
            reverse_sql="ALTER TABLE privacy_budget_transactions ADD COLUMN noise_deterministic TEXT;",
        ),
    ]
