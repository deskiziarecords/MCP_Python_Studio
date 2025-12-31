# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.ai/install.sh | sh

# Install MCP servers
RUN npm install -g @modelcontextprotocol/server-filesystem \
    @modelcontextprotocol/server-memory \
    @modelcontextprotocol/server-duckduckgo

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create directories
RUN mkdir -p /root/.mcp-studio/{plugins,batch_exports,models,logs}

# Pull default Ollama model
RUN ollama pull llama3.1 &

# Expose API port
EXPOSE 8080

# Start the application
CMD ["python", "advanced_mcp_studio.py"]
