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
import simplejson as json
import logging
import re
import boto3
import botocore.exceptions
from docopt import docopt
from decimal import Decimal


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
    def get_hash_key_schema(cls):
        return next(schema for schema in cls.schema['KeySchema'] if schema['KeyType'] == 'HASH')

    @classmethod
    def get_hash_key_name(cls):
        return cls.get_hash_key_schema()['AttributeName']

    @classmethod
    def get_range_key_schema(cls):
        return next((schema for schema in cls.schema['KeySchema'] if schema['KeyType'] == 'RANGE'), None)

    @classmethod
    def get_range_key_name(cls):
        return cls.get_range_key_schema()['AttributeName']

    def get_keys(self):
        hash_key_name = self.get_hash_key_name()
        hash_key_val = getattr(self, hash_key_name)
        keys = { hash_key_name : hash_key_val }
        if self.get_range_key_schema():
            range_key_name = self.get_range_key_name()
            range_key_val = getattr(self, range_key_name)
            keys[range_key_name] = range_key_val
        return keys

    @classmethod
    def get(cls, dynamodb, hash_key, range_key=None):
        keys = { cls.get_hash_key_name(): hash_key }
        if range_key and cls.get_range_key_schema():
            keys[cls.get_range_key_name()] = range_key

        from_dynamo = cls.table(dynamodb).get_item(
            Key=keys,
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from GetItem: %s', from_dynamo['ConsumedCapacity'])

        return jsonpickle.decode(json.dumps(from_dynamo['Item'], use_decimal=True))

    @classmethod
    def scan(cls, dynamodb, **kwargs):
        table = cls.table(dynamodb)
        while True:
            from_dynamo = table.scan(kwargs)
            last_key = from_dynamo.get('LastEvaluatedKey')
            for item in from_dynamo.get('Items'):
                logging.debug('loaded: {0}'.format(item))
                dumped = json.dumps(item, use_decimal=True)
                logging.debug('dumped: {0}'.format(dumped))
                unpickled = jsonpickle.decode(dumped)
                logging.debug('unpickled: {0}'.format(unpickled))
                yield unpickled
            if not last_key:
                break
            else:
                kwargs['ExclusiveStartKey'] = last_key

    @classmethod
    def table(cls, dynamodb):
        return dynamodb.Table(cls.schema['TableName'])

    def put(self, dynamodb):
        logging.debug('self: {0}'.format(self))
        pickled = jsonpickle.encode(self)
        logging.debug('pickled: {0}'.format(pickled))
        re_jsoned = json.loads(pickled, use_decimal=True)
        logging.debug('re-jsoned: {0}'.format(re_jsoned))
        from_dynamo = self.table(dynamodb).put_item(
            Item=re_jsoned,
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from PutItem: %s', from_dynamo['ConsumedCapacity'])

    @staticmethod
    def format_for_dynamo(item):
        '''
        TODO: implement this as a function that takes an item, and converts it into the DynamoDB representation.
        For example, "hello" would become {"S": "hello"}, 2.6 would become {"N": "2.6"}, ["foo", "bar"] would
        become {"SS": ["foo", "bar"]}, and so forth.

        See http://docs.aws.amazon.com/amazondynamodb/latest/APIReference/API_AttributeValue.html
        '''
        pass

    def update(self, dynamodb, fields):
        keys = self.get_keys()
        update_expression = 'SET ' + ' , '.join(['{0} = :{0}'.format(field) for field in fields])
        expression_values = { ':{0}'.format(field) : self.format_for_dynamo(getattr(self, field)) for field in fields }

        from_dynamo = self.table(dynamodb).update_item(
            Key=keys,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_values,
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from UpdateItem: %s', from_dynamo['ConsumedCapacity'])

    def delete(self, dynamodb):
        keys = self.get_keys()
        from_dynamo = self.table(dynamodb).delete_item(
            Key=keys,
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from DeleteItem: %s', from_dynamo['ConsumedCapacity'])

    @staticmethod
    def quotes_csv(values):
        return ','.join(['"{0}"'.format(v) for v in values])

    def field_names(self):
        field_names = sorted([field for field in vars(self)])
        hash_key = self.get_hash_key_name()
        field_names.remove(hash_key)
        field_names.insert(0, hash_key)
        if self.get_range_key_schema():
            range_key = self.get_range_key_name()
            field_names.remove(range_key)
            field_names.insert(1, range_key)
        return field_names

    def module_name(self):
        return '.'.join([self.__module__, self.__class__.__name__])

    def dump_csv_header(self):
        return DAO.quotes_csv(self.field_names())

    def dump_csv(self):
        return DAO.quotes_csv([getattr(self, field) for field in self.field_names()])

    def __str__(self):
        return self.__dict__.__str__()


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
            'ReadCapacityUnits': 2,
            'WriteCapacityUnits': 1
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
            'ReadCapacityUnits': 2,
            'WriteCapacityUnits': 1
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
            'ReadCapacityUnits': 2,
            'WriteCapacityUnits': 1
        }
    }

    def __init__(self, couple_id, her, him, accommodations=False):
        self.couple_id = couple_id
        self.her = her
        self.him = him
        self.accommodations = accommodations


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
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
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
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    }

    def __init__(self, name, email, address, guests, hotel_preference, notes, declined=False, meal_preference={}, rsvp_notes=None):
        self.rsvp_id = re.sub(' +', ' ', name.lower().strip())
        self.name = non_null(name)
        self.email = non_null(email)
        self.address = non_null(address)
        self.guests = non_null(guests)
        self.hotel_preference = non_null(hotel_preference)
        self.notes = non_null(notes)
        self.declined = declined
        self.meal_preference = meal_preference
        self.rsvp_notes = rsvp_notes

    def update_for_rsvp(self, dynamodb):
        keys = self.get_keys()
        update_expression = 'SET meal_preference = :meal_preference' \
            + ' , guests = :guests' \
            + ' , declined = :declined' \
            + ' , rsvp_notes = :rsvp_notes' \
            + ' , #py = :py_object'
        expression_names = {
            '#py': 'py/object'
        }
        expression_values = {
            ':meal_preference': self.meal_preference,
            ':guests': self.guests,
            ':declined': self.declined,
            ':rsvp_notes': self.rsvp_notes or ' ',
            ':py_object': self.module_name()
        }

        from_dynamo = self.table(dynamodb).update_item(
            Key=keys,
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
            ReturnConsumedCapacity='INDEXES'
        )
        logging.info('DynamoDB consumed capacity from UpdateItem: %s', from_dynamo['ConsumedCapacity'])


class Meal(DAO):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'name',
                'AttributeType': 'S'
            },
        ],
        'TableName': 'Meal',
        'KeySchema': [
            {
                'AttributeName': 'name',
                'KeyType': 'HASH'
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        }
    }

    def __init__(self, name, description=None):
        self.name = name
        self.description = description


