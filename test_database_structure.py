"""
Test with actual database structure
"""

import sys
sys.path.insert(0, '.')

from proj.privacy_engine import PrivacyEngine, PrivacyConfig
import json

# Initialize engine
engine = PrivacyEngine(PrivacyConfig(epsilon=1.0))

print("=" * 80)
print("TESTING WITH ACTUAL DATABASE STRUCTURE")
print("=" * 80)

# Simulate the actual data structure from your database
original_record = {
    "Age": "53",
    "State": "Telangana",
    "Gender": "Female",
    "AreaType": "Rural",
    "District": "Hyderabad",
    "Industry": "Transport",
    "RecordID": "1",
    "Education": "Higher Secondary",
    "Disability": "Yes",
    "Occupation": "Construction Worker",
    "HouseholdSize": "7",
    "MaritalStatus": "Widowed",
    "MonthlyIncome": "73976",
    "ChronicIllness": "Yes",
    "EmploymentType": "Permanent",
    "LandOwnedAcres": "4.3",
    "MigrationStatus": "Non-Migrant"
}

print("\n📥 ORIGINAL DATA (from database):")
print(json.dumps(original_record, indent=2))

# Apply privacy transformation
privatized_record = engine._anonymize_nested_json(original_record, engine.config)

print("\n🔒 PRIVATIZED DATA:")
print(json.dumps(privatized_record, indent=2))

print("\n" + "=" * 80)
print("VERIFICATION:")
print("=" * 80)

# Verify key transformations
checks = [
    ("RecordID", privatized_record.get("RecordID") == "[SUPPRESSED]", "Should be [SUPPRESSED]"),
    ("State", privatized_record.get("State") == "[REGION]", "Should be [REGION]"),
    ("District", privatized_record.get("District") == "Hyderabad", "Should be preserved"),
    ("Gender", privatized_record.get("Gender") == "Female", "Should be preserved"),
    ("Age", privatized_record.get("Age") != "53", "Should have DP noise (different from 53)"),
    ("MonthlyIncome", privatized_record.get("MonthlyIncome") != "73976", "Should have DP noise"),
]

for field, passed, description in checks:
    status = "✅ PASS" if passed else "❌ FAIL"
    value = privatized_record.get(field)
    print(f"{status} - {field}: {value} ({description})")

print("\n" + "=" * 80)
