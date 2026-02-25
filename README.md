# Vision Factory

Vision Factory is a robust, production-ready Python package and CLI tool designed to analyze and extract structured JSON data from PDF exam papers using Vision Large Language Models (LLMs) like Google Gemini.

By treating the problem of data extraction as a vision task (rather than purely text extraction), it sidesteps the common pitfalls of parsing complex PDFs, handling diagrams, formulas, and deeply nested layouts seamlessly.

## Features

- **Batch Processing**: Automatically robust processing of multiple PDF files at once.
- **Idempotency**: Retains state allowing you to retry failed chunks without re-processing successfully extracted pages (powered by a local SQLite ledger).
- **Vision LLM Integration**: Uses state-of-the-art vision models to extract complex data structures natively.
- **S3 Asset Uploading**: Automatically identifies, crops, and uploads diagrams/images to AWS S3, embedding the URLs directly into the JSON.
- **Package & CLI Modes**: Flexible to use as a standalone command-line application or embedded directly within your own Python services.

---

## 🚀 Installation

### Prerequisites

For Mac users, you must install `poppler` to enable PDF-to-image processing:
```bash
brew install poppler
```
*(On Ubuntu/Debian, use `apt-get install poppler-utils`)*

### Install from Source (Development)

Clone the repository and install it in editable mode:
```bash
git clone https://github.com/advaitpujari/vision-factory.git
cd vision-factory
pip install -e .
```

### Install as a Package (Production)

You can pip install this package directly from GitHub into any other project:
```bash
pip install git+https://github.com/advaitpujari/vision-factory.git
```

---

## ⚙️ Configuration

The pipeline requires API credentials. Create a `.env` file in the root directory (or use your system environment variables) with the following structure:

```env
# AI Provider (e.g., Google Gemini or DeepInfra)
GEMINI_API_KEY=your_gemini_api_key

# AWS Configuration for Uploading Assets
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=your_aws_region
S3_BUCKET_NAME=your_bucket_name
```

---

## 💻 Usage: CLI Mode

Once installed, the package provides a convenient `vision-factory` CLI command.

### Basic Batch Processing
Process an entire directory of PDFs:
```bash
vision-factory --input ./my_pdfs/ --output ./results/
```

### Single File Processing
```bash
vision-factory -i input/sample.pdf -o my_results/
```

**What happens?**
The pipeline converts the PDFs to images, passes them to the configured Vision LLM, uploads cropped diagrams to S3, and writes the structured JSON to the `--output` directory, alongside a `batch_overview.md` summarising the success rates.

---

## 🐍 Usage: Python Package Mode

Integrating Vision Factory into your existing Python applications is straightforward:

```python
import os
from dotenv import load_dotenv
from vision_factory.pipeline import VisionPipeline

# 1. Load your credentials
load_dotenv()

# 2. Initialize the pipeline
pipeline = VisionPipeline()

# 3. Process a single PDF
input_pdf = "path/to/my_file.pdf"
output_json = "path/to/output.json"

try:
    pipeline.process_pdf(input_pdf, output_json)
    print(f"Successfully processed! Results saved to {output_json}")
except Exception as e:
    print(f"Pipeline failed: {e}")
```

---

## 📥 Inputs & 📤 Outputs

### Inputs
The system takes standard `.pdf` files.
When running in batch mode, simply point the script to a directory of PDFs. 

### Outputs
For every `filename.pdf` ingested, the pipeline produces a strictly conforming `filename.json` file. 
If errors occur during a specific page's extraction, it is logged in the internal SQLite state database. A final summary consisting of `batch_overview.md` and `batch_details.csv` is emitted when batch processing is complete.

---

## 🔮 Future Upgrades & Scope

- **Support for Multi-Modal AI**: Expansion to local models (e.g. LLaVA) for data-privacy sensitive deployments without external API dependencies.
- **Streaming JSON Support**: Begin yielding JSON arrays block-by-block instead of waiting for full page compilation.
- **Custom Schema Injection**: Allow users to pass custom Pydantic schemas dynamically via the CLI to alter the extraction target without requiring code changes.
- **Parallel Processing**: Utilize multi-processing and multi-threading for the image extraction pipeline to significantly speed up processing of large PDFs.
