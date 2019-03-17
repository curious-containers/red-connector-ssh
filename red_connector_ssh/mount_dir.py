import json
import tempfile
import subprocess
from argparse import ArgumentParser

import jsonschema

from red_connector_ssh.helpers import create_password_command, find_executables, DEFAULT_PORT, graceful_error
from red_connector_ssh.schemas import MOUNT_DIR_SCHEMA


MOUNT_DIR_DESCRIPTION = 'Mount dir from SSH server.'
MOUNT_DIR_VALIDATE_DESCRIPTION = 'Validate access data for mount-dir.'

UMOUNT_DIR_DESCRIPTION = 'Unmout directory previously mounted via mount-dir.'


def _mount_dir(access, local_dir_path):
    with open(access) as f:
        access = json.load(f)

    host = access['host']
    port = access.get('port', DEFAULT_PORT)
    dir_path = access['dirPath']
    auth = access['auth']
    username = auth['username']
    password = auth['password']

    with tempfile.NamedTemporaryFile('w') as temp_configfile:
        temp_configfile.write('StrictHostKeyChecking=no')
        temp_configfile.flush()
        command = create_password_command(
            host=host,
            port=port,
            username=username,
            local_dir_path=local_dir_path,
            dir_path=dir_path,
            configfile_path=temp_configfile.name,
            writable=access.get('writable', False)
        )
        command = ' '.join(command)

        process_result = subprocess.run(
            command, input=password.encode('utf-8'), stderr=subprocess.PIPE, shell=True
        )

        if process_result.returncode != 0:
            raise Exception(
                'Could not mount directory using host={host}, port={port}, dirPath={dir_path} via sshfs":'
                '\n{error}'.format(
                    host=host,
                    port=port,
                    dir_path=dir_path,
                    error=process_result.stderr.decode('utf-8')
                )
            )


def _mount_dir_validate(access):
    with open(access) as f:
        access = json.load(f)
    
    jsonschema.validate(access, MOUNT_DIR_SCHEMA)
    _ = find_executables()


def _umount_dir(local_dir_path):
    _, fusermount_executable = find_executables()

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
