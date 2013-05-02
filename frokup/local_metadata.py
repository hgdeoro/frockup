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

    def include_file(self, filename):
        """Returns True if the file must be included in the backup, False otherwise"""
        logger.debug("Accepting '%s'", filename)
        return True

    def update_metadata(self, filename, glacier_data):
        """Update the local metadata with the data returned by glacier"""
        logger.debug("Updating metadata for file '%s'", filename)
        pass


class LocalMetadataMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, filename):
        return True

    def update_metadata(self, glacier_data):
        return
