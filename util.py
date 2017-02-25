#!/usr/bin/env python
"""
Usage:
  util.py [options] ( dump_rsvp | dump_save_the_date )

Options:
  --prefix <prefix>       Prefix for dynamodb table names
  --log-level <level>     Log level (default: INFO)
  --log-file <file>       Log file
"""

import __main__
import boto3
import logging
from apothecary import model
from docopt import docopt
from boto3.dynamodb.conditions import Attr


def dump_rsvp(options):
    dynamodb = boto3.resource('dynamodb')
    if (options['--prefix']):
        model.RSVP.add_tablename_prefix(options['--prefix'])
    if options['dump_rsvp']:
        rsvps = model.RSVP.scan(dynamodb, FilterExpression=Attr('meal_preference').exists())
    else:
        rsvps = model.RSVP.scan(dynamodb)
    header = True
    for rsvp in rsvps:
        if header:
            print(rsvp.dump_csv_header())
            header = False
        print(rsvp.dump_csv())


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
