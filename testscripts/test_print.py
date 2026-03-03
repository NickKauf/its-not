import socket

PRINTER_IP = "192.168.1.245"
PRINTER_PORT = 9100

data = (
  b"\x1b\x40"
    b"test print\n"
    b"it's not nothing\n"
    b"\n\n\n\n\n\n"
)

with socket.create_connection((PRINTER_IP, PRINTER_PORT), timeout=5) as s:
    s.sendall(data)

print("Sent.")