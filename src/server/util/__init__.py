import flask
import numpy as np

class StrictJsonEncoder(flask.json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['allow_nan'] = False
        super().__init__(*args, **kwargs)

    def default(self, o):
        if isinstance(o, np.generic):
            return o.item()
        else:
            return super().default(o)
