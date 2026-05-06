import socket
import json
import threading
import re
import os
from datetime import datetime

HOST = '0.0.0.0'
PORT = int(os.getenv('LIS_PORT', '3020'))

# Get the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ORDERS_FILE = os.path.join(SCRIPT_DIR, 'orders.json')
TESTCODES_FILE = os.path.join(SCRIPT_DIR, 'testcodes.json')
OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'results.json')
PARSED_OUTPUT_FILE = os.path.join(SCRIPT_DIR, 'results_parsed.jsonl')

def calculate_checksum(data):
    total = sum(ord(c) for c in data)
    return format(total % 256, '02X')

def make_frame(seq, record):
    data = str(seq % 8) + record + '\r'
    checksum = calculate_checksum(data)
    return '\x02' + data + '\x03' + checksum + '\r\n'

def load_orders():
    try:
        with open(ORDERS_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f'Error loading orders: {e}')
        return []

def load_testcodes():
    try:
        with open(TESTCODES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f'Error loading test codes: {e}')
        return {}

def parse_result_record(frame, testcodes):
    fields = frame.split('|')
    if len(fields) < 2 or not frame.startswith('R|'):
        return None

    test_field = fields[2] if len(fields) > 2 else ''
    match = re.search(r'\+(\d+)\+', test_field)
    test_code = match.group(1) if match else ''
    test_name = testcodes.get(test_code, test_code)

    # Use the first repetition and the first flag component (e.g. ^0^NR -> 0)
    flag_field = fields[6] if len(fields) > 6 else ''
    first_rep = flag_field.split('\\')[0]
    flag_parts = first_rep.split('^')
    abnormal_flag = flag_parts[1] if len(flag_parts) > 1 else ''

    return {
        'testCode': test_code,
        'testName': test_name,
        'value': fields[3] if len(fields) > 3 else '',
        'units': fields[4] if len(fields) > 4 else '',
        'abnormalFlag': abnormal_flag,
        'collectedAt': fields[12] if len(fields) > 12 else '',
        'resultedAt': fields[13] if len(fields) > 13 else ''
    }

def find_order(sample_id):
    orders = load_orders()
    for order in orders:
        if order['sampleId'] == sample_id:
            return order
    return None

def build_order_response(order, sample_id):
    """Build a properly formatted LIS response with test codes for VITROS 5600"""
    now = datetime.now().strftime('%Y%m%d%H%M%S')
    testcodes = load_testcodes()
    
    # Format test string: ^^^1.0000+300+1.0\301+1.0\302+1.0...
    test_str = '^^^1.0000'
    tests = order.get('tests', [])
    
    for i, test_code in enumerate(tests):
        if i == 0:
            test_str += '+' + test_code + '+1.0'
        else:
            test_str += '\\' + test_code + '+1.0'
    
    response = '\x05'
    response += make_frame(1, 'H|\\^&|||HIS||||||||LIS2-A|' + now)
    response += make_frame(2, 'P|1|' + order.get('patientId', '') + 
                          '|||^' + order.get('lastName', '') + 
                          '^' + order.get('firstName', '') + 
                          '||' + order.get('dob', '') + 
                          '|' + order.get('gender', ''))
    
    # Build order with sample ID in correct format: sample_id^seq_num^seq_type
    sample_id_full = sample_id + '^24^1'
    response += make_frame(3, 'O|1|' + sample_id_full + '||' + test_str + '|R')
    response += make_frame(4, 'L|1|N')
    response += '\x04'
    
    print(f'→ Built response with {len(tests)} test codes: {",".join(tests)}')
    return response

def build_not_found_response():
    now = datetime.now().strftime('%Y%m%d%H%M%S')
    response = '\x05'
    response += make_frame(1, 'H|\\^&|||HIS||||||||LIS2-A|' + now)
    response += make_frame(2, 'L|1|N')
    response += '\x04'
    return response

def save_results(results):
    try:
        testcodes = load_testcodes()

        with open(OUTPUT_FILE, 'a', encoding='latin-1') as f:
            f.write('\n'.join(results) + '\n')

        parsed_results = []
        for frame in results:
            parsed = parse_result_record(frame, testcodes)
            if parsed:
                parsed_results.append(parsed)

        if parsed_results:
            with open(PARSED_OUTPUT_FILE, 'a', encoding='utf-8') as f:
                for item in parsed_results:
                    f.write(json.dumps(item) + '\n')

        print(f'Saved {len(results)} raw frames to results.json and {len(parsed_results)} parsed results to results_parsed.jsonl')
    except Exception as e:
        print(f'Error saving results: {e}')

