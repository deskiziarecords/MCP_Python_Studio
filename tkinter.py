import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading

class MCPStudioTkinter:
    def __init__(self, root):
        self.root = root
        self.root.title("Python MCP Studio")
        self.root.geometry("1200x800")
        
        # Configure styles
        self.setup_styles()
        
        # Create main layout
        self.setup_layout()
        
        # Initialize state
        self.current_model = tk.StringVar(value="claude-3-5-sonnet")
        self.connected_servers = []
        
    def setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        # Custom colors
        self.bg_color = "#f5f5f5"
        self.sidebar_color = "#2c3e50"
        self.accent_color = "#3498db"
        
        self.root.configure(bg=self.bg_color)
    
    def setup_layout(self):
        # Main container
        main_container = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        main_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left sidebar
        self.sidebar = ttk.Frame(main_container, width=250)
        main_container.add(self.sidebar, weight=1)
        
        # Main content area
        content_frame = ttk.Frame(main_container)
        main_container.add(content_frame, weight=4)
        
        # Build sidebar components
        self.build_sidebar(self.sidebar)
        
        # Build main content
        self.build_content(content_frame)
    
    def build_sidebar(self, parent):
        # Title
        title_label = ttk.Label(parent, text="MCP Studio", 
                               font=("Arial", 16, "bold"),
                               foreground=self.accent_color)
        title_label.pack(pady=20)
        
        # Model selection
        ttk.Label(parent, text="AI Model:").pack(anchor=tk.W, padx=10, pady=(20,5))
        
        models = ["claude-3-5-sonnet", "gpt-4o", "gemini-2.0", "llama-3.1", "qwen-2.5"]
        model_combo = ttk.Combobox(parent, textvariable=self.current_model, 
                                  values=models, state="readonly")
        model_combo.pack(fill=tk.X, padx=10, pady=(0,10))
        
        # Connected servers
        servers_frame = ttk.LabelFrame(parent, text="Connected Servers", padding=10)
        servers_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.servers_listbox = tk.Listbox(servers_frame, height=8, 
                                         bg="white", relief=tk.FLAT)
        self.servers_listbox.pack(fill=tk.X)
        
        # Server controls
        server_buttons = ttk.Frame(servers_frame)
        server_buttons.pack(fill=tk.X, pady=(5,0))
        
        ttk.Button(server_buttons, text="Add", 
                  command=self.add_server_dialog).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(server_buttons, text="Remove", 
                  command=self.remove_server).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Quick prompts
        ttk.Label(parent, text="Quick Prompts:").pack(anchor=tk.W, padx=10, pady=(20,5))
        
        prompts = ["/code - Code generation", "/debug - Debug assistance", 
                  "/review - Code review", "/explain - Explain concept"]
        for prompt in prompts:
            btn = ttk.Button(parent, text=prompt, 
                           command=lambda p=prompt: self.insert_prompt(p))
            btn.pack(fill=tk.X, padx=10, pady=2)
    
    def build_content(self, parent):
        # Chat header
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(header_frame, text="Chat", font=("Arial", 14)).pack(side=tk.LEFT)
        
        # Status indicators
        status_frame = ttk.Frame(header_frame)
        status_frame.pack(side=tk.RIGHT)
        
        self.connection_status = ttk.Label(status_frame, text="● Disconnected", 
                                          foreground="red")
        self.connection_status.pack(side=tk.LEFT, padx=5)
        
        # Chat display
        chat_container = ttk.Frame(parent)
        chat_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))
        
        self.chat_display = scrolledtext.ScrolledText(
            chat_container, 
            wrap=tk.WORD,
            bg="white",
            font=("Consolas", 10),
            height=20
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.config(state=tk.DISABLED)
        
        # Tool output area (collapsible)
        self.tools_frame = ttk.LabelFrame(parent, text="Tool Output", padding=5)
        self.tools_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        
        self.tool_output = scrolledtext.ScrolledText(
            self.tools_frame,
            wrap=tk.WORD,
            bg="#f8f9fa",
            font=("Consolas", 9),
            height=6
        )
        self.tool_output.pack(fill=tk.BOTH, expand=True)
        self.tool_output.config(state=tk.DISABLED)
        
        # Input area
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill=tk.X, padx=10, pady=(0,10))
        
        self.message_input = scrolledtext.ScrolledText(
            input_frame,
            wrap=tk.WORD,
            height=4,
            font=("Arial", 10)
        )
        self.message_input.pack(fill=tk.X, pady=(0,5))
        
        # Input buttons
        button_frame = ttk.Frame(input_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(button_frame, text="Send", 
                  command=self.send_message).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Clear", 
                  command=self.clear_chat).pack(side=tk.RIGHT)
    
    def insert_prompt(self, prompt):
        self.message_input.insert(tk.END, prompt.split(" - ")[0] + " ")
        self.message_input.focus()
    
    def send_message(self):
        message = self.message_input.get("1.0", tk.END).strip()
        if message:
            self.display_message("You", message)
            self.message_input.delete("1.0", tk.END)
            # Simulate AI response
            self.root.after(1000, self.simulate_ai_response, message)
    
    def display_message(self, sender, message):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"\n{sender}:\n{message}\n{'='*50}\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
    
    def simulate_ai_response(self, message):
        self.display_message("AI", f"Processing: {message}\n[This would connect to {self.current_model.get()}]")
        self.update_tool_output("Tool executed: filesystem.read()\n- Read file: config.json\n- Content: {...}")
    
    def update_tool_output(self, text):
        self.tool_output.config(state=tk.NORMAL)
        self.tool_output.delete("1.0", tk.END)
        self.tool_output.insert(tk.END, text)
        self.tool_output.config(state=tk.DISABLED)
    
    def add_server_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add MCP Server")
        dialog.geometry("400x300")
        
        ttk.Label(dialog, text="Server Type:").pack(anchor=tk.W, padx=20, pady=(20,5))
        server_type = ttk.Combobox(dialog, values=["stdio", "sse", "http"], state="readonly")
        server_type.pack(fill=tk.X, padx=20)
        
        ttk.Label(dialog, text="Command/URL:").pack(anchor=tk.W, padx=20, pady=(10,5))
        server_url = ttk.Entry(dialog)
        server_url.pack(fill=tk.X, padx=20)
        
        def add_server():
            server_info = f"{server_type.get()}: {server_url.get()}"
            self.servers_listbox.insert(tk.END, server_info)
            self.connected_servers.append(server_info)
            self.connection_status.config(text="● Connected", foreground="green")
            dialog.destroy()
        
        ttk.Button(dialog, text="Connect", command=add_server).pack(pady=20)
    
    def remove_server(self):
        selection = self.servers_listbox.curselection()
        if selection:
            self.servers_listbox.delete(selection[0])
            if self.servers_listbox.size() == 0:
                self.connection_status.config(text="● Disconnected", foreground="red")
    
    def clear_chat(self):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        self.chat_display.config(state=tk.DISABLED)

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = MCPStudioTkinter(root)
    root.mainloop()
