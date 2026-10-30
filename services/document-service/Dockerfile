FROM rust:alpine AS builder

WORKDIR /app

RUN apk add --no-cache musl-dev

COPY Cargo.toml Cargo.lock* ./
# Create dummy main to cache dependency compilation
RUN mkdir src && echo "fn main() {}" > src/main.rs && cargo build --release || true

COPY . .
RUN cargo build --release

FROM alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates libgcc && \
    addgroup -S trustgrid && adduser -S trustgrid -G trustgrid && \
    mkdir -p /data/documents && chown -R trustgrid:trustgrid /data/documents

COPY --from=builder /app/target/release/document-service /app/document-service

USER trustgrid

EXPOSE 8004

CMD ["/app/document-service"]