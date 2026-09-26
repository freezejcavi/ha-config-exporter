FROM ghcr.io/home-assistant/base-python:3.14-alpine3.24

ARG BUILD_VERSION
ARG BUILD_ARCH

LABEL \
  io.hass.version="${BUILD_VERSION}" \
  io.hass.type="app" \
  io.hass.arch="${BUILD_ARCH}"

RUN apk add --no-cache \
      git \
      openssh-client

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY app/ /app/

CMD ["/command/with-contenv", "python3", "/app/exporter.py"]
