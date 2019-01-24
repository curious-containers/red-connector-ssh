from cc_connector_cli.connector_cli import run_connector
from red_connector_ssh.ssh import Ssh


def run_ssh():
    run_connector(Ssh)


if __name__ == '__main__':
    run_ssh()
