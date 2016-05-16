#!/usr/bin/env python
import getpass
import logging
from apothecary import app, model

logging.root.setLevel('INFO')
model.setup(prefix=getpass.getuser() + '_', fresh=False)
app.run(debug=True)
