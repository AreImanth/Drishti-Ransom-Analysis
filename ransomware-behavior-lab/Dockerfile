# Ransomware Behavior Lab — Web UI (Docker)
# Graphs (matplotlib, ~40MB) are OFF by default for thin links.
# Enable with: docker compose build --build-arg INSTALL_GRAPHS=1
FROM python:3.12-slim

ARG INSTALL_GRAPHS=0

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    LAB_ROOT=/data/victim \
    PORT=6767

WORKDIR /app

# System deps only when graphs are enabled (matplotlib needs them).
RUN if [ "$INSTALL_GRAPHS" = "1" ]; then \
        apt-get update && apt-get install -y --no-install-recommends \
            libfreetype6 \
            libpng16-16 \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# Python deps first (better layer caching). Core set is small on purpose:
# watchdog + psutil + flask + gunicorn. matplotlib is opt-in.
COPY requirements.txt ./requirements.txt
COPY webui/requirements.txt ./webui/requirements.txt
COPY requirements-graphs.txt ./requirements-graphs.txt
# No `pip install --upgrade pip`: base pip is fine and the 1.8MB upgrade
# wastes minutes on thin links. Retries raised for flaky connections.
RUN pip install --retries 10 --timeout 60 -r requirements.txt \
    && pip install --retries 10 --timeout 60 -r webui/requirements.txt \
    && if [ "$INSTALL_GRAPHS" = "1" ]; then pip install --retries 10 --timeout 60 -r requirements-graphs.txt; fi

# Application code
COPY . .

# Entrypoint arrives from Windows without the executable bit — restore it.
RUN chmod +x ./docker-entrypoint.sh

# Victim data lives outside the image so runs survive container rebuilds
VOLUME ["/data/victim"]

EXPOSE 6767

ENTRYPOINT ["./docker-entrypoint.sh"]
