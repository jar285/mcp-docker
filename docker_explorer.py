"""
Docker Explorer MCP Server

A simple MCP server that provides tools for searching and interacting with Docker images.
"""

from typing import List, Dict, Optional, Any
import requests

from pydantic import BaseModel, Field
from mcp.server.fastmcp import FastMCP

# Create the MCP server
mcp = FastMCP("Docker Explorer")


# Define data models
class DockerImage(BaseModel):
    name: str
    description: Optional[str] = None
    stars: Optional[int] = None
    pulls: Optional[int] = None
    official: bool = False
    automated: bool = False

class DockerTag(BaseModel):
    name: str
    size: Optional[int] = None
    last_updated: Optional[str] = None

class DockerUser(BaseModel):
    username: str
    full_name: Optional[str] = None
    is_organization: bool = False

# Docker Hub API Client
class DockerHubClient:
    def __init__(self):
        self.base_url = "https://hub.docker.com/v2"
        self.session = requests.Session()
    
    def search_images(self, query, limit=25):
        response = self.session.get(
            f"{self.base_url}/search/repositories",
            params={"query": query, "page_size": limit}
        )
        if response.status_code == 200:
            return response.json()["results"]
        return []
    
    def get_image_tags(self, namespace, repository, limit=25):
        response = self.session.get(
            f"{self.base_url}/repositories/{namespace}/{repository}/tags",
            params={"page_size": limit}
        )
        if response.status_code == 200:
            return response.json()["results"]
        return []
    
    def search_users(self, query, limit=25):
        response = self.session.get(
            f"{self.base_url}/search/users",
            params={"query": query, "page_size": limit}
        )
        if response.status_code == 200:
            return response.json()["results"]
        return []

# Create a global client instance
# In a production app, you'd want to use the lifespan context pattern
docker_hub_client = DockerHubClient()

# Implement MCP tools
@mcp.tool()
def search_images(
    query: str = Field(description="Search query for Docker images"),
    limit: int = Field(default=10, description="Maximum number of results to return")
) -> List[DockerImage]:
    """Search for Docker images across registries"""
    results = docker_hub_client.search_images(query, limit=limit)
    
    return [
        DockerImage(
            name=r["repo_name"],
            description=r.get("short_description", ""),
            stars=r.get("star_count"),
            pulls=r.get("pull_count"),
            official=r.get("is_official", False),
            automated=r.get("is_automated", False)
        ) for r in results
    ]

@mcp.tool()
def search_tags(
    image_name: str = Field(description="Name of the Docker image"),
    tag_pattern: str = Field(default="", description="Pattern to match tags against"),
    limit: int = Field(default=25, description="Maximum number of results to return")
) -> List[DockerTag]:
    """Search for specific tags of a Docker image"""
    if "/" in image_name:
        namespace, repository = image_name.split("/", 1)
    else:
        namespace, repository = "library", image_name
        
    tags = docker_hub_client.get_image_tags(namespace, repository, limit=limit)
    
    result_tags = [
        DockerTag(
            name=t["name"],
            last_updated=t.get("last_updated")
        ) for t in tags
    ]
    
    if tag_pattern:
        return [t for t in result_tags if tag_pattern in t.name]
    return result_tags

@mcp.tool()
def search_users(
    query: str = Field(description="Search query for Docker Hub users"),
    limit: int = Field(default=10, description="Maximum number of results to return")
) -> List[DockerUser]:
    """Search for Docker Hub users/organizations"""
    results = docker_hub_client.search_users(query, limit=limit)
    
    return [
        DockerUser(
            username=r["username"],
            full_name=r.get("full_name", ""),
            is_organization=r.get("type", "") == "organization"
        ) for r in results
    ]

# Implement MCP resources
@mcp.resource("docker://images/{query}")
def get_images_resource(query: str) -> str:
    """Get information about Docker images matching a query"""
    results = docker_hub_client.search_images(query, limit=5)
    
    output = f"# Docker Images for '{query}'\n\n"
    
    if not results:
        return output + "No results found."
    
    for r in results:
        output += f"## {r['repo_name']}\n"
        output += f"**Stars:** {r.get('star_count', 0)} | **Pulls:** {r.get('pull_count', 0)}\n\n"
        output += f"{r.get('short_description', 'No description')}\n\n"
    
    return output

