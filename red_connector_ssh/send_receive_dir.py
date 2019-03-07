from argparse import ArgumentParser

from scp import SCPClient

from red_connector_ssh.schemas import DIR_SCHEMA
from red_connector_ssh.helpers import create_ssh_client, fetch_directory, validate, DEFAULT_PORT


RECEIVE_DIR_DESCRIPTION = 'Receive input dir from SSH server.'
RECEIVE_DIR_VALIDATE_DESCRIPTION = 'Validate access data for receive-dir.'

SEND_DIR_DESCRIPTION = 'Send output dir to SSH server.'
SEND_DIR_VALIDATE_DESCRIPTION = 'Validate access data for send-dir.'


def _receive_dir(access, local_dir_path, listing):
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
            if listing is None:
                scp_client.get(dir_path, local_dir_path, recursive=True)
            else:
                fetch_directory(listing, scp_client, local_dir_path, dir_path)


def _receive_dir_validate(access, listing):
    validate(access, DIR_SCHEMA)


def _send_dir(access, local_dir_path, listing):
    raise NotImplementedError('send-dir is not yet implemented')


def _send_dir_validate(access, listing):
    raise NotImplementedError('send-dir is not yet implemented')


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
