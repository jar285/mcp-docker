# 🐳 Docker Explorer MCP Server

<div align="center">

![Docker Explorer](https://img.shields.io/badge/Docker_Explorer-MCP_Server-blue?style=for-the-badge&logo=docker)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

</div>

## 📋 Overview

Docker Explorer is a powerful Model Context Protocol (MCP) server that provides tools and resources for interacting with Docker images, containers, and registries. This server enables AI assistants like Claude to search for, analyze, and interact with Docker resources through a standardized interface, making container management and exploration more accessible.

## ✨ Features

### Core Features
- Search for Docker images across registries
- Search for specific tags of Docker images
- Search for Docker Hub users/organizations
- Get detailed metadata about Docker images
- Analyze Dockerfile content
- Compare Docker images

### Advanced Tools
- **🔒 Security Scanner**: Analyze Docker images for known vulnerabilities and security issues
- **📦 Image Size Optimizer**: Get recommendations for reducing Docker image size
- **📄 Docker Compose Generator**: Generate docker-compose.yml files for your applications
- **📊 Container Runtime Analyzer**: Get insights about container runtime behavior and resource usage
- **🔍 Image Comparison Tool**: Compare two Docker images and highlight their differences
- **📜 Dockerfile Generator**: Create Dockerfiles from natural language application descriptions

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- Required Python packages: `requests`, `pydantic`

### Setup

1. **Clone this repository**:

```bash
git clone https://github.com/yourusername/docker-mcp-server.git
cd docker-mcp-server
```

2. **Create a virtual environment**:

```bash
python -m venv .venv310
source .venv310/bin/activate  # On Windows: .venv310\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

Or install individual packages:

```bash
pip install anthropic-mcp requests pydantic
```

## 💻 Usage

### Running the Server

You can run the server directly from the command line:

```bash
python docker_explorer.py
```

This will start the MCP server on the default port (5000).

### Integrating with Claude Desktop

To use the Docker Explorer MCP server with Claude Desktop:

1. **Update the Claude Desktop configuration**:
   - Open or create the `claude_desktop_config.json` file in your Claude Desktop configuration directory
   - Add the Docker Explorer server configuration

```json
{
  "mcp_servers": [
    {
      "name": "docker-explorer",
      "command": ["python", "/path/to/mcpIS421/docker_explorer.py"],
      "cwd": "/path/to/mcpIS421"
    }
  ]
}
```

2. **Restart Claude Desktop** to load the new configuration

### Using the Tools

Once integrated with Claude Desktop, you can use the Docker Explorer tools by asking Claude questions like:

#### Core Tools

1. **Search for Docker images**:
   ```
   Can you search for Python Docker images?
   ```

2. **Get image details**:
   ```
   What are the details of the python:3.11-slim image?
   ```

3. **Find available tags**:
   ```
   What tags are available for the nginx image?
   ```

#### Advanced Tools

4. **Security Scanner**:
   ```
   Scan the security of the nginx image
   ```

5. **Image Size Optimizer**:
   ```
   How can I reduce the size of my python:3.9 image?
   ```

6. **Docker Compose Generator**:
   ```
   Generate a docker-compose file for nginx with port 8080:80
   ```

7. **Container Runtime Analyzer**:
   ```
   Analyze the runtime behavior of mysql:5.7 as a database
   ```

## 👷 Development

### Project Structure

```
docker-explorer-mcp/
├── docker_explorer.py      # Main server implementation with all tools
├── requirements.txt        # Project dependencies
├── .gitignore             # Git ignore file
└── docs/                  # Documentation
    ├── server_guide.md    # Guide for setting up and using the server
    ├── new_tools_suggestions.md  # Ideas for additional tools
    └── docker_mcp_server_project.md  # Project overview
```

### Adding New Features

To add a new tool to the Docker Explorer MCP server:

1. Implement the tool function in `docker_explorer.py` using the MCP tool decorator:

```python
@mcp.tool()
def my_new_tool(
    param1: str = Field(description="Description of param1"),
    param2: int = Field(default=10, description="Description of param2")
) -> str:
    """Description of what your tool does"""
    try:
        # Implementation logic here
        result = f"Your formatted result"
        return result
    except Exception as e:
        return f"Error in my_new_tool: {str(e)}"
```

2. Follow these best practices for tool implementation:
   - Keep output concise and formatted for Claude Desktop
   - Handle exceptions gracefully
   - Provide clear parameter descriptions
   - Return well-structured results

### Testing

1. **Manual Testing**:
   - Run the server: `python docker_explorer.py`
   - Test with Claude Desktop by asking relevant questions

2. **Debugging**:
   - Check terminal output for any errors
   - Verify tool responses in Claude Desktop
   - Adjust output formatting if Claude has capacity constraints

## 📚 API Documentation

### Core Tools

#### `search_images`
- **Description**: Search for Docker images across registries
- **Parameters**:
  - `query` (string): Search query for Docker images
  - `limit` (integer, default=10): Maximum number of results to return
- **Returns**: List of Docker images with metadata

#### `search_tags`
- **Description**: Search for specific tags of a Docker image
- **Parameters**:
  - `image_name` (string): Name of the Docker image
  - `tag_pattern` (string, default=""): Pattern to match tags against
  - `limit` (integer, default=25): Maximum number of results to return
- **Returns**: List of matching tags

#### `get_image_details`
- **Description**: Get detailed information about a Docker image
- **Parameters**:
  - `image_name` (string): Name of the Docker image
  - `tag` (string, default="latest"): Tag of the Docker image
- **Returns**: Detailed image information

### Advanced Tools

#### `scan_security`
- **Description**: Analyze Docker images for known vulnerabilities and security issues
- **Parameters**:
  - `image_name` (string): Name of the Docker image
  - `tag` (string, default="latest"): Tag of the Docker image to scan
- **Returns**: Security analysis report with recommendations

#### `optimize_image_size`
- **Description**: Analyze a Docker image and suggest ways to reduce its size
- **Parameters**:
  - `repository_url` (string): Full URL to a Docker Hub repository
  - `tag` (string, default="latest"): Tag of the Docker image to analyze
- **Returns**: Size optimization recommendations

#### `generate_docker_compose`
- **Description**: Generate a docker-compose.yml file based on an image
- **Parameters**:
  - `repository_url` (string): Full URL to a Docker Hub repository
  - `tag` (string, default="latest"): Tag of the Docker image
  - `port_mapping` (string, default=""): Optional port mapping (e.g., '8080:80')
  - `environment_variables` (string, default=""): Optional environment variables
  - `include_db` (boolean, default=false): Whether to include a database service
- **Returns**: Generated docker-compose.yml content

#### `analyze_runtime`
- **Description**: Analyze how a container might behave at runtime
- **Parameters**:
  - `image_name` (string): Name of the Docker image
  - `tag` (string, default="latest"): Tag of the Docker image
  - `app_type` (string, default="web"): Application type (web, database, cache, api, batch)
- **Returns**: Runtime analysis with resource usage predictions and recommendations

#### `compare_images`
- **Description**: Compare two Docker images and highlight the differences
- **Parameters**:
  - `image1` (string): First Docker image to compare (e.g., 'nginx:1.21' or 'user/repo:tag')
  - `image2` (string): Second Docker image to compare (e.g., 'nginx:1.22' or 'user/repo:tag')
- **Returns**: Detailed comparison report highlighting differences in size, layers, configuration, and compatibility

#### `generate_dockerfile`
- **Description**: Generate a Dockerfile based on application requirements described in natural language
- **Parameters**:
  - `app_description` (string): Description of the application to containerize (e.g., 'Python Flask web app with Redis')
  - `app_type` (string, default="web"): Application type (web, api, database, worker, static)
  - `base_image` (string, default=""): Optional base image to use (e.g., 'python:3.9-alpine')
  - `include_comments` (boolean, default=true): Whether to include explanatory comments in the Dockerfile
- **Returns**: Generated Dockerfile with usage instructions

## 🔒 Security Considerations

The Docker Explorer MCP server is designed for educational and development purposes. When using it:

- Do not expose sensitive credentials or API keys
- Be cautious when generating and running Docker Compose files
- Always review security recommendations before implementation

## 📌 License

MIT

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request with new tools or improvements to existing functionality.
