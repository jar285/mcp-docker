# Docker MCP Server Technical Specification

## Architecture Overview

The Docker MCP Server will be built using the MCP Python SDK, which provides a standardized way for applications to expose context and tools to LLMs. Our implementation will focus on creating a server that provides Docker-related functionality through resources and tools.

## Server Implementation

### Core Components

```python
# server.py
from mcp.server.fastmcp import FastMCP, Context
import docker
import requests
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

# Create the MCP server
mcp = FastMCP(
    "Docker Explorer",
    dependencies=[
        "docker",
        "requests",
        "pydantic",
    ]
)
```

### Data Models

```python
class DockerImage(BaseModel):
    name: str
    tag: str
    description: Optional[str] = None
    stars: Optional[int] = None
    pulls: Optional[int] = None
    last_updated: Optional[str] = None
    size: Optional[int] = None

class DockerUser(BaseModel):
    username: str
    full_name: Optional[str] = None
    location: Optional[str] = None
    company: Optional[str] = None
    image_count: Optional[int] = None
    is_organization: bool = False

class DockerfileInfo(BaseModel):
    repo: str
    path: str
    content: str
    size: int
    last_updated: Optional[str] = None

class ImageLayer(BaseModel):
    digest: str
    size: int
    command: Optional[str] = None

class ImageDetail(BaseModel):
    name: str
    tag: str
    digest: str
    architecture: str
    os: str
    layers: List[ImageLayer]
    created: str
    total_size: int
    labels: Dict[str, str] = Field(default_factory=dict)
```

## API Integration

### Docker Hub API Client

```python
class DockerHubClient:
    def __init__(self, username=None, password=None):
        self.base_url = "https://hub.docker.com/v2"
        self.session = requests.Session()
        self.token = None
        if username and password:
            self.login(username, password)
    
    def login(self, username, password):
        response = self.session.post(
            f"{self.base_url}/users/login",
            json={"username": username, "password": password}
        )
        if response.status_code == 200:
            self.token = response.json()["token"]
            self.session.headers.update({"Authorization": f"JWT {self.token}"})
            return True
        return False
    
    def search_images(self, query, limit=25):
        response = self.session.get(
            f"{self.base_url}/search/repositories",
            params={"query": query, "page_size": limit}
        )
        return response.json()["results"]
    
    def get_image_tags(self, namespace, repository, limit=25):
        response = self.session.get(
            f"{self.base_url}/repositories/{namespace}/{repository}/tags",
            params={"page_size": limit}
        )
        return response.json()["results"]
    
    def search_users(self, query, limit=25):
        response = self.session.get(
            f"{self.base_url}/search/users",
            params={"query": query, "page_size": limit}
        )
        return response.json()["results"]
```

### Docker Registry API Client

```python
class DockerRegistryClient:
    def __init__(self, registry_url="https://registry-1.docker.io"):
        self.registry_url = registry_url
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/vnd.docker.distribution.manifest.v2+json"
        })
    
    def get_manifest(self, repository, reference):
        # Handle Docker Hub's namespace requirement
        if "/" not in repository:
            repository = f"library/{repository}"
            
        response = self.session.get(
            f"{self.registry_url}/v2/{repository}/manifests/{reference}"
        )
        return response.json()
    
    def get_image_layers(self, repository, reference):
        manifest = self.get_manifest(repository, reference)
        return manifest.get("layers", [])
```

## MCP Tools Implementation

### Search Tools

```python
@mcp.tool()
def search_images(
    query: str = Field(description="Search query for Docker images"),
    registry: str = Field(default="docker.io", description="Registry to search (default: Docker Hub)"),
    limit: int = Field(default=10, description="Maximum number of results to return")
) -> List[DockerImage]:
    """Search for Docker images across registries"""
    client = DockerHubClient()
    results = client.search_images(query, limit=limit)
    
    return [
        DockerImage(
            name=r["repo_name"],
            tag="latest",
            description=r.get("short_description", ""),
            stars=r.get("star_count"),
            pulls=r.get("pull_count"),
        ) for r in results
    ]

@mcp.tool()
def search_tags(
    image_name: str = Field(description="Name of the Docker image"),
    tag_pattern: str = Field(default="", description="Pattern to match tags against")
) -> List[str]:
    """Search for specific tags of a Docker image"""
    if "/" in image_name:
        namespace, repository = image_name.split("/", 1)
    else:
        namespace, repository = "library", image_name
        
    client = DockerHubClient()
    tags = client.get_image_tags(namespace, repository)
    
    if tag_pattern:
        tags = [t for t in tags if tag_pattern in t["name"]]
        
    return [t["name"] for t in tags]

@mcp.tool()
def get_image_details(
    image_name: str = Field(description="Name of the Docker image"),
    tag: str = Field(default="latest", description="Tag of the Docker image")
) -> ImageDetail:
    """Get detailed information about a Docker image"""
    registry_client = DockerRegistryClient()
    
    # Get manifest
    if "/" in image_name:
        repository = image_name
    else:
        repository = f"library/{image_name}"
        
    manifest = registry_client.get_manifest(repository, tag)
    config = manifest.get("config", {})
    layers = manifest.get("layers", [])
    
    # Calculate total size
    total_size = sum(layer.get("size", 0) for layer in layers)
    
    # Convert layers to our model
    layer_models = [
        ImageLayer(
            digest=layer.get("digest", ""),
            size=layer.get("size", 0)
        ) for layer in layers
    ]
    
    return ImageDetail(
        name=image_name,
        tag=tag,
        digest=manifest.get("config", {}).get("digest", ""),
        architecture="amd64",  # Would need to extract from config
        os="linux",  # Would need to extract from config
        layers=layer_models,
        created="",  # Would need to extract from config
        total_size=total_size,
        labels={}
    )
```

