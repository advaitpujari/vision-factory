# Vision Factory - System Architecture & Flow

This document explains the lifecycle of the Vision Factory serverless pipeline. It covers how the code is deployed, how a request is triggered, how environment variables are loaded, and the step-by-step PDF extraction process using AI.

---

## 1. CI/CD Deployment Flow 🚀

Vision Factory is an independent microservice deployed entirely via AWS Lambda using Docker Containers. Deployment is fully automated using GitHub Actions.

### How it Works
1. **Developer Push:** A developer commits and pushes code to the `main` branch.
2. **GitHub Actions:** The `deploy.yml` workflow is automatically triggered.
3. **Build & Package:** GitHub Actions checks out the code, installs dependencies, and builds a Docker image using the `Dockerfile`.
4. **Push to Amazon ECR:** The image is tagged with the commit SHA and pushed to an Amazon Elastic Container Registry (ECR).
5. **Update AWS Lambda:** GitHub Actions triggers AWS Lambda to update its underlying container image to the new one we just published.

### Deployment Flow Diagram
Developer      GitHub         GHA          ECR         Lambda
      |            |             |            |            |
      | git push   |             |            |            |
      |----------->|             |            |            |
      |            | Trigger     |            |            |
      |            |------------>|            |            |
      |            |             |            |            |
      |            |             | Build Image|            |
      |            |             |----[ ]     |            |
      |            |             |            |            |
      |            |             | docker push|            |
      |            |             |----------->|            |
      |            |             |            |            |
      |            |             |   Success  |            |
      |            |             |<-----------|            |
      |            |             |            |            |
      |            |             | Update Code|            |
      |            |             |------------------------>|
      |            |             |            |            |
      |            |             |   ACK      |            |
      |            |             |<------------------------|
      |            |             |            |            |
      |            |             |            |     [Internal]
      |            |             |            |     Pulls Image &
      |            |             |            |     Provisions
      |            |             |            |            |



---

## 2. Configuration & Secrets (Environment variables) Flow 🔐

Because Vision Factory is hosted on AWS Lambda, it does **not** rely on local `.env` files. Instead, it relies on AWS Lambda Environment Variables.

### The Loading Process
1. **Lambda Boot:** When Lambda spins up the Docker container, it natively injects environment variables into the OS runtime.
2. **Settings Initialization:** The moment the Python handler invokes any core code, `vision_factory/config/settings.py` is loaded into memory. This file uses `os.getenv()` to map AWS context variables directly into a centralized Python `Settings` object.
3. **Provider Configuration (`API_PROVIDER`):** `settings.py` determines if we are routing AI traffic to DeepInfra or Google based on the `API_PROVIDER` and `API_PROVIDER_URL` variables. 
4. **Usage at Instantiation:**
   - When the `S3Uploader` is created in `pipeline.py`, it automatically pulls `settings.AWS_REGION` and `settings.S3_BUCKET_NAME`.
   - When the `DeepInfraClient` is created, it pulls the `VISION_API_KEY`, `TEXT_API_KEY`, and corresponding Model Names.

---

## 3. High-Level Trigger & Request Lifecycle ⚡️

Once deployed, the Vision FactoryLambda function sits idle until it is triggered (usually via an AWS API Gateway or direct Lambda Invoke).

### Payload Acceptance
The Lambda handler `lambda_function.py` expects a JSON payload containing exactly one of two things:
- `"pdf_base64"`: A raw Base64 string of the PDF content.
- `"pdf_url"`: A public URL pointing to a PDF document (which the code will download).

### Element-Level Request Diagram
[ Client ]
    | (PDF URL)
    v
+-----------+       +-----------------+       +-----------------+
|  API GW   | ----> | Lambda Handler  | ----> | /tmp Storage    |
+-----------+       +-------+---------+       +-----------------+
                            |
                    [ Start Pipeline ]
                            |
                            v
                  /-------------------\
                  |  Is Doc Cached?   | --(Yes)--> [ Return JSON ]
                  \---------+---------/
                            | (No)
                            v
                  +-------------------+
                  |  Convert to Image |
                  +---------+---------+
                            |
               /------------+------------\
               |      LOOP PER PAGE      |
               |  +-------------------+  |      +----------------+
               |  | LLM Extraction    |  | ---> | SQLite (State) |
               |  +-------------------+  |      +----------------+
               |            |            |              ^
               |  +-------------------+  |              |
               |  | Upload to S3      |  | -------------/
               |  +-------------------+  |
               \------------+------------/
                            |
                  +---------+---------+
                  |  Final JSON Build | ---> [ 200 OK to API ]
                  +-------------------+

---

## 4. Two-Step AI Extraction Flow 🧠

The most complex part of the pipeline occurs when a single page image is sent to the designated AI models. The system uses a specific prompting technique to achieve high accuracy.

### The Extraction Process
1. **Vision Inference:** The `DeepInfraClient` converts the page into a Base64 image and constructs a payload containing the rigid, expected JSON Schema. 
2. **First Model (Vision):** The image is sent to the Vision model (e.g., Llama-3.2 Vision). The model analyzes the page and outputs a raw, unstructured JSON string describing the questions, options, and bounding boxes.
3. **Text Inference (Fallback/Refinement):** If the JSON from the vision model is slightly malformed or incomplete, a subsequent call can be made to the Text Model to strictly format it.
4. **Parsing:** The raw string is run through the `JSONParser`, which uses Pydantic to strictly validate data types.

### AI Extraction Diagram
[ Start: extract_page ]
                |
                v
      +-------------------------+
      |  Encode Image (Base64)  |
      |  Apply System Prompt    |
      +------------+------------+
                   |
                   v
      +-------------------------+
      |  STEP 1: Vision Model   |
      |  (Extract Raw Content)  |
      +------------+------------+
                   |
          < Raw JSON String >
                   |
                   v
      +-------------------------+
      |  STEP 2: Text Model     |
      |  (Mandatory Refinement) |
      +------------+------------+
                   |
         < Refined JSON String >
                   |
                   v
      +-------------------------+
      |  STEP 3: Pydantic Parse |
      |  (Model Instantiation)  |
      +------------+------------+
                   |
          < Structured Data >
                   |
                   v
      +-------------------------+
      |   Validation Utility    |
      |   (Schema & Logic Check)|
      +------------+------------+
                   |
         /-------------------\
         | Generate Stats:   |
         | - Confidence Score|
         | - Missing Fields  |
         | - LaTeX Integrity |
         \---------+---------/
                   |
         [ Final Output Object ]