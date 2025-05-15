# 🛠️ Docker Explorer MCP Server Tool Examples

This document provides examples of how to use each tool in the Docker Explorer MCP server with Claude Desktop.

## Core Tools

### 1. Search for Docker Images

**Example Query:**
```
Can you search for Python Docker images?
```

**Expected Response:**
Claude will return a list of popular Python Docker images with brief descriptions.

### 2. Search for Image Tags

**Example Query:**
```
What tags are available for the nginx image?
```

**Expected Response:**
Claude will return a list of available tags for the nginx image, such as latest, stable, alpine, etc.

### 3. Get Image Details

**Example Query:**
```
What are the details of the python:3.11-slim image?
```

**Expected Response:**
Claude will provide detailed information about the image, including size, layers, architecture, and other metadata.

## Advanced Tools

### 4. Security Scanner Tool

**Example Query:**
```
Scan the security of the nginx image
```
or
```
Check for security issues in the node:14 image
```

**Expected Response:**
Claude will analyze the image and provide a security report with identified issues categorized by severity (HIGH, MEDIUM, LOW) and recommendations for addressing them.

**Sample Output:**
```
Security scan for library/nginx:latest

Security Issues:

[HIGH] Running as root
  Use USER directive to run as non-root user

[MEDIUM] No health check
  Add HEALTHCHECK to monitor container health

[MEDIUM] Latest tag
  Use specific version tags for reproducibility

[LOW] Large image size
  Use smaller base images like Alpine

General Recommendations:

1. Scan with vulnerability scanners (e.g., Trivy, Clair)
2. Use multi-stage builds to reduce attack surface
3. Keep base images updated regularly
```

### 5. Image Size Optimizer

**Example Query:**
```
How can I reduce the size of my python:3.9 image?
```
or
```
Optimize the size of https://hub.docker.com/repository/docker/jar285/drupal/general
```

**Expected Response:**
Claude will provide recommendations for reducing the image size, including using smaller base images, multi-stage builds, and cleaning up unnecessary files.

