import json
import os
import stat
import subprocess
from tempfile import NamedTemporaryFile
from argparse import ArgumentParser

import jsonschema
import pexpect

from red_connector_ssh.helpers import DEFAULT_PORT, graceful_error, check_remote_dir_available, \
    InvalidAuthenticationError, find_executable
from red_connector_ssh.schemas import MOUNT_DIR_SCHEMA


MOUNT_DIR_DESCRIPTION = 'Mount dir from SSH server.'
MOUNT_DIR_VALIDATE_DESCRIPTION = 'Validate access data for mount-dir.'
UMOUNT_DIR_DESCRIPTION = 'Unmount directory previously mounted via mount-dir.'

FUSERMOUNT_EXECUTABLES = ['fusermount3', 'fusermount']
SSHFS_EXECUTABLES = ['sshfs']
MOUNT_TIMEOUT = 3


def create_configfile(ciphers, enable_password=False):
    """
    Creates a configuration file for the sshfs client.

    :param ciphers: The ciphers to use, given as list or string
    :type ciphers: List[str] or str
    :param enable_password: If False password authentication is disabled
    :type enable_password: bool
    :return: A NamedTemporaryFile, containing the given configuration
    :rtype: NamedTemporaryFile
    """
    configfile = NamedTemporaryFile('w')

    configfile.write('StrictHostKeyChecking=no\n')

    if not enable_password:
        configfile.write('PasswordAuthentication=no\n')

    if ciphers:
        if isinstance(ciphers, list):
            ciphers_string = ','.join(ciphers)
        else:
            ciphers_string = ciphers

        configfile.write('Ciphers={}\n'.format(ciphers_string))

    configfile.flush()

    return configfile


def split_to_length(s, n):
    """
    Splits the given string s into a list of string, where each string has a maximal length n.

    :param s: The string to split
    :param n: The maximum length of each string in the result
    :return: A list of strings with maximum length n
    """
    result = []

    for i in range(0, len(s), n):
        result.append(s[i:i+n])
    return result


def create_identity_file(private_key):
    """
    Creates the identity file from a given private as string.
    Each line is not longer than 64 characters. The line before the body is an empty line. The owner has read
    permissions all other permissions are disabled.

    :param private_key: The private key given as string
    :type private_key: str
    :return: A NamedTemporaryFile that contains the given private key
    :rtype: NamedTemporaryFile
    """
    identity_file = NamedTemporaryFile('w')
    lines = private_key.split('\n')

    # split last line in blocks of 64 chars
    for line in lines:
        small_lines = split_to_length(line, 64)

        # newline before key body
        if len(small_lines) > 1:
            identity_file.write('\n')
        for small_line in small_lines:
            identity_file.write(small_line + '\n')

    identity_file.flush()

    # set file permissions, so sshfs accepts the key
    os.chmod(identity_file.name, stat.S_IRUSR)

    return identity_file


def check_executables():
    find_sshfs_executable()
    find_fusermount_executable()


def find_sshfs_executable():
    return find_executable(SSHFS_EXECUTABLES)


def find_fusermount_executable():
    return find_executable(FUSERMOUNT_EXECUTABLES)


def create_sshfs_command(
        host,
        port,
        username,
        local_dir_path,
        remote_path,
        configfile_path,
        writable,
        enable_password_stdin=False,
        identity_file=None
):
    """
    Creates a command as string list, that can be executed to mount the <dir_path> to <local_dir_path>, using the
    provided information.
    sshfs <username>@<host>:<remote_path> <local_path> -o password_stdin -p <port> -F configfile_path

    :param host: The host to connect to
    :param port: The port to use at the host
    :param username: The username which is used for authentication
    :param local_dir_path: The local directory where to mount the remote directory
    :param remote_path: The directory at the remote machine which is mounted to the local directory
    :param configfile_path: A path to a local configuration file
    :param writable: If False the mounted directory is read only
    :param enable_password_stdin: If set to True, sshfs will wait for the authentication password in stdin
    :param identity_file: The path to the identity file with the private key to use for authentication
    """
    sshfs_executable = find_sshfs_executable()
    remote_connection = '{username}@{host}:{remote_path}'.format(username=username, host=host, remote_path=remote_path)

    command = [
        sshfs_executable,
        remote_connection,
        local_dir_path,
        '-F', configfile_path,
        '-p', str(port)
    ]

    if enable_password_stdin:
        command.extend(('-o', 'password_stdin'))

    if identity_file:
        command.extend(('-o', 'IdentityFile={}'.format(identity_file)))

    if not writable:
        command.extend(('-o', 'ro'))

    return command


