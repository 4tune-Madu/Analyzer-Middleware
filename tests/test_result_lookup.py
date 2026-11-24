
from database import get_machine_result_matches

matches = get_machine_result_matches(
    machine_id=3,
    lab_no="69275",
    test_code="AST",
)

print("Matching records:", len(matches))

for match in matches:
    print(match)