**Sample Output:**
```
# Size Optimization for jar285/drupal:latest

## Current Image Analysis
Base image: jar285/drupal:latest
Estimated size: ~500MB

## Optimization Recommendations

1. Use a smaller base image
   - Consider using MySQL on Alpine Linux
   - Potential size reduction: ~30%

2. Implement multi-stage builds
   - Use a build stage for compilation and a runtime stage for deployment
   - Example Dockerfile section:
     ```dockerfile
     FROM mysql:latest AS builder
     # Build steps here
     
     FROM alpine:latest
     # Copy only necessary files from builder
     COPY --from=builder /usr/bin/mysql /usr/bin/mysql
     ```

3. Clean up package manager caches
   - Add this to your Dockerfile:
     ```dockerfile
     RUN apt-get clean && \
         rm -rf /var/lib/apt/lists/*
     ```

4. Remove unnecessary tools and documentation
   - Identify and remove development packages not needed at runtime

5. Use .dockerignore file
   - Exclude unnecessary files from the build context
```

### 6. Docker Compose Generator

**Example Query:**
```
Generate a docker-compose file for nginx with port 8080:80
```
or
```
Create a docker-compose.yml for https://hub.docker.com/repository/docker/jar285/drupal/general with port mapping 8080:80 and include a database
```

**Expected Response:**
Claude will generate a docker-compose.yml file with the specified configuration.

**Sample Output:**
```
# Docker Compose for jar285/drupal:latest

```yaml
version: '3'

services:
  drupal:
    image: jar285/drupal:latest
    restart: unless-stopped
    ports:
      - "8080:80"
    depends_on:
      - db
    networks:
      - app_network

  db:
    image: mysql:5.7
    restart: unless-stopped
    networks:
      - app_network
    volumes:
      - db_data:/var/lib/mysql
    environment:
      - MYSQL_ROOT_PASSWORD=rootpassword
      - MYSQL_DATABASE=drupal
      - MYSQL_USER=drupal
      - MYSQL_PASSWORD=drupal

networks:
  app_network:
    driver: bridge

volumes:
  db_data:
```

Run with: `docker-compose up -d`
```

### 7. Container Runtime Analyzer

**Example Query:**
```
Analyze the runtime behavior of mysql:5.7 as a database
```
or
```
What are the runtime characteristics of jar285/drupal as a web application?
```

**Expected Response:**
Claude will provide an analysis of how the container might behave at runtime, including resource usage predictions and orchestration recommendations.

### 8. Image Comparison Tool

**Example Query:**
```
Compare nginx:1.21 and nginx:1.22 images
```
or
```
What are the differences between jar285/drupal:latest and jar285/drupal:9.4?
```

**Expected Response:**
Claude will provide a detailed comparison of the two Docker images, highlighting differences in size, layers, configuration, and compatibility.

### 9. Dockerfile Generator

**Example Query:**
```
Generate a Dockerfile for a Python Flask web app with Redis caching
```
or
```
Create a Dockerfile for a Node.js Express API that connects to MongoDB
```

**Expected Response:**
Claude will generate a complete Dockerfile tailored to the application requirements, with appropriate base image, dependencies, configuration, and best practices.

**Sample Output:**
```
# Dockerfile for Python Flask web app with Redis caching

```dockerfile
# Dockerfile for python flask web app with redis caching
# Generated by Docker Explorer MCP Server

FROM python:3.11-slim

# Set metadata
LABEL maintainer="Docker Explorer User <user@example.com>"

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user for security
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
USER appuser

# Expose port 5000 for the application
EXPOSE 5000

# Add healthcheck to verify the application is running
HEALTHCHECK --interval=30s --timeout=3s CMD curl -f http://localhost:${PORT:-8080}/health || exit 1

# Command to run the application
CMD ["python", "app.py"]

# Notes:
# - This Dockerfile is a starting point and may need adjustments for your specific application
# - For redis caching, ensure your application is configured to connect to it
# - For production, consider using multi-stage builds to reduce image size
```

## Usage Instructions

1. Save the above content to a file named `Dockerfile` in your project directory
2. Build the Docker image:

```bash
docker build -t your-app-name .
```

3. Run the container:

```bash
docker run -p 5000:5000 your-app-name
```
```

**Sample Output for Image Comparison:**
```
# Comparison: nginx:1.21 vs nginx:1.22

Comparing different versions of the same image: **library/nginx**

## Size Comparison

- **nginx:1.21**: ~150MB
- **nginx:1.22**: ~180MB

**nginx:1.22** is larger than **nginx:1.21**

## Layer Comparison

- **nginx:1.21**: 5 layers
- **nginx:1.22**: 6 layers

**nginx:1.22** has 1 more layers than **nginx:1.21**

## Configuration Differences

### Environment Variables

**Added in nginx:1.22**:
- `NGINX_VERSION=1.22.1`

## Compatibility Analysis

✅ **Architecture compatibility**: Both images use the same architecture
✅ **OS compatibility**: Both images use the same operating system

## Migration Recommendations

- **Storage Impact**: The newer version requires more storage space
- **Build Impact**: Different number of layers may affect build and pull times
- **Environment Setup**: New environment variables need to be configured
- **Testing**: Test your application thoroughly with the new image before deploying to production
```

**Sample Output for Container Runtime Analysis:**
```
## Runtime Analysis for library/mysql:5.7

### Resource Usage Prediction

- CPU Usage: Medium to High
- Memory Usage: High
- I/O Operations: Very High
- Network Traffic: Medium

### Orchestration Recommendations

- Use persistent volumes for data storage
- Consider using StatefulSets in Kubernetes
- Implement regular backup strategies

### Recommended Resource Limits

```yaml
resources:
  limits:
    cpu: 2
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi
```
```

## Tips for Using the Tools

1. **Be Specific**: When asking Claude to use a tool, be specific about what you want to analyze or generate.

2. **Combine Tools**: You can ask Claude to use multiple tools in sequence. For example:
   ```
   Can you scan the security of the nginx:alpine image and then analyze its runtime behavior as a web application?
   ```

3. **Provide Context**: When using tools like the Docker Compose Generator, provide as much context as possible about your requirements.

4. **Ask for Explanations**: If you don't understand a recommendation or analysis, ask Claude to explain it in more detail.

5. **Iterative Refinement**: Use the tools iteratively to refine your Docker configurations and improve your containerization practices.
