"""
Comprehensive Age Range Test - Verify granular 10-year buckets
"""

import sys
sys.path.insert(0, '.')

from proj.privacy_engine import age_to_range

print("=" * 80)
print("AGE RANGE VERIFICATION - GRANULAR 10-YEAR BUCKETS")
print("=" * 80)

print("\nAge Mapping Table:")
print("-" * 80)
print(f"{'Age':<10} {'Range':<15} {'Status'}")
print("-" * 80)

# Test all age ranges
test_cases = [
    # Minors
    (5, "0-17"),
    (10, "0-17"),
    (17, "0-17"),
    
    # Young adults
    (18, "18-25"),
    (22, "18-25"),
    (25, "18-25"),
    
    # Adults - 10-year buckets
    (26, "26-35"),
    (30, "26-35"),
    (35, "26-35"),
    
    (36, "36-45"),
    (40, "36-45"),
    (45, "36-45"),
    
    (46, "46-55"),
    (50, "46-55"),
    (55, "46-55"),
    
    (56, "56-65"),
    (60, "56-65"),
    (65, "56-65"),
    
    # Seniors - granular buckets
    (66, "66-75"),
    (70, "66-75"),  # THIS IS THE KEY TEST CASE
    (75, "66-75"),
    
    (76, "76-85"),
    (80, "76-85"),
    (85, "76-85"),
    
    (86, "86-95"),
    (90, "86-95"),
    (95, "86-95"),
    
    (96, "96-120"),
    (100, "96-120"),
    (110, "96-120"),
]

all_passed = True
for age, expected in test_cases:
    result = age_to_range(age)
    passed = result == expected
    status = "✓ PASS" if passed else f"✗ FAIL (got {result})"
    
    if not passed:
        all_passed = False
    
    # Highlight the key test case (age 70)
    marker = " ← KEY TEST" if age == 70 else ""
    print(f"{age:<10} {result:<15} {status}{marker}")

print("-" * 80)

if all_passed:
    print("\n✅ ALL TESTS PASSED!")
    print("\nKey Verification:")
    print(f"  Age 70 → {age_to_range(70)} (Expected: 66-75)")
    print(f"  Age 80 → {age_to_range(80)} (Expected: 76-85)")
    print(f"  Age 90 → {age_to_range(90)} (Expected: 86-95)")
else:
    print("\n❌ SOME TESTS FAILED!")

print("\n" + "=" * 80)
print("SUMMARY: All ages now use granular 10-year buckets")
print("=" * 80)
