FROM python:3.12-alpine

WORKDIR /app
COPY server.py /app/server.py

ENV PORT=8092
EXPOSE 8092

CMD ["python", "/app/server.py"]
