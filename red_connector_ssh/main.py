from cc_connector_cli.connector_cli import create_parser
from red_connector_ssh.sftp import Sftp


def main():
    cli = create_parser(Sftp)
    args = cli.parse_args()
    print('args: {}'.format(args.__dict__))


if __name__ == '__main__':
    main()
