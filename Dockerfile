FROM node:22-alpine AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend ./
RUN npm run build

FROM golang:1.23-alpine AS backend
WORKDIR /app/backend
COPY backend ./
COPY --from=frontend /app/frontend/dist ./public
RUN go mod tidy && go build -o /app/mixer ./cmd/api

FROM alpine:3.20
WORKDIR /app
COPY --from=backend /app/mixer /app/mixer
COPY --from=backend /app/backend/public /app/public
ENV PORT=8080
EXPOSE 8080
CMD ["/app/mixer"]
