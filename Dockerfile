# Competition images are required to run on Linux amd64 without GPU support.
FROM --platform=linux/amd64 python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the declared runtime dependencies before copying source for better
# Docker layer caching. The lock file was generated on Windows and contains
# platform-specific wheels, so the portable requirements file is used here.
# No API key or dataset is baked into the image.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir --requirement requirements.txt

COPY main.py README.md COMPETITION_CONSTRAINTS.md ./
COPY config ./config
COPY src ./src

# The judge appends its six required command-line arguments to this entrypoint.
ENTRYPOINT ["python", "main.py"]
