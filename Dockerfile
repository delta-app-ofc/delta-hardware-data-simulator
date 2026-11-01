FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY dataload/ ./dataload/

ENTRYPOINT ["python", "-m", "dataload.cli"]
CMD ["--help"]
