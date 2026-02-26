"""
AWS Lambda Handler for Vision Factory PDF Processing Pipeline.

Supported event shapes:
  1. Base64-encoded PDF:
     { "pdf_base64": "<base64 string>" }

  2. Public URL to a PDF:
     { "pdf_url": "https://example.com/paper.pdf" }

Optional fields:
  - "filename": custom name used for output file (default: "document")
"""

import json
import base64
import logging
import os
import sys
import tempfile
import urllib.request
import urllib.error
from typing import Any, Dict

# Configure logging for Lambda (stdout goes to CloudWatch)
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s %(name)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda entry point.

    Parameters
    ----------
    event : dict
        API Gateway payload or direct invocation payload. Must contain
        either ``pdf_base64`` or ``pdf_url``.
    context : LambdaContext
        Standard Lambda context object (unused directly).

    Returns
    -------
    dict
        HTTP-style response with ``statusCode`` and a JSON ``body``.
    """
    logger.info("Lambda invocation received.")
    logger.debug("Event keys: %s", list(event.keys()))

    # ------------------------------------------------------------------
    # 1. Parse Input
    # ------------------------------------------------------------------
    pdf_base64: str = event.get("pdf_base64", "")
    pdf_url: str = event.get("pdf_url", "")
    filename: str = event.get("filename", "document")

    # Strip any path components from the provided filename for safety
    filename = os.path.basename(filename) or "document"
    # Remove extension if caller accidentally included it
    filename = os.path.splitext(filename)[0]

    if not pdf_base64 and not pdf_url:
        logger.warning("No PDF source provided in the event payload.")
        return _error_response(
            400,
            "Missing payload. Provide either 'pdf_base64' (base64-encoded PDF bytes) "
            "or 'pdf_url' (a public URL pointing to a PDF).",
        )

    # ------------------------------------------------------------------
    # 2. Materialise PDF to a Temporary File
    # ------------------------------------------------------------------
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            input_pdf_path = os.path.join(tmp_dir, f"{filename}.pdf")
            output_json_path = os.path.join(tmp_dir, f"{filename}.json")

            if pdf_base64:
                logger.info("Decoding base64-encoded PDF (%s)…", filename)
                pdf_bytes = _decode_base64_pdf(pdf_base64)
            else:
                logger.info("Downloading PDF from URL: %s", pdf_url)
                pdf_bytes = _download_pdf(pdf_url)

            with open(input_pdf_path, "wb") as f:
                f.write(pdf_bytes)

            logger.info("PDF written to %s (%d bytes)", input_pdf_path, len(pdf_bytes))

            # ----------------------------------------------------------
            # 3. Run the Vision Factory Pipeline
            # ----------------------------------------------------------
            result_payload = _run_pipeline(input_pdf_path, output_json_path, tmp_dir)

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(result_payload),
            }

    except _InputError as exc:
        logger.error("Input error: %s", exc)
        return _error_response(400, str(exc))

    except _PipelineError as exc:
        logger.error("Pipeline error: %s", exc)
        return _error_response(500, f"Pipeline processing failed: {exc}")

    except Exception as exc:  # pragma: no cover
        logger.exception("Unexpected error: %s", exc)
        return _error_response(500, f"Internal server error: {exc}")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

class _InputError(ValueError):
    """Raised for malformed or missing input."""


class _PipelineError(RuntimeError):
    """Raised when the Vision Factory pipeline itself fails."""


def _decode_base64_pdf(pdf_base64: str) -> bytes:
    """Decode a base64 string into raw PDF bytes."""
    try:
        # Accept both standard and URL-safe base64 variants
        return base64.b64decode(pdf_base64 + "==")
    except Exception as exc:
        raise _InputError(f"Failed to decode base64 PDF: {exc}") from exc


def _download_pdf(url: str) -> bytes:
    """Download a PDF from a public URL and return its raw bytes."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "VisionFactory/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                logger.warning(
                    "URL may not point to a PDF (Content-Type: %s). Proceeding anyway.",
                    content_type,
                )
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise _InputError(f"HTTP {exc.code} fetching PDF from URL: {url}") from exc
    except urllib.error.URLError as exc:
        raise _InputError(f"Could not reach URL '{url}': {exc.reason}") from exc
    except Exception as exc:
        raise _InputError(f"Unexpected error downloading PDF: {exc}") from exc


def _run_pipeline(pdf_path: str, output_json_path: str, tmp_dir: str) -> Dict[str, Any]:
    """
    Invoke the VisionPipeline and return a structured response dict.

    The pipeline writes a JSON file to ``output_json_path``; we read it back
    and include it along with pipeline run metadata in the response.
    """
    # Lazy import so that Lambda cold-start only loads heavy deps when needed
    try:
        from vision_factory.pipeline import VisionPipeline
    except ImportError as exc:
        raise _PipelineError(
            f"vision_factory package could not be imported. "
            f"Ensure the package is installed in the Docker image: {exc}"
        ) from exc

    try:
        pipeline = VisionPipeline()
        stats = pipeline.process_pdf(pdf_path, output_json_path)
    except Exception as exc:
        raise _PipelineError(str(exc)) from exc

    # Read the structured JSON output produced by the pipeline
    result_json: Dict[str, Any] = {}
    if os.path.exists(output_json_path):
        try:
            with open(output_json_path, "r") as f:
                result_json = json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Pipeline output is not valid JSON: %s", exc)
            raise _PipelineError(f"Pipeline produced malformed JSON: {exc}") from exc
    else:
        logger.warning(
            "Pipeline completed but output file was not found at %s", output_json_path
        )

    return {
        "pipeline_stats": stats,
        "result": result_json,
    }


def _error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Build a standard error response dict."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"error": message}),
    }
