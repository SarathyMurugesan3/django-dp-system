import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proj.settings")
django.setup()

from proj.privacy_engine import PrivacyEngine, PrivacyConfig
from proj.column_classifier import ColumnClassifier
from proj.risk_engine import RiskAssessmentEngine

records = [
    {
        "id": "6b86b273ff34fce19d6b804eff5a3f57",
        "record_id": "83e4bc3dd87449370da9aadf01169b5a",
        "primary_income_source": "Remittance",
        "secondary_income_source": "Daily Labour",
        "annual_household_income": 0,
        "monthly_household_income": 117912.6,
        "primary_expenditure_category": "Housing Rent",
        "monthly_total_expenditure": 122949,
        "food_expenditure_monthly": 122143,
        "education_expenditure_monthly": 25868,
        "healthcare_expenditure_monthly": 67385,
        "indebtedness_status": "Loan Defaulter",
        "loan_source": "Government Scheme",
        "loan_purpose": "Education",
        "total_loan_amount": 99488,
        "outstanding_loan_amount": 98861,
        "annual_interest_rate_pct": 181,
        "monthly_emi": 208085,
        "savings_annual": 63091
    }
] * 3

classifier = ColumnClassifier()
classifications = classifier.classify_columns(records)

for col, cl in classifications.items():
    print(f"{col}: {cl['type']}")

print("-" * 20)
pe = PrivacyEngine()
anon, meta = pe.apply_privacy(records, classifications, risk_score=80)
import json
print(json.dumps(anon[0], indent=2))

re = RiskAssessmentEngine()
print("Orig Risk:", re.analyze_dataset(records)['risk_score'])
print("New Risk:", re.analyze_dataset(anon)['risk_score'])
