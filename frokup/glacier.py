'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import uuid
import multiprocessing
import logging as logging_
import random
import os

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


class GlacierFtpBased():

    def __init__(self, ctx):
        self.ctx = ctx
        self.ftp_user = 'random_{0}'.format(random.randint(1000000, 9999999))
        self.ftp_password = str(uuid.uuid4())
        self.ftp_port = 18263

    def _launch(self):
        logger.info("Launching FTP server in child process")
        from pyftpdlib.authorizers import DummyAuthorizer
        from pyftpdlib.handlers import FTPHandler
        from pyftpdlib.servers import FTPServer
        authorizer = DummyAuthorizer()
        authorizer.add_user(self.ftp_user, self.ftp_password, "/tmp", perm="w")
        handler = FTPHandler
        handler.authorizer = authorizer
        server = FTPServer(("127.0.0.1", self.ftp_port), handler)
        server.serve_forever()

    def kill_ftp(self):
        logger.info("Terminanting child...")
        self.child.terminate()
        logger.info("Joining child...")
        self.child.join()
        logger.info("Done!")

    def launch(self):
        self.child = multiprocessing.Process(target=self._launch)
        self.child.start()

    def upload_file(self, directory, filename):
        logger.info("Connecting to FTP...")
        from ftplib import FTP
        ftp = FTP()
        ftp.connect('127.0.0.1', self.ftp_port)
        logger.info("Logging in to FTP...")
        ftp.login(self.ftp_user, self.ftp_password)
        generated_uuid = str(uuid.uuid4())
        remote_filename = "{0}-{1}".format(filename, generated_uuid)
        with open(os.path.join(directory, filename)) as fp:
            logger.info("Sending file to FTP server...")
            ftp.storbinary("STOR {0}".format(remote_filename), fp)
        logger.info("File sent OK to FTP")

        glacier_data = GlacierData()
        glacier_data.archive_id = generated_uuid
        return glacier_data
