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
        self.error_count = 0
        self.include_extensions = []
        self.exclude_extensions = []

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

    def add_error(self, directory, filename, error_type, error_message):
        self.add_log(directory, filename, error=True, error_type=error_type,
            error_message=error_message)
        self.error_count += 1

    def set_include_extensions(self, extensions):
        assert isinstance(extensions, (list, tuple))
        self.include_extensions = extensions

    def set_exclude_extensions(self, extensions):
        assert isinstance(extensions, (list, tuple))
        self.exclude_extensions = extensions
