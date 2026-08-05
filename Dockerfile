FROM python:3.12-slim

WORKDIR /app
COPY . /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir .

ENV TRINITY_GATE_DB=/data/trinity-gate.db
ENV TRINITY_GATE_HOST=0.0.0.0
ENV TRINITY_GATE_PORT=8080

VOLUME ["/data"]
EXPOSE 8080

CMD ["python", "-m", "trinity_gate.http_api"]
