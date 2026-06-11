FROM python:3.12-alpine

WORKDIR /app
COPY server.py /app/server.py

ENV PORT=8093
EXPOSE 8093

CMD ["python", "/app/server.py"]
