"""
Test Privacy Engine with Complete Requirements
"""

import sys
sys.path.insert(0, '.')

from proj.privacy_engine import PrivacyEngine, PrivacyConfig
import json

# Initialize engine
engine = PrivacyEngine(PrivacyConfig(epsilon=1.0))

print("=" * 80)
print("COMPREHENSIVE PRIVACY ENGINE TEST")
print("=" * 80)

# Test with your exact example
original_data = {
    "id": "101",
    "recordid": "1335",
    "agegroup": "28",
    "gender": "Male",
    "state": "tamilnadu",
    "district": "salem",
    "areatype": "Urban",
    "education": "Secondary",
    "occupation": "Office Worker",
    "industry": "Services",
    "monthlyincomerange": "20000",
    "householdsizerange": "4",
    "maritalstatus": "Unmarried",
    "disability": "No",
    "chronicillness": "No",
    "migrationstatus": "Non-Migrant",
    "employmenttype": "Contract",
    "landownedrange": "0.7"
}

print("\nORIGINAL DATA:")
print(json.dumps(original_data, indent=2))

# Apply privacy transformation
privatized_data = engine._anonymize_nested_json(original_data, engine.config)

print("\nPRIVATIZED DATA:")
print(json.dumps(privatized_data, indent=2))

print("\n" + "=" * 80)
print("VERIFICATION CHECKS:")
print("=" * 80)

# Verify each transformation
checks = [
    ("id", privatized_data.get("id"), "[SUPPRESSED]", "Should be [SUPPRESSED]"),
    ("recordid", privatized_data.get("recordid"), "[SUPPRESSED]", "Should be [SUPPRESSED]"),
    ("agegroup", privatized_data.get("agegroup"), "26-35", "Should be age range like 26-35"),
    ("gender", privatized_data.get("gender"), "Male", "Should be preserved"),
    ("state", privatized_data.get("state"), "[REGION]", "Should be [REGION]"),
    ("district", privatized_data.get("district"), "District", "Should start with 'District'"),
    ("areatype", privatized_data.get("areatype"), "Urban", "Should be preserved"),
    ("education", privatized_data.get("education"), "Secondary", "Should be preserved"),
    ("monthlyincomerange", privatized_data.get("monthlyincomerange"), "18000-25000", "Should be income range"),
    ("householdsizerange", privatized_data.get("householdsizerange"), "3-5", "Should be household range"),
    ("landownedrange", privatized_data.get("landownedrange"), "0.5-1.0", "Should be land range"),
]

for field, actual, expected, description in checks:
    if isinstance(expected, str) and expected == "District":
        # Special check for district
        passed = actual.startswith("District")
    else:
        passed = actual == expected
    
    status = "PASS" if passed else "FAIL"
    print(f"{status:4s} | {field:20s} | {str(actual):20s} | {description}")

# Test Aadhaar and PAN masking
print("\n" + "=" * 80)
print("AADHAAR AND PAN MASKING TESTS:")
print("=" * 80)

test_aadhaar = {
    "aadhaar": "4821 7394 1056",
    "name": "Test User"
}

privatized_aadhaar = engine._anonymize_nested_json(test_aadhaar, engine.config)
print(f"\nAadhaar: {test_aadhaar['aadhaar']} -> {privatized_aadhaar['aadhaar']}")
print(f"Expected: XXXX XXXX 1056")
print(f"Match: {privatized_aadhaar['aadhaar'] == 'XXXX XXXX 1056'}")

test_pan = {
    "pan": "ABCDE1234F",
    "name": "Test User"
}

privatized_pan = engine._anonymize_nested_json(test_pan, engine.config)
print(f"\nPAN: {test_pan['pan']} -> {privatized_pan['pan']}")
print(f"Expected: ABCDE****F")
print(f"Match: {privatized_pan['pan'] == 'ABCDE****F'}")

print("\n" + "=" * 80)
print("ALL TESTS COMPLETED!")
print("=" * 80)
