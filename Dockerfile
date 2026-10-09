# Optional container image for hosts such as Render, Railway, Fly.io or Cloud Run.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Provide OPENAI_API_KEY at runtime via the host's secret manager - never bake it into the image.
ENV PORT=8501
EXPOSE 8501
CMD streamlit run app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true
