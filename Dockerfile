# ──────────────────────────────────────────────────────────────────────────────
# Vision Factory – AWS Lambda Container Image
#
# Base image: official AWS Lambda Python 3.11 runtime (Amazon Linux 2023)
# ──────────────────────────────────────────────────────────────────────────────
FROM public.ecr.aws/lambda/python:3.11

# ── System dependencies ────────────────────────────────────────────────────────
# poppler-utils  → required by pdf2image (pdftoppm / pdfinfo binaries)
# gcc / libffi   → occasionally needed by Python C-extension wheels
# ──────────────────────────────────────────────────────────────────────────────
RUN yum install -y \
        poppler-utils \
        poppler \
        gcc \
        libffi \
        libffi-devel \
    && yum clean all \
    && rm -rf /var/cache/yum

# ── Python dependencies ────────────────────────────────────────────────────────
# Copy requirements first to leverage Docker layer caching.
# Dev-only packages (pytest, black, flake8) are excluded via --no-dev flag
# equivalent: we filter them out here with a sed one-liner so the original
# requirements.txt doesn't need to be split.
# ──────────────────────────────────────────────────────────────────────────────
COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt

RUN sed -e '/pytest/d' -e '/black/d' -e '/flake8/d' ${LAMBDA_TASK_ROOT}/requirements.txt > /tmp/req_prod.txt \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /tmp/req_prod.txt \
    && rm /tmp/req_prod.txt \
    && echo "Dependencies installed."

# ── Application code ───────────────────────────────────────────────────────────
# Copy the package and supporting files into the Lambda task root.
# The Lambda base image sets LAMBDA_TASK_ROOT=/var/task by default.
# ──────────────────────────────────────────────────────────────────────────────
COPY vision_factory/        ${LAMBDA_TASK_ROOT}/vision_factory/
COPY lambda_function.py     ${LAMBDA_TASK_ROOT}/lambda_function.py
COPY pyproject.toml         ${LAMBDA_TASK_ROOT}/pyproject.toml

# Install the local package so `from vision_factory.xxx import yyy` resolves
RUN pip install --no-cache-dir --no-deps -e ${LAMBDA_TASK_ROOT} || \
    pip install --no-cache-dir ${LAMBDA_TASK_ROOT}

# ── Lambda entry point ────────────────────────────────────────────────────────
# Format: <module_name>.<function_name>
# Matches the handler function defined in lambda_function.py
# ──────────────────────────────────────────────────────────────────────────────
CMD ["lambda_function.handler"]
