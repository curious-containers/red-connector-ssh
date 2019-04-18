import os
import sys
import tempfile
import warnings

import cryptography
import jsonschema
from functools import wraps
from shutil import which

from paramiko import SSHClient, AutoAddPolicy, RSAKey
from scp import SCPException

DEFAULT_PORT = 22

FUSERMOUNT_EXECUTABLES = ['fusermount3', 'fusermount']
SSHFS_EXECUTABLES = ['sshfs']


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
            print('{}:{}{}'.format(repr(e), os.linesep, e), file=sys.stderr)
            exit(3)

    return wrapper


def create_password_command(host, port, username, local_dir_path, dir_path, configfile_path, writable):
    """
    Creates a command as string list, that can be executed to mount the <dir_path> to <local_dir_path>, using the
    provided information.
    sshfs <username>@<host>:<remote_path> <local_path> -o password_stdin -p <port> -F configfile_path
    """

    sshfs_executable = find_sshfs_executable()
    remote_connection = '{username}@{host}:{remote_path}'.format(username=username, host=host, remote_path=dir_path)

    command = [
        sshfs_executable,
        remote_connection,
        local_dir_path,
        '-o', 'password_stdin',
        '-F', configfile_path,
        '-p', str(port)
    ]
    if not writable:
        command.extend(('-o', 'ro'))

    return command


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


def find_sshfs_executable():
    return find_executable(SSHFS_EXECUTABLES)


def find_fusermount_executable():
    return find_executable(FUSERMOUNT_EXECUTABLES)


def check_executables():
    find_sshfs_executable()
    find_fusermount_executable()


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


def ssh_mkdir(sftp, dir_path):
    # source http://stackoverflow.com/a/14819803
    if dir_path == '/':
        sftp.chdir('/')
        return
    if dir_path == '':
        return
    try:
        sftp.chdir(dir_path)
    except IOError:
        dirname, basename = os.path.split(dir_path.rstrip('/'))
        ssh_mkdir(sftp, dirname)
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
    :raise Exception: If neither password nor private_key is given
    :raise SSHException: If the given private_key, username or password is invalid
    :raise socket.gaierror: If the given host is not known
    :return: A connected paramiko.SSHClient
    """
    # TODO: remove this filter, if paramiko 2.5 is released
    warnings.simplefilter('ignore', cryptography.utils.CryptographyDeprecationWarning)

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
        key_file = create_temp_file(private_key)
        pkey = RSAKey.from_private_key(key_file, password=passphrase)
        key_file.close()
        client.connect(host, username=username, pkey=pkey)
    else:
        raise Exception('At least password or private_key must be present.')
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
                raise Exception('The remote file under "{}" could not be transferred.\n{}'.
                                format(remote_path, str(e)))

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
    This base directory should already be present on the local filesystem and contain all files and directories given in
    listing.
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
                raise Exception('The local file "{}" could not be transferred to "{}".\n{}'.
                                format(local_path, remote_path, str(e)))

        elif sub['class'] == 'Directory':
            sftp_client.mkdir(remote_path)
            listing = sub.get('listing')
            if listing:
                send_directory(listing, sftp_client, base_directory, remote_directory, sub_path)
