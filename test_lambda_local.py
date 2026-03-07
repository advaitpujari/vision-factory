import json
from lambda_function import handler

event = {
    "body": json.dumps({
        "webhook_url": "https://httpbin.org/post",
        "job_id": "test-job-id-12345",
        "filename": "broken_test_file.pdf",
        # Intentionally passing no pdf options to trigger the _InputError inside handler
    })
}

class Context:
    pass

if __name__ == "__main__":
    print("Invoking handler locally...")
    result = handler(event, Context())
    print("\nHandler Result:")
    print(json.dumps(result, indent=2))
