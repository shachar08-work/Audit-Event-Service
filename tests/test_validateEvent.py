import requests
from pathlib import Path
import json

# ANSI escape codes for colors
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

API_URL = "http://127.0.0.1:8000/events"

# Get path relative to this file
events_file = Path(__file__).parent / "events.json"

def func(x):
    """Normalize expected fail reason for comparison"""
    if x == "":
        return "missing required field"
    return x

def format_validation_errors(errors):
    """Deduplicate and format validation errors for printing"""
    seen = set()
    messages = []
    for e in errors:
        # e[0] = path, e[1] = message
        # If path empty, extract field from message
        if not e[0]:
            field_name = e[1].split("'")[1]  # gets the field in quotes
            msg_str = f"missing required field: '{field_name}' is a required property"
        else:
            field_name = e[0]
            msg_str = f"{field_name}: {e[1]}"
        if msg_str not in seen:
            seen.add(msg_str)
            messages.append(msg_str)
    return messages

def validate_errors(errors, expected_fail_reasons):
    formatted_errors = format_validation_errors(errors)
    for reason in expected_fail_reasons:
        expected = func(reason)
        if expected == "missing required field":
            assert any("missing required field" in err for err in formatted_errors), \
                f"{RED}Expected missing field error for '{reason}' but not found. Errors: {formatted_errors}{RESET}"
        else:
            assert any(expected in err for err in formatted_errors), \
                f"{RED}Expected fail reason '{expected}' not found in errors: {formatted_errors}{RESET}"
    return formatted_errors

def test_post_events():
    with open(events_file, "r", encoding="utf-8") as f:
        events = json.load(f)

    for i, (event_payload, expect) in enumerate(events, start=1):
        expected_status = expect.get("status")
        expected_fail_reasons = expect.get("fail_reason", [])

        response = requests.post(API_URL, json=event_payload)
        print(f"Event #{i} - Status Code: {response.status_code}")

        assert response.status_code == expected_status, \
            f"{RED}Event {i} expected status {expected_status} but got {response.status_code}{RESET}"

        if expected_status == 400:
            errors = response.json().get("errors", [])
            formatted_errors = validate_errors(errors, expected_fail_reasons)
            print(f"{GREEN}✅ Event #{i} failed as expected due to missing or invalid fields:{RESET}")
            for msg in formatted_errors:
                print(f"   • {msg}")
        else:
            print(f"{GREEN}✅ Event #{i} passed validation and created successfully.{RESET}")

        print("-" * 50)

if __name__ == "__main__":
    test_post_events()
