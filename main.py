"""
Main GUI application for Discord Rich Presence Game Selector.
"""
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import configparser
import os
from database import GameDatabase
from discord_rpc import DiscordRPC
import time


class DiscordRPCApp:
    """Main application window for Discord Rich Presence."""
    
    def __init__(self, root):
        """Initialize the application."""
        self.root = root
        self.root.title("Discord Rich Presence - Game Selector")
        self.root.geometry("700x650")
        self.root.resizable(False, False)
        
        # Initialize variables
        self.client_id = None
        self.rpc = None
        self.db = GameDatabase()
        self.start_time = None
        
        # Load configuration
        self.load_config()
        
        # Create UI
        self.create_widgets()
        
        # Auto-connect if enabled
        if hasattr(self, 'auto_connect') and self.auto_connect:
            self.root.after(1000, self.connect_discord)
    
    def load_config(self):
        """Load configuration from config.ini file."""
        config = configparser.ConfigParser()
        
        # Check if config.ini exists, otherwise use example
        if os.path.exists('config.ini'):
            config.read('config.ini')
        elif os.path.exists('config.ini.example'):
            print("config.ini not found, using config.ini.example")
            config.read('config.ini.example')
        else:
            print("No configuration file found")
            return
        
        # Load Discord settings
        try:
            self.client_id = config.get('Discord', 'CLIENT_ID')
            if self.client_id == "YOUR_CLIENT_ID_HERE":
                self.client_id = None
                print("Please set your Discord Client ID in config.ini")
        except:
            self.client_id = None
        
        # Load general settings
        try:
            self.auto_connect = config.getboolean('Settings', 'AUTO_CONNECT')
        except:
            self.auto_connect = False
    
    def create_widgets(self):
        """Create all GUI widgets."""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(main_frame, text="Discord Rich Presence Manager", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=2, pady=10)
        
        # Connection section
        connection_frame = ttk.LabelFrame(main_frame, text="Discord Connection", padding="10")
        connection_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.connection_status = ttk.Label(connection_frame, text="Status: Not Connected", 
                                          foreground="red")
        self.connection_status.grid(row=0, column=0, padx=5)
        
        self.connect_button = ttk.Button(connection_frame, text="Connect", 
                                        command=self.connect_discord)
        self.connect_button.grid(row=0, column=1, padx=5)
        
        self.disconnect_button = ttk.Button(connection_frame, text="Disconnect", 
                                           command=self.disconnect_discord, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=2, padx=5)
        
        # Client ID section
        client_frame = ttk.Frame(connection_frame)
        client_frame.grid(row=1, column=0, columnspan=3, pady=5)
        
        ttk.Label(client_frame, text="Client ID:").grid(row=0, column=0, padx=5)
        self.client_id_entry = ttk.Entry(client_frame, width=30)
        self.client_id_entry.grid(row=0, column=1, padx=5)
        if self.client_id:
            self.client_id_entry.insert(0, self.client_id)
        
        # Game selection section
        game_frame = ttk.LabelFrame(main_frame, text="Game Selection", padding="10")
        game_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        
        ttk.Label(game_frame, text="Select Game:").grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.game_combo = ttk.Combobox(game_frame, width=40, state='readonly')
        self.game_combo.grid(row=0, column=1, padx=10, pady=5)
        self.game_combo['values'] = self.db.get_all_game_titles()
        self.game_combo.bind('<<ComboboxSelected>>', self.on_game_selected)
        
        ttk.Button(game_frame, text="Reload Database", 
                  command=self.reload_database).grid(row=0, column=2, padx=5)
        
        # Game details section
        details_frame = ttk.LabelFrame(main_frame, text="Game Details", padding="10")
        details_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        # Details field
        ttk.Label(details_frame, text="Details:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.details_entry = ttk.Entry(details_frame, width=50)
        self.details_entry.grid(row=0, column=1, padx=10, pady=5)
        
        # State field
        ttk.Label(details_frame, text="State:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.state_entry = ttk.Entry(details_frame, width=50)
        self.state_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Large image
        ttk.Label(details_frame, text="Large Image:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.large_image_entry = ttk.Entry(details_frame, width=50)
        self.large_image_entry.grid(row=2, column=1, padx=10, pady=5)
        
        # Large image text
        ttk.Label(details_frame, text="Large Image Text:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.large_text_entry = ttk.Entry(details_frame, width=50)
        self.large_text_entry.grid(row=3, column=1, padx=10, pady=5)
        
        # Small image
        ttk.Label(details_frame, text="Small Image:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.small_image_entry = ttk.Entry(details_frame, width=50)
        self.small_image_entry.grid(row=4, column=1, padx=10, pady=5)
        
        # Small image text
        ttk.Label(details_frame, text="Small Image Text:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.small_text_entry = ttk.Entry(details_frame, width=50)
        self.small_text_entry.grid(row=5, column=1, padx=10, pady=5)
        
        # Show elapsed time checkbox
        self.show_time_var = tk.BooleanVar(value=True)
        self.time_checkbox = ttk.Checkbutton(details_frame, text="Show Elapsed Time", 
                                            variable=self.show_time_var)
        self.time_checkbox.grid(row=6, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Action buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        self.update_button = ttk.Button(button_frame, text="Update Presence", 
                                       command=self.update_presence, state=tk.DISABLED)
        self.update_button.grid(row=0, column=0, padx=5)
        
        self.clear_button = ttk.Button(button_frame, text="Clear Presence", 
                                      command=self.clear_presence, state=tk.DISABLED)
        self.clear_button.grid(row=0, column=1, padx=5)
        
        # Log section
        log_frame = ttk.LabelFrame(main_frame, text="Activity Log", padding="5")
        log_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, width=80, 
                                                  state=tk.DISABLED)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Initial log message
        self.log_message("Application started. Please connect to Discord.")
        if not self.client_id:
            self.log_message("WARNING: Client ID not configured. Please enter your Discord Client ID.")
    
    def log_message(self, message):
        """Add a message to the activity log."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def connect_discord(self):
        """Connect to Discord Rich Presence."""
        # Get client ID from entry if not loaded from config
        client_id = self.client_id_entry.get().strip()
        
        if not client_id or client_id == "YOUR_CLIENT_ID_HERE":
            messagebox.showerror("Error", "Please enter a valid Discord Client ID.\n\n"
                               "Get one from: https://discord.com/developers/applications")
            self.log_message("ERROR: Invalid Client ID")
            return
        
        self.client_id = client_id
        self.rpc = DiscordRPC(self.client_id)
        
        if self.rpc.connect():
            self.connection_status.config(text="Status: Connected", foreground="green")
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
            self.update_button.config(state=tk.NORMAL)
            self.clear_button.config(state=tk.NORMAL)
            self.log_message("Successfully connected to Discord")
        else:
            messagebox.showerror("Connection Error", 
                               "Failed to connect to Discord.\n\n"
                               "Make sure Discord is running and the Client ID is correct.")
            self.log_message("ERROR: Failed to connect to Discord")
    
    def disconnect_discord(self):
        """Disconnect from Discord Rich Presence."""
        if self.rpc:
            self.rpc.disconnect()
            self.connection_status.config(text="Status: Not Connected", foreground="red")
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
            self.update_button.config(state=tk.DISABLED)
            self.clear_button.config(state=tk.DISABLED)
            self.log_message("Disconnected from Discord")
    
    def reload_database(self):
        """Reload the game database."""
        self.db.reload_database()
        self.game_combo['values'] = self.db.get_all_game_titles()
        self.log_message(f"Database reloaded. {len(self.db.get_all_game_titles())} games found.")
        messagebox.showinfo("Success", "Database reloaded successfully!")
    
    def on_game_selected(self, event):
        """Handle game selection from dropdown."""
        game_title = self.game_combo.get()
        game_data = self.db.get_game_data(game_title)
        
        if game_data:
            # Populate fields with game data
            self.details_entry.delete(0, tk.END)
            self.details_entry.insert(0, game_data.get('Details', ''))
            
            self.state_entry.delete(0, tk.END)
            self.state_entry.insert(0, game_data.get('State', ''))
            
            self.large_image_entry.delete(0, tk.END)
            self.large_image_entry.insert(0, game_data.get('Large Image', ''))
            
            self.large_text_entry.delete(0, tk.END)
            self.large_text_entry.insert(0, game_data.get('Large Image Text', ''))
            
            self.small_image_entry.delete(0, tk.END)
            self.small_image_entry.insert(0, game_data.get('Small Image', ''))
            
            self.small_text_entry.delete(0, tk.END)
            self.small_text_entry.insert(0, game_data.get('Small Image Text', ''))
            
            self.log_message(f"Loaded: {game_title}")
    
    def update_presence(self):
        """Update Discord Rich Presence with current values."""
        if not self.rpc or not self.rpc.is_connected():
            messagebox.showwarning("Not Connected", "Please connect to Discord first.")
            return
        
        # Get values from entries
        details = self.details_entry.get().strip()
        state = self.state_entry.get().strip()
        large_image = self.large_image_entry.get().strip()
        large_text = self.large_text_entry.get().strip()
        small_image = self.small_image_entry.get().strip()
        small_text = self.small_text_entry.get().strip()
        show_time = self.show_time_var.get()
        
        # Set start time if showing elapsed time
        if show_time and not self.start_time:
            self.start_time = int(time.time())
        elif not show_time:
            self.start_time = None
        
        # Update presence
        success = self.rpc.update_presence(
            details=details if details else None,
            state=state if state else None,
            large_image=large_image if large_image else None,
            large_text=large_text if large_text else None,
            small_image=small_image if small_image else None,
            small_text=small_text if small_text else None,
            start_timestamp=self.start_time
        )
        
        if success:
            self.log_message("Presence updated successfully")
            messagebox.showinfo("Success", "Discord Rich Presence updated!")
        else:
            self.log_message("ERROR: Failed to update presence")
            messagebox.showerror("Error", "Failed to update presence. Check the log for details.")
    
    def clear_presence(self):
        """Clear Discord Rich Presence."""
        if not self.rpc or not self.rpc.is_connected():
            messagebox.showwarning("Not Connected", "Please connect to Discord first.")
            return
        
        if self.rpc.clear_presence():
            self.start_time = None
            self.log_message("Presence cleared")
            messagebox.showinfo("Success", "Discord Rich Presence cleared!")
        else:
            self.log_message("ERROR: Failed to clear presence")
    
    def on_closing(self):
        """Handle application closing."""
        if self.rpc and self.rpc.is_connected():
            self.rpc.disconnect()
        self.root.destroy()


def main():
    """Main entry point for the application."""
    root = tk.Tk()
    app = DiscordRPCApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
