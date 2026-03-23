#!/usr/bin/env python3
"""
Unified File System MCP Chat App.
A centralized chat application that automatically connects everything.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import json
import threading
import time
import asyncio
import subprocess
import os
import sys
from datetime import datetime
from pathlib import Path

# Ensure the project root is in the Python path
def add_project_root_to_path():
    """Adds the project root directory to the system path."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

add_project_root_to_path()

from core.file_system_analyzer import FileSystemMCPTool
from utils.unified_ai_client import get_client

class UnifiedChatApp:
    """
    A unified chat application for the File System MCP.

    Attributes:
        root: The root Tkinter window.
        tool (FileSystemMCPTool): The file system analysis tool.
        ai_client (UnifiedAIClient): The unified client for AI interaction.
        current_session_id (str): The current scan session ID.
        scanning (bool): A flag indicating if a scan is in progress.
        ai_provider (str): The name of the AI provider to use.
    """
    def __init__(self, root):
        """
        Initializes the UnifiedChatApp.

        Args:
            root: The root Tkinter window.
        """
        self.root = root
        self.root.title("🚀 File System MCP - Unified Chat")
        self.root.geometry("1400x900")
        self.root.configure(bg='#1e1e1e')
        
        # Force window to front and make it copyable
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # Initialize components
        self.tool = FileSystemMCPTool()
        self.ai_client = get_client()
        self.ai_provider = 'ollama'  # This app primarily uses Ollama
        self.current_session_id = None
        self.scanning = False
        
        # Setup UI
        self.setup_ui()
        self.setup_styles()
        
        # Cleanup on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Auto-start services
        self.auto_start_services()
        
    def setup_styles(self):
        """Sets up the UI styles."""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors for dark theme
        style.configure('Dark.TFrame', background='#1e1e1e')
        style.configure('Dark.TLabel', background='#1e1e1e', foreground='#ffffff')
        style.configure('Dark.TButton', 
                       background='#007acc', 
                       foreground='white',
                       font=('Segoe UI', 10, 'bold'))
        
    def setup_ui(self):
        """Creates the main UI."""
        # Main container
        main_frame = ttk.Frame(self.root, style='Dark.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Header with status
        self.setup_header(main_frame)
        
        # Split view: Chat and Control Panel
        paned_window = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Left side: Chat area
        self.setup_chat_area(paned_window)
        
        # Right side: Control panel
        self.setup_control_panel(paned_window)
        
        # Input area at bottom
        self.setup_input_area(main_frame)
        
    def setup_header(self, parent):
        """
        Creates the header with status indicators.

        Args:
            parent: The parent widget.
        """
        header_frame = ttk.Frame(parent, style='Dark.TFrame')
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Title
        title_label = tk.Label(header_frame, 
                              text="🚀 File System MCP - Unified Chat", 
                              font=('Segoe UI', 18, 'bold'),
                              fg='#ffffff',
                              bg='#1e1e1e')
        title_label.pack(side=tk.LEFT)
        
        # Status indicators
        status_frame = tk.Frame(header_frame, bg='#1e1e1e')
        status_frame.pack(side=tk.RIGHT)
        
        # File System Status
        self.fs_status = tk.Label(status_frame,
                                 text="📁 File System: Connecting...",
                                 font=('Segoe UI', 9),
                                 fg='#ffaa00',
                                 bg='#1e1e1e')
        self.fs_status.pack(side=tk.LEFT, padx=(0, 10))
        
        # Ollama Status
        self.ollama_status = tk.Label(status_frame,
                                     text="🤖 Ollama: Connecting...",
                                     font=('Segoe UI', 9),
                                     fg='#ffaa00',
                                     bg='#1e1e1e')
        self.ollama_status.pack(side=tk.LEFT, padx=(0, 10))
        
        # Session Status
        self.session_status = tk.Label(status_frame,
                                      text="💾 Session: None",
                                      font=('Segoe UI', 9),
                                      fg='#cccccc',
                                      bg='#1e1e1e')
        self.session_status.pack(side=tk.LEFT)
        
    def setup_chat_area(self, parent):
        """
        Creates the chat area.

        Args:
            parent: The parent widget.
        """
        chat_frame = ttk.Frame(parent, style='Dark.TFrame')
        parent.add(chat_frame, weight=3)
        
        # Chat display with copy functionality
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame,
            wrap=tk.WORD,
            font=('Consolas', 11),
            bg='#2d2d2d',
            fg='#ffffff',
            insertbackground='#ffffff',
            selectbackground='#007acc',
            state=tk.NORMAL,  # Allow copying
            cursor='ibeam'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Add right-click menu for copy/paste
        self.setup_context_menu()
        
    def setup_context_menu(self):
        """Creates the right-click context menu for copy/paste."""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="📋 Copy", command=self.copy_selected)
        self.context_menu.add_command(label="📋 Copy All", command=self.copy_all)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Clear Chat", command=self.clear_chat)
        
        self.chat_display.bind("<Button-3>", self.show_context_menu)
        
    def show_context_menu(self, event):
        """
        Shows the right-click context menu.

        Args:
            event: The event that triggered the menu.
        """
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
            
    def copy_selected(self):
        """Copies the selected text."""
        try:
            selected_text = self.chat_display.get(tk.SEL_FIRST, tk.SEL_LAST)
            self.root.clipboard_clear()
            self.root.clipboard_append(selected_text)
            self.add_system_message("✅ Text copied")
        except tk.TclError:
            self.add_system_message("⚠️ No text selected")
            
    def copy_all(self):
        """Copies all text."""
        all_text = self.chat_display.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(all_text)
        self.add_system_message("✅ All text copied")
        
    def clear_chat(self):
        """Clears the chat."""
        self.chat_display.delete(1.0, tk.END)
        self.add_system_message("🗑️ Chat cleared")
        
    def setup_control_panel(self, parent):
        """
        Creates the control panel.

        Args:
            parent: The parent widget.
        """
        control_frame = ttk.Frame(parent, style='Dark.TFrame')
        parent.add(control_frame, weight=1)
        
        # Control panel title
        title_label = tk.Label(control_frame,
                              text="🎛️ Control Panel",
                              font=('Segoe UI', 14, 'bold'),
                              fg='#ffffff',
                              bg='#1e1e1e')
        title_label.pack(pady=(0, 15))
        
        # Quick actions
        self.setup_quick_actions(control_frame)
        
        # File operations
        self.setup_file_operations(control_frame)
        
        # AI operations
        self.setup_ai_operations(control_frame)
        
        # System info
        self.setup_system_info(control_frame)
        
    def setup_quick_actions(self, parent):
        """
        Creates the quick action buttons.

        Args:
            parent: The parent widget.
        """
        quick_frame = tk.LabelFrame(parent, text="⚡ Quick Actions", 
                                   font=('Segoe UI', 10, 'bold'),
                                   fg='#ffffff', bg='#1e1e1e')
        quick_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Scan button
        self.scan_btn = tk.Button(quick_frame,
                                 text="📁 Scan Folder",
                                 command=self.scan_folder,
                                 bg='#007acc',
                                 fg='white',
                                 font=('Segoe UI', 10, 'bold'),
                                 relief=tk.FLAT,
                                 padx=15,
                                 pady=8)
        self.scan_btn.pack(fill=tk.X, padx=10, pady=5)
        
        # Quick queries
        queries = [
            ("📊 Summary", "give me summary"),
            ("🔍 Large Files", "show me large files"),
            ("🔄 Duplicates", "find duplicate files"),
            ("📁 File Types", "show file types")
        ]
        
        for text, query in queries:
            btn = tk.Button(quick_frame,
                           text=text,
                           command=lambda q=query: self.quick_query(q),
                           bg='#2d2d2d',
                           fg='#ffffff',
                           font=('Segoe UI', 9),
                           relief=tk.FLAT,
                           padx=10,
                           pady=5)
            btn.pack(fill=tk.X, padx=10, pady=2)
            
    def setup_file_operations(self, parent):
        """
        Creates the file operations section.

        Args:
            parent: The parent widget.
        """
        file_frame = tk.LabelFrame(parent, text="📁 File Operations", 
                                  font=('Segoe UI', 10, 'bold'),
                                  fg='#ffffff', bg='#1e1e1e')
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File search
        search_frame = tk.Frame(file_frame, bg='#1e1e1e')
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        tk.Label(search_frame, text="Search:", font=('Segoe UI', 9), 
                fg='#ffffff', bg='#1e1e1e').pack(side=tk.LEFT)
        
        self.search_entry = tk.Entry(search_frame, font=('Segoe UI', 9),
                                    bg='#2d2d2d', fg='#ffffff',
                                    insertbackground='#ffffff')
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        self.search_entry.bind('<Return>', lambda e: self.search_files())
        
        search_btn = tk.Button(search_frame, text="🔍", command=self.search_files,
                              bg='#007acc', fg='white', font=('Segoe UI', 9))
        search_btn.pack(side=tk.RIGHT)
        
    def setup_ai_operations(self, parent):
        """
        Creates the AI operations section.

        Args:
            parent: The parent widget.
        """
        ai_frame = tk.LabelFrame(parent, text="🤖 AI Assistant", 
                                font=('Segoe UI', 10, 'bold'),
                                fg='#ffffff', bg='#1e1e1e')
        ai_frame.pack(fill=tk.X, pady=(0, 10))
        
        # AI status
        self.ai_status_label = tk.Label(ai_frame,
                                       text="Status: Connecting...",
                                       font=('Segoe UI', 9),
                                       fg='#ffaa00',
                                       bg='#1e1e1e')
        self.ai_status_label.pack(pady=5)
        
        # AI actions
        ai_actions = [
            ("🧠 Analyze Structure", self.analyze_structure),
            ("📋 Generate Report", self.generate_report),
            ("💡 Get Suggestions", self.get_suggestions),
            ("🔍 Smart Search", self.smart_search)
        ]
        
        for text, command in ai_actions:
            btn = tk.Button(ai_frame, text=text, command=command,
                           bg='#2d2d2d', fg='#ffffff',
                           font=('Segoe UI', 9), relief=tk.FLAT,
                           padx=10, pady=5)
            btn.pack(fill=tk.X, padx=10, pady=2)
            
    def setup_system_info(self, parent):
        """
        Creates the system info section.

        Args:
            parent: The parent widget.
        """
        info_frame = tk.LabelFrame(parent, text="ℹ️ System Info", 
                                  font=('Segoe UI', 10, 'bold'),
                                  fg='#ffffff', bg='#1e1e1e')
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.info_text = tk.Text(info_frame, height=6, font=('Consolas', 8),
                                bg='#2d2d2d', fg='#ffffff',
                                insertbackground='#ffffff', state=tk.DISABLED)
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
    def setup_input_area(self, parent):
        """
        Creates the input area.

        Args:
            parent: The parent widget.
        """
        input_frame = ttk.Frame(parent, style='Dark.TFrame')
        input_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Input field with placeholder
        self.input_field = tk.Entry(input_frame,
                                   font=('Segoe UI', 12),
                                   bg='#2d2d2d',
                                   fg='#ffffff',
                                   insertbackground='#ffffff',
                                   relief=tk.FLAT)
        self.input_field.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.input_field.bind('<Return>', self.send_message)
        
        # Placeholder text
        self.input_field.insert(0, "💬 Type a question or command...")
        self.input_field.bind('<FocusIn>', self.on_entry_click)
        self.input_field.bind('<FocusOut>', self.on_focus_out)
        self.input_field.config(fg='#888888')
        
        # Send button
        send_btn = tk.Button(input_frame,
                            text="🚀 Send",
                            command=self.send_message,
                            bg='#007acc',
                            fg='white',
                            font=('Segoe UI', 11, 'bold'),
                            relief=tk.FLAT,
                            padx=20,
                            pady=8)
        send_btn.pack(side=tk.RIGHT)
        
    def on_entry_click(self, event):
        """
        Handles the event when the input field is clicked.

        Args:
            event: The event that triggered the handler.
        """
        if self.input_field.get() == "💬 Type a question or command...":
            self.input_field.delete(0, tk.END)
            self.input_field.config(fg='#ffffff')
            
    def on_focus_out(self, event):
        """
        Handles the event when the input field loses focus.

        Args:
            event: The event that triggered the handler.
        """
        if not self.input_field.get():
            self.input_field.insert(0, "💬 Type a question or command...")
            self.input_field.config(fg='#888888')
            
    def auto_start_services(self):
        """Automatically starts the required services."""
        self.add_system_message("🚀 Starting system...")
        
        # Start File System service
        self.start_file_system_service()
        
        # Start Ollama service
        self.start_ollama_service()
        
    def start_file_system_service(self):
        """Starts the File System service."""
        def start_fs():
            try:
                # Test File System connection
                test_result = self.tool._run(json.dumps({
                    "action": "query_function",
                    "function": "get_directory_summary",
                    "session_id": "test",
                    "args": []
                }))
                
                self.root.after(0, lambda: self.update_fs_status("✅ Connected", "#00ff00"))
                self.root.after(0, lambda: self.add_system_message("✅ File System service is ready."))
                
            except Exception as e:
                self.root.after(0, lambda: self.update_fs_status("❌ Error", "#ff4444"))
                self.root.after(0, lambda: self.add_system_message(f"❌ File System error: {str(e)}"))
                
        threading.Thread(target=start_fs, daemon=True).start()
        
    def start_ollama_service(self):
        """Checks for the configured AI provider's availability."""
        def check_ai_provider():
            if self.ai_client and self.ai_client.get_provider(self.ai_provider):
                self.root.after(0, lambda: self.update_ai_status("✅ Connected", "#00ff00"))
                self.root.after(0, lambda: self.add_system_message(f"✅ AI provider '{self.ai_provider}' is ready."))
            else:
                self.root.after(0, lambda: self.update_ai_status("❌ Not Connected", "#ff4444"))
                self.root.after(0, lambda: self.add_system_message(f"⚠️ AI provider '{self.ai_provider}' is not available. Using File System only."))

        threading.Thread(target=check_ai_provider, daemon=True).start()

    def update_fs_status(self, text, color):
        """
        Updates the File System status.

        Args:
            text (str): The status text.
            color (str): The color of the status text.
        """
        self.fs_status.config(text=f"📁 File System: {text}", fg=color)

    def update_ai_status(self, text, color):
        """
        Updates the AI provider status.

        Args:
            text (str): The status text.
            color (str): The color of the status text.
        """
        self.ollama_status.config(text=f"🤖 AI ({self.ai_provider}): {text}", fg=color)
        
    def add_message(self, sender: str, message: str, message_type: str = "normal"):
        """
        Adds a message to the chat.

        Args:
            sender (str): The sender of the message.
            message (str): The message content.
            message_type (str, optional): The type of the message. Defaults to "normal".
        """
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format message based on type
        if message_type == "system":
            formatted_message = f"[{timestamp}] 🤖 {message}\n\n"
            self.chat_display.insert(tk.END, formatted_message)
            self.chat_display.tag_add("system", f"end-{len(formatted_message)+1}c", "end-1c")
            self.chat_display.tag_config("system", foreground="#00ff00")
        elif message_type == "user":
            formatted_message = f"[{timestamp}] 👤 You: {message}\n\n"
            self.chat_display.insert(tk.END, formatted_message)
            self.chat_display.tag_add("user", f"end-{len(formatted_message)+1}c", "end-1c")
            self.chat_display.tag_config("user", foreground="#007acc")
        elif message_type == "result":
            formatted_message = f"[{timestamp}] 📊 Result:\n{message}\n\n"
            self.chat_display.insert(tk.END, formatted_message)
            self.chat_display.tag_add("result", f"end-{len(formatted_message)+1}c", "end-1c")
            self.chat_display.tag_config("result", foreground="#ffaa00")
        elif message_type == "error":
            formatted_message = f"[{timestamp}] ❌ Error: {message}\n\n"
            self.chat_display.insert(tk.END, formatted_message)
            self.chat_display.tag_add("error", f"end-{len(formatted_message)+1}c", "end-1c")
            self.chat_display.tag_config("error", foreground="#ff4444")
        elif message_type == "ai":
            formatted_message = f"[{timestamp}] 🤖 AI: {message}\n\n"
            self.chat_display.insert(tk.END, formatted_message)
            self.chat_display.tag_add("ai", f"end-{len(formatted_message)+1}c", "end-1c")
            self.chat_display.tag_config("ai", foreground="#ff66cc")
        
        self.chat_display.see(tk.END)
        
    def add_system_message(self, message: str):
        """
        Adds a system message to the chat.

        Args:
            message (str): The system message.
        """
        self.add_message("system", message, "system")
        
    def scan_folder(self):
        """Scans a folder."""
        if self.scanning:
            messagebox.showwarning("Scanning", "Please wait for the current scan to finish.")
            return
            
        folder_path = filedialog.askdirectory(title="Select a folder to scan")
        if not folder_path:
            return
            
        self.scanning = True
        self.scan_btn.config(state=tk.DISABLED, text="⏳ Scanning...")
        
        # Run scan in separate thread
        thread = threading.Thread(target=self._perform_scan, args=(folder_path,))
        thread.daemon = True
        thread.start()
        
    def _perform_scan(self, folder_path: str):
        """
        Performs the scan in a separate thread.

        Args:
            folder_path (str): The path to the folder to scan.
        """
        try:
            self.root.after(0, lambda: self.add_system_message(f"🔍 Starting to scan folder: {folder_path}"))
            
            scan_params = {
                "action": "scan",
                "path": folder_path,
                "config": {
                    "max_depth": 10,
                    "include_hidden": False,
                    "calculate_hashes": True,
                    "hash_size_limit_mb": 50
                }
            }
            
            result = self.tool._run(json.dumps(scan_params))
            
            if "Session ID:" in result:
                self.current_session_id = result.split("Session ID: ")[1].strip()
                self.root.after(0, lambda: self.add_system_message(f"✅ Scan complete! Session ID: {self.current_session_id}"))
                self.root.after(0, lambda: self.session_status.config(text=f"💾 Session: {self.current_session_id[:8]}..."))
                self.root.after(0, lambda: self.update_system_info())
            else:
                self.root.after(0, lambda: self.add_system_message(f"❌ Scan failed: {result}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.add_system_message(f"❌ An error occurred: {str(e)}"))
        finally:
            self.scanning = False
            self.root.after(0, lambda: self.scan_btn.config(state=tk.NORMAL, text="📁 Scan Folder"))
            
    def send_message(self, event=None):
        """Sends a message."""
        message = self.input_field.get().strip()
        if not message or message == "💬 Type a question or command...":
            return
            
        self.input_field.delete(0, tk.END)
        self.input_field.insert(0, "💬 Type a question or command...")
        self.input_field.config(fg='#888888')
        
        self.add_message("user", message, "user")
        
        # Process message in separate thread
        thread = threading.Thread(target=self._process_message, args=(message,))
        thread.daemon = True
        thread.start()
        
    def _process_message(self, message: str):
        """
        Processes a message.

        Args:
            message (str): The message to process.
        """
        try:
            if not self.current_session_id:
                self.root.after(0, lambda: self.add_system_message("⚠️ Please scan a folder before use."))
                return
                
            # Check for special commands
            if message.lower().startswith("/help"):
                self._show_help()
                return
            elif message.lower().startswith("/scan"):
                self.root.after(0, lambda: self.add_system_message("Use the 'Scan Folder' button to scan a new folder."))
                return
                
            # Try AI first if available
            if self._should_use_ai(message):
                self._process_with_ai(message)
            else:
                # Use File System query
                self._process_with_filesystem(message)

        except Exception as e:
            self.root.after(0, lambda: self.add_message("error", f"An error occurred: {str(e)}", "error"))

    def _should_use_ai(self, message: str):
        """
        Checks if AI should be used. It's true if the client is available
        and the message contains AI-related keywords.

        Args:
            message (str): The message to check.

        Returns:
            bool: True if AI should be used, False otherwise.
        """
        if not self.ai_client or not self.ai_client.get_provider(self.ai_provider):
            return False
        ai_keywords = ['analyze', 'explain', 'suggest', 'recommend', 'why', 'how', 'what', 'วิเคราะห์', 'อธิบาย', 'แนะนำ', 'ทำไม', 'อย่างไร', 'อะไร']
        return any(keyword in message.lower() for keyword in ai_keywords)

    def _process_with_ai(self, message: str):
        """
        Processes a message with the UnifiedAIClient.

        Args:
            message (str): The message to process.
        """
        try:
            fs_data = self._get_filesystem_data()
            self.root.after(0, lambda: self.add_system_message(f"🤖 Sending request to AI ({self.ai_provider})..."))
            # Run in a thread to keep the UI responsive
            thread = threading.Thread(target=self._ask_ai, args=(message, fs_data))
            thread.daemon = True
            thread.start()
        except Exception as e:
            self.root.after(0, lambda: self.add_system_message("⚠️ AI processing failed. Using File System instead."))
            self._process_with_filesystem(message)

    def _process_with_filesystem(self, message: str):
        """
        Processes a message with the File System tool.

        Args:
            message (str): The message to process.
        """
        try:
            query_params = {
                "action": "query_natural",
                "request": message,
                "session_id": self.current_session_id
            }
            result = self.tool._run(json.dumps(query_params))
            try:
                result_data = json.loads(result)
                if result_data.get('success'):
                    formatted_result = self._format_result(result_data.get('data', result_data))
                    self.root.after(0, lambda: self.add_message("result", formatted_result, "result"))
                else:
                    self.root.after(0, lambda: self.add_message("error", result_data.get('error', 'Could not process'), "error"))
            except json.JSONDecodeError:
                self.root.after(0, lambda: self.add_message("result", result, "result"))
        except Exception as e:
            self.root.after(0, lambda: self.add_message("error", f"An error occurred: {str(e)}", "error"))

    def _get_filesystem_data(self):
        """
        Gets a summary of file system data for the AI context.

        Returns:
            dict: A dictionary containing the file system data summary.
        """
        try:
            summary_params = {
                "action": "query_function",
                "function": "get_directory_summary",
                "session_id": self.current_session_id,
                "args": []
            }
            result = self.tool._run(json.dumps(summary_params))
            # The result from the tool is a JSON string, so we parse it
            return json.loads(result)
        except Exception:
            return {"error": "No file system data available"}

    def _ask_ai(self, message, fs_data):
        """
        Asks the AI a question using the UnifiedAIClient.

        Args:
            message (str): The question to ask.
            fs_data (dict): The file system data summary.
        """
        try:
            system_prompt = """You are a helpful File System Analysis Assistant. Your job is to analyze file system data and provide clear, useful answers in Thai.
IMPORTANT: Use the actual file system data provided. Do not say you cannot help with file management - this IS your job."""

            # Create a clear prompt with context
            user_prompt = f"""FILE SYSTEM DATA:
{json.dumps(fs_data, indent=2, ensure_ascii=False)}

USER QUESTION: {message}

TASK: Analyze the file system data above and answer the user's question. Be specific and helpful."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    response = executor.submit(asyncio.run, self.ai_client.generate_response(self.ai_provider, messages)).result()
            else:
                response = asyncio.run(self.ai_client.generate_response(self.ai_provider, messages))

            if response and response.get('success'):
                ai_response = response.get('content', 'Could not process')
                self.root.after(0, lambda: self.add_message("ai", ai_response, "ai"))
            else:
                error_msg = response.get('error', 'Ollama request failed')
                self.root.after(0, lambda: self.add_message("error", f"AI Error: {error_msg}", "error"))

        except Exception as e:
            self.root.after(0, lambda: self.add_message("error", f"An unexpected error occurred while asking the AI: {str(e)}", "error"))
            # Fallback to filesystem if AI fails catastrophically
            self._process_with_filesystem(message)
            
    def _format_file_types(self, file_types):
        """
        Formats the file types.

        Args:
            file_types: The file types to format.

        Returns:
            str: The formatted file types.
        """
        if not file_types:
            return "No data found"
            
        formatted = []
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]:
            formatted.append(f"   • {ext}: {count} files")
        return "\n".join(formatted)
        
    def _format_largest_files(self, largest_files):
        """
        Formats the largest files.

        Args:
            largest_files: The largest files to format.

        Returns:
            str: The formatted largest files.
        """
        if not largest_files:
            return "No data found"
            
        formatted = []
        for i, file_info in enumerate(largest_files[:3], 1):
            size_mb = file_info.get('file_size', 0) / (1024 * 1024)
            formatted.append(f"   {i}. {file_info.get('file_name', 'Unknown')} ({size_mb:.2f} MB)")
        return "\n".join(formatted)
        
    def quick_query(self, query):
        """
        Performs a quick query.

        Args:
            query (str): The query to perform.
        """
        if not self.current_session_id:
            self.add_system_message("⚠️ Please scan a folder before use.")
            return
            
        self.add_message("user", query, "user")
        
        # Process in thread
        thread = threading.Thread(target=self._process_message, args=(query,))
        thread.daemon = True
        thread.start()
        
    def search_files(self):
        """Searches for files."""
        search_term = self.search_entry.get().strip()
        if not search_term:
            return
            
        if not self.current_session_id:
            self.add_system_message("⚠️ Please scan a folder before use.")
            return
            
        self.add_message("user", f"search: {search_term}", "user")
        
        # Process in thread
        thread = threading.Thread(target=self._process_message, args=(f"find files containing {search_term}",))
        thread.daemon = True
        thread.start()
        
    def analyze_structure(self):
        """Analyzes the structure."""
        if not self.current_session_id:
            self.add_system_message("⚠️ Please scan a folder before use.")
            return
            
        self.add_message("user", "analyze the file structure and explain what this project is about", "user")
        
        thread = threading.Thread(target=self._process_message, args=("analyze the file structure and explain what this project is about",))
        thread.daemon = True
        thread.start()
        
    def generate_report(self):
        """Generates a report."""
        if not self.current_session_id:
            self.add_system_message("⚠️ Please scan a folder before use.")
            return
            
        self.add_message("user", "generate a comprehensive report about this file system", "user")
        
        thread = threading.Thread(target=self._process_message, args=("generate a comprehensive report about this file system",))
        thread.daemon = True
        thread.start()
        
    def get_suggestions(self):
        """Gets suggestions."""
        if not self.current_session_id:
            self.add_system_message("⚠️ Please scan a folder before use.")
            return
            
        self.add_message("user", "what suggestions do you have for improving this file organization", "user")
        
        thread = threading.Thread(target=self._process_message, args=("what suggestions do you have for improving this file organization",))
        thread.daemon = True
        thread.start()
        
    def smart_search(self):
        """Performs a smart search."""
        if not self.current_session_id:
            self.add_system_message("⚠️ Please scan a folder before use.")
            return
            
        self.add_message("user", "perform a smart search to find important files and patterns", "user")
        
        thread = threading.Thread(target=self._process_message, args=("perform a smart search to find important files and patterns",))
        thread.daemon = True
        thread.start()
        
    def update_system_info(self):
        """Updates the system information."""
        try:
            if self.current_session_id:
                # Get basic stats
                stats_params = {
                    "action": "query_function",
                    "function": "get_directory_summary",
                    "session_id": self.current_session_id,
                    "args": []
                }
                
                result = self.tool._run(json.dumps(stats_params))
                result_data = json.loads(result)
                
                info_text = f"""
Session: {self.current_session_id[:8]}...
Files: {result_data.get('total_files', 'N/A')}
Size: {result_data.get('total_size_mb', 'N/A')} MB
Types: {len(result_data.get('file_types', []))} types

Ollama: {'✅ Connected' if self.ollama_connected else '❌ Not Connected'}
Models: Available for AI analysis
                """
                
                self.info_text.config(state=tk.NORMAL)
                self.info_text.delete(1.0, tk.END)
                self.info_text.insert(1.0, info_text)
                self.info_text.config(state=tk.DISABLED)
                
        except Exception as e:
            pass
            
    def _format_result(self, data):
        """
        Formats the result.

        Args:
            data: The data to format.

        Returns:
            str: The formatted result.
        """
        if isinstance(data, list):
            if not data:
                return "No data found"
            
            # Check if it's a list of dictionaries (table data)
            if isinstance(data[0], dict):
                return self._format_table(data)
            else:
                return "\n".join(str(item) for item in data)
        elif isinstance(data, dict):
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            return str(data)
            
    def _format_table(self, data):
        """
        Formats data as a table.

        Args:
            data: The data to format.

        Returns:
            str: The formatted table.
        """
        if not data:
            return "No data found"
            
        # Get headers
        headers = list(data[0].keys())
        
        # Calculate column widths
        col_widths = {}
        for header in headers:
            col_widths[header] = len(str(header))
            
        for row in data:
            for header in headers:
                col_widths[header] = max(col_widths[header], len(str(row.get(header, ''))))
                
        # Create table
        table = []
        
        # Header
        header_row = " | ".join(f"{header:<{col_widths[header]}}" for header in headers)
        table.append(header_row)
        table.append("-" * len(header_row))
        
        # Data rows
        for row in data:
            row_str = " | ".join(f"{str(row.get(header, '')):<{col_widths[header]}}" for header in headers)
            table.append(row_str)
            
        return "\n".join(table)
        
    def _show_help(self):
        """Shows the help message."""
        help_text = """
📋 Available Commands:

🔍 Natural Language Queries:
• "show me large files"
• "find duplicate files"
• "give me summary"
• "show files with extension .py"

🤖 AI Assistant (if Ollama is connected):
• "analyze this project"
• "explain the structure"
• "suggest improvements"

💾 SQL Queries:
• "SELECT * FROM files WHERE file_size > 1000000"

🔧 Special Commands:
• /help - Show this help message
• /scan - Scan information

💡 Tips:
• Use natural language for searching.
• The AI will help analyze and provide recommendations.
• Right-click to copy text.
        """
        self.add_system_message(help_text)

    def on_close(self):
        """Clean up and close the application."""
        try:
            # Shutdown AI client
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    executor.submit(asyncio.run, self.ai_client.shutdown()).result()
            else:
                asyncio.run(self.ai_client.shutdown())
        except Exception:
            pass
        self.root.destroy()

def main():
    """Main function."""
    try:
        root = tk.Tk()
        app = UnifiedChatApp(root)
        
        # Center window
        root.update_idletasks()
        width = root.winfo_width()
        height = root.winfo_height()
        x = (root.winfo_screenwidth() // 2) - (width // 2)
        y = (root.winfo_screenheight() // 2) - (height // 2)
        root.geometry(f'{width}x{height}+{x}+{y}')
        
        # Force focus and show window
        root.focus_force()
        root.deiconify()
        
        print("🚀 Unified Chat App is ready!")
        print("✅ The system will automatically connect to the File System and Ollama.")
        print("�� The GUI window should be visible.")
        
        root.mainloop()
    except Exception as e:
        print(f"❌ An error occurred: {str(e)}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
