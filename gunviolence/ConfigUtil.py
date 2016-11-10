import os
import configs
try: import simplejson as json
except ImportError: import json


def load_json(filename):
    settings_file_path = os.path.join(os.path.dirname(configs.__path__[0]), filename)
    with open(settings_file_path, 'rb') as json_settings:
        s = json.load(json_settings)
        return s

def load_config():
    s = load_json('configs/settings.json')
    return s

config = load_config()
