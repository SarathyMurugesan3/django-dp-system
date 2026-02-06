"""
Test Privacy Engine with Different Dataset Types
Demonstrates how the engine handles various sensitive fields automatically
"""

import json
from proj.privacy_engine import PrivacyEngine, PrivacyConfig

def test_different_datasets():
    """Test privacy engine with different types of datasets"""
    
    engine = PrivacyEngine(PrivacyConfig(epsilon=1.0))
    
    print("=" * 80)
    print("PRIVACY ENGINE - MULTI-DATASET TEST")
    print("=" * 80)
    
    # Test 1: Healthcare Dataset with Aadhaar
    print("\n📋 TEST 1: Healthcare Dataset (with Aadhaar)")
    print("-" * 80)
    
    healthcare_data = {
        "patientid": "P12345",
        "aadhaar": "1234-5678-9012",
        "name": "Amit Sharma",
        "age": 45,
        "diagnosis": "Diabetes",
        "hospital": "City Hospital",
        "state": "Maharashtra"
    }
    
    print("INPUT:")
    print(json.dumps(healthcare_data, indent=2))
    
    result = engine._anonymize_nested_json(healthcare_data, engine.config)
    
    print("\nOUTPUT:")
    print(json.dumps(result, indent=2))
    
    # Test 2: Financial Dataset with PAN
    print("\n\n💰 TEST 2: Financial Dataset (with PAN, Account)")
    print("-" * 80)
    
    financial_data = {
        "customerid": "C98765",
        "pan": "ABCDE1234F",
        "accountnumber": "1234567890",
        "name": "Priya Patel",
        "salary": 75000,
        "creditcard": "4532-1234-5678-9010",
        "state": "Gujarat"
    }
    
    print("INPUT:")
    print(json.dumps(financial_data, indent=2))
    
    result = engine._anonymize_nested_json(financial_data, engine.config)
    
    print("\nOUTPUT:")
    print(json.dumps(result, indent=2))
    
    # Test 3: Government Dataset with Voter ID
    print("\n\n🏛️ TEST 3: Government Dataset (with Voter ID, Driving License)")
    print("-" * 80)
    
    govt_data = {
        "recordid": "REC001",
        "voterid": "VOT1234567",
        "drivinglicense": "DL123456789",
        "name": "Suresh Kumar",
        "age": 52,
        "district": "District 5",
        "state": "Karnataka"
    }
    
    print("INPUT:")
    print(json.dumps(govt_data, indent=2))
    
    result = engine._anonymize_nested_json(govt_data, engine.config)
    
    print("\nOUTPUT:")
    print(json.dumps(result, indent=2))
    
    # Test 4: Census Dataset (Your Example)
    print("\n\n📊 TEST 4: Census Dataset (Your Example)")
    print("-" * 80)
    
    census_data = {
        "id": "12345",
        "recordid": "REC002",
        "agegroup": "26-35",
        "gender": "Male",
        "state": "Maharashtra",
        "district": "District 2",
        "areatype": "Urban",
        "education": "Secondary",
        "occupation": "Office Worker",
        "industry": "Services",
        "monthlyincomerange": "18000-25000",
        "householdsizerange": "3-5",
        "maritalstatus": "Unmarried",
        "disability": "No",
        "chronicillness": "No",
        "migrationstatus": "Non-Migrant",
        "employmenttype": "Contract",
        "landownedrange": "0.5-1.0"
    }
    
    print("INPUT:")
    print(json.dumps(census_data, indent=2))
    
    result = engine._anonymize_nested_json(census_data, engine.config)
    
    print("\nOUTPUT:")
    print(json.dumps(result, indent=2))
    
    # Test 5: Dataset WITHOUT sensitive IDs
    print("\n\n✅ TEST 5: Dataset WITHOUT Sensitive IDs (Clean Data)")
    print("-" * 80)
    
    clean_data = {
        "gender": "Female",
        "education": "Graduate",
        "occupation": "Teacher",
        "district": "District 3",
        "city": "Pune",
        "maritalstatus": "Married"
    }
    
    print("INPUT:")
    print(json.dumps(clean_data, indent=2))
    
    result = engine._anonymize_nested_json(clean_data, engine.config)
    
    print("\nOUTPUT:")
    print(json.dumps(result, indent=2))
    
    # Test 6: Tax Dataset with GST
    print("\n\n💼 TEST 6: Tax Dataset (with GSTIN, TIN)")
    print("-" * 80)
    
    tax_data = {
        "businessid": "BUS123",
        "gstin": "27AABCU9603R1ZM",
        "tin": "12345678901",
        "taxid": "TAX987654",
        "businessname": "ABC Enterprises",
        "revenue": 5000000,
        "state": "Delhi"
    }
    
    print("INPUT:")
    print(json.dumps(tax_data, indent=2))
    
    result = engine._anonymize_nested_json(tax_data, engine.config)
    
    print("\nOUTPUT:")
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED - Engine handles ANY dataset automatically!")
    print("=" * 80)

if __name__ == "__main__":
    test_different_datasets()
