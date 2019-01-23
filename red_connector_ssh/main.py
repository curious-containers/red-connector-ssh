from cc_connector_cli.connector_cli import run_connector
from red_connector_ssh.sftp import Sftp


def run_sftp():
    run_connector(Sftp)


if __name__ == '__main__':
    run_sftp()
