# syntax=docker/dockerfile:1

FROM python:3.11-slim

# Don't buffer stdout/stderr (so logs show up immediately) and don't write
# .pyc files inside the container.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8420

WORKDIR /app

# Create an unprivileged user up front; the app never needs root at runtime.
RUN useradd --create-home --uid 10001 appuser

# Install dependencies first, in their own layer, so that editing application
# code doesn't invalidate the (slow) pip install cache. lxml/trafilatura pull
# in native builds that are far cheaper to cache than to rebuild every time.
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Now copy the application code. Changes here reuse the dependency layer above.
COPY app/ ./app/
COPY robots.txt ./

# The token is persisted to /app/data (a named volume in compose). Create it
# and hand ownership to the runtime user so first-run writes succeed.
RUN mkdir -p /app/data && chown -R appuser:appuser /app

USER appuser

EXPOSE 8420

# Poll the unauthenticated /health endpoint. Uses the stdlib (no curl in slim)
# and honours PORT so it tracks whatever the server actually binds to.
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import os,urllib.request,sys; \
url='http://127.0.0.1:%s/health' % os.environ.get('PORT','8420'); \
sys.exit(0 if urllib.request.urlopen(url, timeout=3).status == 200 else 1)"

# Shell form so ${PORT:-8420} is expanded at container start.
ENTRYPOINT ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8420}"]
