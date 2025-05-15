"""
Docker MCP Server - Sample Implementation

This sample demonstrates the core functionality of a Docker MCP server
that provides tools for searching and interacting with Docker images and registries.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import asyncio
import os

import requests
from pydantic import BaseModel, Field

from mcp.server.fastmcp import FastMCP, Context, Image

# Create the MCP server
mcp = FastMCP(
    "Docker Explorer",
    dependencies=[
        "requests",
        "pydantic",
    ]
)

# Define data models
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

class ImageLayer(BaseModel):
    digest: str
    size: int
    command: Optional[str] = None

class ImageDetail(BaseModel):
    name: str
    tag: str
    digest: Optional[str] = None
    architecture: Optional[str] = None
    os: Optional[str] = None
    layers: List[ImageLayer] = Field(default_factory=list)
    created: Optional[str] = None
    total_size: Optional[int] = None
    labels: Dict[str, str] = Field(default_factory=dict)

# Docker Hub API Client
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

# Docker Registry API Client
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
            
        # First get token for the repository
        auth_url = f"https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repository}:pull"
        auth_response = requests.get(auth_url)
        if auth_response.status_code != 200:
            raise Exception(f"Failed to authenticate: {auth_response.text}")
            
        token = auth_response.json()["token"]
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        
        # Now get the manifest
        response = self.session.get(
            f"{self.registry_url}/v2/{repository}/manifests/{reference}"
        )
        if response.status_code != 200:
            raise Exception(f"Failed to get manifest: {response.text}")
            
        return response.json()
    
    def get_image_layers(self, repository, reference):
        manifest = self.get_manifest(repository, reference)
        return manifest.get("layers", [])

# Server context for managing clients
@dataclass
class AppContext:
    docker_hub_client: DockerHubClient
    registry_client: DockerRegistryClient

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    """Manage application lifecycle with type-safe context"""
    # Initialize clients
    docker_hub_client = DockerHubClient()
    registry_client = DockerRegistryClient()
    
    try:
        yield AppContext(
            docker_hub_client=docker_hub_client,
            registry_client=registry_client
        )
    finally:
        # Cleanup if needed
        pass

# Pass lifespan to server
mcp = FastMCP("Docker Explorer", lifespan=app_lifespan)

# Implement MCP tools
@mcp.tool()
def search_images(
    query: str = Field(description="Search query for Docker images"),
    limit: int = Field(default=10, description="Maximum number of results to return"),
    ctx: Context = None
) -> List[DockerImage]:
    """Search for Docker images across registries"""
    client = ctx.request_context.lifespan_context.docker_hub_client
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
    tag_pattern: str = Field(default="", description="Pattern to match tags against"),
    limit: int = Field(default=25, description="Maximum number of results to return"),
    ctx: Context = None
) -> List[str]:
    """Search for specific tags of a Docker image"""
    client = ctx.request_context.lifespan_context.docker_hub_client
    
    if "/" in image_name:
        namespace, repository = image_name.split("/", 1)
    else:
        namespace, repository = "library", image_name
        
    tags = client.get_image_tags(namespace, repository, limit=limit)
    
    if tag_pattern:
        return [t["name"] for t in tags if tag_pattern in t["name"]]
    return [t["name"] for t in tags]

@mcp.tool()
def search_users(
    query: str = Field(description="Search query for Docker Hub users"),
    limit: int = Field(default=10, description="Maximum number of results to return"),
    ctx: Context = None
) -> List[DockerUser]:
    """Search for Docker Hub users/organizations"""
    client = ctx.request_context.lifespan_context.docker_hub_client
    results = client.search_users(query, limit=limit)
    
    return [
        DockerUser(
            username=r["username"],
            full_name=r.get("full_name", ""),
            is_organization=r.get("type", "") == "organization"
        ) for r in results
    ]

@mcp.tool()
def get_image_details(
    image_name: str = Field(description="Name of the Docker image"),
    tag: str = Field(default="latest", description="Tag of the Docker image"),
    ctx: Context = None
) -> ImageDetail:
    """Get detailed information about a Docker image"""
    registry_client = ctx.request_context.lifespan_context.registry_client
    
    try:
        # Get manifest
        manifest = registry_client.get_manifest(image_name, tag)
        
        # Extract layers
        layers = []
        total_size = 0
        
        for layer in manifest.get("layers", []):
            size = layer.get("size", 0)
            total_size += size
            layers.append(ImageLayer(
                digest=layer.get("digest", ""),
                size=size
            ))
        
        # Create image detail
        return ImageDetail(
            name=image_name,
            tag=tag,
            digest=manifest.get("config", {}).get("digest", ""),
            layers=layers,
            total_size=total_size
        )
    except Exception as e:
        # In a real implementation, you'd want better error handling
        ctx.error(f"Error getting image details: {str(e)}")
        return ImageDetail(
            name=image_name,
            tag=tag,
            layers=[],
            total_size=0
        )

# Implement MCP resources
@mcp.resource("docker://images/{query}")
def get_images_resource(query: str, ctx: Context) -> str:
    """Get information about Docker images matching a query"""
    client = ctx.request_context.lifespan_context.docker_hub_client
    results = client.search_images(query, limit=5)
    
    output = f"# Docker Images for '{query}'\n\n"
    
    if not results:
        return output + "No results found."
    
    for r in results:
        output += f"## {r['repo_name']}\n"
        output += f"**Stars:** {r.get('star_count', 0)} | **Pulls:** {r.get('pull_count', 0)}\n\n"
        output += f"{r.get('short_description', 'No description')}\n\n"
    
    return output

@mcp.resource("docker://image/{name}/{tag}")
def get_image_resource(name: str, tag: str, ctx: Context) -> str:
    """Get detailed information about a specific Docker image and tag"""
    registry_client = ctx.request_context.lifespan_context.registry_client
    
    try:
        manifest = registry_client.get_manifest(name, tag)
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
        ctx.error(f"Error retrieving image details: {str(e)}")
        return f"# {name}:{tag}\n\nError retrieving image details."

@mcp.resource("docker://user/{username}")
def get_user_resource(username: str, ctx: Context) -> str:
    """Get information about a Docker Hub user/organization"""
    # In a real implementation, you'd call the Docker Hub API to get user details
    # For this sample, we'll return a placeholder
    return f"# Docker Hub User: {username}\n\nUser profile information would be displayed here."

# Run the server when executed directly
if __name__ == "__main__":
    mcp.run()
