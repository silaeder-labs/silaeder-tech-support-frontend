FROM python:3.12-alpine

WORKDIR /app
COPY server.py /app/server.py

ENV PORT=8090
EXPOSE 8090

CMD ["python", "/app/server.py"]
