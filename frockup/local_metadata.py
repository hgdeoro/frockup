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

import logging as logging_
import gdbm
import os
import json

from frockup.glacier import GlacierData
from frockup.common import FLAG_FILE_CHANGED_WHILE_UPLOADING, Context

logger = logging_.getLogger(__name__)


class FileStats():
    """
    Holds all the information about a file, used to decide if
    the file must be included or not in the backup.

    This is needed to update the local metadata DB with the
    file's information used to DECIDE either to backup the file or not
    at the time of the CHECK, and NOT at the time of the upload.
    This way: (a) if the file changes while being uploaded, the next
    time the file will be uploaded again, (b) we can check if the
    file changed while the upload.
    """

    def __init__(self, stats):
        self.stats = stats


class LocalMetadata():
    """
    Service that filters files to include in backup based on the local metadata
    (the status of previous upload of the file, if any).
    """

    def __init__(self, ctx):
        self.ctx = ctx
        self.last_directory = None
        self.database = None
        assert isinstance(self.ctx, Context)

    def _stats_equals(self, stats1, stats2):
        return (stats1.st_size == stats2.st_size
            and stats1.st_mtime == stats2.st_mtime)

    def _file_stats_and_local_metadata_equals(self, file_stats, local_metadata):
        return (file_stats.st_size == local_metadata.get('stats.st_size', None)
            and file_stats.st_mtime == local_metadata.get('stats.st_mtime', None))

    def _opendb(self, directory):
        if self.database is None:
            assert self.last_directory is None
            # continue, to open the DB
        else:
            if self.last_directory != directory:
                # close the old DB
                assert self.database is not None
                self.database.close()
                self.database = None
                self.last_directory = None
                # continue, to open the DB
            else:
                # just return, the current DB is the good one
                return

        db_filename = os.path.join(directory, '.frockup.gdbm')
        logger.debug("Opening metadata DB at '%s'", db_filename)
        self.last_directory = directory
        try:
            self.database = gdbm.open(db_filename, 'c')
        except:
            logger.exception("gdbm.open() failed when trying to open DB {}".format(
                db_filename))
            raise

    def _get_filename_data(self, filename):
        try:
            raw_data = self.database[filename]
            data = json.loads(raw_data)
            return data
        except KeyError:
            return {}

    def _set_filename_data(self, filename, data):
        self.database[filename] = json.dumps(data)

    def include_file(self, directory, filename):
        """Returns an instance of FileStats if the file must be included in the backup,
        False otherwise."""
        logger.debug("Checking '%s/%s'", directory, filename)
        full_filename = os.path.join(directory, filename)
        assert os.path.isfile(full_filename)
        file_stats = os.stat(full_filename)
        self._opendb(directory)
        data = self._get_filename_data(filename)

        if self._file_stats_and_local_metadata_equals(file_stats, data):
            logger.debug("Excluding %s/%s (metadata are equals)", directory, filename)
            return False
        else:
            logger.debug("Including %s/%s (metadata differ or don't exists)", directory, filename)
            return FileStats(file_stats)

    def update_metadata(self, directory, filename, file_stats, glacier_data):
        """Update the local metadata with the data returned by glacier"""
        logger.debug("Updating metadata for file '%s/%s'", directory, filename)
        if self.ctx.dry_run:
            return

        assert isinstance(glacier_data, GlacierData)
        assert isinstance(file_stats, FileStats)
        self._opendb(directory)
        data = self._get_filename_data(filename)
        if 'archive_id' in data:
            # save old value
            if not 'old_archive_ids' in data:
                data['old_archive_ids'] = []
            data['old_archive_ids'].append(data['archive_id'])
        data['archive_id'] = glacier_data.archive_id
        data['stats.st_size'] = file_stats.stats.st_size
        data['stats.st_mtime'] = file_stats.stats.st_mtime

        self._set_filename_data(filename, data)

        current_stats = os.stat(os.path.join(directory, filename))
        if not self._stats_equals(current_stats, file_stats.stats):
            self.ctx.add_log(directory, filename,
                {FLAG_FILE_CHANGED_WHILE_UPLOADING: True})
            logger.warn("File changed while uploading: %s/%s", directory, filename)

    def close(self):
        if self.database:
            logger.debug("Closing database...")
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
