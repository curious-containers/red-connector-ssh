import os
import jsonschema
import stat
import tempfile
from scp import SCPClient, SCPException
from paramiko import SSHClient, AutoAddPolicy, RSAKey


DEFAULT_DIRECTORY_MODE = stat.S_IWUSR | stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH \
                         | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH


sftp_schema = {
    'type': 'object',
    'properties': {
        'host': {'type': 'string'},
        'port': {'type': 'integer'},
        'username': {'type': 'string'},
        'password': {'type': 'string'},
        'privateKey': {'type': 'string'},
        'passphrase': {'type': 'string'},
        'fileDir': {'type': 'string'},
        'fileName': {'type': 'string'}
    },
    'additionalProperties': False,
    'required': ['host', 'username', 'fileDir', 'fileName']
}

sftp_directory_schema = {
    'type': 'object',
    'properties': {
        'host': {'type': 'string'},
        'port': {'type': 'integer'},
        'username': {'type': 'string'},
        'password': {'type': 'string'},
        'privateKey': {'type': 'string'},
        'passphrase': {'type': 'string'},
        'dirName': {'type': 'string'},
    },
    'additionalProperties': False,
    'required': ['host', 'username', 'dirName']
}


def _create_temp_file(content):
    """
    Creates a temporary file that resists in memory.
    :param content:
    :return:
    """
    tmp_file = tempfile.SpooledTemporaryFile(max_size=1000000, mode='w+')
    tmp_file.write(content)
    tmp_file.seek(0)
    return tmp_file


def _create_ssh_client(host, username, port=22, password=None, private_key=None, passphrase=None):
    """
    Creates and returns a connected SSHClient.
    If a password is supplied the connection is created using this password.
    If no password is supplied a valid private key must be present. If this private key is encrypted the associated
    passphrase must be supplied.

    :param host: The host to connect to
    :param username: The username which is used to connect to the ssh host
    :param port: The port number to connect to. Default is 22
    :param password: The password to authenticate
    :param private_key: A valid private RSA key as string
    :param passphrase: A passphrase to decrypt the private key, if the private key is encrypted
    :raise Exception: If neither password nor private_key is given
    :raise SSHException: If the given private_key, username or password is invalid
    :raise socket.gaierror: If the given host is not known
    :return: A connected paramiko.SSHClient
    """
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    if password is not None:
        client.connect(
            host,
            port=port,
            username=username,
            password=password
        )
    elif private_key is not None:
        key_file = _create_temp_file(private_key)
        pkey = RSAKey.from_private_key(key_file, password=passphrase)
        key_file.close()
        client.connect(host, username=username, pkey=pkey)
    else:
        raise Exception('At least password or private_key must be present.')
    return client


class Sftp:
    @staticmethod
    def receive(access, internal):
        host = access['host']
        port = access.get('port', 22)
        username = access['username']
        password = access.get('password')
        file_dir = access['fileDir']
        file_name = access['fileName']
        private_key = access.get('privateKey')
        passphrase = access.get('passphrase')

        with _create_ssh_client(host, username, port, password, private_key, passphrase) as client:
            with client.open_sftp() as sftp:
                remote_file_path = os.path.join(file_dir, file_name)
                sftp.get(remote_file_path, internal['path'])

    @staticmethod
    def receive_validate(access):
        jsonschema.validate(access, sftp_schema)

        # At least password or privateKey must be present
        if ('password' not in access) and ('privateKey' not in access):
            raise Exception('At least "password" or "privateKey" must be present.')

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
        password = access.get('password')
        file_dir = access['fileDir']
        file_name = access['fileName']
        private_key = access.get('privateKey')
        passphrase = access.get('passphrase')

        remote_file_path = os.path.join(file_dir, file_name)

        with _create_ssh_client(host, username, port, password, private_key, passphrase) as client:
            with client.open_sftp() as sftp:
                Sftp._ssh_mkdir(sftp, file_dir)
                sftp.put(
                    internal['path'],
                    os.path.join(remote_file_path)
                )

    @staticmethod
    def send_validate(access):
        try:
            jsonschema.validate(access, sftp_schema)
        except jsonschema.ValidationError as e:
            if e.context:
                raise Exception(e.context)
            else:
                raise Exception(str(e))

    @staticmethod
    def fetch_directory(listing, scp_client, base_directory, remote_directory, path="./"):
        """
        Fetches the directories given in the listing using the given scp_client.
        The read/write/execute permissions of the remote and local directories may differ.

        :param listing: A complete listing with complete urls for every containing file.
        :param scp_client: A SCPClient, that has to be connected to a host.
        :param base_directory: The path to the base directory, where to create the fetched files and directories.
                          This base directory should already be present on the local filesystem.
        :param remote_directory: The path to the remote base directory from where to fetch the subfiles and directories.
        :param path: A path specifying which subdirectory of remove_directory should be fetched and where to place it
                     under base_directory. The files are fetched from os.path.join(remote_directory, path) and placed
                     under os.path.join(base_directory, path)

        :raise Exception: If the listing specifies a file or directory which is not present on the remote host
        """

        for sub in listing:
            sub_path = os.path.normpath(os.path.join(path, sub['basename']))
            remote_path = os.path.normpath(os.path.join(remote_directory, sub_path))
            local_path = os.path.normpath(os.path.join(base_directory, sub_path))

            if sub['class'] == 'File':
                try:
                    scp_client.get(remote_path=remote_path, local_path=local_path)
                except SCPException as e:
                    raise Exception('The remote file under "{}" could not be transferred.\n{}'.
                                    format(remote_path, str(e)))

            elif sub['class'] == 'Directory':
                os.mkdir(local_path, DEFAULT_DIRECTORY_MODE)
                listing = sub.get('listing')
                if listing:
                    Sftp.fetch_directory(listing, scp_client, base_directory, remote_directory, sub_path)

    @staticmethod
    def receive_directory(access, internal, listing):
        """
        Fetches a directory from a ssh server and stores at under the path given by internal['path']

        :param access: A dictionary containing access information. Has the following keys
                       - 'host': The host to connect to
                       - 'username': A username that is used to perform authentication
                       - 'password': A password that is used to perform authentication
                       - 'dirName': The name of the directory to fetch
        :param internal: A dictionary containing information about where to put the directory content
        :param listing: Listing of subfiles and subdirectories which are contained by the directory given in access.
                        Specified like a listing in the common workflow language
        :raise Exception: If the remote host is not accessible or the listing specifies a directory or a file, which is
                          not present on the remote machine.
        """

        host = access['host']
        port = access.get('port', 22)
        username = access['username']
        password = access.get('password')
        private_key = access.get('privateKey')
        passphrase = access.get('passphrase')
        remote_path = access['dirName']

        with _create_ssh_client(host, username, port, password, private_key, passphrase) as ssh_client:
            local_path = internal['path']

            with SCPClient(ssh_client.get_transport()) as scp_client:
                if listing is None:
                    scp_client.get(remote_path, local_path, recursive=True)
                else:
                    os.mkdir(local_path, DEFAULT_DIRECTORY_MODE)
                    Sftp.fetch_directory(listing, scp_client, local_path, remote_path)

    @staticmethod
    def receive_directory_validate(access):
        try:
            jsonschema.validate(access, sftp_directory_schema)
        except jsonschema.ValidationError as e:
            if e.context:
                raise Exception(e.context)
            else:
                raise Exception(str(e))

        # At least password or privateKey must be present
        if ('password' not in access) and ('privateKey' not in access):
            raise Exception('At least "password" or "privateKey" must be present.')
