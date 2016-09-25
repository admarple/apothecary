#!/usr/bin/env python
'''
Usage:
  util.py dump_rsvp
'''
import boto3
from apothecary import model
from docopt import docopt

def dump_rsvp(options):
    dynamodb = boto3.resource('dynamodb')
    rsvps = model.RSVP.scan(dynamodb)
    header = True
    for rsvp in rsvps:
        if header:
            print(rsvp.dump_csv_header())
            header = False
        print(rsvp.dump_csv())

if __name__ == '__main__':
    options = docopt(__doc__)
    if options['dump_rsvp']:
        dump_rsvp(options)
