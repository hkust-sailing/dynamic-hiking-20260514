import socket
import threading
import time
from typing import Optional
from .ip_setting import IpSetting
from .feedback_message import FeedbackMessage
from .command_message import CommandMessage

class DofController:
    """platfrom controller"""
#     def __init__(self):
#         self._socket_lock = threading.Lock()
#         self._socket: Optional[socket.socket] = None
#         self._local_endpoint = ("192.168.0.131", 10000)  # Host PC IP and port
#         self._remote_endpoint = ("192.168.0.125", 5000)  # Embedded controller IP and port

#         self.is_connect_disabled = False
#         self.is_auto_connect_enabled = True
#         self.is_connecting = False
#         self.is_connected = False
#         self.connect_message = ""

#         self._no_feedback_time = 0
#         self._connection_broken_timer = threading.Timer(0.1, self._check_connection)
#         self._connection_broken_timer.start()

#         self._feedback_thread = threading.Thread(target=self._get_feedback_message, daemon=True)
#         self._feedback_thread.start()

#     def start_connecting(self):
#         """Start the connection process."""
#         if self.is_connect_disabled:
#             print("Connection was manually disabled and cannot be started")
#             return

#         self.is_connected = False
#         self.is_connecting = True
#         self.connect_message = "Connecting"
#         print(self.connect_message)

#     def connect(self):
#         """Try connecting to embedded controller."""
#         with self._socket_lock:
#             if self._socket:
#                 self._socket.close()
#                 print("Close existing connection")

#             self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#             try:
#                 self._socket.bind(self._local_endpoint)
#                 self._socket.settimeout(0.5)  # Set socket timeout.
#                 self.is_connected = True
#                 self.connect_message = "Connection established"
#                 print(self.connect_message)
#             except Exception as e:
#                 self.is_connected = False
#                 self.connect_message = f"Connection failed: {e}"
#                 print(self.connect_message)

#     def send_command_message(self, command_message: bytes):
#         """Send command message."""
#         if not self.is_connected:
#             print("Not connected to embedded controller; cannot send command")
#             return

#         with self._socket_lock:
#             try:
#                 self._socket.sendto(command_message, self._remote_endpoint)
#                 print("Command sent")
#             except Exception as e:
#                 print(f"Failed to send command: {e}")

#     def _get_feedback_message(self):
#         """Receive feedback message."""
#         while True:
#             try:
#                 if not self.is_connected and not self.is_auto_connect_enabled or self.is_connect_disabled:
#                     print("Not connected and auto-reconnect disabled, waiting...")
#                     time.sleep(1)
#                     continue

#                 if not self.is_connected:
#                     print("Trying to reconnect...")
#                     self.connect()

#                 data, _ = self._socket.recvfrom(200)  # Receive data.
#                 if data[0] != 55:  # Check packet identifier.
#                     raise ValueError("Invalid packet")

#                 # Process feedback message.
#                 feedback_message = FeedbackMessage.from_bytes(data)
#                 self.is_connected = True
#                 print(f"Received feedback: {feedback_message}")
#                 self._no_feedback_time = 0  # Reset no-feedback timer.

#             except socket.timeout:
#                 print("Connection timed out: no feedback from embedded controller")
#                 self._no_feedback_time += 500
#                 if self._no_feedback_time >= 500:
#                     self.is_connected = False
#                     self.connect_message = "Disconnected"
#                     print(self.connect_message)

#             except Exception as e:
#                 print(f"Error while receiving feedback: {e}")
#                 self.is_connected = False
#                 self.connect_message = "Disconnected"
#             time.sleep(1)


#     def _check_connection(self):
#         """Check whether connection is broken."""
        
#         self._no_feedback_time += 100

#         if self._no_feedback_time >= 500 and self.is_connected:
#             print("Communication timeout, treated as disconnected")
#             self.is_connected = False

#         self._connection_broken_timer = threading.Timer(0.1, self._check_connection)
#         self._connection_broken_timer.start()


#     def dispose(self):
#         """Release resources."""
#         with self._socket_lock:
#             if self._socket:
#                 self._socket.close()
#             self._connection_broken_timer.cancel()
#             self.is_connected = False
#             self.is_connecting = False
#             self.is_connect_disabled = True
#             self.is_auto_connect_enabled = False
#             print("Resources released")

#     @property
#     def is_connected(self):
#         return self._is_connected