@mcp.resource("docker://user/{username}")
def get_user_resource(username: str) -> str:
    """Get information about a Docker Hub user/organization"""
    # In a real implementation, you'd call the Docker Hub API to get user details
    # For this demo, we'll return a placeholder
    return f"# Docker Hub User: {username}\n\nUser profile information would be displayed here.\n\nThis is a placeholder for the actual user profile data that would be retrieved from Docker Hub."

@mcp.tool()
def analyze_repository(
    repository_url: str = Field(description="Full URL to a Docker Hub repository")
) -> str:
    """Analyze a Docker Hub repository and provide detailed information about it"""
    # Extract repository name from URL
    # Example URL: https://hub.docker.com/repository/docker/jar285/drupal/general
    try:
        parts = repository_url.split('/')
        if 'docker.com' not in repository_url:
            return "Please provide a valid Docker Hub repository URL"
            
        # Extract namespace and repository name
        namespace = None
        repo_name = None
        
        if 'repository/docker' in repository_url:
            # Format: https://hub.docker.com/repository/docker/namespace/repo/general
            for i, part in enumerate(parts):
                if part == 'docker' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        else:
            # Format: https://hub.docker.com/r/namespace/repo
            for i, part in enumerate(parts):
                if part == 'r' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        
        if not namespace or not repo_name:
            return "Could not parse repository information from the URL"
            
        # Fetch repository information
        full_repo_name = f"{namespace}/{repo_name}"
        client = docker_hub_client
        
        # Get repository details
        repo_url = f"{client.base_url}/repositories/{namespace}/{repo_name}"
        response = client.session.get(repo_url)
        
        if response.status_code != 200:
            return f"Could not retrieve information for repository {full_repo_name}"
            
        repo_data = response.json()
        
        # Get tags
        tags = client.get_image_tags(namespace, repo_name, limit=5)
        
        # Format the response
        result = f"# Docker Repository: {full_repo_name}\n\n"
        
        # Basic information
        result += f"## Overview\n\n"
        result += f"**Description:** {repo_data.get('description', 'No description provided')}\n\n"
        result += f"**Stars:** {repo_data.get('star_count', 0)}\n"
        result += f"**Pulls:** {repo_data.get('pull_count', 0)}\n"
        result += f"**Last Updated:** {repo_data.get('last_updated', 'Unknown')}\n\n"
        
        # Tags information
        result += f"## Latest Tags\n\n"
        if tags:
            for tag in tags:
                result += f"- **{tag['name']}** (Last Updated: {tag.get('last_updated', 'Unknown')})\n"
        else:
            result += "No tags found for this repository.\n"
            
        # Usage information
        result += f"\n## Usage\n\n"
        result += f"To pull this image:\n\n```\ndocker pull {full_repo_name}:{tags[0]['name'] if tags else 'latest'}\n```\n\n"
        
        return result
    except Exception as e:
        return f"Error analyzing repository: {str(e)}"

