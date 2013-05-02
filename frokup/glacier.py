'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import uuid
import logging as logging_

logger = logging_.getLogger(__name__)


class GlacierData():

    def __init__(self):
        self.archive_id = None


class Glacier():
    """Service to interact with Amazon Glacier"""

    def __init__(self, ctx):
        self.ctx = ctx

    def upload_file(self, directory, filename):
        """Uploads a file to glacier. Returns an instance of GlacierData"""
        logger.debug("Uploading file '%s/%s'", directory, filename)
        glacier_data = GlacierData()
        glacier_data.archive_id = str(uuid.uuid4())
        return glacier_data


class GlacierMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def upload_file(self, directory, filename):
        return GlacierData()
