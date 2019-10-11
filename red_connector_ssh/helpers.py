import os
import socket
import sys
import tempfile

import jsonschema
from functools import wraps
from shutil import which

from paramiko import SSHClient, AutoAddPolicy, RSAKey, SFTPClient, AuthenticationException, SSHException
from scp import SCPException

DEFAULT_PORT = 22


def graceful_error(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)

        except jsonschema.exceptions.ValidationError as e:
            if hasattr(e, 'context'):
                print('{}:{}Context: {}'.format(repr(e), os.linesep, e.context), file=sys.stderr)
                exit(1)

            print(repr(e), file=sys.stderr)
            exit(2)

        except Exception as e:
            print('{}: {}'.format(type(e).__name__, e), file=sys.stderr)
            exit(3)

    return wrapper


def find_executable(executables):
    """
    Tries every executable in the given executables, and returns the first that exists in PATH
    :param executables: List of executables
    :return: A string representing the first executable in executables, that is found in PATH
    """
    for executable in executables:
        if which(executable):
            return executable
    raise Exception('One of the following executables must be present in PATH: {}'.format(
        executables
    ))


def create_temp_file(content):
    """
    Creates a temporary file that resists in memory.
    :param content:
    :return:
    """
    tmp_file = tempfile.SpooledTemporaryFile(max_size=1000000, mode='w+')
    tmp_file.write(content)
    tmp_file.seek(0)
    return tmp_file


def cut_remote_user_dir(remote_path):
    """
    sftp does not understand '~', so we cut it away since sftp interprets relative paths relative to the sftp working
    directory, which is initialized as home directory.

    :param remote_path: The path from which to cut the user directory
    :type remote_path: str
    :return: The given path without ~ at the beginning
    :rtype: str
    """
    if remote_path.startswith('~/'):
        return remote_path[2:]

    return remote_path


def ssh_mkdir(sftp, dir_path):
    """
    Recursively creates the given remote_path at the remote location.
    It interprets ~ as home directory and relative path as relative to the home directory.

    :param sftp: The SFTPClient to use
    :type sftp: SFTPClient
    :param dir_path: The path to create at the remote location.
    :type dir_path: str
    """
    dir_path = cut_remote_user_dir(dir_path)

    cwd = sftp.getcwd()
    _ssh_mkdir_recursive(sftp, dir_path)

    # reset sftp client working directory
    sftp.chdir(cwd)


def _ssh_mkdir_recursive(sftp, dir_path):
    # source http://stackoverflow.com/a/14819803
    if dir_path == '/':
        sftp.chdir('/')
        return
    if dir_path == '':
        return
    try:
        sftp.chdir(dir_path)
    except IOError:
        dirname, basename = os.path.split(os.path.normpath(dir_path))
        _ssh_mkdir_recursive(sftp, dirname)
        sftp.mkdir(basename)
        sftp.chdir(basename)


def create_ssh_client(host, port, username, password, private_key, passphrase):
    """
    Creates and returns a connected SSHClient.
    If a password is supplied the connection is created using this password.
    If no password is supplied a valid private key must be present. If this private key is encrypted the associated
    passphrase must be supplied.

    :param host: The host to connect to
    :param username: The username which is used to connect to the ssh host
    :param port: The port number to connect to
    :param password: The password to authenticate
    :param private_key: A valid private RSA key as string
    :param passphrase: A passphrase to decrypt the private key, if the private key is encrypted

    :return: A connected paramiko.SSHClient

    :raise ConnectionError: If the connection to the remote host failed or if neither password nor pkey are specified
    :raise InvalidAuthenticationError: If the authentication to the remote host failed
    """
    client = SSHClient()
    client.set_missing_host_key_policy(AutoAddPolicy())
    if password is not None:
        try:
            client.connect(
                host,
                port=port,
                username=username,
                password=password
            )
        except socket.gaierror:
            raise ConnectionError('Could not connect to remote host "{}"'.format(host))
        except AuthenticationException:
            raise InvalidAuthenticationError(
                'Could not connect to remote host "{}". Invalid username/password.'.format(host)
            )
    elif private_key is not None:
        with create_temp_file(private_key) as key_file:
            try:
                pkey = RSAKey.from_private_key(key_file, password=passphrase)
            except SSHException:
                raise InvalidAuthenticationError('Could not connect to remote host "{}". Invalid key.'.format(host))

        try:
            client.connect(host, username=username, pkey=pkey)
        except socket.gaierror:
            raise ConnectionError('Could not connect to remote host "{}"'.format(host))
    else:
        raise ConnectionError('At least password or private_key must be present.')

    return client


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
                raise SCPException(
                    'The remote file under "{}" could not be transferred.\n{}'.format(remote_path, str(e))
                )

        elif sub['class'] == 'Directory':
            os.mkdir(local_path)
            listing = sub.get('listing')
            if listing:
                fetch_directory(listing, scp_client, base_directory, remote_directory, sub_path)


def send_directory(listing, sftp_client, base_directory, remote_directory, path="./"):
    """
    Sends the files/directories given in the listing using the given scp_client.
    The read/write/execute permissions of the remote and local directories may differ.

    :param listing: A listing specifying the directories and files to send to the remote host.
    :param sftp_client: A paramiko SFTPClient, that has to be connected to a host.
    :param base_directory: The path to the directory, where the files to send are stored.
                           This base directory should already be present on the local filesystem and contain all files
                           and directories given in listing.
    :param remote_directory: The path to the remote base directory where to put the subfiles and directories.
    :param path: A path specifying which subdirectory of remove_directory should be fetched and where to place it
                 under base_directory. The files are fetched from os.path.join(remote_directory, path) and placed
                 under os.path.join(base_directory, path)

    :raise Exception: If the listing specifies a file or directory that is not present in the local base_directory
    """
    for sub in listing:
        sub_path = os.path.normpath(os.path.join(path, sub['basename']))
        remote_path = os.path.normpath(os.path.join(remote_directory, sub_path))
        local_path = os.path.normpath(os.path.join(base_directory, sub_path))

        if sub['class'] == 'File':
            try:
                sftp_client.put(local_path, remote_path)
            except SCPException as e:
                raise SCPException(
                    'The local file "{}" could not be transferred to "{}".\n{}'.format(local_path, remote_path, str(e))
                )

        elif sub['class'] == 'Directory':
            sys.stdout.flush()
            try:
                sftp_client.mkdir(remote_path)
            except OSError:
                # this happens, if this directory already exists
                pass
            listing = sub.get('listing')
            if listing:
                send_directory(listing, sftp_client, base_directory, remote_directory, sub_path)


def check_remote_dir_available(access):
    """
    Tries to create an SSHClient with the given access information and checks if the specified directory is available

    :param access: The access information to use

    :raise FileNotFoundError: If the remote directory is not available
    :raise ConnectionError: If the connection to the remote host failed or if neither password nor pkey are specified
    :raise InvalidAuthenticationError: If the authentication to the remote host failed
    """
    auth = access['auth']
    remote_dir_path = cut_remote_user_dir(access['dirPath'])

    with create_ssh_client(
            host=access['host'],
            port=access.get('port', DEFAULT_PORT),
            username=auth['username'],
            password=auth.get('password'),
            private_key=auth.get('privateKey'),
            passphrase=auth.get('passphrase')
    ) as client:
        with client.open_sftp() as sftp:
            try:
                sftp.listdir(remote_dir_path)
            except FileNotFoundError:
                raise FileNotFoundError('Could not find remote directory "{}"'.format(remote_dir_path))


class InvalidAuthenticationError(Exception):
    pass
