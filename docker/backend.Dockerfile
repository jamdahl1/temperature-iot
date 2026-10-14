# syntax=docker/dockerfile:1

# Development image for the external temperature-iot-backend checkout.
# Build contexts are supplied by temperature_demo.build_image.
# This file does not vendor application source.

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --from=commons compute-manager /opt/vendor/compute-manager
COPY --from=commons uapi-adapter /opt/vendor/uapi-adapter
COPY --from=backend . /opt/vendor/temperature-iot-backend

RUN python -m pip install --no-cache-dir \
        /opt/vendor/compute-manager \
        /opt/vendor/uapi-adapter \
    && python -m pip install --no-cache-dir \
        /opt/vendor/temperature-iot-backend \
    && rm -rf /opt/vendor

EXPOSE 8000

ENTRYPOINT ["python", "-m", "temperature_iot_backend"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8000"]
