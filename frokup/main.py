'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import os
import logging as logging_

from frokup.common import Context
from frokup.file_filter import FileFilter
from frokup.glacier import Glacier
from frokup.local_metadata import LocalMetadata

logger = logging_.getLogger(__name__)


class Main():

    def __init__(self):
        self.ctx = Context()
        self.file_filter = FileFilter(self.ctx)
        self.glacier = Glacier(self.ctx)
        self.local_metadata = LocalMetadata(self.ctx)

    def process_directory(self, directory):
        logger.debug("process_directory(): '%s'", directory)
        assert os.path.isabs(directory)
        assert os.path.exists(directory)
        assert os.path.isdir(directory)
        for entry in os.listdir(directory):
            filename = os.path.join(directory, entry)
            if os.path.isfile(filename):
                self.process_file(filename)
            else:
                logger.debug("Ignoring '%s'", filename)

    def process_file(self, filename):
        logger.debug("process_file(): '%s'", filename)
        assert os.path.isabs(filename)
        assert os.path.exists(filename)
        assert not os.path.isdir(filename)
        if not self.file_filter.include_file(filename):
            return
        if not self.local_metadata.include_file(filename):
            return
        glacier_data = self.glacier.upload_file(filename)
        self.local_metadata.update_metadata(filename, glacier_data)

    def main(self):
        self.process_directory(os.path.split(__file__)[0])


def main():
    Main().main()

if __name__ == '__main__':
    logging_.basicConfig(level=logging_.DEBUG)
    main()
