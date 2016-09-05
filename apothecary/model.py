import jsonpickle
import json
import logging
import boto3
import botocore.exceptions
from docopt import docopt


class DAO(object):
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

        return jsonpickle.decode(json.dumps(from_dynamo['Item']))

    @classmethod
    def table(cls, dynamodb):
        return dynamodb.Table(cls.schema['TableName'])

    def put(self, dynamodb):
        from_dynamo = self.table(dynamodb).put_item(
            Item=json.loads(jsonpickle.encode(self)),
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from PutItem: %s', from_dynamo['ConsumedCapacity'])

    def update(self, dynamodb):
        from_dynamo = self.table(dynamodb).update_item(
            Item=json.loads(jsonpickle.encode(self)),
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from UpdateItem: %s', from_dynamo['ConsumedCapacity'])

    def delete(self, dynamodb):
        hash_key = cls.get_hash_key()['AttributeName']
        hash_key_value = getattr(self, hash_key)
        keys = { hash_key: hash_key_value }
        if cls.get_range_key():
            range_key = cls.get_range_key()['AttributeName']
            range_key_value = getattr(self, range_key)
            keys[range_key] = range_key_value

        from_dynamo = self.table(dynamodb).delete_item(
            Key=keys,
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from DeleteItem: %s', from_dynamo['ConsumedCapacity'])


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


class Nav(object):
    def __init__(self, nav_id, href, caption):
        self.nav_id = nav_id
        self.href = href
        self.caption = caption


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

    def __init__(self, section_group_id):
        self.section_group_id = section_group_id
        self.sections = []


class Section(object):
    def __init__(self, section_id, title, text):
        self.section_id = section_id
        self.title = title
        self.text = text


class Couple(DAO):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'couple_id',
                'AttributeType': 'S'
            },
        ],
        'TableName': 'Couple',
        'KeySchema': [
            {
                'AttributeName': 'couple_id',
                'KeyType': 'HASH'
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 3,
            'WriteCapacityUnits': 3
        }
    }

    def __init__(self, couple_id, her, him):
        self.couple_id = couple_id
        self.her = her
        self.him = him


class Guest(DAO):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'guest_id',
                'AttributeType': 'N'
            },
        ],
        'TableName': 'Guest',
        'KeySchema': [
            {
                'AttributeName': 'guest_id',
                'KeyType': 'HASH'
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 2,
            'WriteCapacityUnits': 2
        }
    }

    def __init__(self, user_id):
        self.user_id = user_id


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
                else:
                    raise e

        # create the new table
        try:
            dao_class.create_table(client)
            dao_table.wait_until_exists()
            logging.info('Created table for %s', dao_class)
        except botocore.exceptions.ClientError as e:
            if 'Table already exists' in str(e):
                logging.info('Table for %s already exists', dao_class)
            else:
                raise e

    if fresh:
        header_nav = NavGroup('header_nav')
        header_nav.navs.extend([
            Nav('index', '/', 'a M t'),
            Nav('story', '/story/', 'Our Story'),
            Nav('event', '/event/', 'Event Info'),
            Nav('travel', '/travel/', 'Travel Info'),
            Nav('area', '/area/', 'In the Area')
        ])
        header_nav.put(dynamodb)

        footer_nav = NavGroup('footer_nav')
        footer_nav.navs.append(Nav('github', 'https://github.com/admarple/apothecary', 'Source on GitHub'))
        footer_nav.put(dynamodb)

        story = SectionGroup('story')
        story.sections.append(Section('her', 'Tatiana', 'Tatiana is the best :D'))
        story.sections.append(Section('him', 'Alex', 'Tatiana is the best :D'))
        story.sections.append(Section('couple', 'Our Story', 'Tat and Alex met in 2010 in Philadelphia. ' +
                                      ' After a stint on opposite coasts following school, they converged ' +
                                      ' on New York in 2014 and were engaged in 2016.'))
        story.put(dynamodb)

        couple = Couple('0', 'Tatiana McLauchlan', 'Alex Marple')
        couple.put(dynamodb)

        event = SectionGroup('event')
        event.sections.append(Section('ceremony', 'Ceremony', 'The ceremony will be held at ... '))
        event.sections.append(Section('reception', 'Reception', 'The reception will be held at Atlantic Beach Country Club. ...'))
        event.put(dynamodb)

        travel = SectionGroup('travel')
        travel.sections.append(Section('getting_there', 'Getting There', 'Jacksonville International Airport ... '))
        travel.sections.append(Section('accommodations', 'Accommodations', ' ... '))
        travel.put(dynamodb)

        area = SectionGroup('area')
        area.sections.append(Section('dining', 'Dining', 'Dining nearby ... '))
        area.sections.append(Section('activities', 'Activities', 'Activities nearby ... '
           + '\n Atlantic Beach & Neptune Beach'
           + '\n St. Augustine'))
        area.sections.append(Section('shopping', 'Shopping', 'Shopping nearby ... '))
        area.put(dynamodb)
