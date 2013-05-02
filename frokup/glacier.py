'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import uuid
import logging as logging_

logger = logging_.getLogger(__name__)


class Glacier():
    """Service to interact with Amazon Glacier"""

    def __init__(self, ctx):
        self.ctx = ctx

    def upload_file(self, filename):
        """Uploads a file to glacier. Returns the archiveID"""
        logger.debug("Uploading file '%s'", filename)
        return ""


class GlacierMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def upload_file(self, filename):
        return uuid.uuid4()