## Resources Implementation

```python
@mcp.resource("docker://images/{query}")
def get_images_resource(query: str) -> str:
    """Get information about Docker images matching a query"""
    client = DockerHubClient()
    results = client.search_images(query, limit=5)
    
    output = f"# Docker Images for '{query}'

"
    for r in results:
        output += f"## {r['repo_name']}\n"
        output += f"**Stars:** {r.get('star_count', 0)} | **Pulls:** {r.get('pull_count', 0)}\n\n"
        output += f"{r.get('short_description', 'No description')}\n\n"
    
    return output

@mcp.resource("docker://image/{name}/{tag}")
def get_image_resource(name: str, tag: str) -> str:
    """Get detailed information about a specific Docker image and tag"""
    registry_client = DockerRegistryClient()
    
    # Handle Docker Hub's namespace requirement
    if "/" in name:
        repository = name
    else:
        repository = f"library/{name}"
        
    try:
        manifest = registry_client.get_manifest(repository, tag)
        layers = manifest.get("layers", [])
        total_size = sum(layer.get("size", 0) for layer in layers)
        
        output = f"# {name}:{tag}\n\n"
        output += f"**Digest:** {manifest.get('config', {}).get('digest', '')}\n"
        output += f"**Size:** {total_size / 1024 / 1024:.2f} MB\n"
        output += f"**Layers:** {len(layers)}\n\n"
        
        output += "## Layers\n\n"
        for i, layer in enumerate(layers):
            output += f"### Layer {i+1}\n"
            output += f"**Digest:** {layer.get('digest', '')}\n"
            output += f"**Size:** {layer.get('size', 0) / 1024 / 1024:.2f} MB\n\n"
        
        return output
    except Exception as e:
        return f"Error retrieving image details: {str(e)}"
```

## Authentication Implementation

```python
from mcp.server.auth import OAuthServerProvider, AuthSettings, RevocationOptions, ClientRegistrationOptions
from mcp.server.auth.provider import TokenResponse, ClientCredentials

class DockerAuthProvider(OAuthServerProvider):
    async def authenticate_user(self, username: str, password: str) -> TokenResponse:
        client = DockerHubClient()
        if client.login(username, password):
            return TokenResponse(
                access_token=client.token,
                token_type="Bearer",
                expires_in=3600,  # Docker Hub tokens typically expire after 1 hour
                scope="read write"
            )
        raise ValueError("Invalid credentials")
    
    async def register_client(self, client_name: str, redirect_uris: List[str], scopes: List[str]) -> ClientCredentials:
        # In a real implementation, you would register the client with Docker Hub
        # For now, we'll just generate a dummy client ID and secret
        return ClientCredentials(
            client_id=f"docker-mcp-{client_name}",
            client_secret="dummy-secret",
            scopes=scopes
        )

# Configure authentication
mcp = FastMCP(
    "Docker Explorer",
    auth_server_provider=DockerAuthProvider(),
    auth=AuthSettings(
        issuer_url="https://your-docker-mcp-server.com",
        revocation_options=RevocationOptions(
            enabled=True,
        ),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["read", "write"],
            default_scopes=["read"],
        ),
        required_scopes=["read"],
    ),
)
```

## Deployment Configuration

```python
# For development
if __name__ == "__main__":
    mcp.run()

# For production deployment
# app = mcp.get_asgi_app()
```

## Testing Strategy

1. **Unit Tests**: Test individual components like the DockerHubClient and DockerRegistryClient
2. **Integration Tests**: Test the integration between the MCP server and Docker APIs
3. **End-to-End Tests**: Test the complete flow from MCP client to Docker APIs and back

## Next Steps

1. Implement the core search functionality
2. Add authentication and authorization
3. Implement Dockerfile search and analysis
4. Add caching for improved performance
5. Create comprehensive documentation and examples