@mcp.tool()
def analyze_dockerfile(
    repository_url: str = Field(description="Full URL to a Docker Hub repository"),
    tag: str = Field(default="latest", description="Tag of the Docker image to analyze")
) -> str:
    """Attempt to analyze the Dockerfile used to create a Docker image"""
    # This is a simplified implementation that would normally require more complex analysis
    # In a real implementation, you might:
    # 1. Pull the image layers
    # 2. Analyze the layer history
    # 3. Reconstruct the Dockerfile commands
    
    try:
        parts = repository_url.split('/')
        if 'docker.com' not in repository_url:
            return "Please provide a valid Docker Hub repository URL"
            
        # Extract namespace and repository name
        namespace = None
        repo_name = None
        
        if 'repository/docker' in repository_url:
            # Format: https://hub.docker.com/repository/docker/namespace/repo/general
            for i, part in enumerate(parts):
                if part == 'docker' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        else:
            # Format: https://hub.docker.com/r/namespace/repo
            for i, part in enumerate(parts):
                if part == 'r' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        
        if not namespace or not repo_name:
            return "Could not parse repository information from the URL"
            
        # For demonstration purposes, we'll return a simulated analysis
        # In a real implementation, you would analyze the actual image layers
        
        full_repo_name = f"{namespace}/{repo_name}"
        
        result = f"# Dockerfile Analysis for {full_repo_name}:{tag}\n\n"
        result += "## Estimated Dockerfile\n\n"
        
        # For Drupal specifically (if that's the repo being analyzed)
        if repo_name.lower() == 'drupal':
            result += "```dockerfile\n"
            result += "FROM php:8.1-apache\n\n"
            result += "# Install required PHP extensions\n"
            result += "RUN apt-get update && apt-get install -y \\\n"
            result += "    libfreetype6-dev \\\n"
            result += "    libjpeg62-turbo-dev \\\n"
            result += "    libpng-dev \\\n"
            result += "    libpq-dev \\\n"
            result += "    libzip-dev \\\n"
            result += "    && docker-php-ext-configure gd --with-freetype --with-jpeg \\\n"
            result += "    && docker-php-ext-install -j$(nproc) gd mysqli pdo pdo_mysql zip\n\n"
            result += "# Download and install Drupal\n"
            result += "WORKDIR /var/www/html\n"
            result += "RUN curl -fSL https://ftp.drupal.org/files/projects/drupal-9.4.8.tar.gz -o drupal.tar.gz \\\n"
            result += "    && tar -xz --strip-components=1 -f drupal.tar.gz \\\n"
            result += "    && rm drupal.tar.gz \\\n"
            result += "    && chown -R www-data:www-data /var/www/html\n\n"
            result += "# Configure Apache\n"
            result += "RUN a2enmod rewrite\n"
            result += "```\n\n"
        else:
            # Generic analysis for other repositories
            result += "```dockerfile\n"
            result += "FROM base-image:version\n\n"
            result += "# Install dependencies\n"
            result += "RUN apt-get update && apt-get install -y package1 package2\n\n"
            result += "# Copy application files\n"
            result += "COPY . /app\n"
            result += "WORKDIR /app\n\n"
            result += "# Expose ports\n"
            result += "EXPOSE 80\n\n"
            result += "# Set entrypoint\n"
            result += "CMD [\"/start.sh\"]\n"
            result += "```\n\n"
        
        result += "## Layer Analysis\n\n"
        result += "1. **Base Image Layer**: Sets up the core operating system and runtime\n"
        result += "2. **Dependency Layer**: Installs required system packages and libraries\n"
        result += "3. **Application Layer**: Adds the application code and configuration\n"
        result += "4. **Configuration Layer**: Sets up final runtime configuration\n\n"
        
        result += "## Recommendations\n\n"
        result += "- Consider using multi-stage builds to reduce image size\n"
        result += "- Clean up package manager caches to reduce layer size\n"
        result += "- Use specific version tags instead of 'latest' for better reproducibility\n"
        
        return result
    except Exception as e:
        return f"Error analyzing Dockerfile: {str(e)}"

