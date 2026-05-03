import json
import re
from datetime import datetime


def fmt_ts(ts):
    """Convert ASTM timestamp to human-readable format."""
    if not ts:
        return ""
    ts = ts.strip()
    try:
        if len(ts) == 14:
            return datetime.strptime(ts, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
        elif len(ts) == 12:
            return datetime.strptime(ts, "%Y%m%d%H%M").strftime("%Y-%m-%d %H:%M")
        elif len(ts) == 8:
            return datetime.strptime(ts, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        pass
    return ts


def extract_flag(field):
    first_rep = field.split("\\")[0]  # take first repetition (\ is repeat separator)
    parts = first_rep.split("^")
    return parts[1] if len(parts) > 1 else ""


FLAG_LABELS = {
    "": "Normal",
    "0": "Normal",
    "N": "Normal",
    "A": "Abnormal",
    "H": "High",
    "L": "Low",
    "HH": "Critical High",
    "LL": "Critical Low",
}


def parse_astm_file(filepath):
    with open(filepath, "r") as f:
        raw = f.read()

    lines = raw.strip().split("\n")
    sessions = []
    current_session = None
    current_order = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Strip leading ASTM frame sequence number (single digit 0-9)
        if line[0].isdigit():
            line = line[1:]

        fields = line.split("|")
        record_type = fields[0]

        if record_type == "H":
            current_session = {
                "reportedAt": fmt_ts(fields[13]) if len(fields) > 13 else "",
                "analyzerId": fields[4] if len(fields) > 4 else "",
                "patient": {},
                "orders": [],
            }
            sessions.append(current_session)
            current_order = None

        elif record_type == "P":
            if current_session:
                name_parts = fields[5].split("^") if len(fields) > 5 else []
                current_session["patient"] = {
                    "patientId": fields[3] if len(fields) > 3 else "",
                    "lastName": name_parts[1] if len(name_parts) > 1 else "",
                    "firstName": name_parts[2] if len(name_parts) > 2 else "",
                    "dob": fmt_ts(fields[7]) if len(fields) > 7 else "",
                    "gender": fields[8] if len(fields) > 8 else "",
                }

        elif record_type == "O":
            if current_session:
                sample_parts = fields[2].split("^") if len(fields) > 2 else []
                current_order = {
                    "sampleId": sample_parts[0] if sample_parts else "",
                    "results": [],
                }
                current_session["orders"].append(current_order)

        elif record_type == "R":
            if current_session and current_order is not None:
                test_field = fields[2] if len(fields) > 2 else ""
                match = re.search(r"\+(\d+)\+", test_field)
                test_code = match.group(1) if match else test_field

                flag_raw = fields[6] if len(fields) > 6 else ""
                flag = extract_flag(flag_raw)

                value_raw = fields[3] if len(fields) > 3 else ""
                is_no_result = value_raw.strip().lower() == "no result"

                result = {
                    "testCode": test_code,
                    "value": None if is_no_result else value_raw,
                    "units": fields[4] if len(fields) > 4 else "",
                    "abnormalFlag": FLAG_LABELS.get(flag, flag) if flag else "Normal",
                    "isAbnormal": flag not in ("", "0", "N"),
                    "collectedAt": fmt_ts(fields[12]) if len(fields) > 12 else "",
                    "resultedAt": fmt_ts(fields[13]) if len(fields) > 13 else "",
                }
                current_order["results"].append(result)

    return sessions


data = parse_astm_file("machine_outputs/vitros/output.txt")
# print(json.dumps(data, indent=2))

with open("outputs/vitros/output_decoded.json", "w") as f:
    json.dump(data, f, indent=2)

print("\nSaved to outputs/vitros/output_decoded.json")
