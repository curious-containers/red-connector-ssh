import json
import os
from argparse import ArgumentParser

import jsonschema
from scp import SCPClient, SCPException

from red_connector_ssh.schemas import DIR_SCHEMA, LISTING_SCHEMA
from red_connector_ssh.helpers import create_ssh_client, fetch_directory, DEFAULT_PORT, graceful_error, \
    send_directory, ssh_mkdir, cut_remote_user_dir, check_remote_dir_available

RECEIVE_DIR_DESCRIPTION = 'Receive input dir from SSH server.'
RECEIVE_DIR_VALIDATE_DESCRIPTION = 'Validate access data for receive-dir.'

SEND_DIR_DESCRIPTION = 'Send output dir to SSH server.'
SEND_DIR_VALIDATE_DESCRIPTION = 'Validate access data for send-dir.'


def _load_access_listing(access, listing):
    with open(access) as f:
        access = json.load(f)

    if listing:
        with open(listing) as f:
            listing = json.load(f)

    return access, listing


def _receive_dir(access, local_dir_path, listing):
    local_dir_path = os.path.normpath(local_dir_path)
    access, listing = _load_access_listing(access, listing)
    auth = access['auth']
    remote_dir_path = os.path.normpath(cut_remote_user_dir(access['dirPath']))

    if not os.path.isdir(os.path.dirname(local_dir_path)):
        raise FileNotFoundError(
            'Could not create local directory "{}", because parent directory does not exist'.format(local_dir_path)
        )

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
                try:
                    os.mkdir(local_dir_path)
                except FileExistsError:
                    pass
                fetch_directory(listing, scp_client, local_dir_path, remote_dir_path)
            else:
                try:
                    scp_client.get(remote_dir_path, local_dir_path, recursive=True)
                except SCPException:
                    raise FileNotFoundError('Could not find remote directory "{}"'.format(remote_dir_path))
                except FileNotFoundError:
                    raise NotADirectoryError(
                        'Could not create local directory "{}", because parent directory does not exist'
                        .format(local_dir_path)
                    )


def _receive_dir_validate(access, listing):
    access, listing = _load_access_listing(access, listing)

    jsonschema.validate(access, DIR_SCHEMA)
    if listing:
        jsonschema.validate(listing, LISTING_SCHEMA)

    check_remote_dir_available(access)


def _send_dir(access, local_dir_path, listing):
    access, listing = _load_access_listing(access, listing)
    auth = access['auth']
    remote_dir_path = os.path.normpath(cut_remote_user_dir(access['dirPath']))

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
                ssh_mkdir(sftp_client, remote_dir_path)
                send_directory(listing, sftp_client, local_dir_path, remote_dir_path)
        else:
            with ssh_client.open_sftp() as sftp_client:
                remote_parent_dir = os.path.dirname(remote_dir_path)
                ssh_mkdir(sftp_client, remote_parent_dir)
            with SCPClient(ssh_client.get_transport()) as scp_client:
                scp_client.put(local_dir_path, remote_dir_path, recursive=True)


def _send_dir_validate(access, listing):
    access, listing = _load_access_listing(access, listing)

    jsonschema.validate(access, DIR_SCHEMA)
    if listing:
        jsonschema.validate(listing, LISTING_SCHEMA)

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
