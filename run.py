#!/usr/bin/env python
"""
Usage:
  run.py [options]

Utility for running apothecary in a development environment

Options:
  -f --fresh            Recreate fresh tables.  Will blow away any existing data.

"""

import getpass
import logging
from apothecary import app, model
from docopt import docopt

if __name__ == '__main__':
    options = docopt(__doc__)
    logging.root.setLevel('INFO')
    model.setup(prefix=getpass.getuser() + '_', fresh=options['--fresh'])
    authDB = FlaskRealmDigestDB('ApothecaryAuth')
    authDB.add_user('admin', 'test')
    app.run(debug=True)
