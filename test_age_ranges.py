"""
Test age range conversion
"""

import sys
sys.path.insert(0, '.')

from proj.privacy_engine import PrivacyEngine, PrivacyConfig, age_to_range
import json

print("=" * 70)
print("TESTING AGE RANGE CONVERSION")
print("=" * 70)

# Test the age_to_range function directly
print("\nDirect Age Range Tests:")
print("-" * 70)
test_ages = [1, 18, 20, 25, 27, 33, 45, 53, 58, 67, 75]
for age in test_ages:
    range_result = age_to_range(age)
    print(f"Age {age:2d} -> {range_result}")

# Test with actual data
print("\n\nTesting with Database Structure:")
print("-" * 70)

engine = PrivacyEngine(PrivacyConfig(epsilon=1.0))

# Test record 1: Age 53
record1 = {
    "Age": "53",
    "RecordID": "1",
    "State": "Telangana",
    "District": "Hyderabad",
    "Gender": "Female",
    "MonthlyIncome": "73976",
    "HouseholdSize": "7"
}

print("\nRecord 1 - Original:")
print(json.dumps(record1, indent=2))

privatized1 = engine._anonymize_nested_json(record1, engine.config)

print("\nRecord 1 - Privatized:")
print(json.dumps(privatized1, indent=2))

# Test record 2: Age 26
record2 = {
    "Age": "26",
    "RecordID": "2",
    "State": "Delhi",
    "District": "District 1",
    "Gender": "Male"
}

print("\n\nRecord 2 - Original:")
print(json.dumps(record2, indent=2))

privatized2 = engine._anonymize_nested_json(record2, engine.config)

print("\nRecord 2 - Privatized:")
print(json.dumps(privatized2, indent=2))

print("\n" + "=" * 70)
print("VERIFICATION:")
print("=" * 70)

# Check Age field
age1 = privatized1.get("Age")
age2 = privatized2.get("Age")

print(f"\nAge 53 converted to: {age1}")
print(f"Expected format: '51-55' or similar range")
print(f"Is range format? {'-' in str(age1)}")

print(f"\nAge 26 converted to: {age2}")
print(f"Expected format: '26-30' or similar range")
print(f"Is range format? {'-' in str(age2)}")

# Check RecordID suppression
print(f"\nRecordID suppression: {privatized1.get('RecordID')}")
print(f"Expected: [SUPPRESSED]")
print(f"Correct? {privatized1.get('RecordID') == '[SUPPRESSED]'}")

# Check State generalization
print(f"\nState generalization: {privatized1.get('State')}")
print(f"Expected: [REGION]")
print(f"Correct? {privatized1.get('State') == '[REGION]'}")

print("\n" + "=" * 70)
