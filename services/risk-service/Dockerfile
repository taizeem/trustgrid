FROM rust:alpine AS builder

WORKDIR /app

RUN apk add --no-cache musl-dev

# Cache dependencies
COPY Cargo.toml Cargo.lock* ./
RUN mkdir src && echo "pub fn dummy() {}" > src/lib.rs && echo "fn main() {}" > src/main.rs && cargo build --release || true
RUN rm -rf src target/release/deps/risk_service* target/release/risk-service*

COPY . .
RUN cargo build --release

FROM alpine:3.20

WORKDIR /app

RUN apk add --no-cache ca-certificates libgcc && \
    addgroup -S trustgrid && adduser -S trustgrid -G trustgrid

COPY --from=builder /app/target/release/risk-service /app/risk-service

USER trustgrid

EXPOSE 8005

CMD ["/app/risk-service"]