import testNoSuchModule

def discover(*args, **kwargs):
    raise AssertionError("This module is expected not to be loaded")
