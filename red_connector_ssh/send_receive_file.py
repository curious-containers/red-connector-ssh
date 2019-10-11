import os
import json
from argparse import ArgumentParser

import jsonschema

from red_connector_ssh.schemas import FILE_SCHEMA
from red_connector_ssh.helpers import create_ssh_client, ssh_mkdir, DEFAULT_PORT, graceful_error, cut_remote_user_dir, \
    InvalidAuthenticationError

RECEIVE_FILE_DESCRIPTION = 'Receive input file from SSH server.'
RECEIVE_FILE_VALIDATE_DESCRIPTION = 'Validate access data for receive-file.'

SEND_FILE_DESCRIPTION = 'Send output file to SSH server.'
SEND_FILE_VALIDATE_DESCRIPTION = 'Validate access data for send-file.'


def _receive_file(access, local_file_path):
    with open(access) as f:
        access = json.load(f)

    if not os.path.isdir(os.path.dirname(local_file_path)):
        raise NotADirectoryError(
            'Could not create local file "{}". The parent directory does not exist.'.format(local_file_path)
        )

    auth = access['auth']

    remote_file_path = cut_remote_user_dir(access['filePath'])

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
                sftp.get(remote_file_path, local_file_path)
            except FileNotFoundError:
                raise FileNotFoundError('Remote file "{}" could not be found'.format(remote_file_path))


def _receive_file_validate(access):
    with open(access) as f:
        access = json.load(f)

    jsonschema.validate(access, FILE_SCHEMA)

    auth = access['auth']

    remote_file_path = cut_remote_user_dir(access['filePath'])

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
                with sftp.open(remote_file_path, mode='r', bufsize=0):
                    pass
            except FileNotFoundError:
                raise FileNotFoundError('Could not find remote file "{}"'.format(remote_file_path))


def _send_file(access, local_file_path):
    with open(access) as f:
        access = json.load(f)

    if not os.path.isfile(local_file_path):
        raise FileNotFoundError('Could not find local file "{}"'.format(local_file_path))

    auth = access['auth']
    remote_file_path = cut_remote_user_dir(access['filePath'])

    remote_dir_path = os.path.dirname(remote_file_path)

    with create_ssh_client(
            host=access['host'],
            port=access.get('port', DEFAULT_PORT),
            username=auth['username'],
            password=auth.get('password'),
            private_key=auth.get('privateKey'),
            passphrase=auth.get('passphrase')
    ) as client:
        with client.open_sftp() as sftp:
            ssh_mkdir(sftp, remote_dir_path)
            sftp.put(local_file_path, remote_file_path)


def _send_file_validate(access):
    with open(access) as f:
        access = json.load(f)

    jsonschema.validate(access, FILE_SCHEMA)

    # check whether authentication works
    auth = access['auth']
    with create_ssh_client(
            host=access['host'],
            port=access.get('port', DEFAULT_PORT),
            username=auth['username'],
            password=auth.get('password'),
            private_key=auth.get('privateKey'),
            passphrase=auth.get('passphrase')
    ):
        pass


@graceful_error
def receive_file():
    parser = ArgumentParser(description=RECEIVE_FILE_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    parser.add_argument(
        'local_file_path', action='store', type=str, metavar='LOCALFILE',
        help='Local input file path.'
    )
    args = parser.parse_args()
    _receive_file(**args.__dict__)


@graceful_error
def receive_file_validate():
    parser = ArgumentParser(description=RECEIVE_FILE_VALIDATE_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    args = parser.parse_args()
    _receive_file_validate(**args.__dict__)


@graceful_error
def send_file():
    parser = ArgumentParser(description=SEND_FILE_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    parser.add_argument(
        'local_file_path', action='store', type=str, metavar='LOCALFILE',
        help='Local output file path.'
    )
    args = parser.parse_args()
    _send_file(**args.__dict__)


@graceful_error
def send_file_validate():
    parser = ArgumentParser(description=SEND_FILE_VALIDATE_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    args = parser.parse_args()
    _send_file_validate(**args.__dict__)
