from copy import deepcopy

_AUTH_SCHEMA = {
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
}

_BASE_SCHEMA = {
    'type': 'object',
    'properties': {
        'host': {'type': 'string'},
        'port': {'type': 'integer'},
        'auth': _AUTH_SCHEMA,
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


_CIPHERS_SCHEMA = {
    'oneOf': [
        {
            'type': 'array',
            'items': {'type': 'string'}
        }, {
            'type': 'string'
        }
    ]
}


MOUNT_DIR_SCHEMA = {
    'type': 'object',
    'properties': {
        'host': {'type': 'string'},
        'port': {'type': 'integer'},
        'auth': _AUTH_SCHEMA,
        'dirPath': {'type': 'string'},
        'writable': {'type': 'boolean'},
        'ciphers': _CIPHERS_SCHEMA
    },
    'additionalProperties': False,
    'required': ['host', 'auth', 'dirPath']
}

_LISTING_SUB_FILE_SCHEMA = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['File']},
        'basename': {'type': 'string'},
    },
    'required': ['class', 'basename'],
    'additionalProperties': False
}

_LISTING_SUB_DIRECTORY_SCHEMA = {
    'type': 'object',
    'properties': {
        'class': {'enum': ['Directory']},
        'basename': {'type': 'string'},
        'listing': {'$ref': '#/'}
    },
    'additionalProperties': False,
    'required': ['class', 'basename']
}

# WARNING: Do not embed this schema into another schema,
# because this breaks the '$ref' in listing_sub_directory_schema
LISTING_SCHEMA = {
    'type': 'array',
    'items': {
        'oneOf': [_LISTING_SUB_FILE_SCHEMA, _LISTING_SUB_DIRECTORY_SCHEMA]
    }
}
