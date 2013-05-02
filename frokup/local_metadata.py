'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import logging as logging_
import shelve
import os

logger = logging_.getLogger(__name__)


class LocalMetadata():
    """
    Service that filters files to include in backup based on the local metadata
    (the status of previous upload of the file, if any).
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.last_directory = None
        self.database = None

    def _opendb(self, directory):
        if self.database is None:
            assert self.last_directory is None
            # continue, to open the DB
        else:
            if self.last_directory != directory:
                # close the old DB
                assert self.database
                self.database.close()
                self.database = None
                self.last_directory = None
                # continue, to open the DB
            else:
                # just return, the current DB is the good one
                return

        db_filename = os.path.join(directory, '.frokup.db')
        logger.debug("Opening metadata DB at '%s'", db_filename)
        self.last_directory = directory
        self.database = shelve.open(db_filename)

    def include_file(self, directory, filename):
        """Returns True if the file must be included in the backup, False otherwise"""
        logger.debug("Accepting '%s/%s'", directory, filename)
        self._opendb(directory)
        return True

    def update_metadata(self, directory, filename, glacier_data):
        """Update the local metadata with the data returned by glacier"""
        logger.debug("Updating metadata for file '%s/%s'", directory, filename)
        self._opendb(directory)
        return

    def close(self):
        if self.database:
            self.database.close()
            self.database = None
            self.last_directory = None


class LocalMetadataMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, directory, filename):
        return True

    def update_metadata(self, directory, filename, glacier_data):
        return