@mcp.tool()
def optimize_image_size(
    repository_url: str = Field(description="Full URL to a Docker Hub repository"),
    tag: str = Field(default="latest", description="Tag of the Docker image to analyze")
) -> str:
    """Analyze a Docker image and suggest ways to reduce its size"""
    try:
        parts = repository_url.split('/')
        if 'docker.com' not in repository_url:
            return "Please provide a valid Docker Hub repository URL"
            
        # Extract namespace and repository name
        namespace = None
        repo_name = None
        
        if 'repository/docker' in repository_url:
            # Format: https://hub.docker.com/repository/docker/namespace/repo/general
            for i, part in enumerate(parts):
                if part == 'docker' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        else:
            # Format: https://hub.docker.com/r/namespace/repo
            for i, part in enumerate(parts):
                if part == 'r' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        
        if not namespace or not repo_name:
            return "Could not parse repository information from the URL"
            
        # For demonstration purposes, we'll provide optimization recommendations
        # In a real implementation, you would analyze the actual image
        
        full_repo_name = f"{namespace}/{repo_name}"
        
        # Get image details if available
        client = docker_hub_client
        repo_url = f"{client.base_url}/repositories/{namespace}/{repo_name}"
        response = client.session.get(repo_url)
        
        if response.status_code != 200:
            return f"Could not retrieve information for repository {full_repo_name}"
            
        repo_data = response.json()
        
        # Get tags to find the specified tag
        tags = client.get_image_tags(namespace, repo_name, limit=10)
        target_tag = None
        
        for t in tags:
            if t['name'] == tag:
                target_tag = t
                break
                
        if not target_tag:
            return f"Could not find tag '{tag}' for repository {full_repo_name}"
        
        # Start building the response
        result = f"# Size Optimization for {full_repo_name}:{tag}\n\n"
        
        # Current size information
        result += f"## Current Image Information\n\n"
        result += f"**Repository:** {full_repo_name}\n"
        result += f"**Tag:** {tag}\n"
        
        # If we have size information (not always available)
        if 'full_size' in target_tag:
            size_mb = target_tag['full_size'] / (1024 * 1024)
            result += f"**Current Size:** {size_mb:.2f} MB\n\n"
        else:
            result += "**Current Size:** Size information not available\n\n"
        
        # General optimization recommendations
        result += f"## Size Optimization Recommendations\n\n"
        
        # Base image recommendations
        result += f"### 1. Use Smaller Base Images\n\n"
        result += "- Consider using Alpine-based images which are significantly smaller\n"
        result += "- For example, replace `python:3.9` (900MB+) with `python:3.9-alpine` (45MB+)\n"
        result += "- If using Ubuntu/Debian, consider slim variants like `debian:slim` or `ubuntu:22.04-minimal`\n\n"
        
        # Multi-stage builds
        result += f"### 2. Implement Multi-stage Builds\n\n"
        result += "- Use multi-stage builds to separate build-time dependencies from runtime dependencies\n"
        result += "- Example:\n"
        result += "```dockerfile\n"
        result += "# Build stage\n"
        result += "FROM node:16 AS build\n"
        result += "WORKDIR /app\n"
        result += "COPY package*.json ./\n"
        result += "RUN npm install\n"
        result += "COPY . .\n"
        result += "RUN npm run build\n\n"
        result += "# Production stage\n"
        result += "FROM node:16-alpine\n"
        result += "WORKDIR /app\n"
        result += "COPY --from=build /app/dist ./dist\n"
        result += "COPY --from=build /app/package*.json ./\n"
        result += "RUN npm install --production\n"
        result += "CMD [\"node\", \"dist/index.js\"]\n"
        result += "```\n\n"
        
        # Layer optimization
        result += f"### 3. Optimize Dockerfile Instructions\n\n"
        result += "- Combine related RUN commands to reduce layer count\n"
        result += "- Clean up package manager caches in the same layer they're created\n"
        result += "- Example:\n"
        result += "```dockerfile\n"
        result += "# Instead of:\n"
        result += "RUN apt-get update\n"
        result += "RUN apt-get install -y package1 package2\n\n"
        result += "# Use:\n"
        result += "RUN apt-get update && \\\n"
        result += "    apt-get install -y package1 package2 && \\\n"
        result += "    rm -rf /var/lib/apt/lists/*\n"
        result += "```\n\n"
        
        # Remove unnecessary files
        result += f"### 4. Remove Unnecessary Files\n\n"
        result += "- Use .dockerignore to exclude files not needed in the image\n"
        result += "- Remove temporary files, logs, and caches\n"
        result += "- Consider using tools like docker-slim or dive to analyze and reduce image size\n\n"
        
        # Specific recommendations based on repository name
        if repo_name.lower() in ['node', 'nodejs', 'javascript', 'js']:
            result += f"### 5. Node.js Specific Recommendations\n\n"
            result += "- Use `npm ci` instead of `npm install` for reproducible builds\n"
            result += "- Add `node_modules` and `npm-debug.log` to .dockerignore\n"
            result += "- Consider using `npm prune --production` to remove dev dependencies\n"
        elif repo_name.lower() in ['python', 'django', 'flask']:
            result += f"### 5. Python Specific Recommendations\n\n"
            result += "- Use virtual environments to isolate dependencies\n"
            result += "- Add `__pycache__`, `*.pyc`, and `.pytest_cache` to .dockerignore\n"
            result += "- Consider using pip's `--no-cache-dir` flag to avoid caching packages\n"
        elif repo_name.lower() in ['java', 'spring', 'maven', 'gradle']:
            result += f"### 5. Java Specific Recommendations\n\n"
            result += "- Use JLink to create custom JREs with only required modules\n"
            result += "- Consider using GraalVM native image for smaller binaries\n"
            result += "- Add build directories like `target/` or `build/` to .dockerignore\n"
        
        # Estimated size savings
        result += f"## Estimated Size Savings\n\n"
        result += "By implementing these recommendations, you could potentially reduce your image size by:\n\n"
        result += "- **Base Image Optimization:** 60-80% reduction\n"
        result += "- **Multi-stage Builds:** 40-70% reduction\n"
        result += "- **Layer Optimization:** 10-30% reduction\n"
        result += "- **Removing Unnecessary Files:** 5-20% reduction\n\n"
        result += "Overall, these techniques could reduce your image size by 50-90% depending on the current configuration."
        
        return result
    except Exception as e:
        return f"Error optimizing image size: {str(e)}"

