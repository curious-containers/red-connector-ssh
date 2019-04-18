import json
from argparse import ArgumentParser

import jsonschema
from scp import SCPClient

from red_connector_ssh.schemas import DIR_SCHEMA, LISTING_SCHEMA
from red_connector_ssh.helpers import create_ssh_client, fetch_directory, DEFAULT_PORT, graceful_error, send_directory

RECEIVE_DIR_DESCRIPTION = 'Receive input dir from SSH server.'
RECEIVE_DIR_VALIDATE_DESCRIPTION = 'Validate access data for receive-dir.'

SEND_DIR_DESCRIPTION = 'Send output dir to SSH server.'
SEND_DIR_VALIDATE_DESCRIPTION = 'Validate access data for send-dir.'


def _receive_dir(access, local_dir_path, listing):
    with open(access) as f:
        access = json.load(f)

    if listing:
        with open(listing) as f:
            listing = json.load(f)

    auth = access['auth']
    dir_path = access['dirPath']

    with create_ssh_client(
        host=access['host'],
        port=access.get('port', DEFAULT_PORT),
        username=auth['username'],
        password=auth.get('password'),
        private_key=auth.get('privateKey'),
        passphrase=auth.get('passphrase')
    ) as client:
        with SCPClient(client.get_transport()) as scp_client:
            if listing:
                fetch_directory(listing, scp_client, local_dir_path, dir_path)
            else:
                scp_client.get(dir_path, local_dir_path, recursive=True)


def _receive_dir_validate(access, listing):
    with open(access) as f:
        access = json.load(f)
    jsonschema.validate(access, DIR_SCHEMA)

    if listing:
        with open(listing) as f:
            listing = json.load(f)
        jsonschema.validate(listing, LISTING_SCHEMA)


def _send_dir(access, local_dir_path, listing):
    with open(access) as f:
        access = json.load(f)

    if listing:
        with open(listing) as f:
            listing = json.load(f)

    auth = access['auth']
    remote_dir_path = access['dirPath']

    with create_ssh_client(
            host=access['host'],
            port=access.get('port', DEFAULT_PORT),
            username=auth['username'],
            password=auth.get('password'),
            private_key=auth.get('privateKey'),
            passphrase=auth.get('passphrase')
    ) as ssh_client:
        if listing:
            with ssh_client.open_sftp() as sftp_client:
                sftp_client.mkdir(remote_dir_path)
                send_directory(listing, sftp_client, local_dir_path, remote_dir_path)
        else:
            with SCPClient(ssh_client.get_transport()) as scp_client:
                scp_client.put(local_dir_path, remote_dir_path, recursive=True)


def _send_dir_validate(access, listing):
    with open(access) as f:
        access = json.load(f)
    jsonschema.validate(access, DIR_SCHEMA)

    if listing:
        with open(listing) as f:
            listing = json.load(f)
        jsonschema.validate(listing, LISTING_SCHEMA)


@graceful_error
def receive_dir():
    parser = ArgumentParser(description=RECEIVE_DIR_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    parser.add_argument(
        'local_dir_path', action='store', type=str, metavar='LOCALDIR',
        help='Local input dir path.'
    )
    parser.add_argument(
        '--listing', action='store', type=str, metavar='LISTINGFILE',
        help='Local path to LISTINGFILE in JSON format.'
    )
    args = parser.parse_args()
    _receive_dir(**args.__dict__)


@graceful_error
def receive_dir_validate():
    parser = ArgumentParser(description=RECEIVE_DIR_VALIDATE_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    parser.add_argument(
        '--listing', action='store', type=str, metavar='LISTINGFILE',
        help='Local path to LISTINGFILE in JSON format.'
    )
    args = parser.parse_args()
    _receive_dir_validate(**args.__dict__)


@graceful_error
def send_dir():
    parser = ArgumentParser(description=SEND_DIR_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    parser.add_argument(
        'local_dir_path', action='store', type=str, metavar='LOCALDIR',
        help='Local output dir path.'
    )
    parser.add_argument(
        '--listing', action='store', type=str, metavar='LISTINGFILE',
        help='Local path to LISTINGFILE in JSON format.'
    )
    args = parser.parse_args()
    _send_dir(**args.__dict__)


@graceful_error
def send_dir_validate():
    parser = ArgumentParser(description=SEND_DIR_VALIDATE_DESCRIPTION)
    parser.add_argument(
        'access', action='store', type=str, metavar='ACCESSFILE',
        help='Local path to ACCESSFILE in JSON format.'
    )
    parser.add_argument(
        '--listing', action='store', type=str, metavar='LISTINGFILE',
        help='Local path to LISTINGFILE in JSON format.'
    )
    args = parser.parse_args()
    _send_dir_validate(**args.__dict__)
