import paramiko
import pandas as pd
import duckdb


def connect_and_stream(hostname, port, username, password, filename):
    """
    Connects to an SFTP server and opens a remote file as a stream.
    Returns the transport, sftp client, and file stream.
    """
    # Create the encrypted tunnel to the server
    transport = paramiko.Transport((hostname, port))

    # Authenticate with username and password
    transport.connect(username=username, password=password)

    # Open an SFTP session over that tunnel
    sftp = paramiko.SFTPClient.from_transport(transport)

    # Open the remote file as a stream (no download)
    sftp_file = sftp.open(filename)

    return transport, sftp, sftp_file


def load_to_dataframe(sftp_file):
    """
    Reads the SFTP file stream into a Pandas DataFrame in memory.
    No data is written to disk.
    """
    df = pd.read_csv(sftp_file)
    return df


def run_queries(df):
    """
    Runs SQL queries against the in-memory DataFrame using DuckDB.
    """
    # Show all records
    print("── All Records ──")
    duckdb.query("SELECT * FROM df").show()

    # Count customers per state
    print("── Customers by State ──")
    duckdb.query("""
        SELECT state, COUNT(*) as customer_count 
        FROM df 
        GROUP BY state
        ORDER BY customer_count DESC
    """).show()

    # Find all customers in Denver
    print("── Denver Customers ──")
    duckdb.query("SELECT * FROM df WHERE city = 'Denver'").show()


def close_connections(transport, sftp, sftp_file):
    """
    Closes all connections. Always clean up when you're done.
    """
    sftp_file.close()
    sftp.close()
    transport.close()
    print("All connections closed.")


# ── Main ──
if __name__ == "__main__":
    # Phase 1: The Handshake
    transport, sftp, sftp_file = connect_and_stream(
        hostname="127.0.0.1",
        port=2022,
        username="stream_user",
        password="stream123",
        filename="customers.csv"
    )
    print("Phase 1 complete — connected and stream is open.")

    # Phase 2: The In-Memory Bridge
    df = load_to_dataframe(sftp_file)
    print(f"Phase 2 complete — {len(df)} rows loaded into memory.")

    # Phase 3: The Query
    run_queries(df)

    # Clean up
    close_connections(transport, sftp, sftp_file)