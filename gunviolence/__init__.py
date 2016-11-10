__import__('pkg_resources').declare_namespace(__name__)
from flask import Flask
from flask_flatpages import FlatPages
from flask_frozen import Freezer

app = Flask(__name__)

import gunviolence.views
