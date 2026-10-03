# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.11
FROM python:${PYTHON_VERSION}-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update --fix-missing && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

WORKDIR /app 

# ARG var during build
ARG UID=10001

# Create non-root user
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/user_home" \
    --shell "/sbin/nologin" \
#   --no-create-home 
    --uid "${UID}" \
    appuser

# Minimum privilege: give only privileges to a specific dir to download the whisper models
# RUN mkdir -p /app/.cache/whisper && chown -R appuser:appuser /app/.cache
# ENV HOME=/app

RUN chown -R appuser:appuser /app

# No cpu-torch
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Create cache to not re-download all the requirements
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=bind,source=requirements.txt,target=requirements.txt \
    python -m pip install -r requirements.txt

USER appuser

RUN mkdir -p /user_home/user_cache/whisper

COPY . .

EXPOSE 8000

# exec format for better performance
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
