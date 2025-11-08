"""
Dockerfile templates for different languages/frameworks
Docker 담당자가 이 파일을 수정하면 Lambda가 자동으로 반영합니다.
"""

# Python Dockerfile template
PYTHON_TEMPLATE = """# Multi-stage build for Python application
FROM python:3.11-slim as builder
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim
WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:{port}/health || exit 1

EXPOSE {port}

# Start command
CMD {start_command}
"""

# Node.js Dockerfile template
NODEJS_TEMPLATE = """# Multi-stage build for Node.js application
FROM node:20-alpine as builder
WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci --only=production

# Build if needed
COPY . .
RUN npm run build || echo "No build script"

# Final stage
FROM node:20-alpine
WORKDIR /app

# Copy from builder
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/build ./build
COPY package*.json ./

# Create non-root user
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
  CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/health || exit 1

EXPOSE {port}

# Start command
CMD {start_command}
"""

# Go Dockerfile template
GO_TEMPLATE = """# Multi-stage build for Go application
FROM golang:1.21-alpine as builder
WORKDIR /app

# Copy go mod files
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o app .

# Final stage - minimal image
FROM alpine:latest
WORKDIR /app

# Install ca-certificates for HTTPS
RUN apk --no-cache add ca-certificates curl

# Copy binary from builder
COPY --from=builder /app/app .

# Create non-root user
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:{port}/health || exit 1

EXPOSE {port}

# Start command
CMD ["./app"]
"""

# Rust Dockerfile template
RUST_TEMPLATE = """# Multi-stage build for Rust application
FROM rust:1.75 as builder
WORKDIR /app

# Copy manifest files
COPY Cargo.toml Cargo.lock ./

# Cache dependencies
RUN mkdir src && echo "fn main() {{}}" > src/main.rs
RUN cargo build --release
RUN rm -rf src

# Copy source code
COPY . .

# Build release
RUN cargo build --release

# Final stage - minimal image
FROM debian:bookworm-slim
WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \\
    ca-certificates curl \\
    && rm -rf /var/lib/apt/lists/*

# Copy binary from builder
COPY --from=builder /app/target/release/app .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \\
  CMD curl -f http://localhost:{port}/health || exit 1

EXPOSE {port}

# Start command
CMD ["./app"]
"""

# Java Dockerfile template
JAVA_TEMPLATE = """# Multi-stage build for Java application
FROM eclipse-temurin:17-jdk-alpine as builder
WORKDIR /app

# Copy build files
COPY . .

# Build with Maven or Gradle
RUN if [ -f "mvnw" ]; then \\
      ./mvnw clean package -DskipTests; \\
    elif [ -f "gradlew" ]; then \\
      ./gradlew build -x test; \\
    else \\
      echo "No build tool found"; exit 1; \\
    fi

# Final stage
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

# Copy JAR from builder
COPY --from=builder /app/target/*.jar app.jar 2>/dev/null || \\
     COPY --from=builder /app/build/libs/*.jar app.jar

# Create non-root user
RUN adduser -D -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \\
  CMD wget --no-verbose --tries=1 --spider http://localhost:{port}/health || exit 1

EXPOSE {port}

# Start command
CMD ["java", "-jar", "app.jar"]
"""


def get_dockerfile_template(language: str) -> str:
    """언어에 맞는 Dockerfile 템플릿 반환"""
    language_lower = language.lower()

    if "python" in language_lower:
        return PYTHON_TEMPLATE
    elif "javascript" in language_lower or "typescript" in language_lower or "node" in language_lower:
        return NODEJS_TEMPLATE
    elif "go" in language_lower or "golang" in language_lower:
        return GO_TEMPLATE
    elif "rust" in language_lower:
        return RUST_TEMPLATE
    elif "java" in language_lower or "kotlin" in language_lower:
        return JAVA_TEMPLATE
    else:
        # 기본: Python 템플릿 사용
        return PYTHON_TEMPLATE