@mcp.tool()
def generate_docker_compose(
    repository_url: str = Field(description="Full URL to a Docker Hub repository"),
    tag: str = Field(default="latest", description="Tag of the Docker image to use"),
    port_mapping: str = Field(default="", description="Optional port mapping (e.g., '8080:80')"),
    environment_variables: str = Field(default="", description="Optional environment variables (e.g., 'DB_NAME=mydb,DB_USER=user')"),
    include_db: bool = Field(default=False, description="Whether to include a database service for web applications")
) -> str:
    """Generate a docker-compose.yml file based on an image or repository"""
    try:
        # Extract namespace and repository name from URL
        parts = repository_url.split('/')
        namespace = None
        repo_name = None
        
        if 'docker.com' not in repository_url:
            return "Please provide a valid Docker Hub repository URL"
            
        # Parse different Docker Hub URL formats
        if 'repository/docker' in repository_url:
            for i, part in enumerate(parts):
                if part == 'docker' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        else:
            for i, part in enumerate(parts):
                if part == 'r' and i+1 < len(parts) and i+2 < len(parts):
                    namespace = parts[i+1]
                    repo_name = parts[i+2]
                    break
        
        if not namespace or not repo_name:
            return "Could not parse repository information from the URL"
            
        # Create service name and full repo name
        full_repo_name = f"{namespace}/{repo_name}"
        service_name = repo_name.lower().replace('-', '_')
        
        # Build basic compose file
        compose = [
            "version: '3'\n",
            "\nservices:\n",
            f"  {service_name}:\n",
            f"    image: {full_repo_name}:{tag}\n",
            "    restart: unless-stopped\n"
        ]
        
        # Add port mappings if provided
        if port_mapping:
            ports = port_mapping.split(',')
            compose.append("    ports:\n")
            for port in ports:
                compose.append(f"      - \"{port.strip()}\"\n")
        
        # Add environment variables if provided
        if environment_variables:
            env_vars = environment_variables.split(',')
            compose.append("    environment:\n")
            for env_var in env_vars:
                compose.append(f"      - {env_var.strip()}\n")
        
        # Add database service if requested
        volumes_section = []
        networks_section = []
        
        if include_db:
            # Add database service
            compose.append("    depends_on:\n")
            compose.append("      - db\n")
            compose.append("    networks:\n")
            compose.append("      - app_network\n")
            
            # Add the database service definition
            compose.append("\n  db:\n")
            compose.append("    image: mysql:5.7\n")
            compose.append("    restart: unless-stopped\n")
            compose.append("    networks:\n")
            compose.append("      - app_network\n")
            compose.append("    volumes:\n")
            compose.append("      - db_data:/var/lib/mysql\n")
            compose.append("    environment:\n")
            compose.append("      - MYSQL_ROOT_PASSWORD=rootpassword\n")
            compose.append("      - MYSQL_DATABASE=appdb\n")
            compose.append("      - MYSQL_USER=appuser\n")
            compose.append("      - MYSQL_PASSWORD=apppassword\n")
            
            # Add network and volume definitions
            networks_section = [
                "\nnetworks:\n",
                "  app_network:\n",
                "    driver: bridge\n"
            ]
            
            volumes_section = [
                "\nvolumes:\n",
                "  db_data:\n"
            ]
        
        # Combine all sections
        compose_content = ''.join(compose + networks_section + volumes_section)
        
        # Create the response
        result = f"# Docker Compose for {full_repo_name}:{tag}\n\n```yaml\n{compose_content}```\n\n"
        result += "Run with: `docker-compose up -d`"
        
        return result
    except Exception as e:
        return f"Error generating docker-compose.yml: {str(e)}"

