import paramiko
import pandas as pd
import duckdb


# client = paramiko.SSHClient()
# client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# client.connect(
#     hostname="localhost",
#     port=2022,
#     username="stream_user",
#     password="stream123",
# )

# sftp = client.open_sftp()

# sftp_file = sftp.open("customers.csv")

# print("Handshake complete! Connected and file stream is open.")
# print(type(sftp_file))

transport = paramiko.Transport(("localhost", 2022))
transport.connect(username="stream_user", password="stream123")

sftp = paramiko.SFTPClient.from_transport(transport)

sftp_file = sftp.open("customers.csv")

print("Handshake complete! Connected and file stream is open.")
print(type(sftp_file))

customers = pd.read_csv(sftp_file)
print(customers.head())

duckdb.query("SELECT * FROM customers").show()
# How many customers per state?
duckdb.query("SELECT state, COUNT(*) as customer_count FROM customers GROUP BY state").show()

# Find all customers in Denver
duckdb.query("SELECT * FROM customers WHERE city = 'Denver'").show()