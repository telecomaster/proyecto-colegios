FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-descarga el modelo de embeddings dentro de la imagen para que el
# contenedor pueda arrancar sin conexion a internet (importante para un
# servidor escolar con conectividad limitada).
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY *.py .
# Contenido de referencia: docker-compose.yml monta ./orchestrator/knowledge_base
# como volumen y sustituye esto en tiempo de ejecucion, para que un profesor
# pueda agregar material sin reconstruir la imagen.
COPY knowledge_base/ ./knowledge_base/

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