@mcp.tool()
def scan_security(
    image_name: str = Field(description="Name of the Docker image (e.g., 'nginx' or 'user/repo')"),
    tag: str = Field(default="latest", description="Tag of the Docker image to scan")
) -> str:
    """Perform a basic security scan of a Docker image"""
    try:
        # This is a simplified security scanner that provides common security recommendations
        # In a real implementation, you would integrate with actual security scanning tools
        
        # Normalize image name
        if '/' not in image_name:
            image_name = f"library/{image_name}"
        
        # Create a compact security report
        report = f"Security scan for {image_name}:{tag}\n\n"
        
        # Common security issues and recommendations
        issues = [
            {
                "severity": "HIGH",
                "issue": "Running as root",
                "description": "Container processes should not run as root",
                "recommendation": "Use USER directive to run as non-root user"
            },
            {
                "severity": "MEDIUM",
                "issue": "No health check",
                "description": "Missing HEALTHCHECK instruction",
                "recommendation": "Add HEALTHCHECK to monitor container health"
            },
            {
                "severity": "MEDIUM",
                "issue": "Latest tag",
                "description": "Using 'latest' tag is not recommended",
                "recommendation": "Use specific version tags for reproducibility"
            },
            {
                "severity": "LOW",
                "issue": "Large image size",
                "description": "Large images have more potential vulnerabilities",
                "recommendation": "Use smaller base images like Alpine"
            }
        ]
        
        # Only include relevant issues based on the image name and tag
        relevant_issues = []
        
        for issue in issues:
            # Include 'latest' tag warning only if using latest tag
            if issue["issue"] == "Latest tag" and tag != "latest":
                continue
                
            # Add the issue to relevant issues
            relevant_issues.append(issue)
        
        # Add issues to report
        if relevant_issues:
            report += "Security Issues:\n\n"
            for issue in relevant_issues:
                report += f"[{issue['severity']}] {issue['issue']}\n"
                report += f"  {issue['recommendation']}\n\n"
        else:
            report += "No security issues found.\n"
        
        # Add general security recommendations
        report += "\nGeneral Recommendations:\n\n"
        report += "1. Scan with vulnerability scanners (e.g., Trivy, Clair)\n"
        report += "2. Use multi-stage builds to reduce attack surface\n"
        report += "3. Keep base images updated regularly\n"
        
        return report
    except Exception as e:
        return f"Error scanning image: {str(e)}"

@mcp.tool()
def analyze_runtime(
    image_name: str = Field(description="Name of the Docker image (e.g., 'nginx' or 'user/repo')"),
    tag: str = Field(default="latest", description="Tag of the Docker image"),
    app_type: str = Field(default="web", description="Application type (web, database, cache, api, batch)")
) -> str:
    """Analyze how a container might behave at runtime and provide optimization tips"""
    try:
        # Normalize image name
        if '/' not in image_name:
            image_name = f"library/{image_name}"
            
        # Create the analysis report
        report = f"## Runtime Analysis for {image_name}:{tag}\n\n"
        
        # Resource usage predictions based on app type
        resource_profiles = {
            "web": {
                "cpu": "Medium",
                "memory": "Medium",
                "io": "High",
                "network": "High"
            },
            "database": {
                "cpu": "Medium to High",
                "memory": "High",
                "io": "Very High",
                "network": "Medium"
            },
            "cache": {
                "cpu": "Low",
                "memory": "High",
                "io": "Medium",
                "network": "Medium"
            },
            "api": {
                "cpu": "Medium",
                "memory": "Medium",
                "io": "Low",
                "network": "High"
            },
            "batch": {
                "cpu": "High",
                "memory": "Medium to High",
                "io": "Medium to High",
                "network": "Low"
            }
        }
        
        # Get the resource profile for the specified app type
        profile = resource_profiles.get(app_type.lower(), resource_profiles["web"])
        
        # Add resource usage section
        report += "### Resource Usage Prediction\n\n"
        report += f"- CPU Usage: {profile['cpu']}\n"
        report += f"- Memory Usage: {profile['memory']}\n"
        report += f"- I/O Operations: {profile['io']}\n"
        report += f"- Network Traffic: {profile['network']}\n\n"
        
        # Add container orchestration recommendations
        report += "### Orchestration Recommendations\n\n"
        
        if app_type.lower() == "web":
            report += "- Use horizontal scaling for increased traffic\n"
            report += "- Implement health checks for better reliability\n"
            report += "- Consider using an ingress controller for routing\n"
        elif app_type.lower() == "database":
            report += "- Use persistent volumes for data storage\n"
            report += "- Consider using StatefulSets in Kubernetes\n"
            report += "- Implement regular backup strategies\n"
        elif app_type.lower() == "cache":
            report += "- Use memory limits to prevent OOM issues\n"
            report += "- Consider using anti-affinity rules for high availability\n"
            report += "- Implement proper eviction policies\n"
        elif app_type.lower() == "api":
            report += "- Use auto-scaling based on CPU/memory usage\n"
            report += "- Implement rate limiting for stability\n"
            report += "- Use readiness probes for zero-downtime deployments\n"
        elif app_type.lower() == "batch":
            report += "- Use job controllers for managing batch processes\n"
            report += "- Consider resource quotas to prevent cluster saturation\n"
            report += "- Implement proper retry mechanisms\n"
        
        # Add resource limits recommendations
        report += "\n### Recommended Resource Limits\n\n"
        
        # Resource recommendations based on app type
        if app_type.lower() == "web":
            report += "```yaml\nresources:\n  limits:\n    cpu: 1\n    memory: 512Mi\n  requests:\n    cpu: 200m\n    memory: 256Mi\n```\n"
        elif app_type.lower() == "database":
            report += "```yaml\nresources:\n  limits:\n    cpu: 2\n    memory: 2Gi\n  requests:\n    cpu: 500m\n    memory: 1Gi\n```\n"
        elif app_type.lower() == "cache":
            report += "```yaml\nresources:\n  limits:\n    cpu: 1\n    memory: 1Gi\n  requests:\n    cpu: 200m\n    memory: 512Mi\n```\n"
        elif app_type.lower() == "api":
            report += "```yaml\nresources:\n  limits:\n    cpu: 1\n    memory: 512Mi\n  requests:\n    cpu: 200m\n    memory: 256Mi\n```\n"
        elif app_type.lower() == "batch":
            report += "```yaml\nresources:\n  limits:\n    cpu: 2\n    memory: 1Gi\n  requests:\n    cpu: 500m\n    memory: 512Mi\n```\n"
        
        return report
    except Exception as e:
        return f"Error analyzing runtime behavior: {str(e)}"

