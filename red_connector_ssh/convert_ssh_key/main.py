import binascii
import os
import sys
from argparse import ArgumentParser

import paramiko
from red_connector_ssh.version import VERSION


DESCRIPTION = 'Converts a given private key file into an entry for a red connector. This is useful, if you want to ' \
              'enable ssh access in an experiment via a private key.'

DEFAULT_OUTPUT_FILE = 'variables.yml'
DEFAULT_VARIABLE_KEY = 'privateKey'
DEFAULT_PASSPHRASE_KEY = 'passphrase'


def main():
    parser = ArgumentParser(description=DESCRIPTION)
    parser.add_argument(
        'key_file', action='store', type=str, metavar='KEYFILE',
        help='The private key file to convert.'
    )
    parser.add_argument(
        '--format', action='store', type=str, metavar='FORMAT', choices=['json', 'yaml', 'yml'], default='yaml',
        help='Specify FORMAT for generated data as one of [json, yaml, yml]. Default is yaml.'
    )
    parser.add_argument(
        '--passphrase', action='store', type=str, default=None,
        help='Passphrase to validate the given key file. If no validation is wanted, you can bypass with '
             '--no-validation.'
    )
    parser.add_argument(
        '--no-validation', action='store_true', help='Bypass key validation.'
    )
    parser.add_argument(
        '--output-file', action='store', type=str, default=DEFAULT_OUTPUT_FILE,
        help='The output file to write. Default is "{}".'.format(DEFAULT_OUTPUT_FILE)
    )
    parser.add_argument(
        '--variable-key', action='store', type=str, default=DEFAULT_VARIABLE_KEY,
        help='The variable key in the output file. Default is "{}".'.format(DEFAULT_VARIABLE_KEY)
    )
    parser.add_argument(
        '-v', '--version', action='version', version=VERSION
    )

    args = parser.parse_args()

    key_file_path = args.key_file

    try:
        key_file = open(key_file_path, 'r')
    except FileNotFoundError:
        print('Error: File "{}" not found'.format(key_file_path))
        return 1

    # validate key_file
    if not args.no_validation:
        try:
            paramiko.RSAKey.from_private_key(key_file, password=args.passphrase)
            key_file.seek(0)
        except paramiko.ssh_exception.PasswordRequiredException:
            print(
                'The given private key file needs a passphrase for validation (see --help). If you want to bypass '
                'validation run again with "--no-validation"',
                file=sys.stderr
            )
            return 2
        except binascii.Error:
            print('The given private key file "{}" is not valid.'.format(key_file_path))
            return 3
        except paramiko.ssh_exception.SSHException as e:
            print('{}: {}'.format(type(e).__name__, str(e)))
            return 4

    # read key_file
    lines = []
    for line in key_file:
        lines.append(line.strip())

    # write everything to string
    key_string = '\\n'.join(lines)

    # write to output_file
    with open(os.path.expanduser(args.output_file), 'a') as output_file:
        output_file.write('{}: \"{}\"\n'.format(args.variable_key, key_string))
        if args.passphrase:
            output_file.write('{}: \"{}\"\n'.format(DEFAULT_PASSPHRASE_KEY, args.passphrase))

    print('Success: output file has been written to "{}"'.format(args.output_file))
