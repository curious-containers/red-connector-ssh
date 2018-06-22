import os
import jsonschema
from paramiko import SSHClient, AutoAddPolicy


sftp_schema = {
    'type': 'object',
    'properties': {
        'host': {'type': 'string'},
        'port': {'type': 'integer'},
        'username': {'type': 'string'},
        'password': {'type': 'string'},
        'file_dir': {'type': 'string'},
        'file_name': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['host', 'username', 'password', 'file_dir', 'file_name']
}


class Sftp:
    @staticmethod
    def receive(access, internal):
        host = access['host']
        port = access.get('port', 22)
        username = access['username']
        password = access['password']
        file_dir = access['file_dir']
        file_name = access['file_name']

        remote_file_path = os.path.join(file_dir, file_name)

        with SSHClient() as client:
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(
                host,
                port=port,
                username=username,
                password=password
            )
            with client.open_sftp() as sftp:
                sftp.get(remote_file_path, internal['path'])

    @staticmethod
    def receive_validate(access):
        jsonschema.validate(access, sftp_schema)

    @staticmethod
    def _ssh_mkdir(sftp, remote_directory):
        # source http://stackoverflow.com/a/14819803
        if remote_directory == '/':
            sftp.chdir('/')
            return
        if remote_directory == '':
            return
        try:
            sftp.chdir(remote_directory)
        except IOError:
            dirname, basename = os.path.split(remote_directory.rstrip('/'))
            Sftp._ssh_mkdir(sftp, dirname)
            sftp.mkdir(basename)
            sftp.chdir(basename)

    @staticmethod
    def send(access, internal):
        host = access['host']
        port = access.get('port', 22)
        username = access['username']
        password = access['password']
        file_dir = access['file_dir']
        file_name = access['file_name']

        remote_file_path = os.path.join(file_dir, file_name)

        with SSHClient() as client:
            client.set_missing_host_key_policy(AutoAddPolicy())
            client.connect(
                host,
                port=port,
                username=username,
                password=password
            )
            with client.open_sftp() as sftp:
                Sftp._ssh_mkdir(sftp, file_dir)
                sftp.put(
                    internal['path'],
                    os.path.join(remote_file_path)
                )

    @staticmethod
    def send_validate(access):
        jsonschema.validate(access, sftp_schema)
