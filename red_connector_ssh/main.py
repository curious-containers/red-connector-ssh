from cc_connector_cli.connector_cli import run_connector
from red_connector_ssh.sftp import Sftp
from red_connector_ssh.version import VERSION


def main():
    run_connector(Sftp, version=VERSION)


if __name__ == '__main__':
    main()