def handle_client(conn, addr):
    print(f'\nConnected: {addr}')
    conn.settimeout(30)
    buffer = b''
    results = []
    sample_id = ''
    is_query = False

    try:
        while True:
            try:
                data = conn.recv(4096)
            except socket.timeout:
                print('Connection timed out')
                break

            if not data:
                print('Client disconnected')
                break

            buffer += data

            while buffer:
                # ENQ
                if buffer[0:1] == b'\x05':
                    print('ENQ → sending ACK')
                    conn.send(b'\x06')
                    conn.sendall(b'')
                    buffer = buffer[1:]
                    continue

                # EOT
                if buffer[0:1] == b'\x04':
                    print('EOT received')
                    buffer = buffer[1:]
                    # Save results if any
                    if results:
                        save_results(results)
                        results = []
                    continue

                # ACK
                if buffer[0:1] == b'\x06':
                    buffer = buffer[1:]
                    continue

                # STX - start of frame
                if buffer[0:1] == b'\x02':
                    etx_pos = buffer.find(b'\x03')
                    if etx_pos == -1:
                        break  # Wait for more data

                    # Get frame data between STX and ETX
                    frame_bytes = buffer[1:etx_pos]
                    # Skip ETX + 2 checksum bytes + CR + LF
                    end_pos = etx_pos + 1
                    # Skip checksum (2 bytes)
                    if len(buffer) > end_pos + 1:
                        end_pos += 2
                    # Skip CR
                    if len(buffer) > end_pos and buffer[end_pos:end_pos+1] == b'\r':
                        end_pos += 1
                    # Skip LF
                    if len(buffer) > end_pos and buffer[end_pos:end_pos+1] == b'\n':
                        end_pos += 1

                    buffer = buffer[end_pos:]

                    # Decode frame
                    frame = frame_bytes.decode('latin-1').rstrip('\r\n')

                    # Strip frame number (first char if digit)
                    if frame and frame[0].isdigit():
                        frame = frame[1:]

                    print(f'Frame: {frame[:80]}')

                    # ACK every frame
                    conn.send(b'\x06')

                    # Process record type
                    if frame.startswith('H|'):
                        print('→ Header')

                    elif frame.startswith('Q|'):
                        print('→ Query record')
                        is_query = True
                        fields = frame.split('|')
                        
                        # Parse sample ID from Q record
                        # Format: Q|seq|sample_id or Q|seq|sample_id^seq^type
                        sample_id = None
                        if len(fields) > 2 and fields[2]:
                            sample_id_field = fields[2].strip()
                            # Extract first part if it has ^ separators
                            if '^' in sample_id_field:
                                parts = sample_id_field.split('^')
                                sample_id = parts[0].strip()
                            else:
                                sample_id = sample_id_field
                        
                        if sample_id:
                            print(f'→ Sample ID: {sample_id}')
                            order = find_order(sample_id)
                            if order:
                                print(f'→ Order found! Tests: {",".join(order.get("tests", []))}')
                                response = build_order_response(order, sample_id)
                            else:
                                print(f'→ Order NOT found for {sample_id}')
                                response = build_not_found_response()

                            conn.sendall(response.encode('latin-1'))
                            print('→ Order response sent')
                        else:
                            print('→ Could not parse sample ID from query')


                    elif frame.startswith('P|'):
                        print('→ Patient record')

                    elif frame.startswith('O|'):
                        print('→ Order record')

                    elif frame.startswith('R|'):
                        print(f'→ Result: {frame}')
                        results.append(frame)

                    elif frame.startswith('L|'):
                        print('→ End of message')
                        if results:
                            save_results(results)
                            results = []

                    elif frame.startswith('M|'):
                        print(f'→ Manufacturer message: {frame}')

                    continue

                # Unknown byte - skip
                print(f'Unknown: {repr(buffer[0:1])}')
                buffer = buffer[1:]

    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()
    finally:
        if results:
            save_results(results)
        conn.close()
        print(f'Disconnected: {addr}')

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f'ASTM Server listening on port {PORT}')
    print(f'Orders file: {ORDERS_FILE}')
    print(f'Output file: {OUTPUT_FILE}')
    print('Waiting for Vitros connection...\n')

    while True:
        try:
            conn, addr = server.accept()
            thread = threading.Thread(
                target=handle_client, 
                args=(conn, addr),
                daemon=True
            )
            thread.start()
        except KeyboardInterrupt:
            print('\nShutting down...')
            server.close()
            break

if __name__ == '__main__':
    main()