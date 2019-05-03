import os
import json
from argparse import ArgumentParser

import jsonschema

from red_connector_ssh.schemas import FILE_SCHEMA
from red_connector_ssh.helpers import create_ssh_client, ssh_mkdir, DEFAULT_PORT, graceful_error

RECEIVE_FILE_DESCRIPTION = 'Receive input file from SSH server.'
RECEIVE_FILE_VALIDATE_DESCRIPTION = 'Validate access data for receive-file.'

SEND_FILE_DESCRIPTION = 'Send output file to SSH server.'
SEND_FILE_VALIDATE_DESCRIPTION = 'Validate access data for send-file.'


def _receive_file(access, local_file_path):
    with open(access) as f:
        access = json.load(f)

    auth = access['auth']

    with create_ssh_client(
        host=access['host'],
        port=access.get('port', DEFAULT_PORT),
        username=auth['username'],
        password=auth.get('password'),
        private_key=auth.get('privateKey'),
        passphrase=auth.get('passphrase')
    ) as client:
        with client.open_sftp() as sftp:
            sftp.get(access['filePath'], local_file_path)


def _receive_file_validate(access):
    with open(access) as f:
        access = json.load(f)

    jsonschema.validate(access, FILE_SCHEMA)


def _send_file(access, local_file_path):
    with open(access) as f:
        access = json.load(f)

    auth = access['auth']
    file_path = access['filePath']
    dir_path = os.path.dirname(file_path)

    with create_ssh_client(
            host=access['host'],
            port=access.get('port', DEFAULT_PORT),
            username=auth['username'],
            password=auth.get('password'),
            private_key=auth.get('privateKey'),
            passphrase=auth.get('passphrase')
    ) as client:
        with client.open_sftp() as sftp:
            ssh_mkdir(sftp, dir_path)
            sftp.put(local_file_path, file_path)


def _send_file_validate(access):
    with open(access) as f:
        access = json.load(f)

    jsonschema.validate(access, FILE_SCHEMA)


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
