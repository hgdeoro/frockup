# -*- coding: utf-8 -*-
#===============================================================================
#    frockup - FROzen baCKUP or backup to Amazon Glacier
#    Copyright (C) 2013 Horacio Guillermo de Oro <hgdeoro@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#===============================================================================

import uuid
import multiprocessing
import logging as logging_
import random
import os
import time
from ftplib import FTP

logger = logging_.getLogger(__name__)


class GlacierData():

    def __init__(self):
        self.archive_id = None


class Glacier():
    """Service to interact with Amazon Glacier"""

    def __init__(self, ctx):
        self.ctx = ctx
        self.layer2 = None

    def upload_file(self, directory, filename):
        """Uploads a file to glacier. Returns an instance of GlacierData"""
        logger.debug("Uploading file '%s/%s'", directory, filename)
        from boto.glacier.layer2 import Layer2
        self.layer2 = Layer2(
            self.ctx.config.get("identity", "aws_access_key_id"),
            self.ctx.config.get("identity", "aws_secret_access_key")
        )

        vault = self.layer2.get_vault(self.ctx.config.get("defaults", "vault_name"))
        archive_id = vault.create_archive_from_file(os.path.join(directory, filename),
            description=os.path.join(directory, filename))

        glacier_data = GlacierData()
        glacier_data.archive_id = archive_id
        return glacier_data

    def close(self):
        if self.layer2:
            try:
                self.layer2.close()
            except:
                logger.exception("Exception detected when trying to close(), "
                                 "will log and ignore it...")
            finally:
                self.layer2 = None


#===============================================================================
# Mocks and other implementations to easy tests
#===============================================================================

class GlacierMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def upload_file(self, directory, filename):
        logger.debug("Uploading file '%s/%s'", directory, filename)
        glacier_data = GlacierData()
        glacier_data.archive_id = str(uuid.uuid4())
        return glacier_data

    def close(self):
        pass


class GlacierErrorOnUploadMock(GlacierMock):

    def upload_file(self, directory, filename):
        raise(Exception("This implementation of upload_file() ALWAYS raises an exception"))


class GlacierFtpBased():

    def __init__(self, ctx):
        self.ctx = ctx
        self.ftp_user = 'random_{0}'.format(random.randint(1000000, 9999999))
        self.ftp_password = str(uuid.uuid4())
        self.ftp_port = 18263
        self.upload_file_ftp_callback = None

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

    def wait_for_ftpserver(self):
        ftp = FTP()
        for try_num in range(1, 11):
            try:
                ftp.connect('127.0.0.1', self.ftp_port)
                logger.info("Connect OK after %s tries", try_num)
                return
            except:
                time.sleep(0.1)
        ftp.connect('127.0.0.1', self.ftp_port)

    def upload_file(self, directory, filename):
        logger.info("Connecting to FTP...")
        ftp = FTP()
        ftp.connect('127.0.0.1', self.ftp_port)
        logger.info("Logging in to FTP...")
        ftp.login(self.ftp_user, self.ftp_password)
        generated_uuid = str(uuid.uuid4())
        remote_filename = "{0}-{1}".format(filename, generated_uuid)
        with open(os.path.join(directory, filename)) as fp:
            logger.info("Sending file to FTP server...")
            ftp.storbinary("STOR {0}".format(remote_filename), fp, 128,
                self.upload_file_ftp_callback)
        logger.info("File sent OK to FTP")

        glacier_data = GlacierData()
        glacier_data.archive_id = generated_uuid
        return glacier_data

    def close(self):
        pass
