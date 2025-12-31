# ollama_mcp_server.py
import json
import asyncio
import aiohttp
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import subprocess
import sys
import os

class OllamaServer:
    """MCP-compatible server for Ollama.cpp integration"""
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
        self.available_models: List[str] = []
        self.session: Optional[aiohttp.ClientSession] = None
        self.is_running = False
        
    async def start(self):
        """Start the Ollama server connection"""
        try:
            self.session = aiohttp.ClientSession()
            
            # Test connection and get available models
            await self.refresh_models()
            
            self.is_running = True
            print(f"✅ Ollama MCP Server started at {self.base_url}")
            print(f"📦 Available models: {', '.join(self.available_models)}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to start Ollama server: {e}")
            return False
    
    async def refresh_models(self):
        """Fetch available Ollama models"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    self.available_models = [model['name'] for model in data.get('models', [])]
                else:
                    self.available_models = ["llama3.1", "mistral", "codellama"]
        except:
            # Fallback if Ollama isn't running
            self.available_models = ["llama3.1", "mistral", "codellama", "phi", "qwen"]
    
    async def generate(self, model: str, prompt: str, 
                      system: str = "", 
                      options: Dict = None) -> Dict[str, Any]:
        """Generate text using Ollama"""
        if not self.is_running:
            return {"error": "Ollama server not running"}
        
        if model not in self.available_models:
            return {"error": f"Model '{model}' not available. Available: {self.available_models}"}
        
        try:
            payload = {
                "model": model,
                "prompt": prompt,
                "system": system,
                "stream": False,
                "options": options or {}
            }
            
            async with self.session.post(
                f"{self.base_url}/api/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "response": result.get("response", ""),
                        "model": result.get("model", model),
                        "total_duration": result.get("total_duration", 0),
                        "load_duration": result.get("load_duration", 0),
                        "prompt_eval_count": result.get("prompt_eval_count", 0),
                        "eval_count": result.get("eval_count", 0)
                    }
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
                    
        except Exception as e:
            return {"error": f"Generation failed: {str(e)}"}
    
    async def chat(self, model: str, messages: List[Dict], 
                  options: Dict = None) -> Dict[str, Any]:
        """Chat completion using Ollama"""
        if not self.is_running:
            return {"error": "Ollama server not running"}
        
        try:
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": options or {}
            }
            
            async with self.session.post(
                f"{self.base_url}/api/chat",
                json=payload
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return {
                        "message": result.get("message", {}),
                        "model": result.get("model", model),
                        "total_duration": result.get("total_duration", 0),
                        "load_duration": result.get("load_duration", 0)
                    }
                else:
                    error_text = await response.text()
                    return {"error": f"API error {response.status}: {error_text}"}
                    
        except Exception as e:
            return {"error": f"Chat failed: {str(e)}"}
    
    async def list_models(self) -> List[Dict]:
        """List all available models with details"""
        try:
            async with self.session.get(f"{self.base_url}/api/tags") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get('models', [])
                return []
        except:
            return []
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Pull a model from Ollama library"""
        try:
            async with self.session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name}
            ) as response:
                if response.status == 200:
                    return {"status": "success", "model": model_name}
                return {"error": f"Failed to pull model: {response.status}"}
        except Exception as e:
            return {"error": f"Pull failed: {str(e)}"}
    
    async def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get detailed information about a model"""
        try:
            # Show command to get model info since Ollama doesn't have a direct API
            return {
                "model": model_name,
                "info": f"Use 'ollama show {model_name}' in terminal for details",
                "size": "Unknown (check with 'ollama list')",
                "parameters": "Varies by model"
            }
        except Exception as e:
            return {"error": f"Info retrieval failed: {str(e)}"}
    
    async def stop(self):
        """Stop the Ollama server connection"""
        if self.session:
            await self.session.close()
        self.is_running = False
    
    def get_tools(self) -> List[Dict]:
        """Return MCP tools definition for Ollama server"""
        return [
            {
                "name": "ollama_generate",
                "description": "Generate text using Ollama models",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Model name (e.g., 'llama3.1', 'mistral')",
                            "enum": self.available_models
                        },
                        "prompt": {
                            "type": "string",
                            "description": "Prompt text"
                        },
                        "system": {
                            "type": "string",
                            "description": "System prompt (optional)"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Sampling temperature (0.1-2.0)"
                        },
                        "max_tokens": {
                            "type": "integer",
                            "description": "Maximum tokens to generate"
                        }
                    },
                    "required": ["model", "prompt"]
                }
            },
            {
                "name": "ollama_chat",
                "description": "Chat with Ollama models using message history",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model": {
                            "type": "string",
                            "description": "Model name",
                            "enum": self.available_models
                        },
                        "messages": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "role": {
                                        "type": "string",
                                        "enum": ["user", "assistant", "system"]
                                    },
                                    "content": {
                                        "type": "string"
                                    }
                                },
                                "required": ["role", "content"]
                            },
                            "description": "Chat message history"
                        },
                        "temperature": {
                            "type": "number",
                            "description": "Sampling temperature"
                        }
                    },
                    "required": ["model", "messages"]
                }
            },
            {
                "name": "ollama_list_models",
                "description": "List all available Ollama models",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "ollama_pull_model",
                "description": "Download a model from Ollama library",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": "Name of model to download"
                        }
                    },
                    "required": ["model_name"]
                }
            },
            {
                "name": "ollama_model_info",
                "description": "Get information about a specific model",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": "Model name"
                        }
                    },
                    "required": ["model_name"]
                }
            }
        ]
