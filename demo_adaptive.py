"""
Quick Demo: Privacy Engine handles ANY dataset automatically
"""

import sys
sys.path.insert(0, '.')

from proj.privacy_engine import PrivacyEngine, PrivacyConfig
import json

# Initialize engine
engine = PrivacyEngine(PrivacyConfig(epsilon=1.0))

print("=" * 70)
print("PRIVACY ENGINE - ADAPTIVE DATASET HANDLING DEMO")
print("=" * 70)

# Example 1: Dataset with Aadhaar
print("\n✅ Example 1: Dataset WITH Aadhaar number")
print("-" * 70)
data1 = {
    "id": "123",
    "aadhaar": "1234-5678-9012",
    "name": "John Doe",
    "age": 35,
    "state": "Maharashtra",
    "district": "District 1"
}
print("Input: ", json.dumps(data1))
result1 = engine._anonymize_nested_json(data1, engine.config)
print("Output:", json.dumps(result1))

# Example 2: Dataset with PAN
print("\n✅ Example 2: Dataset WITH PAN card")
print("-" * 70)
data2 = {
    "recordid": "REC001",
    "pan": "ABCDE1234F",
    "salary": 50000,
    "state": "Karnataka",
    "district": "District 2"
}
print("Input: ", json.dumps(data2))
result2 = engine._anonymize_nested_json(data2, engine.config)
print("Output:", json.dumps(result2))

# Example 3: Dataset WITHOUT sensitive IDs
print("\n✅ Example 3: Dataset WITHOUT sensitive IDs")
print("-" * 70)
data3 = {
    "gender": "Male",
    "education": "Graduate",
    "occupation": "Engineer",
    "state": "Tamil Nadu",
    "district": "District 3"
}
print("Input: ", json.dumps(data3))
result3 = engine._anonymize_nested_json(data3, engine.config)
print("Output:", json.dumps(result3))

# Example 4: Dataset with Voter ID and License
print("\n✅ Example 4: Dataset WITH Voter ID & Driving License")
print("-" * 70)
data4 = {
    "voterid": "VOT123456",
    "drivinglicense": "DL987654",
    "accountnumber": "ACC123456",
    "state": "Gujarat",
    "district": "District 4"
}
print("Input: ", json.dumps(data4))
result4 = engine._anonymize_nested_json(data4, engine.config)
print("Output:", json.dumps(result4))

print("\n" + "=" * 70)
print("✅ CONCLUSION: Engine automatically adapts to ANY dataset!")
print("=" * 70)
print("\nKey Points:")
print("• Aadhaar, PAN, Voter ID, etc. → [SUPPRESSED]")
print("• State → [REGION]")
print("• District → Preserved")
print("• Categorical fields → Preserved")
print("• Numeric fields → Differential Privacy applied")
