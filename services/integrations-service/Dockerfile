FROM golang:1.23-alpine AS builder

WORKDIR /app

RUN apk add --no-cache git

COPY go.mod go.sum* ./
RUN go mod download || true

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /bin/integrations-service ./cmd/server

FROM alpine:3.20

WORKDIR /app

RUN addgroup -S trustgrid && adduser -S trustgrid -G trustgrid

COPY --from=builder /bin/integrations-service /app/integrations-service

USER trustgrid

EXPOSE 8006

CMD ["/app/integrations-service"]