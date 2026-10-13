"""
Discord Rich Presence integration module.
"""
from pypresence import Presence
from pypresence.exceptions import DiscordNotFound, InvalidPipe, ConnectionTimeout, InvalidID, DiscordError
from pypresence.utils import get_ipc_path
import asyncio
import json
import struct
import sys
import time
import threading


class _Presence(Presence):
    """pypresence's Presence, but keeps the user from Discord's READY handshake.

    Mirrors BaseClient.handshake from pypresence 4.3.0, which discards it.
    """
    user = None

    async def handshake(self):
        ipc_path = get_ipc_path(self.pipe)
        if not ipc_path:
            raise DiscordNotFound
        try:
            if sys.platform == 'win32':
                self.sock_reader = asyncio.StreamReader(loop=self.loop)
                reader_protocol = asyncio.StreamReaderProtocol(self.sock_reader, loop=self.loop)
                self.sock_writer, _ = await asyncio.wait_for(
                    self.loop.create_pipe_connection(lambda: reader_protocol, ipc_path), self.connection_timeout)
            else:
                self.sock_reader, self.sock_writer = await asyncio.wait_for(
                    asyncio.open_unix_connection(ipc_path), self.connection_timeout)
        except FileNotFoundError:
            raise InvalidPipe
        except asyncio.TimeoutError:
            raise ConnectionTimeout

        self.send_data(0, {'v': 1, 'client_id': self.client_id})
        preamble = await self.sock_reader.read(8)
        code, length = struct.unpack('<ii', preamble)
        data = json.loads(await self.sock_reader.read(length))
        if 'code' in data:
            if data['message'] == 'Invalid Client ID':
                raise InvalidID
            raise DiscordError(data['code'], data['message'])
        self.user = (data.get('data') or {}).get('user')
        if self._events_on:
            self.sock_reader.feed_data = self.on_event


class DiscordRPC:
    """Handles Discord Rich Presence connection and updates."""
    
    def __init__(self, client_id):
        """
        Initialize Discord RPC client.
        
        Args:
            client_id: Discord application client ID
        """
        self.client_id = str(client_id)
        self.rpc = None
        self.connected = False
        self.current_presence = {}
        self.user = None  # dict with id, username, global_name, avatar once connected
        self._update_thread = None
        self._stop_update = False
    
    def connect(self):
        """
        Connect to Discord Rich Presence.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            if self.connected:
                print("Already connected to Discord")
                return True
            
            self.rpc = _Presence(self.client_id)
            self.rpc.connect()
            self.user = self.rpc.user
            self.connected = True
            print("Successfully connected to Discord RPC")
            return True
        except Exception as e:
            print(f"Failed to connect to Discord: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Discord Rich Presence."""
        try:
            self._stop_update = True
            if self._update_thread and self._update_thread.is_alive():
                self._update_thread.join(timeout=2)
            
            if self.rpc and self.connected:
                self.rpc.close()
                print("Disconnected from Discord RPC")
            self.connected = False
            self.rpc = None
        except Exception as e:
            print(f"Error disconnecting: {e}")
    
    def update_presence(self, details=None, state=None, large_image=None, 
                       large_text=None, small_image=None, small_text=None,
                       start_timestamp=None, party_size=None):
        """
        Update Discord Rich Presence.
        
        Args:
            details: First line of presence (e.g., "Playing Pokemon Red")
            state: Second line of presence (e.g., "Exploring Kanto")
            large_image: Asset name or URL for large image
            large_text: Hover text for large image
            small_image: Asset name or URL for small image
            small_text: Hover text for small image
            start_timestamp: Unix timestamp for elapsed time
            party_size: [current, max] shown as "(1 of 4)" after the state
        
        Returns:
            True if update successful, False otherwise
        """
        if not self.connected:
            print("Not connected to Discord")
            return False
        
        try:
            # Build presence dictionary with only non-None values
            presence = {}
            
            if details:
                presence['details'] = str(details)
            if state:
                presence['state'] = str(state)
            if large_image:
                presence['large_image'] = str(large_image)
            if large_text:
                presence['large_text'] = str(large_text)
            if small_image:
                presence['small_image'] = str(small_image)
            if small_text:
                presence['small_text'] = str(small_text)
            if start_timestamp:
                presence['start'] = int(start_timestamp)
            if party_size:
                presence['party_size'] = [int(n) for n in party_size]
            
            # Update presence
            self.rpc.update(**presence)
            self.current_presence = presence.copy()
            print("Presence updated successfully")
            return True
        except Exception as e:
            print(f"Failed to update presence: {e}")
            return False
    
    def clear_presence(self):
        """Clear the current Discord Rich Presence."""
        if not self.connected:
            return False
        
        try:
            self.rpc.clear()
            self.current_presence = {}
            print("Presence cleared")
            return True
        except Exception as e:
            print(f"Failed to clear presence: {e}")
            return False
    
    def set_game_presence(self, game_data, show_elapsed_time=True):
        """
        Set presence from game data dictionary.
        
        Args:
            game_data: Dictionary containing game information
            show_elapsed_time: Whether to show elapsed time
            
        Returns:
            True if successful, False otherwise
        """
        details = game_data.get('Details', '')
        state = game_data.get('State', '')
        large_image = game_data.get('Large Image', '')
        large_text = game_data.get('Large Image Text', '')
        small_image = game_data.get('Small Image', '')
        small_text = game_data.get('Small Image Text', '')
        
        start_time = int(time.time()) if show_elapsed_time else None
        
        return self.update_presence(
            details=details,
            state=state,
            large_image=large_image,
            large_text=large_text,
            small_image=small_image,
            small_text=small_text,
            start_timestamp=start_time
        )
    
    def is_connected(self):
        """Check if connected to Discord."""
        return self.connected


if __name__ == "__main__":
    # Test the Discord RPC module
    print("Discord RPC Test")
    print("Note: You need a valid Client ID to test this properly")
    print("Get one from: https://discord.com/developers/applications")
    
    # Example test (will fail without valid client ID)
    client_id = "YOUR_CLIENT_ID_HERE"
    rpc = DiscordRPC(client_id)
    
    if rpc.connect():
        print("Testing presence update...")
        rpc.update_presence(
            details="Playing Pokemon Red",
            state="Exploring Kanto",
            large_image="pokemon",
            large_text="Pokemon Red"
        )
        
        # Keep presence active for 30 seconds
        print("Presence active for 30 seconds...")
        time.sleep(30)
        
        rpc.disconnect()
    else:
        print("Failed to connect. Check your client ID.")
