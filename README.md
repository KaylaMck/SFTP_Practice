# SFTP In-Memory Streaming: SFTP → DuckDB

## Objective

Authenticate with a remote SFTP server, open a file stream, and feed it directly into DuckDB for analysis — **without ever saving the file to disk**.

## Why This Matters

- **Security**: In healthcare and finance, you often can't write sensitive data to a local disk. In-memory processing keeps you compliant.
- **Speed**: Skip the cost of writing to disk and reading it back.
- **Modern ETL**: This is how serverless functions (like AWS Lambda) work — pull, process, push, no persistent storage.

## Tech Stack

| Tool | Role |
|------|------|
| **Docker** | Runs the SFTPGo server locally |
| **SFTPGo** | Open-source SFTP server |
| **paramiko** | Python library for SSH/SFTP connections |
| **pandas** | Reads the network stream into an in-memory DataFrame |
| **duckdb** | Runs SQL queries directly on the DataFrame |

## Setup

### 1. Start the SFTP Server

Create a `docker-compose.yml`:

```yaml
services:
  sftpgo:
    image: drakkan/sftpgo:latest
    container_name: sftpgo_server
    ports:
      - "8080:8080"   # Web Admin UI
      - "2022:2022"   # SFTP connection port
    environment:
      - SFTPGO_DEFAULT_ADMIN_USERNAME=admin
      - SFTPGO_DEFAULT_ADMIN_PASSWORD=password
    volumes:
      - sftpgo_data:/srv/sftpgo/data
    restart: unless-stopped

volumes:
  sftpgo_data:
```

```bash
docker compose up -d
```

### 2. Configure the SFTP Server

1. Go to **http://localhost:8080** and log in with `admin` / `password`
2. Create a user: `stream_user` / `stream123`
3. Go to **http://localhost:8080/web/client**, log in as `stream_user`, and upload your CSV file

### 3. Install Python Dependencies

```bash
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows PowerShell
pip install paramiko pandas duckdb
```

## The Script

```python
import paramiko
import pandas as pd
import duckdb

# Phase 1: The Handshake
transport = paramiko.Transport(("127.0.0.1", 2022))
transport.connect(username="stream_user", password="stream123")
sftp = paramiko.SFTPClient.from_transport(transport)
sftp_file = sftp.open("customers.csv")
print("Handshake complete!")

# Phase 2: The In-Memory Bridge
df = pd.read_csv(sftp_file)
print(f"{len(df)} rows loaded into memory.")

# Phase 3: The Query
duckdb.query("SELECT * FROM df").show()

duckdb.query("""
    SELECT state, COUNT(*) as customer_count
    FROM df
    GROUP BY state
    ORDER BY customer_count DESC
""").show()

duckdb.query("SELECT * FROM df WHERE city = 'Denver'").show()

# Close connections (inside out: file → sftp → transport)
sftp_file.close()
sftp.close()
transport.close()
print("Connections closed.")
```

## How the Data Flows

```
SFTP Server  →  Network Stream  →  Pandas DataFrame (RAM)  →  DuckDB SQL Queries
                 sftp.open()        pd.read_csv()              duckdb.query()
```

**No file is ever written to disk.** The data exists only in transit and in memory.

## Key Concepts

### `Transport` vs `SSHClient`

`SSHClient` is paramiko's high-level interface — it tries multiple auth methods (keys, agent, password) and can trip up with some servers. `Transport` is the lower-level layer that goes straight to password authentication. We used `Transport` because `SSHClient` had authentication issues with SFTPGo.

### `sftp.open()` vs `sftp.get()`

- `sftp.open()` returns a **file-like object** (a stream). Nothing is downloaded — it's like putting a straw into the remote server.
- `sftp.get()` **downloads** the file to your local disk. That's what we're avoiding.

### Why Pandas as the Bridge?

DuckDB's SQL engine needs a structured object like a DataFrame. The raw SFTP stream is just bytes. Pandas reads those bytes, understands the CSV format, and builds a DataFrame in RAM that DuckDB can query directly by variable name.

### Closing Connections

Always close from the inside out: file → SFTP session → transport. Like closing nested boxes — smallest first. In short scripts Python cleans up on exit, but in production, unclosed connections stack up and exhaust server resources.

## Verification

After running the script, check your project folder. There should be **no CSV file** — only your `.py` script and virtual environment. The data only ever existed on the SFTP server and in your computer's RAM.