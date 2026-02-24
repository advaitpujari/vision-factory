
**About the JSON Output:**

The JSON output for **Page 1** (or any cached page) is stored in the `cache/` directory.

- **Current Location:** `/Users/advaitpujari/Developer/database-creation/cache/page_1_response.json`
- **Recommended Location:**
    - **For Development/Debugging:** The `cache/` folder is perfect as it avoids re-fetching from the API.
    - **For Final Output:** The full consolidated JSON (all pages merged) is saved to the file path you provide when running the script (e.g., `processed_json/sample.json`).

The pipeline currently:
1.  Checks `cache/page_{N}_response.json`.
2.  If found, uses it.
3.  If not, calls the API (currently DeepInfra) and *saves* the result to that cache file.

Shall I proceed with switching the API client to **Gemini**, which natively supports this JSON verification workflow much better?