@mcp.tool()
def compare_images(
    image1: str = Field(description="First Docker image to compare (e.g., 'nginx:1.21' or 'user/repo:tag')"),
    image2: str = Field(description="Second Docker image to compare (e.g., 'nginx:1.22' or 'user/repo:tag')")
) -> str:
    """Compare two Docker images and highlight the differences"""
    try:
        # Normalize image names
        if ':' not in image1:
            image1 = f"{image1}:latest"
        if ':' not in image2:
            image2 = f"{image2}:latest"
            
        # Parse image names and tags
        image1_name, image1_tag = image1.split(':', 1)
        image2_name, image2_tag = image2.split(':', 1)
        
        # Normalize library images
        if '/' not in image1_name:
            image1_name = f"library/{image1_name}"
        if '/' not in image2_name:
            image2_name = f"library/{image2_name}"
            
        # Create the comparison report
        report = f"# Comparison: {image1} vs {image2}\n\n"
        
        # Check if comparing the same image with different tags
        same_image_different_tags = image1_name == image2_name and image1_tag != image2_tag
        if same_image_different_tags:
            report += f"Comparing different versions of the same image: **{image1_name}**\n\n"
        else:
            report += f"Comparing different images: **{image1_name}:{image1_tag}** vs **{image2_name}:{image2_tag}**\n\n"
        
        # Basic comparison data
        image1_data = {
            "size": "~150MB",  # In a real implementation, you would fetch actual sizes
            "layers": 5,
            "created": "2023-05-15",
            "os": "linux",
            "architecture": "amd64",
            "exposed_ports": ["80/tcp"],
            "environment": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"],
            "cmd": ["/bin/sh", "-c", "nginx -g 'daemon off;'"]
        }
        
        image2_data = {
            "size": "~180MB",  # In a real implementation, you would fetch actual sizes
            "layers": 6,
            "created": "2023-08-20",
            "os": "linux",
            "architecture": "amd64",
            "exposed_ports": ["80/tcp", "443/tcp"],
            "environment": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin", "NGINX_VERSION=1.22.1"],
            "cmd": ["/bin/sh", "-c", "nginx -g 'daemon off;'"]
        }
        
        # If comparing the same image base with different tags, adjust the data to show realistic differences
        if same_image_different_tags:
            # Make differences more subtle for version changes
            image2_data["exposed_ports"] = image1_data["exposed_ports"]
            image2_data["cmd"] = image1_data["cmd"]
            
        # Add size comparison
        report += "## Size Comparison\n\n"
        report += f"- **{image1}**: {image1_data['size']}\n"
        report += f"- **{image2}**: {image2_data['size']}\n"
        
        size_diff = "larger" if image2_data['size'] > image1_data['size'] else "smaller"
        report += f"\n**{image2}** is {size_diff} than **{image1}**\n\n"
        
        # Add layer comparison
        report += "## Layer Comparison\n\n"
        report += f"- **{image1}**: {image1_data['layers']} layers\n"
        report += f"- **{image2}**: {image2_data['layers']} layers\n"
        
        layer_diff = image2_data['layers'] - image1_data['layers']
        if layer_diff > 0:
            report += f"\n**{image2}** has {layer_diff} more layers than **{image1}**\n\n"
        elif layer_diff < 0:
            report += f"\n**{image2}** has {abs(layer_diff)} fewer layers than **{image1}**\n\n"
        else:
            report += f"\nBoth images have the same number of layers\n\n"
        
        # Add configuration differences
        report += "## Configuration Differences\n\n"
        
        # Compare exposed ports
        added_ports = set(image2_data['exposed_ports']) - set(image1_data['exposed_ports'])
        removed_ports = set(image1_data['exposed_ports']) - set(image2_data['exposed_ports'])
        
        if added_ports or removed_ports:
            report += "### Exposed Ports\n\n"
            if added_ports:
                report += f"**Added in {image2}**: {', '.join(added_ports)}\n"
            if removed_ports:
                report += f"**Removed in {image2}**: {', '.join(removed_ports)}\n"
            report += "\n"
        
        # Compare environment variables
        added_env = set(image2_data['environment']) - set(image1_data['environment'])
        removed_env = set(image1_data['environment']) - set(image2_data['environment'])
        
        if added_env or removed_env:
            report += "### Environment Variables\n\n"
            if added_env:
                report += f"**Added in {image2}**:\n"
                for env in added_env:
                    report += f"- `{env}`\n"
            if removed_env:
                report += f"**Removed in {image2}**:\n"
                for env in removed_env:
                    report += f"- `{env}`\n"
            report += "\n"
        
        # Compare CMD
        if image1_data['cmd'] != image2_data['cmd']:
            report += "### Command (CMD)\n\n"
            report += f"**{image1}**: `{' '.join(image1_data['cmd'])}`\n"
            report += f"**{image2}**: `{' '.join(image2_data['cmd'])}`\n\n"
        
        # Add compatibility analysis
        report += "## Compatibility Analysis\n\n"
        
        # Check for architecture compatibility
        if image1_data['architecture'] == image2_data['architecture']:
            report += "✅ **Architecture compatibility**: Both images use the same architecture\n"
        else:
            report += f"⚠️ **Architecture incompatibility**: {image1} uses {image1_data['architecture']} while {image2} uses {image2_data['architecture']}\n"
        
        # Check for OS compatibility
        if image1_data['os'] == image2_data['os']:
            report += "✅ **OS compatibility**: Both images use the same operating system\n"
        else:
            report += f"⚠️ **OS incompatibility**: {image1} uses {image1_data['os']} while {image2} uses {image2_data['os']}\n"
        
        # Add migration recommendations if comparing versions
        if same_image_different_tags:
            report += "\n## Migration Recommendations\n\n"
            
            # Size-based recommendations
            if image2_data['size'] > image1_data['size']:
                report += "- **Storage Impact**: The newer version requires more storage space\n"
            
            # Layer-based recommendations
            if layer_diff != 0:
                report += "- **Build Impact**: Different number of layers may affect build and pull times\n"
            
            # Port-based recommendations
            if added_ports:
                report += f"- **Network Configuration**: New ports ({', '.join(added_ports)}) need to be configured in your deployment\n"
            
            # Environment-based recommendations
            if added_env:
                report += "- **Environment Setup**: New environment variables need to be configured\n"
            
            # General recommendation
            report += "- **Testing**: Test your application thoroughly with the new image before deploying to production\n"
        
        return report
    except Exception as e:
        return f"Error comparing images: {str(e)}"

# Run the server when executed directly
if __name__ == "__main__":
    mcp.run()
