#!/usr/bin/env python3
"""
Diagnostic tool to test VITROS LIS connectivity
This helps identify connection issues
"""

import socket
import sys
import time

def get_local_ip():
    """Get the local IP address accessible from the network"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("172.20.13.131", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return None

def test_port_open(host, port):
    """Test if a port is open and listening"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False

def main():
    print("=" * 60)
    print("VITROS LIS Connectivity Diagnostic")
    print("=" * 60)
    
    local_ip = get_local_ip()
    print(f"\n✓ Local IP (reachable from network): {local_ip}")
    
    print(f"\n✓ Testing port 3020 on localhost:3020...")
    if test_port_open('127.0.0.1', 3020):
        print(f"  ✓ Server is listening on localhost:3020")
    else:
        print(f"  ✗ Server NOT listening on localhost:3020")
    
    print(f"\n✓ Testing port 3020 on {local_ip}:3020...")
    if test_port_open(local_ip, 3020):
        print(f"  ✓ Server is reachable on {local_ip}:3020")
        print(f"\n✓ VITROS should be configured to connect to: {local_ip}:3020")
    else:
        print(f"  ✗ Server NOT reachable on {local_ip}:3020")
    
    # Try common VITROS ports
    print(f"\n✓ Checking for VITROS analyzer at 172.20.13.131...")
    for port in [3020, 5020, 4080]:
        if test_port_open('172.20.13.131', port):
            print(f"  ✓ Found service on 172.20.13.131:{port}")
        else:
            print(f"  ✗ No service on 172.20.13.131:{port}")
    
    print("\n" + "=" * 60)
    print("CONFIGURATION RECOMMENDATIONS:")
    print("=" * 60)
    print(f"\n1. VITROS should connect to: {local_ip}:3020")
    print(f"   (Your machine IP on the network)")
    print(f"\n2. Verify VITROS LIS settings:")
    print(f"   - Server IP: {local_ip}")
    print(f"   - Port: 3020")
    print(f"   - Protocol: ASTM/LIS2-A")
    print(f"\n3. Run server with: python3 /Users/aadhi/Developer/lis/scripts/vitros/server/server.py")
    print(f"\n4. Check VITROS error 'PX2-011' indicates LIS connection failed")
    print("=" * 60)

if __name__ == '__main__':
    main()
