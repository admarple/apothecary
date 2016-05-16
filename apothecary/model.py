import json
import logging
import boto3
import botocore.exceptions
from abc import ABCMeta, abstractmethod
from docopt import docopt
"""
Usage:
  model.py [options]

Utility for setting up data model in persistent storage (currently DynamoDB)

Options:
  -f --fresh            Recreate fresh tables.  Will blow away any existing data.
  -p --prefix <prefix>  Prefix table names.  Useful for dev environments.

"""


class DAO(metaclass=ABCMeta):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'string',
                'AttributeType': 'S | N | B'
            },
        ],
        'TableName': 'string',
        'KeySchema': [
            {
                'AttributeName': 'string',
                'KeyType': 'HASH | RANGE'
            },
        ],
        'LocalSecondaryIndexes': [
            {
                'IndexName': 'string',
                'KeySchema': [
                    {
                        'AttributeName': 'string',
                        'KeyType': 'HASH | RANGE'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL | KEYS_ONLY | INCLUDE',
                    'NonKeyAttributes': [
                        'string',
                    ]
                }
            },
        ],
        'GlobalSecondaryIndexes': [
            {
                'IndexName': 'string',
                'KeySchema': [
                    {
                        'AttributeName': 'string',
                        'KeyType': 'HASH | RANGE'
                    },
                ],
                'Projection': {
                    'ProjectionType': 'ALL | KEYS_ONLY | INCLUDE',
                    'NonKeyAttributes': [
                        'string',
                    ]
                },
                'ProvisionedThroughput': {
                    'ReadCapacityUnits': 1,
                    'WriteCapacityUnits': 1
                }
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        },
        'StreamSpecification': {
            'StreamEnabled': True | False,
            'StreamViewType': 'NEW_IMAGE | OLD_IMAGE | NEW_AND_OLD_IMAGES | KEYS_ONLY'
        }
    }

    @staticmethod
    @abstractmethod
    def from_json(dao_json):
        pass

    @classmethod
    def create_table(cls, client):
        client.create_table(**cls.schema)

    @classmethod
    def delete_table(cls, dynamodb):
        cls.table(dynamodb).delete()

    @classmethod
    def add_tablename_prefix(cls, prefix):
        cls.schema['TableName'] = prefix + cls.schema['TableName']

    @classmethod
    def get_hash_key(cls):
        return next(schema for schema in cls.schema['KeySchema'] if schema['KeyType'] == 'HASH')

    @classmethod
    def get_range_key(cls):
        return next((schema for schema in cls.schema['KeySchema'] if schema['KeyType'] == 'HASH'), None)

    @classmethod
    def get(cls, dynamodb, hash_key, range_key=None):
        keys = { cls.get_hash_key()['AttributeName']: hash_key }
        if range_key and cls.get_range_key():
            keys[cls.get_range_key()['AttributeName']] = range_key

        from_dynamo = cls.table(dynamodb).get_item(
            Key=keys,
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from GetItem: %s', from_dynamo['ConsumedCapacity'])

        return json.loads(from_dynamo['Item'], object_hook=cls.from_json)

    @classmethod
    def table(cls, dynamodb):
        return dynamodb.Table(cls.schema['TableName'])

    def put(self, dynamodb):
        from_dynamo = self.table(dynamodb).put_item(
            Item=vars(self),
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from PutItem: %s', from_dynamo['ConsumedCapacity'])

    def update(self, dynamodb):
        from_dynamo = self.table(dynamodb).update_item(
            Item=vars(self),
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from UpdateItem: %s', from_dynamo['ConsumedCapacity'])
        pass


class NavGroup(DAO):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'nav_group_id',
                'AttributeType': 'S'
            },
        ],
        'TableName': 'Nav',
        'KeySchema': [
            {
                'AttributeName': 'nav_group_id',
                'KeyType': 'HASH'
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 3,
            'WriteCapacityUnits': 3
        }
    }

    def __init__(self, nav_group_id):
        self.nav_group_id = nav_group_id
        self.navs = []

    @staticmethod
    def from_json(nav_group_json):
        nav_group = NavGroup(nav_group_json['nav_group_id'])
        if hasattr(nav_group_json, 'navs'):
            for nav_json in nav_group_json['navs']:
                nav_group.navs.append(Nav.from_json(nav_json))
        return nav_group


class Nav(object):
    def __init__(self, nav_id, href, caption):
        self.nav_id = nav_id
        self.href = href
        self.caption = caption

    @staticmethod
    def from_json(nav_json):
        return Nav(nav_json['nav_id'], nav_json['href'], nav_json['caption'])


class SectionGroup(DAO):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'section_group_id',
                'AttributeType': 'S'
            },
        ],
        'TableName': 'Section',
        'KeySchema': [
            {
                'AttributeName': 'section_group_id',
                'KeyType': 'HASH'
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 3,
            'WriteCapacityUnits': 3
        }
    }

    def __init__(self, section_group_id, href, caption):
        self.section_group_id = section_group_id
        self.sections = []

    @staticmethod
    def from_json(section_group_json):
        section_group = NavGroup(section_group_json['section_group_id'])
        if hasattr(section_group_json, 'sections'):
            for section_json in section_group_json['sections']:
                section_group.navs.append(Section.from_json(section_json))
        return section_group


class Section(object):
    def __init__(self, section_id, title, text):
        self.section_id = section_id
        self.title = title
        self.text = text

    @staticmethod
    def from_json(nav_json):
        return Section(nav_json['section_id'], nav_json['title'], nav_json['text'])


def all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]


def setup(fresh=False, prefix=''):
    client = boto3.client('dynamodb')
    dynamodb = boto3.resource('dynamodb')

    dao_classes = all_subclasses(DAO)
    for dao_class in dao_classes:
        if prefix:
            dao_class.add_tablename_prefix(prefix)
        dao_table = dao_class.table(dynamodb)

        # optionally delete the existing table
        if fresh:
            try:
                dao_table.delete()
                dao_table.wait_until_not_exists()
                logging.info('Deleted table for %s', dao_class)
            except botocore.exceptions.ClientError as e:
                if 'Requested resource not found: Table' in str(e):
                    logging.info('Table for %s does not yet exist', dao_class)

        # create the new table
        try:
            dao_class.create_table(client)
            dao_table.wait_until_exists()
            logging.info('Created table for %s', dao_class)
        except botocore.exceptions.ClientError as e:
            if 'Table already exists' in str(e):
                logging.info('Table for %s already exists', dao_class)


if __name__ == '__main__':
    options = docopt(__doc__)
    setup(options['-f'])
