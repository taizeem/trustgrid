FROM golang:1.23-alpine AS builder

WORKDIR /app

RUN apk add --no-cache git

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /bin/workflow-service ./cmd/server

FROM alpine:3.20

WORKDIR /app

RUN addgroup -S trustgrid && adduser -S trustgrid -G trustgrid

COPY --from=builder /bin/workflow-service /app/workflow-service
COPY internal/repository/schema.sql /app/internal/repository/schema.sql

USER trustgrid

EXPOSE 8003

CMD ["/app/workflow-service"]