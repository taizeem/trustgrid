FROM rust:alpine AS builder

WORKDIR /app

RUN apk add --no-cache musl-dev

# Cache dependencies
COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "pub fn dummy() {}" > src/lib.rs && echo "fn main() {}" > src/main.rs && cargo build --release || true
RUN rm -rf src target/release/deps/document_service* target/release/document-service*

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