'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''


class Context(dict):
    """Context to share state between all the components"""

    def __init__(self):
        self['current_dir_path'] = None
        self['current_dir_database'] = None
