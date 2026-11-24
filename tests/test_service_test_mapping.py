from database import get_machine_tests_for_services

tests = get_machine_tests_for_services([1, 100], 3)

for test in tests:
    print(
        f"ServiceId={test['service_id']} | "
        f"MapType={test['map_type']} | "
        f"TestId={test['test_id']} | "
        f"ChannelNo={test['channel_no']} | "
        f"TestCode={test['test_code']}"
    )

print("Total resolved tests:", len(tests))