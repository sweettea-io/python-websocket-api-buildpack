import os

base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

config_file = '.sweettea.yml'
config_path = base_dir + '/' + config_file

client_id_header = 'SweetTea-Client-ID'
client_secret_header = 'SweetTea-Client-Secret'

host = '0.0.0.0'
port = 443

model_archive_format = 'zip'