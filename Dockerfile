# Competition images are required to run on Linux amd64 without GPU support.
FROM --platform=linux/amd64 python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install only the pinned runtime dependencies; no developer tools or datasets.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY main.py README.md ./
COPY config ./config
COPY src ./src

# Runtime arguments belong after the image name in docker run, not here.
# The judge supplies all six arguments, including its API key and input/output paths.
# ./input and ./output now resolve to /input and /output, matching the judge.
WORKDIR /
ENTRYPOINT ["python", "/app/main.py"]
