#!/usr/bin/env python
"""
Usage:
  util.py [options] ( dump_rsvp | dump_save_the_date | cleanup_rsvp | raw_dump_rsvp )

Options:
  --prefix <prefix>       Prefix for dynamodb table names
  --log-level <level>     Log level [default: INFO]
  --log-file <file>       Log file
"""

import __main__
import sys
import boto3
import logging
import simplejson as json
from apothecary import model
from docopt import docopt
from boto3.dynamodb.conditions import Attr


def dump_rsvp(options):
    dynamodb = boto3.resource('dynamodb')
    if options['--prefix']:
        model.RSVP.add_tablename_prefix(options['--prefix'])
        options['--prefix'] = None
    if options['dump_rsvp']:
        logging.info('ONLY DUMPING RSVPS')
        rsvps = model.RSVP.scan(dynamodb,
                                FilterExpression=Attr('meal_preference').exists() | Attr('declined').eq(True))
    else:
        rsvps = model.RSVP.scan(dynamodb)
    header_rsvp = model.RSVP('name',
                             'email',
                             'address',
                             'guests',
                             'hotel_preference',
                             'notes',
                             declined=False,
                             meal_preference={"meal": "pref"},
                             rsvp_notes='rsvp_notes')
    print(header_rsvp.dump_csv_header())
    for rsvp in rsvps:
        print(rsvp.dump_csv(ref_obj=header_rsvp))


def raw_dump_rsvp(options):
    dynamodb = boto3.resource('dynamodb')
    if options['--prefix']:
        model.RSVP.add_tablename_prefix(options['--prefix'])
        options['--prefix'] = None
    rsvp_table = model.RSVP.table(dynamodb)
    from_dynamo = rsvp_table.scan()
    args = {}
    while True:
        last_key = from_dynamo.get('LastEvaluatedKey')
        for item in from_dynamo.get('Items'):
            logging.debug('loaded: {0}'.format(item))
            print(json.dumps(item, use_decimal=True))
        if not last_key:
            break
        else:
            args['ExclusiveStartKey'] = last_key
            from_dynamo = rsvp_table.scan(args)


def cleanup_rsvp(options):
    dynamodb = boto3.resource('dynamodb')
    if options['--prefix']:
        model.RSVP.add_tablename_prefix(options['--prefix'])
        options['--prefix'] = None
    rsvps = model.RSVP.scan(dynamodb, FilterExpression=Attr('meal_preference').exists())
    # rsvps = [model.RSVP.get(dynamodb, 'lover')]
    for rsvp in rsvps:
        try:
            if isinstance(rsvp, model.RSVP):
                logging.info('Skipping RSVP that already looks healthy: "{0}"'.format(rsvp))
                continue
        except TypeError:
            logging.info('TypeError on RSVP "{0}".  Maybe it\'s already been cleaned up?'.format(rsvp))
            continue

        new_rsvp = model.RSVP(rsvp['rsvp_id'], 'email', 'address', 0, 'hotel', 'notes')
        safe_to_update = True
        try:
            new_rsvp.meal_preference = rsvp['meal_preference']
        except:
            logging.warning('Error on RSVP "{0}" "meal_preference": {1}'.format(new_rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        try:
            new_rsvp.declined = rsvp['declined']['N']
        except:
            logging.warning('Error on RSVP "{0}" "declined": {1}'.format(new_rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        try:
            new_rsvp.guests = rsvp['guests']['N']
        except:
            logging.warning('Error on RSVP "{0}" "guests": {1}'.format(new_rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        try:
            new_rsvp.rsvp_notes = rsvp['rsvp_notes']['S']
        except:
            logging.warning('Error on RSVP "{0}" "rsvp_notes": {1}'.format(new_rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        if safe_to_update:
            logging.info('Updating RSVP {0}'.format(rsvp))
            new_rsvp.update_for_rsvp(dynamodb)


def cleanup_old_rsvp(options):
    dynamodb = boto3.resource('dynamodb')
    if options['--prefix']:
        model.RSVP.add_tablename_prefix(options['--prefix'])
        options['--prefix'] = None
    rsvps = model.RSVP.scan(dynamodb, FilterExpression=Attr('meal_preference').exists())
    for rsvp in rsvps:
        try:
            if not isinstance(rsvp, model.RSVP):
                logging.info('Skipping RSVP that isn\'t old: "{0}"'.format(rsvp))
                continue
        except TypeError:
            logging.info('TypeError on RSVP "{0}".  Maybe it\'s already been cleaned up?'.format(rsvp))
            continue
        except KeyError:
            logging.info('KeyError on RSVP "{0}".  Maybe it\'s already been cleaned up?'.format(rsvp))
            continue

        safe_to_update = True
        try:
            rsvp.meal_preference = rsvp.meal_preference
        except:
            logging.warning('Error on RSVP "{0}" "meal_preference": {1}'.format(rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        try:
            rsvp.declined = rsvp.declined['N']
        except:
            logging.warning('Error on RSVP "{0}" "declined": {1}'.format(rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        try:
            rsvp.guests = rsvp.guests['N']
        except:
            logging.warning('Error on RSVP "{0}" "guests": {1}'.format(rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        try:
            rsvp.rsvp_notes = rsvp.rsvp_notes['S']
        except:
            logging.warning('Error on RSVP "{0}" "rsvp_notes": {1}'.format(rsvp.rsvp_id, sys.exc_info()[0]))
            safe_to_update = False
        if safe_to_update:
            logging.info('Updating RSVP {0}'.format(rsvp))
            rsvp.update_for_rsvp(dynamodb)


def get_log_file(options):
    log_file = options['--log-file']
    if not log_file:
        program_name = '.'.join(__main__.__file__.split('/')[-1].split('.')[:1])
        log_file = '{0}.log'.format(program_name)
    return log_file


if __name__ == '__main__':
    options = docopt(__doc__)
    logging.basicConfig(filename=get_log_file(options), level=logging.getLevelName(options['--log-level'].upper()))
    if options['dump_rsvp'] or options['dump_save_the_date']:
        dump_rsvp(options)
    if options['cleanup_rsvp']:
        cleanup_rsvp(options)
        cleanup_old_rsvp(options)
    if options['raw_dump_rsvp']:
        raw_dump_rsvp(options)
