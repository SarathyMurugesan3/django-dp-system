"""
Simple test without unicode characters
"""

import sys
sys.path.insert(0, '.')

from proj.privacy_engine import PrivacyEngine, PrivacyConfig
import json

# Initialize engine
engine = PrivacyEngine(PrivacyConfig(epsilon=1.0))

print("TESTING WITH ACTUAL DATABASE STRUCTURE")
print("=" * 60)

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

print("\nORIGINAL DATA (from database):")
print(json.dumps(original_record, indent=2))

# Apply privacy transformation
privatized_record = engine._anonymize_nested_json(original_record, engine.config)

print("\nPRIVATIZED DATA:")
print(json.dumps(privatized_record, indent=2))

print("\n" + "=" * 60)
print("VERIFICATION:")
print("=" * 60)

# Verify key transformations
print(f"RecordID: {privatized_record.get('RecordID')} (should be [SUPPRESSED])")
print(f"State: {privatized_record.get('State')} (should be [REGION])")
print(f"District: {privatized_record.get('District')} (should be Hyderabad)")
print(f"Gender: {privatized_record.get('Gender')} (should be Female)")
print(f"Age: {privatized_record.get('Age')} (should have DP noise, not 53)")
print(f"MonthlyIncome: {privatized_record.get('MonthlyIncome')} (should have DP noise, not 73976)")
print(f"HouseholdSize: {privatized_record.get('HouseholdSize')} (should have DP noise, not 7)")
print(f"LandOwnedAcres: {privatized_record.get('LandOwnedAcres')} (should have DP noise, not 4.3)")

# Check if RecordID is properly suppressed
if privatized_record.get('RecordID') == '[SUPPRESSED]':
    print("\nSUCCESS: RecordID is properly suppressed!")
else:
    print(f"\nERROR: RecordID should be [SUPPRESSED] but got {privatized_record.get('RecordID')}")

if privatized_record.get('State') == '[REGION]':
    print("SUCCESS: State is properly generalized!")
else:
    print(f"ERROR: State should be [REGION] but got {privatized_record.get('State')}")
