# enhanced_mcp_studio.py
import flet as ft
import asyncio
import json
import os
import sys
import traceback
from datetime import datetime
from typing import Dict, List, Optional, Any
import aiohttp
from dataclasses import dataclass, asdict
from enum import Enum
import pickle
from pathlib import Path

# Import our Ollama server
from ollama_mcp_server import OllamaServer

# Import MCP SDK
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client import sse, stdio
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("⚠️ MCP SDK not installed. Run: pip install mcp")

class ConnectionStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

@dataclass
class ServerConfig:
    name: str
    type: str
    config: Dict
    last_connected: Optional[datetime] = None
    error_count: int = 0
    
    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "config": self.config,
            "last_connected": self.last_connected.isoformat() if self.last_connected else None,
            "error_count": self.error_count
        }
    
    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data["name"],
            type=data["type"],
            config=data["config"],
            last_connected=datetime.fromisoformat(data["last_connected"]) if data.get("last_connected") else None,
            error_count=data.get("error_count", 0)
        )

class EnhancedMCPStudio:
    def __init__(self):
        self.current_model = "llama3.1"  # Default to Ollama model
        self.connected_servers: Dict[str, Dict] = {}
        self.active_sessions: Dict[str, Any] = {}
        self.available_tools: List[Dict] = []
        self.chat_history = []
        self.config_path = Path.home() / ".mcp-studio"
        self.config_path.mkdir(exist_ok=True)
        
        # Initialize Ollama server
        self.ollama_server = OllamaServer()
        
        # Enhanced predefined servers with Ollama
        self.predefined_servers = {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": ["@modelcontextprotocol/server-filesystem", "."],
                "description": "File system access",
                "category": "system"
            },
            "memory": {
                "type": "stdio", 
                "command": "npx",
                "args": ["@modelcontextprotocol/server-memory"],
                "description": "Memory operations",
                "category": "system"
            },
            "ollama": {
                "type": "python",
                "module": "ollama_mcp_server",
                "class": "OllamaServer",
                "description": "Local LLM models via Ollama",
                "category": "ai",
                "config": {"base_url": "http://localhost:11434"}
            },
            "weather": {
                "type": "sse",
                "url": "https://demo.mcp-server.com/weather/sse",
                "description": "Weather data",
                "category": "web"
            },
            "duckduckgo": {
                "type": "stdio",
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-duckduckgo"],
                "description": "Web search",
                "category": "web"
            }
        }
        
        # Error recovery configuration
        self.recovery_attempts = 3
        self.recovery_delay = 2  # seconds
        
        # Statistics
        self.stats = {
            "tool_calls": 0,
            "errors": 0,
            "connections": 0,
            "messages_sent": 0
        }
        
        # Load saved configuration
        self.load_config()
    
    # ==================== CONFIGURATION MANAGEMENT ====================
    
    def load_config(self):
        """Load saved configuration from disk"""
        config_file = self.config_path / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    # Load saved servers
                    saved_servers = config.get("servers", {})
                    for name, data in saved_servers.items():
                        if name in self.predefined_servers:
                            self.predefined_servers[name].update(data)
                    
                    # Load model preferences
                    self.current_model = config.get("model", self.current_model)
                    
                    print("✅ Configuration loaded")
            except Exception as e:
                print(f"⚠️ Failed to load config: {e}")
    
    def save_config(self):
        """Save configuration to disk"""
        config_file = self.config_path / "config.json"
        try:
            config = {
                "servers": self.predefined_servers,
                "model": self.current_model,
                "connected_servers": list(self.connected_servers.keys()),
                "last_saved": datetime.now().isoformat()
            }
            
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            print("💾 Configuration saved")
        except Exception as e:
            print(f"⚠️ Failed to save config: {e}")
    
    def save_chat_history(self):
        """Save chat history to disk"""
        history_file = self.config_path / f"chat_{datetime.now().strftime('%Y%m%d')}.json"
        try:
            history = []
            for chat in self.chat_history:
                if hasattr(chat, 'to_dict'):
                    history.append(chat.to_dict())
                else:
                    history.append(chat)
            
            with open(history_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            print(f"💾 Chat history saved to {history_file}")
        except Exception as e:
            print(f"⚠️ Failed to save chat history: {e}")
    
    # ==================== ENHANCED ERROR HANDLING ====================
    
    async def safe_execute(self, coroutine, operation_name: str, retries: int = 3):
        """Execute a coroutine with retry logic and error handling"""
        last_error = None
        
        for attempt in range(retries):
            try:
                result = await coroutine
                return result
                
            except aiohttp.ClientError as e:
                last_error = f"Network error: {str(e)}"
                if attempt < retries - 1:
                    await asyncio.sleep(self.recovery_delay * (attempt + 1))
                    
            except ConnectionError as e:
                last_error = f"Connection error: {str(e)}"
                if attempt < retries - 1:
                    await asyncio.sleep(self.recovery_delay * (attempt + 1))
                    
            except Exception as e:
                last_error = f"Error in {operation_name}: {str(e)}"
                break  # Don't retry on other errors
        
        self.stats["errors"] += 1
        error_details = {
            "operation": operation_name,
            "error": last_error,
            "timestamp": datetime.now().isoformat(),
            "attempts": attempt + 1
        }
        
        # Log error
        await self.log_error(error_details)
        
        # Show error in UI
        await self.show_error_notification(operation_name, last_error)
        
        return {"error": last_error}
    
    async def log_error(self, error_details: Dict):
        """Log error to file"""
        error_file = self.config_path / "errors.log"
        try:
            with open(error_file, 'a') as f:
                f.write(json.dumps(error_details) + "\n")
        except:
            pass
    
    async def show_error_notification(self, operation: str, error: str):
        """Show error notification in UI"""
        if hasattr(self, 'page'):
            notification = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(ft.icons.ERROR, color=ft.colors.RED),
                    ft.Column([
                        ft.Text(f"{operation} failed", weight=ft.FontWeight.BOLD),
                        ft.Text(error[:100] + "..." if len(error) > 100 else error, size=12)
                    ], tight=True)
                ]),
                action="Dismiss",
                bgcolor=ft.colors.ERROR_CONTAINER
            )
            self.page.snack_bar = notification
            self.page.snack_bar.open = True
            await self.page.update_async()
    
    async def validate_server_connection(self, server_name: str) -> bool:
        """Validate that a server connection is still alive"""
        if server_name not in self.active_sessions:
            return False
        
        try:
            if server_name == "ollama":
                # Check Ollama server
                if hasattr(self.ollama_server, 'is_running'):
                    return self.ollama_server.is_running
                return False
            else:
                # Check MCP server
                session = self.active_sessions[server_name]
                # Try to list tools (lightweight operation)
                await asyncio.wait_for(session.list_tools(), timeout=5)
                return True
                
        except (asyncio.TimeoutError, ConnectionError, Exception):
            return False
    
    async def reconnect_server(self, server_name: str):
        """Attempt to reconnect a disconnected server"""
        if server_name not in self.predefined_servers:
            return False
        
        config = self.predefined_servers[server_name]
        
        await self.add_chat_message(
            "System",
            f"🔄 Attempting to reconnect to {server_name}...",
            ft.colors.ORANGE
        )
        
        # Disconnect first if still connected
        if server_name in self.active_sessions:
            await self.disconnect_server(server_name)
        
        # Reconnect
        success = await self.connect_to_server(server_name)
        
        if success:
            await self.add_chat_message(
                "System",
                f"✅ Successfully reconnected to {server_name}",
                ft.colors.GREEN
            )
        else:
            await self.add_chat_message(
                "System",
                f"❌ Failed to reconnect to {server_name}",
                ft.colors.RED
            )
        
        return success
    
    # ==================== OLLAMA SERVER INTEGRATION ====================
    
    async def connect_ollama_server(self, config: Dict):
        """Connect to the Ollama MCP server"""
        try:
            # Initialize Ollama server
            base_url = config.get("config", {}).get("base_url", "http://localhost:11434")
            self.ollama_server = OllamaServer(base_url=base_url)
            
            # Start the server
            success = await self.ollama_server.start()
            
            if success:
                # Get available tools
                tools = self.ollama_server.get_tools()
                
                # Store in active sessions
                self.active_sessions["ollama"] = self.ollama_server
                self.connected_servers["ollama"] = {
                    "config": config,
                    "tools": tools,
                    "connected_at": datetime.now(),
                    "type": "python"
                }
                
                return tools
            else:
                raise ConnectionError("Failed to start Ollama server")
                
        except Exception as e:
            raise ConnectionError(f"Ollama connection failed: {str(e)}")
    
    async def execute_ollama_tool(self, tool_name: str, arguments: Dict):
        """Execute an Ollama tool"""
        if not hasattr(self.ollama_server, 'is_running') or not self.ollama_server.is_running:
            return {"error": "Ollama server not running"}
        
        try:
            if tool_name == "ollama_generate":
                result = await self.ollama_server.generate(
                    model=arguments.get("model", self.current_model),
                    prompt=arguments.get("prompt", ""),
                    system=arguments.get("system", ""),
                    options={
                        "temperature": arguments.get("temperature", 0.7),
                        "num_predict": arguments.get("max_tokens", 512)
                    }
                )
                
            elif tool_name == "ollama_chat":
                result = await self.ollama_server.chat(
                    model=arguments.get("model", self.current_model),
                    messages=arguments.get("messages", []),
                    options={
                        "temperature": arguments.get("temperature", 0.7)
                    }
                )
                
            elif tool_name == "ollama_list_models":
                models = await self.ollama_server.list_models()
                result = {"models": models}
                
            elif tool_name == "ollama_pull_model":
                result = await self.ollama_server.pull_model(
                    arguments.get("model_name", "")
                )
                
            elif tool_name == "ollama_model_info":
                result = await self.ollama_server.get_model_info(
                    arguments.get("model_name", "")
                )
                
            else:
                result = {"error": f"Unknown tool: {tool_name}"}
            
            return result
            
        except Exception as e:
            return {"error": f"Ollama tool execution failed: {str(e)}"}
    
    # ==================== ENHANCED CONNECTION MANAGEMENT ====================
    
    async def connect_to_server(self, server_name: str):
        """Enhanced server connection with error handling"""
        if server_name in self.connected_servers:
            await self.disconnect_server(server_name)
            return True
        
        config = self.predefined_servers.get(server_name)
        if not config:
            await self.show_error_notification("Connection", f"Unknown server: {server_name}")
            return False
        
        # Update UI to show connecting
        await self.update_status(f"Connecting to {server_name}...", ft.colors.ORANGE)
        
        try:
            # Connect based on server type
            if config["type"] == "python" and server_name == "ollama":
                tools = await self.safe_execute(
                    self.connect_ollama_server(config),
                    f"Connect {server_name}"
                )
                
            elif config["type"] == "stdio" and MCP_AVAILABLE:
                tools = await self.safe_execute(
                    self.connect_stdio_server(config),
                    f"Connect {server_name}"
                )
                
            elif config["type"] == "sse" and MCP_AVAILABLE:
                tools = await self.safe_execute(
                    self.connect_sse_server(config),
                    f"Connect {server_name}"
                )
                
            else:
                raise ValueError(f"Unsupported server type: {config['type']}")
            
            if "error" in tools:
                raise ConnectionError(tools["error"])
            
            # Store connection
            self.connected_servers[server_name] = {
                "config": config,
                "tools": tools if isinstance(tools, list) else [],
                "connected_at": datetime.now(),
                "type": config["type"]
            }
            
            # Update tools list
            await self.update_tools_list()
            
            # Update UI
            await self.add_server_to_list(server_name, config, tools)
            await self.update_status(f"Connected to {server_name}", ft.colors.GREEN)
            
            # Show success message
            tool_count = len(tools) if isinstance(tools, list) else 0
            await self.add_chat_message(
                "System",
                f"✅ Connected to {server_name} ({config['description']})\n"
                f"📦 Available tools: {tool_count}\n"
                f"⚡ Type '/tools' to see all tools",
                ft.colors.BLUE
            )
            
            self.stats["connections"] += 1
            await self.update_stats_display()
            
            # Save config after successful connection
            self.save_config()
            
            return True
            
        except Exception as e:
            error_msg = f"Failed to connect to {server_name}: {str(e)}"
            await self.update_status(error_msg, ft.colors.RED)
            await self.add_chat_message("System", f"❌ {error_msg}", ft.colors.RED)
            return False
    
    async def disconnect_server(self, server_name: str):
        """Enhanced server disconnection"""
        try:
            if server_name == "ollama":
                if hasattr(self.ollama_server, 'stop'):
                    await self.ollama_server.stop()
                    
            elif server_name in self.active_sessions and MCP_AVAILABLE:
                session = self.active_sessions[server_name]
                await session.__aexit__(None, None, None)
            
            # Cleanup
            self.active_sessions.pop(server_name, None)
            self.connected_servers.pop(server_name, None)
            
            # Update UI
            await self.update_tools_list()
            await self.refresh_servers_list()
            await self.update_status("Server disconnected", ft.colors.ORANGE)
            
            await self.add_chat_message(
                "System",
                f"🔌 Disconnected from {server_name}",
                ft.colors.ORANGE
            )
            
            # Save config
            self.save_config()
            
        except Exception as e:
            await self.show_error_notification("Disconnection", str(e))
    
    # ==================== ENHANCED UI COMPONENTS ====================
    
    async def build_stats_tab(self):
        """Build statistics and monitoring tab"""
        self.stats_display = ft.Column([
            ft.Text("Statistics & Monitoring", size=20, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            
            # Real-time stats
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.icons.TERMINAL, color=ft.colors.BLUE),
                        ft.Text("Tool Calls: ", weight=ft.FontWeight.BOLD),
                        ft.Text("0", ref=self.stats_tool_calls)
                    ]),
                    ft.Row([
                        ft.Icon(ft.icons.ERROR, color=ft.colors.RED),
                        ft.Text("Errors: ", weight=ft.FontWeight.BOLD),
                        ft.Text("0", ref=self.stats_errors)
                    ]),
                    ft.Row([
                        ft.Icon(ft.icons.LINK, color=ft.colors.GREEN),
                        ft.Text("Connections: ", weight=ft.FontWeight.BOLD),
                        ft.Text("0", ref=self.stats_connections)
                    ]),
                    ft.Row([
                        ft.Icon(ft.icons.MESSAGE, color=ft.colors.PURPLE),
                        ft.Text("Messages: ", weight=ft.FontWeight.BOLD),
                        ft.Text("0", ref=self.stats_messages)
                    ]),
                ]),
                padding=10,
                border=ft.border.all(1, ft.colors.OUTLINE),
                border_radius=5
            ),
            
            ft.Divider(),
            
            # Server health
            ft.Text("Server Health", size=16, weight=ft.FontWeight.BOLD),
            ft.Container(
                content=ft.Column([], ref=self.health_status),
                padding=10,
                border=ft.border.all(1, ft.colors.OUTLINE),
                border_radius=5
            ),
            
            ft.Divider(),
            
            # Connection diagnostics
            ft.Text("Diagnostics", size=16, weight=ft.FontWeight.BOLD),
            ft.ElevatedButton(
                "Run Diagnostics",
                icon=ft.icons.DIAGNOSTICS,
                on_click=self.run_diagnostics
            ),
            
            # Export data
            ft.Divider(),
            ft.Text("Data Management", size=16, weight=ft.FontWeight.BOLD),
            ft.Row([
                ft.ElevatedButton(
                    "Export Chat",
                    icon=ft.icons.EXPORT_EXCEL,
                    on_click=self.export_chat
                ),
                ft.ElevatedButton(
                    "Clear Stats",
                    icon=ft.icons.CLEAR_ALL,
                    on_click=self.clear_stats
                ),
            ])
        ])
        
        return ft.Container(
            content=self.stats_display,
            padding=20
        )
    
    async def update_stats_display(self):
        """Update the statistics display"""
        if hasattr(self, 'stats_tool_calls'):
            self.stats_tool_calls.current.value = str(self.stats["tool_calls"])
            self.stats_errors.current.value = str(self.stats["errors"])
            self.stats_connections.current.value = str(self.stats["connections"])
            self.stats_messages.current.value = str(self.stats["messages_sent"])
            
            await self.stats_tool_calls.current.update_async()
            await self.stats_errors.current.update_async()
            await self.stats_connections.current.update_async()
            await self.stats_messages.current.update_async()
    
    async def run_diagnostics(self, e):
        """Run connection diagnostics"""
        await self.add_chat_message("System", "🔍 Running diagnostics...", ft.colors.BLUE)
        
        diagnostics = []
        
        # Check Ollama
        try:
            import requests
            response = requests.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                diagnostics.append("✅ Ollama: Running")
            else:
                diagnostics.append("❌ Ollama: Not responding")
        except:
            diagnostics.append("❌ Ollama: Not installed or not running")
        
        # Check Node.js
        try:
            result = subprocess.run(["node", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                diagnostics.append(f"✅ Node.js: {result.stdout.strip()}")
            else:
                diagnostics.append("❌ Node.js: Not installed")
        except:
            diagnostics.append("❌ Node.js: Not installed")
        
        # Check MCP servers
        try:
            result = subprocess.run(["npm", "list", "-g", "@modelcontextprotocol/server-filesystem"], 
                                  capture_output=True, text=True)
            if "@modelcontextprotocol/server-filesystem" in result.stdout:
                diagnostics.append("✅ MCP Filesystem: Installed")
            else:
                diagnostics.append("⚠️ MCP Filesystem: Not installed globally")
        except:
            diagnostics.append("❌ NPM: Not available")
        
        # Show results
        await self.add_chat_message(
            "Diagnostics",
            "\n".join(diagnostics),
            ft.colors.PURPLE
        )
    
    async def export_chat(self, e):
        """Export chat history"""
        try:
            self.save_chat_history()
            
            # Show success
            notification = ft.SnackBar(
                content=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN),
                    ft.Text("Chat exported successfully!", weight=ft.FontWeight.BOLD)
                ]),
                bgcolor=ft.colors.GREEN
            )
            self.page.snack_bar = notification
            self.page.snack_bar.open = True
            await self.page.update_async()
            
        except Exception as e:
            await self.show_error_notification("Export", str(e))
    
    async def clear_stats(self, e):
        """Clear statistics"""
        self.stats = {
            "tool_calls": 0,
            "errors": 0,
            "connections": 0,
            "messages_sent": 0
        }
        await self.update_stats_display()
        
        notification = ft.SnackBar(
            content=ft.Text("Statistics cleared"),
            bgcolor=ft.colors.BLUE
        )
        self.page.snack_bar = notification
        self.page.snack_bar.open = True
        await self.page.update_async()
    
    # ==================== MAIN APPLICATION ====================
    
    async def main(self, page: ft.Page):
        self.page = page
        page.title = "Enhanced MCP Studio with Ollama"
        page.theme_mode = ft.ThemeMode.LIGHT
        page.padding = 10
        
        # Add theme toggle
        self.theme_toggle = ft.IconButton(
            icon=ft.icons.DARK_MODE,
            on_click=self.toggle_theme,
            tooltip="Toggle dark/light mode"
        )
        
        # Initialize UI
        await self.init_components()
        
        # Build enhanced UI with additional tabs
        tabs = ft.Tabs(
            selected_index=0,
            tabs=[
                ft.Tab(text="Chat", icon=ft.icons.CHAT, content=await self.build_chat_tab()),
                ft.Tab(text="Servers", icon=ft.icons.STORAGE, content=await self.build_servers_tab()),
                ft.Tab(text="Tools", icon=ft.icons.BUILD, content=await self.build_tools_tab()),
                ft.Tab(text="Models", icon=ft.icons.SMART_TOY, content=await self.build_models_tab()),
                ft.Tab(text="Stats", icon=ft.icons.ANALYTICS, content=await self.build_stats_tab()),
                ft.Tab(text="Settings", icon=ft.icons.SETTINGS, content=await self.build_settings_tab()),
            ],
            expand=True,
        )
        
        # Add theme toggle to app bar
        page.appbar = ft.AppBar(
            title=ft.Text("MCP Studio with Ollama"),
            center_title=True,
            actions=[self.theme_toggle],
            bgcolor=ft.colors.SURFACE_VARIANT
        )
        
        page.add(tabs)
        
        # Auto-connect to Ollama if available
        await asyncio.sleep(1)
        await self.auto_connect_servers()
    
    async def toggle_theme(self, e):
        """Toggle between dark and light theme"""
        self.page.theme_mode = (
            ft.ThemeMode.DARK 
            if self.page.theme_mode == ft.ThemeMode.LIGHT 
            else ft.ThemeMode.LIGHT
        )
        
        self.theme_toggle.icon = (
            ft.icons.LIGHT_MODE 
            if self.page.theme_mode == ft.ThemeMode.DARK 
            else ft.icons.DARK_MODE
        )
        
        await self.page.update_async()
    
    async def auto_connect_servers(self):
        """Auto-connect to commonly used servers"""
        # Try Ollama first
        await self.connect_to_server("ollama")
        
        # Then try filesystem
        await asyncio.sleep(0.5)
        await self.connect_to_server("filesystem")
    
    async def build_settings_tab(self):
        """Build settings tab"""
        return ft.Container(
            content=ft.Column([
                ft.Text("Settings", size=20, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                
                # Auto-reconnect
                ft.Switch(
                    label="Auto-reconnect on failure",
                    value=True,
                    label_position=ft.LabelPosition.LEFT
                ),
                
                # Recovery settings
                ft.Text("Recovery Settings", size=16, weight=ft.FontWeight.BOLD),
                ft.Slider(
                    min=1,
                    max=10,
                    divisions=9,
                    label="Max retries: {value}",
                    value=3
                ),
                
                # Data management
                ft.Text("Data Management", size=16, weight=ft.FontWeight.BOLD),
                ft.Row([
                    ft.ElevatedButton(
                        "Backup All Data",
                        icon=ft.icons.BACKUP
                    ),
                    ft.ElevatedButton(
                        "Restore Backup",
                        icon=ft.icons.RESTORE
                    ),
                ]),
                
                # Reset
                ft.Divider(),
                ft.Text("Reset", size=16, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton(
                    "Reset to Defaults",
                    icon=ft.icons.RESTART_ALT,
                    color=ft.colors.RED
                )
            ], scroll=ft.ScrollMode.AUTO),
            padding=20
        )
    
    # ... [Previous UI methods from the first implementation would go here]
    # build_chat_tab(), build_servers_tab(), build_tools_tab(), build_models_tab()
    # update_tools_list(), add_chat_message(), update_tool_output(), etc.

# Main entry point
if __name__ == "__main__":
    print("🚀 Starting Enhanced MCP Studio with Ollama...")
    print("=" * 50)
    print("Features:")
    print("✅ Ollama.cpp MCP server integration")
    print("✅ Enhanced error handling with auto-recovery")
    print("✅ Configuration persistence")
    print("✅ Statistics and monitoring")
    print("✅ Dark/light theme toggle")
    print("=" * 50)
    
    app = EnhancedMCPStudio()
    ft.app(target=app.main)
