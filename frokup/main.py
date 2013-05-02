'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import argparse
import os
import logging as logging_

from frokup.common import Context, EXCLUDED_BY_FILE_FILTER, \
    EXCLUDED_BY_LOCAL_METADATA
from frokup.file_filter import FileFilter
from frokup.glacier import Glacier
from frokup.local_metadata import LocalMetadata, FileStats
import traceback

logger = logging_.getLogger(__name__)


class Main():

    def __init__(self, file_filter=FileFilter, glacier=Glacier, local_metadata=LocalMetadata):
        self.ctx = Context()
        self.file_filter = file_filter(self.ctx)
        self.glacier = glacier(self.ctx)
        self.local_metadata = local_metadata(self.ctx)

    def process_directory(self, directory):
        """Process the directory"""
        logger.debug("process_directory(): '%s'", directory)
        assert os.path.isabs(directory)
        assert os.path.exists(directory)
        assert os.path.isdir(directory)
        for entry in os.listdir(directory):
            if os.path.isfile(os.path.join(directory, entry)):
                self.process_file(directory, entry)
            else:
                logger.debug("Ignoring sub-directory '%s/%s'", directory, entry)

    def process_file(self, directory, filename):
        """Process a single file"""
        logger.debug("process_file(): '%s/%s'", directory, filename)
        # check `directory`
        assert os.path.isabs(directory)
        assert os.path.isdir(directory)
        # check `filename`
        assert not os.path.isabs(filename)
        full_filename = os.path.join(directory, filename)
        assert not os.path.isdir(full_filename)
        assert os.path.exists(full_filename)
        assert os.path.isfile(full_filename)

        if not self.file_filter.include_file(directory, filename):
            self.ctx.add_excluded(directory, filename, EXCLUDED_BY_FILE_FILTER)
            return
        file_stats = self.local_metadata.include_file(directory, filename)
        assert isinstance(file_stats, (FileStats, bool))
        if file_stats is False:
            self.ctx.add_excluded(directory, filename, EXCLUDED_BY_LOCAL_METADATA)
            return
        self.ctx.add_included(directory, filename)
        error = None
        try:
            glacier_data = self.glacier.upload_file(directory, filename)
        except Exception, e:
            logger.info("Exception '%s' detected while uploading file: '%s/%s'", e, directory, filename)
            error = traceback.format_exc() or str(e) or 'error'

        if error:
            self.ctx.add_error(directory, filename, 'upload_error', error)
        else:
            self.local_metadata.update_metadata(directory, filename, file_stats, glacier_data)

    def close(self):
        self.local_metadata.close()


def main():
    parser = argparse.ArgumentParser(description='Backup files to Glacier')
    parser.add_argument('--include', dest='include',
        help="File extensions to include, separated by commas (ej: jpg,JPG)")
    parser.add_argument('--exclude', dest='exclude',
        help="File extensions to exclude, separated by commas (ej: avi,AVI,mov,MOV,xcf,XCF)")
    parser.add_argument('directory', nargs='+', metavar='DIRECTORY',
        help="Directory to backup")

    args = parser.parse_args()
    main = Main()

    if args.include and args.exclude:
        parser.error("Can't use --include and --exclude at the same time.")
        return
    elif args.include:
        main.ctx.set_include_extensions(args.include.split(','))
    elif args.exclude:
        main.ctx.set_exclude_extensions(args.exclude.split(','))

    for a_directory in args.directory:
        main.process_directory(a_directory)
    main.close()

if __name__ == '__main__':
    logging_.basicConfig(level=logging_.DEBUG)
    main()