#     @is_connected.setter
#     def is_connected(self, value):
#         self._is_connected = value
#         print(f"Connection state: {value}")
   
    def __init__(self, ip_setting: IpSetting):
        self._socket_lock = threading.Lock()
        self.ip_settings = ip_setting
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._is_connected = False
        # self._feedback_thread = threading.Thread(target=self._receive_feedback, daemon=True)
        # self._feedback_thread.start()

    def connect(self):
        try:
            self._socket.bind((self.ip_settings.local_ip, self.ip_settings.local_port))
            self._socket.settimeout(0.5)
            self._is_connected = True
            print(f"Connection established: local {self.ip_settings.local_ip}:{self.ip_settings.local_port} -> remote {self.ip_settings.remote_ip}:{self.ip_settings.remote_port}")
        except Exception as e:
            self._is_connected = False
            print(f"Connection failed: {e}")

    def disconnect(self):
        """Disconnect socket."""
        if self._is_connected:
            self._socket.close()
            self._is_connected = False
            print("Disconnected")

    def send_command(self, command_message: CommandMessage):
        if not self._is_connected:
            print("Not connected to embedded controller. Check IP and port settings")
            return

        try:
            command_bytes = command_message.to_bytes()
            if not command_bytes:
                print("Failed to pack command data")
                return
            self._socket.sendto(command_bytes, (self.ip_settings.remote_ip, self.ip_settings.remote_port))
            # print(f"Command sent")
            # Print each argument value for debugging.
            # print(f"Id: {command_message.Id}")
            # print(f"CommandCode: {command_message.CommandCode.value}")
            # print(f"SubCommandCode: {command_message.SubCommandCode.value}")
            # print(f"ScriptFileIndex: {command_message.ScriptFileIndex}")
            # print(f"DO: {command_message.DO}")
            # print(f"CyChoose: {command_message.CyChoose}")
            # print(f"JogSpeed: {command_message.JogSpeed}")
            # print(f"Send DOFs: {command_message.DOFs}")
            # print(f"AmplitudeArray: {command_message.AmplitudeArray}")
            # print(f"FrequencyArray: {command_message.FrequencyArray}")
            # print(f"PhaseArray: {command_message.PhaseArray}")
            # print(f"DestinationPosition: {command_message.DestinationPosition}")
            # print(f"Speed: {command_message.Speed}")
            # print(f"Vxyz: {command_message.Vxyz}")
            # print(f"Axyz: {command_message.Axyz}")
            # print(f"Timestamp: {command_message.Timestamp}")
        except Exception as e:
            print(f"Failed to send command: {e}")

    # def _receive_feedback(self):
    #     """Receive feedback messages."""
    #     while True:
    #         try:
    #             data, _ = self._socket.recvfrom(200)
    #             feedback = FeedbackMessage.from_bytes(data)
    #             self._is_connected = True
    #             print(f"Received data size: {len(data)} bytes")
    #             print(f"Received feedback: {feedback}")
    #         except socket.timeout:
    #             #self._is_connected = False
    #             print("Connection timed out: no feedback from embedded controller")
    #         except Exception as e:
    #             print(f"Error receiving feedback: {e}")
    #             #self._is_connected = False
    #         time.sleep(10) # 10s update
    def get_feedback(self):
        """Receive one feedback packet on demand."""
        try:
            data, _ = self._socket.recvfrom(200)

            # UDP feedback may already be buffered when a new motion command is sent.
            # Drain the socket backlog and briefly poll for in-flight packets so callers
            # observe the freshest controller state on the first read.
            self._socket.setblocking(False)
            try:
                poll_deadline = time.monotonic() + 0.03
                while True:
                    try:
                        latest_data, _ = self._socket.recvfrom(200)
                        data = latest_data
                        continue
                    except BlockingIOError:
                        if time.monotonic() >= poll_deadline:
                            break
                        time.sleep(0.001)
            except BlockingIOError:
                pass
            finally:
                self._socket.setblocking(True)
                self._socket.settimeout(0.5)

            feedback = FeedbackMessage.from_bytes(data)
            self._is_connected = True
            # print(f"Received data size: {len(data)} bytes")
            #print(f"Received feedback: {feedback}")
            # print(f"Received DOFs: {feedback.AttitudesArray}")
            return feedback
        except socket.timeout:
            print("Connection timed out: no feedback from embedded controller")
            return None
        except Exception as e:
            print(f"Error while receiving feedback: {e}")
            self._is_connected = False
            return None

    def dispose(self):
        """Release socket and internal connection flags."""
        
        with self._socket_lock:
            if self._socket:
                self._socket.close()
            self.is_connected = False
            self.is_connecting = False
            self.is_connect_disabled = True
            self.is_auto_connect_enabled = False
            print("Resources released")