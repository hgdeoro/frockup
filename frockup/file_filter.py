'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import logging as logging_

logger = logging_.getLogger(__name__)


class FileFilter():
    """
    Service that filters files to include in backup based on the file's properties,
    like directory, extension, last modification time, etc. (but does NOT
    check file metadata nor knows if the file was already uploaded).
    """

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, directory, filename):
        """Returns True if the file must be included in the backup, False otherwise"""
        if filename == '.frockup.db':
            logger.debug("Excluding '%s/%s'", directory, filename)
            return False
        logger.debug("Including '%s/%s'", directory, filename)
        return True


class FileFilterMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, directory, filename):
        return True
