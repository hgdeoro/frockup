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

import argparse
import os
import logging as logging_
import traceback
import time

from frockup.common import Context, EXCLUDED_BY_FILE_FILTER, \
    EXCLUDED_BY_LOCAL_METADATA
from frockup.file_filter import FileFilter
from frockup.glacier import Glacier, GlacierFtpBased
from frockup.local_metadata import LocalMetadata, FileStats

logger = logging_.getLogger(__name__)


class Main():

    def __init__(self, ctx=None, file_filter=FileFilter, glacier=Glacier,
        local_metadata=LocalMetadata, config=None):
        if ctx is None:
            self.ctx = Context(config=config)
        else:
            self.ctx = ctx
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
        # check `directory` (same of `process_directory()`)
        assert os.path.isabs(directory)
        assert os.path.exists(directory)
        assert os.path.isdir(directory)
        # check `filename`
        assert not os.path.isabs(filename)
        full_filename = os.path.join(directory, filename)
        assert not os.path.isdir(full_filename)
        assert os.path.exists(full_filename)
        assert os.path.isfile(full_filename)

        if not self.file_filter.include_file(directory, filename):
            self.ctx.add_excluded(directory, filename, EXCLUDED_BY_FILE_FILTER)
            logger.info("Ignoring file %s (excluded by filter)", filename)
            return
        file_stats = self.local_metadata.include_file(directory, filename)
        assert isinstance(file_stats, (FileStats, bool))
        if file_stats is False:
            self.ctx.add_excluded(directory, filename, EXCLUDED_BY_LOCAL_METADATA)
            logger.info("Ignoring file %s (excluded by metadata)", filename)
            return
        self.ctx.add_included(directory, filename)
        error = None
        try:
            logger.info("Starting upload of file '%s'...", filename)
            start_time = time.time()
            glacier_data = self.glacier.upload_file(directory, filename)
            end_time = time.time()
            logger.info(" + upload complete! Took %s secs, %s kbps", end_time - start_time,
                (file_stats.stats.st_size / (end_time - start_time)) / 1024.0)
        except Exception, e:
            logger.info("Exception '%s' detected while uploading file: '%s/%s'", e, directory,
                filename)
            error = traceback.format_exc() or str(e) or 'error'

        if error:
            self.ctx.add_error(directory, filename, 'upload_error', error)
        else:
            self.local_metadata.update_metadata(directory, filename, file_stats, glacier_data)

    def close(self):
        self.local_metadata.close()
        self.glacier.close()


def main():
    parser = argparse.ArgumentParser(description='Backup files to Glacier')
    parser.add_argument('--info', dest='log_level', action='store_const', const='info',
        help="Set log level to info")
    parser.add_argument('--debug', dest='log_level', action='store_const', const='debug',
        help="Set log level to debug")
    parser.add_argument('--include', dest='include',
        help="File extensions to include, separated by commas (ej: jpg,JPG)")
    parser.add_argument('--exclude', dest='exclude',
        help="File extensions to exclude, separated by commas (ej: avi,AVI,mov,MOV,xcf,XCF)")
    parser.add_argument('--one-file', dest='one_file',
        help="To upload only one file, if needed")
    parser.add_argument('directory', nargs='+', metavar='DIRECTORY',
        help="Directory to backup")

    args = parser.parse_args()
    if args.log_level == 'debug':
        logging_.basicConfig(level=logging_.DEBUG)
    elif args.log_level == 'info':
        logging_.basicConfig(level=logging_.INFO)
    else:
        logging_.basicConfig(level=logging_.WARN)

    ctx = Context()

    if args.include and args.exclude:
        parser.error("Can't use --include and --exclude at the same time.")
        return
    elif args.include:
        ctx.set_include_extensions(args.include.split(','))
    elif args.exclude:
        ctx.set_exclude_extensions(args.exclude.split(','))

    if 'FROKUP_FTP_MODE' in os.environ:
        main = Main(ctx=ctx, glacier=GlacierFtpBased)
        try:
            main.glacier.launch()
            main.glacier.wait_for_ftpserver()
            for a_directory in args.directory:
                main.process_directory(a_directory)
            main.close()
        finally:
            main.glacier.kill_ftp()
    else:
        main = Main(ctx=ctx)
        if args.one_file:
            main.process_file(args.directory[0], args.one_file)
        else:
            for a_directory in args.directory:
                main.process_directory(a_directory)
        main.close()

    included, excluded = ctx.get_log_processed()
    print "{0} included file(s):".format(len(included))
    for dirname, filename in included:
        print " + {0}/{1}".format(dirname, filename)

    print "{0} excluded file(s):".format(len(excluded))
    for dirname, filename in excluded:
        print " - {0}/{1}".format(dirname, filename)

if __name__ == '__main__':
    main()
