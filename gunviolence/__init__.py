__import__('pkg_resources').declare_namespace(__name__)
from flask import Flask

app = Flask(__name__)

import gunviolence.views
