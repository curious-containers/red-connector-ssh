from cc_connector_cli.connector_cli import run_connector
from red_connector_ssh.ssh import Ssh


def main():
    run_connector(Ssh)
