"""
Test Age Range Format - Verify all ranges use "age-age" format
"""

import sys
sys.path.insert(0, '.')

from proj.privacy_engine import age_to_range, income_to_range, household_to_range, land_to_range

print("=" * 80)
print("TESTING RANGE FORMAT CONSISTENCY")
print("=" * 80)

print("\n1. AGE RANGES (should all be 'age-age' format):")
print("-" * 80)
test_ages = [5, 15, 20, 28, 40, 53, 65, 75, 90, 110]
for age in test_ages:
    result = age_to_range(age)
    print(f"Age {age:3d} -> {result:10s} {'✓' if '-' in result else '✗ ERROR: No hyphen!'}")

print("\n2. INCOME RANGES (should all be 'income-income' format):")
print("-" * 80)
test_incomes = [5000, 15000, 22000, 30000, 45000, 60000, 85000, 150000, 500000]
for income in test_incomes:
    result = income_to_range(income)
    print(f"Income {income:7d} -> {result:20s} {'✓' if '-' in result else '✗ ERROR: No hyphen!'}")

print("\n3. HOUSEHOLD SIZE RANGES (should all be 'size-size' format):")
print("-" * 80)
test_sizes = [1, 2, 3, 5, 7, 10, 15, 25]
for size in test_sizes:
    result = household_to_range(size)
    print(f"Size {size:2d} -> {result:10s} {'✓' if '-' in result else '✗ ERROR: No hyphen!'}")

print("\n4. LAND RANGES (should all be 'acres-acres' format):")
print("-" * 80)
test_land = [0.2, 0.7, 1.5, 2.5, 4.0, 8.0, 50.0, 200.0]
for land in test_land:
    result = land_to_range(land)
    print(f"Land {land:6.1f} -> {result:15s} {'✓' if '-' in result else '✗ ERROR: No hyphen!'}")

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE!")
print("=" * 80)
print("\nAll ranges should now use consistent 'value-value' format")
print("No '+' symbols should appear in the output")
