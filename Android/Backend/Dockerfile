FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ERRNO_REQUIRE_POSTGRES=true \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/errno/Android/Backend

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN addgroup --system --gid 10001 errno \
    && adduser --system --uid 10001 --ingroup errno errno \
    && chown -R errno:errno /srv/errno

USER errno
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1"]
