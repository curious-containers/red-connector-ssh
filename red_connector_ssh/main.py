from collections import OrderedDict

from red_connector_ssh.cli_modes import cli_modes
from red_connector_ssh.version import VERSION

from red_connector_ssh.send_receive_file import receive_file, receive_file_validate
from red_connector_ssh.send_receive_file import RECEIVE_FILE_DESCRIPTION, RECEIVE_FILE_VALIDATE_DESCRIPTION
from red_connector_ssh.send_receive_file import send_file, send_file_validate
from red_connector_ssh.send_receive_file import SEND_FILE_DESCRIPTION, SEND_FILE_VALIDATE_DESCRIPTION

from red_connector_ssh.send_receive_dir import receive_dir, receive_dir_validate
from red_connector_ssh.send_receive_dir import RECEIVE_DIR_DESCRIPTION, RECEIVE_DIR_VALIDATE_DESCRIPTION
from red_connector_ssh.send_receive_dir import send_dir, send_dir_validate
from red_connector_ssh.send_receive_dir import SEND_DIR_DESCRIPTION, SEND_DIR_VALIDATE_DESCRIPTION

from red_connector_ssh.mount_dir import mount_dir, mount_dir_validate, umount_dir
from red_connector_ssh.mount_dir import MOUNT_DIR_DESCRIPTION, MOUNT_DIR_VALIDATE_DESCRIPTION, UMOUNT_DIR_DESCRIPTION


CLI_VERSION = '1'
SCRIPT_NAME = 'red-connector-ssh'
DESCRIPTION = 'RED Connector SSH'
TITLE = 'modes'

MODES = OrderedDict([
    ('cli-version', {'main': lambda: print(CLI_VERSION), 'description': 'RED connector CLI version.'}),
    ('receive-file', {'main': receive_file, 'description': RECEIVE_FILE_DESCRIPTION}),
    ('receive-file-validate', {'main': receive_file_validate, 'description': RECEIVE_FILE_VALIDATE_DESCRIPTION}),
    ('send-file', {'main': send_file, 'description': SEND_FILE_DESCRIPTION}),
    ('send-file-validate', {'main': send_file_validate, 'description': SEND_FILE_VALIDATE_DESCRIPTION}),
    ('receive-dir', {'main': receive_dir, 'description': RECEIVE_DIR_DESCRIPTION}),
    ('receive-dir-validate', {'main': receive_dir_validate, 'description': RECEIVE_DIR_VALIDATE_DESCRIPTION}),
    ('send-dir', {'main': send_dir, 'description': SEND_DIR_DESCRIPTION}),
    ('send-dir-validate', {'main': send_dir_validate, 'description': SEND_DIR_VALIDATE_DESCRIPTION}),
    ('mount-dir', {'main': mount_dir, 'description': MOUNT_DIR_DESCRIPTION}),
    ('mount-dir-validate', {'main': mount_dir_validate, 'description': MOUNT_DIR_VALIDATE_DESCRIPTION}),
    ('umount-dir', {'main': umount_dir, 'description': UMOUNT_DIR_DESCRIPTION}),
])


def main():
    cli_modes(SCRIPT_NAME, TITLE, DESCRIPTION, MODES, VERSION)
