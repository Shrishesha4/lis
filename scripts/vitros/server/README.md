# VITROS 5600 LIS Server Setup Guide

## System Information

- **Server Machine IP**: 172.20.13.123
- **VITROS Machine IP**: 172.20.13.131
- **LIS Server Port**: 3020
- **Protocol**: ASTM LIS2-A

## Starting the Server

```bash
cd /Users/aadhi/Developer/lis/scripts/vitros/server
python3 server.py
```

Expected output:

```
ASTM Server listening on port 3020
Orders file: /Users/aadhi/Developer/lis/scripts/vitros/server/orders.json
Output file: /Users/aadhi/Developer/lis/scripts/vitros/server/results.json
Waiting for Vitros connection...
```

## Configuring VITROS 5600 Machine

The VITROS machine needs to be configured to connect to your LIS server:

### VITROS Configuration Settings:

1. **Host/Server Address**: `172.20.13.123`
2. **Port**: `3020`
3. **Protocol**: ASTM/LIS2-A (or similar)
4. **Connection Type**: TCP/IP

### Steps to Configure (typical VITROS interface):

1. Navigate to: System → Communication Settings → LIS Connection
2. Set Server Address: `172.20.13.123`
3. Set Port: `3020`
4. Enable/Activate the LIS connection
5. Test connection
6. Save settings

## How It Works

### Query Flow:

1. VITROS sends a **Query (Q) record** with sample ID
2. Server looks up the sample ID in `orders.json`
3. Server responds with **Header (H), Patient (P), Order (O), and Terminator (L) records**
4. VITROS receives test codes and prepares for analysis

### Sample IDs Available:

- `1100708672` - Nithya shree (15 test codes)
- `1100695765` - S Devan (3 test codes)

### Test Codes Supported:

- 300: GLU (Glucose)
- 301: TP (Total Protein)
- 302: URIC (Uric Acid)
- 303: ALB (Albumin)
- 307-310: Electrolytes (Cl-, K+, Na+, HCO2)
- 314: CREA (Creatinine)
- 315: UREA (Urea)
- 317: Bu (Bilirubin)
- 319: TBIL (Total Bilirubin)
- 320: AST
- 321: ALKP (Alkaline Phosphatase)
- 322: ALT (Alanine Aminotransferase)
- 326: GGT (Gamma-Glutamyl Transferase)
- And more in testcodes.json

## Troubleshooting

### Error PX2-011 (LIS Connection Failed)

**Check 1**: Verify VITROS has correct server IP

```bash
# On your server machine, verify connectivity
ping 172.20.13.131
```

**Check 2**: Verify server is running

```bash
ps aux | grep "python3 server.py" | grep -v grep
```

**Check 3**: Verify port is accessible

```bash
lsof -i :3020
```

**Check 4**: Test connectivity from VITROS

- Try pinging 172.20.13.123 from VITROS
- Verify network connectivity with subnet 172.20.13.0/24

**Check 5**: Check server logs

```bash
# Watch server output for connection attempts
tail -f /Users/aadhi/Developer/lis/scripts/vitros/server/results.json
```

### Results Verification

After VITROS sends results, they are saved to:

```
/Users/aadhi/Developer/lis/scripts/vitros/server/results.json
```

View results:

```bash
cat /Users/aadhi/Developer/lis/scripts/vitros/server/results.json
```

## Testing Without VITROS

You can test the server locally:

```bash
python3 /Users/aadhi/Developer/lis/scripts/vitros/server/test_client.py 1100708672
```

Or run diagnostics:

```bash
python3 /Users/aadhi/Developer/lis/scripts/vitros/server/diagnostic.py
```

## Files Structure

```
/Users/aadhi/Developer/lis/scripts/vitros/server/
├── server.py              # Main LIS server
├── orders.json            # Sample orders database
├── testcodes.json         # Test code mapping
├── test_client.py         # Test client for debugging
├── diagnostic.py          # Connectivity diagnostic tool
└── results.json           # Results from analyzer (auto-created)
```

## Network Configuration

Both machines on same subnet: `172.20.13.0/24`

- Gateway: 172.20.15.255
- Server: 172.20.13.123:3020
- VITROS: 172.20.13.131

## Support

If connection fails:

1. Verify both machines are on same network
2. Ping each other to confirm connectivity
3. Check firewall settings on server
4. Review server console output for error messages
5. Ensure VITROS firmware supports ASTM LIS2-A protocol
