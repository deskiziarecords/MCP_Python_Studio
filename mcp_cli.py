# mcp_cli.py
import argparse
import json
import sys
import os
import asyncio
import aiohttp
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import subprocess
import csv
from dataclasses import dataclass, asdict
from enum import Enum
import getpass
import hashlib

# CLI Version of MCP Studio
class MCPCLI:
    """Command-line interface for MCP Studio automation"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or Path.home() / ".mcp-studio" / "cli_config.json"
        self.config = self.load_config()
        self.session = None
        self.logger = self.setup_logger()
        
    def setup_logger(self):
        """Setup logging for CLI"""
        logger = logging.getLogger('mcp-cli')
        logger.setLevel(logging.INFO)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        
        # File handler
        log_dir = Path.home() / ".mcp-studio" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_dir / "cli.log")
        fh.setLevel(logging.DEBUG)
        
        # Formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        fh.setFormatter(formatter)
        
        logger.addHandler(ch)
        logger.addHandler(fh)
        
        return logger
    
    def load_config(self) -> Dict:
        """Load CLI configuration"""
        config_file = Path(self.config_path)
        if config_file.exists():
            with open(config_file, 'r') as f:
                return json.load(f)
        return {
            "api_url": "http://localhost:8080",
            "api_key": None,
            "default_model": "llama3.1",
            "timeout": 30,
            "output_format": "json"
        }
    
    def save_config(self):
        """Save CLI configuration"""
        config_file = Path(self.config_path)
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    async def connect(self):
        """Connect to MCP Studio API"""
        if not self.session:
            self.session = aiohttp.ClientSession(
                headers={"X-API-Key": self.config["api_key"]} if self.config["api_key"] else {}
            )
        
        # Test connection
        try:
            async with self.session.get(f"{self.config['api_url']}/api/health") as response:
                if response.status == 200:
                    self.logger.info("Connected to MCP Studio API")
                    return True
                else:
                    self.logger.error(f"Connection failed: {response.status}")
                    return False
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Disconnect from API"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def chat(self, message: str, model: Optional[str] = None) -> Dict:
        """Send chat message"""
        try:
            async with self.session.post(
                f"{self.config['api_url']}/api/chat",
                json={
                    "message": message,
                    "model": model or self.config["default_model"]
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"API error: {response.status}"}
        except Exception as e:
            return {"error": f"Request failed: {e}"}
    
    async def execute_tool(self, server: str, tool: str, arguments: Dict) -> Dict:
        """Execute a tool"""
        try:
            async with self.session.post(
                f"{self.config['api_url']}/api/tools/execute",
                json={
                    "server": server,
                    "tool": tool,
                    "arguments": arguments
                }
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    return {"error": f"API error: {response.status}"}
        except Exception as e:
            return {"error": f"Request failed: {e}"}
    
    async def list_tools(self) -> List[Dict]:
        """List all available tools"""
        try:
            async with self.session.get(f"{self.config['api_url']}/api/tools") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("tools", [])
                return []
        except Exception as e:
            self.logger.error(f"Failed to list tools: {e}")
            return []
    
    async def list_servers(self) -> List[Dict]:
        """List connected servers"""
        try:
            async with self.session.get(f"{self.config['api_url']}/api/servers") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("servers", [])
                return []
        except Exception as e:
            self.logger.error(f"Failed to list servers: {e}")
            return []
    
    async def connect_server(self, server_name: str) -> Dict:
        """Connect to a server"""
        try:
            async with self.session.post(
                f"{self.config['api_url']}/api/servers/connect",
                json={"server": server_name}
            ) as response:
                return await response.json()
        except Exception as e:
            return {"error": f"Request failed: {e}"}
    
    async def batch_execute(self, batch_file: str, concurrent: bool = False) -> Dict:
        """Execute batch operations"""
        try:
            with open(batch_file, 'r') as f:
                batch_data = json.load(f)
            
            async with self.session.post(
                f"{self.config['api_url']}/api/batch",
                json={
                    "tools": batch_data,
                    "concurrent": concurrent,
                    "name": Path(batch_file).stem
                }
            ) as response:
                return await response.json()
        except Exception as e:
            return {"error": f"Batch execution failed: {e}"}
    
    async def fine_tune(self, config_file: str) -> Dict:
        """Start fine-tuning job"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            async with self.session.post(
                f"{self.config['api_url']}/api/finetune",
                json=config
            ) as response:
                return await response.json()
        except Exception as e:
            return {"error": f"Fine-tuning failed: {e}"}
    
    def format_output(self, data: Any, format_type: str = None) -> str:
        """Format output based on configuration"""
        fmt = format_type or self.config.get("output_format", "json")
        
        if fmt == "json":
            return json.dumps(data, indent=2)
        elif fmt == "yaml":
            return yaml.dump(data, default_flow_style=False)
        elif fmt == "csv" and isinstance(data, list):
            return self._to_csv(data)
        elif fmt == "table" and isinstance(data, list):
            return self._to_table(data)
        else:
            return str(data)
    
    def _to_csv(self, data: List[Dict]) -> str:
        """Convert data to CSV"""
        if not data:
            return ""
        
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        return output.getvalue()
    
    def _to_table(self, data: List[Dict]) -> str:
        """Convert data to ASCII table"""
        if not data:
            return "No data"
        
        # Simple table formatting
        headers = data[0].keys()
        rows = []
        for item in data:
            rows.append([str(item.get(h, ""))[:50] for h in headers])
        
        # Calculate column widths
        col_widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))
        
        # Build table
        separator = "+" + "+".join(["-" * (w + 2) for w in col_widths]) + "+"
        header_row = "| " + " | ".join([h.ljust(col_widths[i]) for i, h in enumerate(headers)]) + " |"
        data_rows = []
        for row in rows:
            data_rows.append("| " + " | ".join([cell.ljust(col_widths[i]) for i, cell in enumerate(row)]) + " |")
        
        return "\n".join([separator, header_row, separator] + data_rows + [separator])
    
    async def run_script(self, script_file: str):
        """Run an automation script"""
        try:
            with open(script_file, 'r') as f:
                script = json.load(f)
            
            results = []
            for step in script.get("steps", []):
                step_type = step.get("type")
                self.logger.info(f"Executing step: {step.get('name', step_type)}")
                
                if step_type == "chat":
                    result = await self.chat(
                        step.get("message"),
                        step.get("model")
                    )
                elif step_type == "tool":
                    result = await self.execute_tool(
                        step.get("server"),
                        step.get("tool"),
                        step.get("arguments", {})
                    )
                elif step_type == "batch":
                    result = await self.batch_execute(step.get("batch_file"))
                elif step_type == "wait":
                    await asyncio.sleep(step.get("seconds", 1))
                    result = {"status": "waited", "seconds": step.get("seconds")}
                else:
                    result = {"error": f"Unknown step type: {step_type}"}
                
                results.append({
                    "step": step.get("name", step_type),
                    "result": result
                })
                
                # Check for condition
                if step.get("condition"):
                    condition = step["condition"]
                    if condition.get("if_error") and "error" in result:
                        self.logger.warning(f"Condition triggered: {condition.get('if_error')}")
                        break
            
            return results
            
        except Exception as e:
            self.logger.error(f"Script execution failed: {e}")
            return [{"error": str(e)}]

