import json
import re

def parse_astm_file(filepath):
    with open(filepath, 'r', encoding='latin-1') as f:
        raw = f.read()

    # Strip non-printable characters
    raw = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', raw)

    lines = re.split(r'[\r\n]+', raw)
    sessions = []
    current_session = None
    current_order = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Strip leading frame number (single digit at start)
        line = re.sub(r'^\d', '', line)

        fields = line.split('|')
        record_type = fields[0]

        if record_type == 'H':
            current_session = {
                'timestamp': fields[13] if len(fields) > 13 else '',
                'patient': {},
                'orders': [],
                'results': []
            }
            sessions.append(current_session)
            current_order = None

        elif record_type == 'P':
            if current_session:
                name_parts = fields[5].split('^') if len(fields) > 5 else []
                current_session['patient'] = {
                    'patientId': fields[3] if len(fields) > 3 else '',
                    'lastName':  name_parts[1] if len(name_parts) > 1 else '',
                    'firstName': name_parts[2] if len(name_parts) > 2 else '',
                    'dob':       fields[7] if len(fields) > 7 else '',
                    'gender':    fields[8] if len(fields) > 8 else ''
                }

        elif record_type == 'O':
            if current_session:
                sample_parts = fields[2].split('^') if len(fields) > 2 else []
                current_order = {
                    'sampleId': sample_parts[0] if sample_parts else '',
                    'results': []
                }
                current_session['orders'].append(current_order)

        elif record_type == 'R':
            if current_session:
                test_field = fields[2] if len(fields) > 2 else ''
                match = re.search(r'\+(\d+)\+', test_field)
                test_code = match.group(1) if match else test_field
                flag_parts = fields[6].split('^') if len(fields) > 6 else []
                result = {
                    'testCode':     test_code,
                    'value':        fields[3] if len(fields) > 3 else '',
                    'units':        fields[4] if len(fields) > 4 else '',
                    'abnormalFlag': flag_parts[2] if len(flag_parts) > 2 else '',
                    'collectedAt':  fields[12] if len(fields) > 12 else '',
                    'resultedAt':   fields[13] if len(fields) > 13 else ''
                }
                current_session['results'].append(result)
                if current_order:
                    current_order['results'].append(result)

    return sessions

# Run
data = parse_astm_file('/Users/aadhi/Desktop/mc/output111.json')
print(json.dumps(data, indent=2))