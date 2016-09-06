#!/usr/bin/env python
"""
Usage:
  run.py [options]

Utility for running apothecary in a development environment

Options:
  --fresh-tables            Recreate fresh tables.  Will blow away any existing data.
  --fresh-data              Add all of the data from setup.

"""

import getpass
import logging
from apothecary import app, model
from docopt import docopt

if __name__ == '__main__':
    options = docopt(__doc__)
    logging.root.setLevel('INFO')
    model.setup(prefix=getpass.getuser() + '_',
        fresh_data=options['--fresh-data'],
        fresh_tables=options['--fresh-tables'])
    app.run(debug=True, use_reloader=False)
