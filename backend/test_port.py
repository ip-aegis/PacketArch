import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(('0.0.0.0', 8001))
    print("Successfully bound to port 8001")
    s.close()
except Exception as e:
    print(f"Failed: {e}")
