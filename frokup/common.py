'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

EXCLUDED_BY_FILE_FILTER = 'file-filter'
EXCLUDED_BY_LOCAL_METADATA = 'local-metadata'
FLAG_FILE_CHANGED_WHILE_UPLOADING = 'file-changed'


class Context(dict):
    """Context to share state between all the components"""

    def __init__(self):
        self.log = {}
        self.excluded_count = 0
        self.included_count = 0

    def add_log(self, directory, filename, **kwargs):
        self.log[directory] = self.log.get(directory, dict())
        self.log[directory][filename] = self.log[directory].get(filename, dict())
        self.log[directory][filename].update(**kwargs)

    def add_excluded(self, directory, filename, reason):
        self.add_log(directory, filename, excluded=True,
            excluded_reason=reason)
        self.excluded_count += 1

    def add_included(self, directory, filename):
        self.add_log(directory, filename, included=True)
        self.included_count += 1
