import lambda_function
import base64
import sys
import json

try:
    with open("../sample.pdf", "rb") as f:
        pdf_bytes = f.read()
    b64 = base64.b64encode(pdf_bytes).decode('utf-8')

    event = {
        "body": json.dumps({
            "pdf_base64": b64,
            "filename": "sample.pdf"
        })
    }

    print("Calling handler...")
    res = lambda_function.handler(event, None)
    print("Result:", res)
except Exception as e:
    import traceback
    traceback.print_exc()
