from copy import deepcopy

_BASE_SCHEMA = {
    'type': 'object',
    'properties': {
        'host': {'type': 'string'},
        'port': {'type': 'integer'},
        'auth': {
            'oneOf': [{
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'password': {'type': 'string'},
                },
                'additionalProperties': False,
                'required': ['username', 'password']
            }, {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'privateKey': {'type': 'string'},
                    'passphrase': {'type': 'string'},
                },
                'additionalProperties': False,
                'required': ['username', 'privateKey']
            }]
        },
    },
    'additionalProperties': False,
    'required': ['host', 'auth']
}


FILE_SCHEMA = deepcopy(_BASE_SCHEMA)
FILE_SCHEMA['properties']['filePath'] = {'type': 'string'}
FILE_SCHEMA['required'].append('filePath')


DIR_SCHEMA = deepcopy(_BASE_SCHEMA)
DIR_SCHEMA['properties']['dirPath'] = {'type': 'string'}
DIR_SCHEMA['required'].append('dirPath')


MOUNT_DIR_SCHEMA = {
    'type': 'object',
    'properties': {
        'host': {'type': 'string'},
        'port': {'type': 'integer'},
        'auth': {
            'type': 'object',
            'properties': {
                'username': {'type': 'string'},
                'password': {'type': 'string'},
            },
            'additionalProperties': False,
            'required': ['username', 'password']
        },
        'dirPath': {'type': 'string'},
        'writable': {'type': 'boolean'}
    },
    'additionalProperties': False,
    'required': ['host', 'auth', 'dirPath']
}