#!/usr/bin/env python3
"""
Test client for VITROS 5600 LIS server
Sends a query for a sample ID and receives the order response
"""

import socket
import sys
import time

HOST = 'localhost'
PORT = 3020

def calculate_checksum(data):
    total = sum(ord(c) for c in data)
    return format(total % 256, '02X')

def make_frame(seq, record):
    data = str(seq % 8) + record + '\r'
    checksum = calculate_checksum(data)
    return b'\x02' + data.encode('latin-1') + b'\x03' + checksum.encode('latin-1') + b'\r\n'

def send_query(sample_id):
    """Send a query for the given sample ID"""
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((HOST, PORT))
        print(f"Connected to {HOST}:{PORT}")
        
        # Send ENQ
        print("\n→ Sending ENQ...")
        conn.send(b'\x05')
        time.sleep(0.1)
        
        # Receive ACK
        ack = conn.recv(1)
        print(f"← Received: {repr(ack)}")
        
        # Send Header
        print("→ Sending Header...")
        header = make_frame(1, 'H|\\^&|||TEST||||||||LIS2-A|20260506120000')
        conn.send(header)
        time.sleep(0.1)
        
        # Receive ACK
        ack = conn.recv(1)
        print(f"← Received: {repr(ack)}")
        
        # Send Query for sample ID
        print(f"→ Sending Query for sample ID: {sample_id}...")
        query = make_frame(2, f'Q|1|{sample_id}')
        conn.send(query)
        time.sleep(0.2)
        
        # Receive ACK
        ack = conn.recv(1)
        print(f"← Received: {repr(ack)}")
        
        # Receive response (may be multiple frames)
        print("\n← Receiving response...")
        response = b''
        while True:
            try:
                data = conn.recv(4096)
                if not data:
                    break
                response += data
                if b'\x04' in response:  # EOT marker
                    break
            except socket.timeout:
                break
        
        # Decode and display response
        print(f"\nResponse received ({len(response)} bytes):")
        try:
            decoded = response.decode('latin-1')
            # Split by control characters for readability
            lines = decoded.split('\x02')
            for line in lines:
                if line.strip():
                    print(f"  {repr(line)}")
        except:
            print(f"  {repr(response[:200])}")
        
        # Send EOT
        print("\n→ Sending EOT...")
        conn.send(b'\x04')
        
        conn.close()
        print("Disconnected")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    sample_id = sys.argv[1] if len(sys.argv) > 1 else '1100708672'
    print(f"Testing VITROS 5600 LIS Server")
    print(f"Query sample ID: {sample_id}\n")
    send_query(sample_id)
