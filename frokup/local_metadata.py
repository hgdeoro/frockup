'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import logging as logging_

logger = logging_.getLogger(__name__)


class LocalMetadata():
    """
    Service that filters files to include in backup based on the local metadata
    (the status of previous upload of the file, if any).
    """

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, directory, filename):
        """Returns True if the file must be included in the backup, False otherwise"""
        logger.debug("Accepting '%s/%s'", directory, filename)
        return True

    def update_metadata(self, directory, filename, glacier_data):
        """Update the local metadata with the data returned by glacier"""
        logger.debug("Updating metadata for file '%s/%s'", directory, filename)
        pass

    def close(self):
        pass


class LocalMetadataMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, directory, filename):
        return True

    def update_metadata(self, directory, filename, glacier_data):
        return