class Accommodation(DAO):
    schema = {
        'AttributeDefinitions': [
            {
                'AttributeName': 'name',
                'AttributeType': 'S'
            },
        ],
        'TableName': 'Accommodation',
        'KeySchema': [
            {
                'AttributeName': 'name',
                'KeyType': 'HASH'
            },
        ],
        'ProvisionedThroughput': {
            'ReadCapacityUnits': 2,
            'WriteCapacityUnits': 1
        }
    }

    def __init__(self, name, link, price, miles_to_reception, driving_minutes_to_reception):
        self.name = name
        self.link = link
        self.price = price
        self.miles_to_reception = miles_to_reception
        self.driving_minutes_to_reception = driving_minutes_to_reception


def all_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__() for g in all_subclasses(s)]


def non_null(thing):
    return thing or 'N/A'


# Needed to get json, jsonpickle, and boto3 to play nicely with Decimals
class DecimalHandler(jsonpickle.handlers.BaseHandler):
    def flatten(self, obj, data):
        return float(str(obj))

# jsonpickle.handlers.registry.register(Decimal, DecimalHandler)


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
            Nav('party', '/party/', 'Wedding Party'),
            Nav('event', '/event/', 'Event Info'),
            Nav('travel', '/travel/', 'Travel Info'),
            Nav('area', '/area/', 'In the Area'),
            Nav('rsvp', '/rsvp/', 'RSVP')
        ])
        header_nav.put(dynamodb)

        footer_nav = NavGroup('footer_nav')
        footer_nav.navs.append(Nav('github', 'https://github.com/admarple/apothecary', 'Source on GitHub'))
        footer_nav.put(dynamodb)

        story = SectionGroup('story')
        story.sections.append(Section('fling', 'The Beginning',
            'Alex was a sophomore engineer on the diving team and Tat was a freshman engineer on the swim team. They started talking during \'10 Spring Fling. '
            + '<br/><img src="/static/story/fling.jpg"/>'))
        story.sections.append(Section('diving', 'Diving...',
            'They managed to find time to date between school, diving...'
            + '<br/><img src="/static/story/diving.jpg"/>'))
        story.sections.append(Section('swimming', 'Swimming ...',
            '... and swimming'
            + '<br/><img src="/static/story/swimming.jpg"/>'))
        story.sections.append(Section('alex_grad', 'Alex\'s Graduation',
             'Two years flew by and all of a sudden Alex was graduating and moving to Seattle.'
             + '<br/><img src="/static/story/alex_grad.jpg"/>'))
        story.sections.append(Section('seattle', 'Alex in Seattle',
            'Tat would visit him and they went to pick out pumpkins, toured the city, and even went skiing!'
            + '<br/><img src="/static/story/skiing.jpg"/>'))
        story.sections.append(Section('tat_grad', 'Tat\'s Graduation',
            'It was then Tat\'s turn to graduate and she moved to the Big Apple.'
            + '<br/><img src="/static/story/tat_grad.jpg"/>'))
        story.sections.append(Section('chichen_itza', 'Chichen Itza',
            'In February 2014 Alex & Tat went on their first trip together.Tat was super excited to escape frozen NYC to see Alex... Alex was excited about the columns at Chichen Itza.'
            + '<br/><img src="/static/story/chichen_itza.jpg"/>'))
        story.sections.append(Section('newark', 'Alex moves back East',
            'A long four months later Alex moved to the city in June of 2014!!'
            + '<br/><img src="/static/story/newark.jpg"/>'))
        story.sections.append(Section('met', 'The Met',
            '... where they would go to the Met ...'
            + '<br/><img src="/static/story/met_rooftop.jpg"/>'))
        story.sections.append(Section('central_park', 'Central Park',
            '... and for walks in Central Park.'
            + '<br/><img src="/static/story/central_park.jpg"/>'))
        story.sections.append(Section('london', 'London',
            'Their next trip was to London (This was Alex\'s first trip to Europe).'
            + '<br/><img src="/static/story/tower_bridge.jpg"/>'))
        story.sections.append(Section('paris', 'Paris',
            'They then spent 2 days in Paris ...'
            + '<br/><img src="/static/story/paris.jpg"/>'))
        story.sections.append(Section('ireland', 'Ireland',
            '... and a couple days in Ireland where Alex drove on the wrong side of the road and Tat navigated with a real map. They did not get lost... or crash.'
            + '<br/><img src="/static/story/guinness.jpg"/>'))
        story.sections.append(Section('vermont', 'Vermont',
            'They survived the winter of 2014-2015 and decided to spend memorial day hiking and eating ice cream at the Ben & Jerry\'s factory in Waterbury, VT.'
            + '<br/><img src="/static/story/green_mountains.jpg"/>'))
        story.sections.append(Section('christmas', 'Christmas 2015',
            'Alex had to work over Christmas so they spent the 2015 holidays in the city surrounded by beautiful christmas trees and lights. Tat even got her first New Years kiss!'
            + '<br/><img src="/static/story/lincoln_square.jpg"/>'))
        story.sections.append(Section('london_again', 'Londond ... again!',
            'In April of 2016 they went back to London for Tat\'s second marathon...'
            + '<br/><img src="/static/story/london_eye.jpg"/>'))
        story.sections.append(Section('engaged', 'Engaged!',
            '... and then flew to Iceland to see the beautiful contrasting country of fire & ice where Alex asked Tat to marry him (she said yes!)'
            + '<br/><img src="/static/story/hallgrimskirkja.jpg"/>'))

        story.put(dynamodb)

        couple = Couple('0', 'Tatiana McLauchlan', 'Alex Marple')
        couple.put(dynamodb)

        event = SectionGroup('event')
        event.sections.append(Section('ceremony', 'Ceremony', 'The ceremony will be held at ... '))
        event.sections.append(Section('reception', 'Reception', 'The reception will be held at Atlantic Beach Country Club. ...'))
        event.put(dynamodb)

        travel = SectionGroup('travel')
        travel.sections.append(Section('flying', 'Flying In', 'The nearest airport is Jacksonville International Airport.'))
        travel.sections.append(Section('around_town', 'Getting Around Town', 'Getting around Jacksonville is most'
            + ' manageable by car.  However, with ceremony, reception, and accommodations in walkable Neptune Beach,'
            + ' it would be perfectly reasonable to take a shuttle to/from the airport and not set foot in another'
            + ' vehicle for the remainder of the trip.  Tat & Alex will have info on shuttles up shortly!'))
        travel.put(dynamodb)

        accommodations = []
        accommodations.append(Accommodation(
                                  'One Ocean',
                                  'https://www.oneoceanresort.com/',
                                  '~$250 / night',
                                  Decimal('1.5'),
                                  6))
        accommodations.append(Accommodation(
                                  'Courtyard Marriott',
                                  'http://www.marriott.com/hotels/travel/jaxjv-courtyard-jacksonville-beach-oceanfront/',
                                  '$210 + / night',
                                  Decimal('3'),
                                  9))
        accommodations.append(Accommodation(
                                  'Fairfield Inn & Suites',
                                  'http://www.marriott.com/hotels/travel/jaxjb-fairfield-inn-and-suites-jacksonville-beach',
                                  'CURRENTLY NO ROOMS AVAILABLE',
                                  Decimal('3'),
                                  9))
        accommodations.append(Accommodation(
                                  'Best Western',
                                  'http://www.bestwesternjacksonvillebeach.com/',
                                  '$200 + / night',
                                  Decimal('3.9'),
                                  12))
        accommodations.append(Accommodation(
                                  'Four Points by Sheraton',
                                  'http://www.fourpointsjacksonvillebeach.com/',
                                  '~ $300 / night',
                                  Decimal('4'),
                                  12))
        accommodations.append(Accommodation(
                                  'Ponte Vedra Inn & Club',
                                  'http://www.pontevedra.com/inn_and_club/lodginginnclub/',
                                  '~ $300 / night',
                                  Decimal('7.3'),
                                  20))
        for accommodation in accommodations:
            accommodation.put(dynamodb)

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

        save_the_date = SectionGroup('save-the-date')
        save_the_date.sections.append(Section('info', ' ',
            'Please help us by filling in your name, mailing address, and the number of adults in your family '
            + 'likely to attend. We appreciate your help in our planning! Formal Save the Date cards and '
            + 'invitations to follow.'))
        save_the_date.put(dynamodb)

        rsvp_sections = SectionGroup('rsvp')
        rsvp_sections.sections.append(Section('info', ' ', ' '))
        rsvp_sections.put(dynamodb)

        meals = []
        meals.append(Meal('Chicken'))
        meals.append(Meal('Beef'))
        meals.append(Meal('Vegetable'))

        for meal in meals:
            meal.put(dynamodb)

if __name__ == '__main__':
    options = docopt(__doc__)
    setup(prefix=options['--prefix'] + '_',
          fresh_data=options['--fresh-data'],
          fresh_tables=options['--fresh-tables'])