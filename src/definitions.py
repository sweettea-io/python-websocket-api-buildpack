import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

config_path = base_dir + '/.tensorci.yml'

client_id_header = 'TensorCI-Client-ID'
client_secret_header = 'TensorCI-Client-Secret'

host = '0.0.0.0'
port = 443