def _mount_with_key_and_passphrase(command, passphrase):
    """
    Mounts a directory using the given command and enters a passphrase, if necessary.
    See https://github.com/pexpect/pexpect/issues/192 for information, why a bash shell is started.

    :param command: The sshfs command that mounts the remote directory
    :param passphrase: The passphrase to enter, after command execution

    :raise InvalidAuthorizationError: If the authorization failed
    """
    bash = pexpect.spawn('bash', echo=False)

    bash.sendline('echo READY')
    bash.expect_exact('READY')

    bash.sendline(' '.join(command))

    bash.expect(
        ['.*Enter passphrase for key \'.*\':', '.*Connection reset by peer.*', pexpect.TIMEOUT],
        timeout=MOUNT_TIMEOUT
    )
    if bash.match_index == 0:
        bash.sendline(passphrase)
        bash.expect([
                '.*Connection reset by peer.*',
                '.*Enter passphrase for key \'.*\':',  # sshfs asks for passphrase again, if the given passphrase was
                                                       # wrong
                '\r\n',
                pexpect.TIMEOUT],
            timeout=0.5
        )
        if bash.match_index == 0:
            raise InvalidAuthenticationError('Permission denied.')
        elif bash.match_index == 1:
            raise InvalidAuthenticationError('Invalid passphrase')
    else:
        raise InvalidAuthenticationError('Permission denied.')

    bash.sendline('echo FINISHED')
    bash.expect(['FINISHED', pexpect.TIMEOUT], timeout=1)

    bash.sendline('exit')
    bash.expect_exact(pexpect.EOF)


def _mount_dir(access, local_dir_path):
    with open(access) as f:
        access = json.load(f)

    os.makedirs(local_dir_path, exist_ok=True)

    host = access['host']
    port = access.get('port', DEFAULT_PORT)
    dir_path = access['dirPath']
    auth = access['auth']
    username = auth['username']
    password = auth.get('password')
    private_key = auth.get('privateKey')
    passphrase = auth.get('passphrase')
    ciphers = access.get('ciphers')

    enable_password = False
    identity_file = None

    if private_key:
        identity_file = create_identity_file(private_key)
    elif password:
        enable_password = True
    else:
        raise InvalidAuthenticationError('At least password or private_key must be present.')

    with create_configfile(ciphers, enable_password=enable_password) as temp_configfile:
        command = create_sshfs_command(
            host=host,
            port=port,
            username=username,
            local_dir_path=local_dir_path,
            remote_path=dir_path,
            configfile_path=temp_configfile.name,
            writable=access.get('writable', False),
            enable_password_stdin=enable_password,
            identity_file=identity_file.name if identity_file else None
        )

        if private_key:
            if passphrase:
                try:
                    _mount_with_key_and_passphrase(command, passphrase)
                except InvalidAuthenticationError as e:
                    raise InvalidAuthenticationError(
                        'Could not mount directory using\n\thost={host}\n\tport={port}\n\tlocalDir={local_dir_path}\n\t'
                        'dirPath={dir_path}\n\tauthentication=key + passphrase\nvia sshfs:\n{error}.'.format(
                            host=host,
                            port=port,
                            local_dir_path=local_dir_path,
                            dir_path=dir_path,
                            error=str(e)
                        )
                    )
                finally:
                    identity_file.close()
            else:
                process_result = subprocess.run(
                    command, stderr=subprocess.PIPE
                )

                identity_file.close()

                if process_result.returncode != 0:
                    raise InvalidAuthenticationError(
                        'Could not mount directory using\n\thost={host}\n\tport={port}\n\tlocalDir={local_dir_path}\n\t'
                        'dirPath={dir_path}\n\tauthentication=key no passphrase\nvia sshfs:\n{error}'.format(
                            host=host,
                            port=port,
                            local_dir_path=local_dir_path,
                            dir_path=dir_path,
                            error=process_result.stderr.decode('utf-8')
                        )
                    )
        elif password:
            process_result = subprocess.run(
                command, input=password.encode('utf-8'), stderr=subprocess.PIPE
            )

            if process_result.returncode != 0:
                raise InvalidAuthenticationError(
                    'Could not mount directory using\n\thost={host}\n\tport={port}\n\tlocalDir={local_dir_path}\n\t'
                    'dirPath={dir_path}\n\tauthentication=password\nvia sshfs:\n{error}'.format(
                        host=host,
                        port=port,
                        local_dir_path=local_dir_path,
                        dir_path=dir_path,
                        error=process_result.stderr.decode('utf-8')
                    )
                )


def _mount_dir_validate(access):
    with open(access) as f:
        access = json.load(f)
    
    jsonschema.validate(access, MOUNT_DIR_SCHEMA)
    check_executables()

    check_remote_dir_available(access)


def _umount_dir(local_dir_path):
    fusermount_executable = find_fusermount_executable()

    process_result = subprocess.run([fusermount_executable, '-u', local_dir_path], stderr=subprocess.PIPE)
    if process_result.returncode != 0:
        raise Exception(
            'Could not unmount local_dir_path={local_dir_path} via {fusermount_executable}:\n{error}'.format(
                local_dir_path=local_dir_path,
                fusermount_executable=fusermount_executable,
                error=process_result.stderr
            )
        )


@graceful_error
def mount_dir():
    parser = ArgumentParser(description=MOUNT_DIR_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    parser.add_argument(
        'local_dir_path', action='store', type=str, metavar='LOCALDIR',
        help='Local dir path.'
    )
    args = parser.parse_args()
    _mount_dir(**args.__dict__)


@graceful_error
def mount_dir_validate():
    parser = ArgumentParser(description=MOUNT_DIR_VALIDATE_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    args = parser.parse_args()
    _mount_dir_validate(**args.__dict__)


@graceful_error
def umount_dir():
    parser = ArgumentParser(description=UMOUNT_DIR_DESCRIPTION)
    parser.add_argument(
        'local_dir_path', action='store', type=str, metavar='LOCALDIR',
        help='Local output dir path.'
    )
    args = parser.parse_args()
    _umount_dir(**args.__dict__)