# CLI Commands
def setup_commands():
    """Setup CLI command parser"""
    parser = argparse.ArgumentParser(
        description="MCP Studio CLI - Automation interface for MCP Studio",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s chat "Hello, how are you?"
  %(prog)s tool filesystem read_file '{"path": "config.json"}'
  %(prog)s script automation/workflow.json
  %(prog)s batch tools/data_processing.json --concurrent
  %(prog)s servers list --format table
        """
    )
    
    # Global arguments
    parser.add_argument('--config', help='Configuration file path')
    parser.add_argument('--format', choices=['json', 'yaml', 'csv', 'table'], help='Output format')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Chat command
    chat_parser = subparsers.add_parser('chat', help='Chat with AI models')
    chat_parser.add_argument('message', help='Message to send')
    chat_parser.add_argument('--model', help='Model to use')
    
    # Tool command
    tool_parser = subparsers.add_parser('tool', help='Execute a tool')
    tool_parser.add_argument('server', help='Server name')
    tool_parser.add_argument('tool_name', help='Tool name')
    tool_parser.add_argument('arguments', help='JSON arguments')
    
    # Batch command
    batch_parser = subparsers.add_parser('batch', help='Execute batch operations')
    batch_parser.add_argument('file', help='Batch JSON file')
    batch_parser.add_argument('--concurrent', action='store_true', help='Execute concurrently')
    
    # Script command
    script_parser = subparsers.add_parser('script', help='Run automation script')
    script_parser.add_argument('file', help='Script JSON file')
    
    # Servers command
    servers_parser = subparsers.add_parser('servers', help='Manage servers')
    servers_subparsers = servers_parser.add_subparsers(dest='servers_command')
    servers_subparsers.add_parser('list', help='List servers')
    servers_subparsers.add_parser('connect', help='Connect to server').add_argument('name', help='Server name')
    
    # Tools command
    tools_parser = subparsers.add_parser('tools', help='List available tools')
    tools_parser.add_argument('--server', help='Filter by server')
    
    # Fine-tune command
    finetune_parser = subparsers.add_parser('finetune', help='Fine-tune a model')
    finetune_parser.add_argument('config', help='Fine-tuning configuration file')
    
    # Config command
    config_parser = subparsers.add_parser('config', help='Manage configuration')
    config_subparsers = config_parser.add_subparsers(dest='config_command')
    config_subparsers.add_parser('show', help='Show current configuration')
    config_subparsers.add_parser('set', help='Set configuration').add_argument('key', help='Config key').add_argument('value', help='Config value')
    config_subparsers.add_parser('test', help='Test API connection')
    
    # Generate command
    generate_parser = subparsers.add_parser('generate', help='Generate templates')
    generate_subparsers = generate_parser.add_subparsers(dest='generate_command')
    generate_subparsers.add_parser('batch', help='Generate batch template').add_argument('name', help='Template name')
    generate_subparsers.add_parser('script', help='Generate script template').add_argument('name', help='Script name')
    
    return parser

async def main():
    """Main CLI entry point"""
    parser = setup_commands()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Setup CLI
    cli = MCPCLI(args.config)
    
    if args.debug:
        cli.logger.setLevel(logging.DEBUG)
    
    # Connect to API
    if not await cli.connect():
        print("Failed to connect to MCP Studio API")
        sys.exit(1)
    
    try:
        # Handle commands
        if args.command == "chat":
            result = await cli.chat(args.message, args.model)
            print(cli.format_output(result, args.format))
        
        elif args.command == "tool":
            arguments = json.loads(args.arguments)
            result = await cli.execute_tool(args.server, args.tool_name, arguments)
            print(cli.format_output(result, args.format))
        
        elif args.command == "batch":
            result = await cli.batch_execute(args.file, args.concurrent)
            print(cli.format_output(result, args.format))
        
        elif args.command == "script":
            results = await cli.run_script(args.file)
            print(cli.format_output(results, args.format))
        
        elif args.command == "servers":
            if args.servers_command == "list":
                servers = await cli.list_servers()
                print(cli.format_output(servers, args.format))
            elif args.servers_command == "connect":
                result = await cli.connect_server(args.name)
                print(cli.format_output(result, args.format))
        
        elif args.command == "tools":
            tools = await cli.list_tools()
            if args.server:
                tools = [t for t in tools if t.get("server") == args.server]
            print(cli.format_output(tools, args.format))
        
        elif args.command == "finetune":
            result = await cli.fine_tune(args.config)
            print(cli.format_output(result, args.format))
        
        elif args.command == "config":
            if args.config_command == "show":
                print(cli.format_output(cli.config, args.format))
            elif args.config_command == "set":
                cli.config[args.key] = args.value
                cli.save_config()
                print(f"Configuration updated: {args.key} = {args.value}")
            elif args.config_command == "test":
                if await cli.connect():
                    print("✓ Connection successful")
                else:
                    print("✗ Connection failed")
        
        elif args.command == "generate":
            if args.generate_command == "batch":
                template = create_batch_template(args.name)
                print(cli.format_output(template, args.format))
            elif args.generate_command == "script":
                template = create_script_template(args.name)
                print(cli.format_output(template, args.format))
    
    except Exception as e:
        cli.logger.error(f"Command failed: {e}")
        print(f"Error: {e}")
        sys.exit(1)
    
    finally:
        await cli.disconnect()

def create_batch_template(name: str) -> Dict:
    """Create a batch template"""
    return {
        "name": name,
        "description": f"Batch job: {name}",
        "tools": [
            {
                "server": "filesystem",
                "tool": "list_files",
                "arguments": {"path": ".", "recursive": True}
            },
            {
                "server": "filesystem",
                "tool": "read_file",
                "arguments": {"path": "config.json"}
            }
        ]
    }

def create_script_template(name: str) -> Dict:
    """Create a script template"""
    return {
        "name": name,
        "description": f"Automation script: {name}",
        "steps": [
            {
                "type": "chat",
                "name": "Initial greeting",
                "message": "Hello, prepare to execute the workflow"
            },
            {
                "type": "tool",
                "name": "List files",
                "server": "filesystem",
                "tool": "list_files",
                "arguments": {"path": "."}
            },
            {
                "type": "wait",
                "name": "Processing delay",
                "seconds": 2
            }
        ]
    }

# Create example scripts directory
def create_example_scripts():
    """Create example automation scripts"""
    examples_dir = Path.home() / ".mcp-studio" / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    # Data processing script
    data_processing = {
        "name": "data_processing",
        "description": "Process data files",
        "steps": [
            {
                "type": "tool",
                "name": "List data files",
                "server": "filesystem",
                "tool": "list_files",
                "arguments": {"path": "./data", "pattern": "*.csv"}
            },
            {
                "type": "tool",
                "name": "Read first CSV",
                "server": "filesystem",
                "tool": "read_file",
                "arguments": {"path": "./data/sample.csv"}
            },
            {
                "type": "chat",
                "name": "Analyze data",
                "message": "Analyze this CSV data and provide insights",
                "model": "llama3.1"
            },
            {
                "type": "tool",
                "name": "Save analysis",
                "server": "filesystem",
                "tool": "write_file",
                "arguments": {"path": "./analysis.txt", "content": "{{previous_result}}"}
            }
        ]
    }
    
    with open(examples_dir / "data_processing.json", 'w') as f:
        json.dump(data_processing, f, indent=2)
    
    # Model training script
    model_training = {
        "name": "model_training",
        "description": "Fine-tune a model",
        "steps": [
            {
                "type": "chat",
                "name": "Prepare training",
                "message": "Prepare training data for fine-tuning",
                "model": "llama3.1"
            },
            {
                "type": "finetune",
                "name": "Start training",
                "config_file": "./training_config.json"
            },
            {
                "type": "wait",
                "name": "Wait for training",
                "seconds": 300
            },
            {
                "type": "chat",
                "name": "Check results",
                "message": "Check if training completed successfully",
                "model": "llama3.1"
            }
        ]
    }
    
    with open(examples_dir / "model_training.json", 'w') as f:
        json.dump(model_training, f, indent=2)
    
    print(f"Example scripts created in: {examples_dir}")

if __name__ == "__main__":
    # Create example scripts on first run
    if not (Path.home() / ".mcp-studio" / "examples").exists():
        create_example_scripts()
    
    # Run CLI
    asyncio.run(main())
