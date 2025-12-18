import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from tea_data import TEAS
    print("Successfully imported TEAS.")
    print(f"Total flavors: {len(TEAS)}")
    expected_flavors = ["sencha", "matcha", "genmaicha", "gyokuro", "hojicha", "jasmine", "sakura", "oolong", "puerh", "earl_grey", "white_peony"]
    
    missing = []
    for flavor in expected_flavors:
        if flavor not in TEAS:
            missing.append(flavor)
    
    if missing:
        print(f"FAIL: Missing flavors: {missing}")
    else:
        print("PASS: All expected flavors are present.")
        
    # Check for unexpected
    extra = set(TEAS.keys()) - set(expected_flavors)
    if extra:
        print(f"NOTE: Extra flavors found: {extra}")

except Exception as e:
    print(f"FAIL: Error importing tea_data: {e}")
