# syntax=docker/dockerfile:1
# =============================================================================
# odoo-hub — Odoo 18 + Custom Addons
# =============================================================================
ARG ODOO_BASE=odoo:18.0
FROM ${ODOO_BASE}

ARG GIT_SHA=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.source="https://github.com/achimdehnert/odoo-hub"
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.title="odoo-hub"
LABEL org.opencontainers.image.description="Odoo 18 custom addons hub"

USER root

# -- System dependencies ------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    fonts-dejavu \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# -- Python deps for custom modules -------------------------------------------
COPY requirements.txt /tmp/requirements.txt
RUN if [ -s /tmp/requirements.txt ]; then \
        pip install --no-cache-dir --break-system-packages -r /tmp/requirements.txt; \
    fi

# -- Copy custom addons -------------------------------------------------------
COPY addons/ /mnt/extra-addons/

# -- Odoo config ---------------------------------------------------------------
COPY odoo.conf /etc/odoo/odoo.conf

USER odoo

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -sf http://127.0.0.1:8069/web/login || exit 1
