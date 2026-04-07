FROM python:3.9

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

# Copy src directory while preserving structure
COPY src/ /app/src/

# Set PYTHONPATH so imports work correctly
ENV PYTHONPATH=/app/src

EXPOSE 8080

ENTRYPOINT ["python", "/app/src/app.py"]