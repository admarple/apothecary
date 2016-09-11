#!/usr/bin/env python
"""
Usage:
  model.py [options]

Utility for setting up data model in persistent storage (currently DynamoDB)

Options:
  --fresh-tables            Recreate fresh tables.  Will blow away any existing data.
  --fresh-data              Add all of the data from setup.
  -p --prefix <prefix>      Prefix table names.  Useful for dev environments.

"""

import jsonpickle
import json
import logging
import re
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


class RSVP(DAO):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'rsvp_id',
                'AttributeType': 'S'
            },
        ],
        'TableName': 'RSVP',
        'KeySchema': [
            {
                'AttributeName': 'rsvp_id',
                'KeyType': 'HASH'
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 2,
            'WriteCapacityUnits': 2
        }
    }

    def __init__(self, name, email, address, guests, hotel_preference, notes):
        self.rsvp_id = re.sub(' +', ' ', name.lower().strip())
        self.name = non_null(name)
        self.email = non_null(email)
        self.address = non_null(address)
        self.guests = non_null(guests)
        self.hotel_preference = non_null(hotel_preference)
        self.notes = non_null(notes)


def all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]


def non_null(thing):
    return thing or 'N/A'


def setup(fresh_data=False, fresh_tables=False, prefix=''):
    client = boto3.client('dynamodb')
    dynamodb = boto3.resource('dynamodb')

    dao_classes = all_subclasses(DAO)
    for dao_class in dao_classes:
        if prefix:
            dao_class.add_tablename_prefix(prefix)
        dao_table = dao_class.table(dynamodb)

        # optionally delete the existing table
        if fresh_tables:
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

    if fresh_data:
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
        travel.sections.append(Section('accommodations', 'Accommodations',
            '<a href="https://www.oneoceanresort.com/special-pkg?gclid=CK2BqZiQ-c4CFVVahgodJwsCaQ">One Ocean</a>:'
            + ' ~$250 / night, 1.5 Miles / 6 min from reception'
            + '<br/>'
            + '<a href="http://www.marriott.com/hotels/travel/jaxjv-courtyard-jacksonville-beach-oceanfront/">Courtyard Marriott</a>:'
            + ' $210 + / Night, 3 Miles / 9 min from reception'
            + '<br/>'
            + '<a href="http://www.marriott.com/hotels/travel/jaxjb-fairfield-inn-and-suites-jacksonville-beach/?scid=bb1a189a-fec3-4d19-a255-54ba596febe2">Fairfield Inn & Suites</a>:'
            + ' CURRENTLY NO ROOMS AVAILABLE'
            + '<br/>'
            + '<a href="http://www.bestwesternjacksonvillebeach.com/">Best Western</a>:'
            + ' $200 + / Night, 3.9 Miles / 12 min from reception'
            + '<br/>'
            + '<a href="http://www.fourpointsjacksonvillebeach.com/">Four Points by Sheraton</a>:'
            + ' ~$300/ night, 4 Miles / 12 min from reception'
            + '<br/>'
            + '<a href="http://www.pontevedra.com/inn_and_club/lodginginnclub/">Ponte Vedra Inn & Club</a>:'
            + ' ~$350 / night, 7.3 Miles / 20min  from the reception'))
        travel.put(dynamodb)

        area = SectionGroup('area')
        area.sections.append(Section('neptune_beach', 'Neptune Beach',
            '''The City of Neptune Beach is a small, quiet coastal community nestled on the northeast coast of Florida between Atlantic Beach and Jacksonville Beach. Neptune Beach has a comfortable, casual and laid-back atmosphere that causes people of all ages to flock here to enjoy the beach. The hard-packed sand is great for cycling and the surf is super for the avid surfer. If you're an early bird, catch the sun rising above the ocean, it's a site to behold. The inviting, pedestrian friendly area offers many boutiques and restaurants and in close proximity to a variety of hotels.
              <br/>
              The name Neptune Beach has origins dating back to the year 1922 when Dan Wheeler built his own train station next to his home and named it Neptune. Mr. Wheeler had been informed that if he were to build a station, the train would be required to stop. The construction of the station eliminated his walking to Mayport in order to take the train to work in Jacksonville. The station was located where the Sea Turtle Inn is now located.
              The area remained a part of Jacksonville Beach until the tax revolt of 1931, when on August 11, the residents of Neptune voted 113 to 31 to secede from Jacksonville Beach and incorporate the City of Neptune Beach.'''))
        area.sections.append(Section('restaurants', 'Restaurants',
            '<a href="http://thenorthbeachfishcamp.com/">The North Beach Fish Camp</a>:'
            + ' Our favorite restaurant with a neighborhood feel and the freshest seafood. Tat\'s favorite is the fried'
            + ' shrimp platter.'
            + '<br/>'
            + '<a href="http://www.whitsfrozencustard.com">Whit\'s Frozen Custard</a>:'
            + ' Cool off with a sweet treat after a day in the Jacksonville heat. Tat & Alex\'s favorite flavors are'
            + ' Mud Pie and Black Raspberry Chip.'
            + '<br/>'
            + '<a href="http://www.tacolu.com/">TacoLu</a>:'
            + ' A broad selection of tacos, and a broader selection of Tequila, for anyone wanting to relive Alex &'
            + ' Tat\'s impromptu Mexico trip.'
            + '<br/>'
            + '<a href="http://www.allmenus.com/fl/jacksonville/109176-angies-subs/menu/">Angie\'s Subs</a>'
            + ' Quirky sub shop, showcased by the fact that the most popular sandwich is "The Peruvian".'
            + ' Enjoy with an endless glass of Tat\'s favorite sweet tea.'
            + ' Extracurricular activity: ask if anyone knows what a "hoagie" is.'
            + '<br/>'
            + '<a href="http://sogrocoffee.com/menu/">Southern Grounds Coffee</a>:'
            + ' A casual cafe with outdoor seating. Tat loves both the iced chai latte and the cappuccino, and a'
            + ' Caprese Panini when she\'s feeling peckish.'))
        area.sections.append(Section('rentals', 'Beach Rentals',
            '<a href="http://www.beachliferentals.com/">Beach Life Rentals</a>:'
            + ' Rental beach gear, along with bike rentals for anyone looking to enjoy Neptune Beach on two wheels.'
            + '<br/>'
            + '<a href="http://www.eastcoastsportrentals.info/services.htm">East Coast Sport Rentals</a>:'
            + ' More of the same, but perhaps more convenient for anyone staying closer to Jax Beach.'))
        area.sections.append(Section('nightlife', 'Nightlife',
            '<a href="http://flyingiguana.com/">The Flying Iguana</a>:'
            + ' '
            + '<br/>'
            + '<a href="http://www.lemonbarjax.com/">The Lemon Bar</a>:'
            + ' Tat may not love lemons, but she has nothing against this unpretentious bar by the beach.'))
        area.sections.append(Section('around_jax', 'Around Jacksonville',
            '<a href="http://www.oldcity.com/">St. Augustine</a>:'
            + ' There is plenty to do in the U.S.\'s oldest city, St. Augustine. In fact, the first time Alex visited'
            + ' Tat in Jacksonville, they visited the Castillo de San Marcos National Monument, the Fort Matanzas, and'
            + ' the Lightner Museum. Alex even bought some tea at the Spice & Tea Exchange right off the historic St.'
            + ' George Street. On your ~50min drive back to Jax / Neptune beach, perhaps stop for a tree-shaded dinner'
            + ' on the water at Tat\'s favorite outdoor restaurant, <a href="http://www.capsonthewater.com/">Cap\'s</a>'
            + '<br/>'
            + '<a href="http://www.simon.com/mall/st-johns-town-center">St. John\'s Town Center</a>:'
            + ' Jacksonville has an outdoor shopping mall with some great chain restaurants such as '
            + ' <a href="https://www.cantinalaredo.com">Cantina Laredo</a>.'
            + ' <a href="http://www.cinemark.com/theatre-detail.aspx?node_id=1547&#4/28/2017">Tinseltown</a> movie'
            + ' theater is near by as well where you may find Tat in a sweatshirt watching an action movie with Alex.'
            + '<br/>'
            + 'For those of you who golf, make sure the check out the'
            + ' <a href="http://www.worldgolfhalloffame.org/">World Golf Hall of Fame</a> (40min drive from Neptune'
            + ' Beach) and <a href="http://www.pgatour.com/tournaments/the-players-championship.html">TPC Sawgrass</a>'
            + ' (25min drive from Neptune Beach).'
            + '<br/>'
            + '<a href="http://www.cummer.org/">The Cummer Museum</a>:'
            + ' The Cummer Museum not only holds one of the finest art collections in the Southeast but is also home to'
            + ' gorgeous outdoor gardens. If you are planning on spending time in down town Jax this is a must see.'
            + '<br/>'))
        area.sections.append(Section('beyond', 'Beyond Jacksonville',
            'Tat & Alex hope that those with a bit more wanderlust have a chance to visit other parts of Florida either'
            + ' before or after the wedding.'
            + '<br/>'
            + '<br/>'
            + '<a href="https://www.kennedyspacecenter.com/">Kennedy Space Center</a>:'
            + ' For anyone with a tendency to geek out about space flight, NASA\'s Kennedy Space Center is about 2.5'
            + ' hours\' drive from Neptune Beach.'
            + '<br/>'
            + '<a href="https://disneyworld.disney.go.com/">Disney</a> & <a href="https://www.universalorlando.com/">Universal</a>:'
            + ' Orlando is home to both Disney and Universal theme parks, and is 3 hours by car from Neptune Beach. If'
            + ' you do stop by, Tat\'s favorite rise is <a href="https://www.universalorlando.com/Rides/Islands-of-Adventure/Dragon-Challenge.aspx">"Dragon Challenge"</a>'
            + ' - formerly "Fire & Ice" - in Islands of Adventure.'
            + '<br/>'
            + '<a href="http://www.visitflorida.com/en-us.html">visitflorida.com</a>:'
            + ' additional info on destinations in the Sunshine State.'))
        area.put(dynamodb)

if __name__ == '__main__':
    setup(prefix=options['--prefix'] + '_',
          fresh_data=options['--fresh-data'],
          fresh_tables=options['--fresh-tables'])