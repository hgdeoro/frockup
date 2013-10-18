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

import logging
import os
import unittest
import uuid
import pprint
import shutil
import time
import gdbm
import json

from frockup.main import Main
from frockup.glacier import GlacierFtpBased, GlacierMock, \
    GlacierErrorOnUploadMock
from frockup.common import get_config, Context
from frockup.file_filter import FileFilter

DB_FILENAME = '.frockup.gdbm'


def _generate_local_metadata_db(directory, files, overwrite=False):
    assert os.path.exists(directory)
    # Create local metadata DB
    db_filename = os.path.join(directory, DB_FILENAME)
    if overwrite and os.path.exists(db_filename):
        os.unlink(db_filename)
    assert not os.path.exists(db_filename)
    database = gdbm.open(db_filename, 'c')
    created_metadata = {}
    for filename in files:
        assert os.path.isfile(os.path.join(directory, filename))
        file_stats = os.stat(os.path.join(directory, filename))
        data = {}
        data['archive_id'] = str(uuid.uuid4())
        data['stats.st_size'] = file_stats.st_size
        data['stats.st_mtime'] = file_stats.st_mtime
        database[filename] = json.dumps(data)
        database.sync()
        created_metadata[filename] = {}
        created_metadata[filename].update(data)
    database.close()
    return created_metadata


class BaseTest(unittest.TestCase):

    def _get_test_subdir(self, dirname):
        module_dir = os.path.abspath(os.path.split(__file__)[0])
        root_dir = os.path.abspath(os.path.split(module_dir)[0])
        test_dir = os.path.join(root_dir, 'tests')
        subdir = os.path.join(test_dir, dirname)
        self.assertTrue(os.path.exists(subdir))
        self.assertTrue(os.path.isdir(subdir))
        return subdir

    def _remove_db_if_exists(self, dirname):
        try:
            os.unlink(os.path.join(dirname, '.frockup.db'))
        except OSError:
            pass

        try:
            os.unlink(os.path.join(dirname, DB_FILENAME))
        except OSError:
            pass

    def _get_db_copy(self, dirname):
        """Returns a dict with a copy of the DB contents"""
        db = gdbm.open(os.path.join(dirname, DB_FILENAME), 'c')
        copy = {}
        k = db.firstkey()
        while k != None:
            copy[k] = json.loads(db[k])
            k = db.nextkey(k)
        db.close()
        return copy

    def test_01_metadata_crated_when_doesnt_exists(self):
        """Tests that metadata is created when don't exists"""
        dir1 = self._get_test_subdir('dir1')
        # Remove DB if exists (of previous run of the tests)
        self._remove_db_if_exists(dir1)
        # Call process_directory()
        main = Main(glacier=GlacierMock)
        main.process_directory(dir1)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 3)
        self.assertEqual(main.ctx.excluded_count, 0)
        # Check that local metadata was created
        db_filename = os.path.join(dir1, DB_FILENAME)
        database = gdbm.open(db_filename, 'c')
        logging.debug("Database at %s: %s", db_filename, pprint.pformat(database))
        for filename in ('file1.txt', 'file2.txt', 'file3.txt'):
            data = json.loads(database[filename])
            data['archive_id']
            data['stats.st_size']
            data['stats.st_mtime']

    def test_02_comparison_works_with_existing_metadata(self):
        """Tests that metadata is compared sucesfully when no change exists in files,
        and no file should be uploaded"""
        dir2 = self._get_test_subdir('dir2')
        # Create local metadata DB
        created_metadata = _generate_local_metadata_db(dir2,
            ('file1.txt', 'file2.txt', 'file3.txt'), overwrite=True)
        # Call process_directory()
        main = Main(glacier=GlacierMock)
        main.process_directory(dir2)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 0)
        self.assertIn(main.ctx.excluded_count, [3, 4])
        # Check that local metadata wasn't changed
        db_filename = os.path.join(dir2, DB_FILENAME)
        database = gdbm.open(db_filename, 'c')
        logging.debug("Database at %s: %s", db_filename, pprint.pformat(database))
        for filename in ('file1.txt', 'file2.txt', 'file3.txt'):
            data = json.loads(database[filename])
            self.assertDictEqual(data,
                created_metadata[filename])

    def test_03_metadata_is_updated_and_files_changes_are_detected(self):
        """Tests metadata updates"""
        dir3 = self._get_test_subdir('dir3')
        # Remove files
        self._remove_db_if_exists(dir3)
        for filename in ('file2.txt', 'file3.txt'):
            try:
                os.unlink(os.path.join(dir3, filename))
            except OSError:
                pass

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 1)  # file1.txt
        self.assertEqual(main.ctx.excluded_count, 0)

        # --- Call process_directory() ---
        for _ in range(0, 2):
            main = Main(glacier=GlacierMock)
            main.process_directory(dir3)
            main.close()
            # Check statistics
            logging.debug("Log: %s", pprint.pformat(main.ctx.log))
            self.assertEqual(main.ctx.included_count, 0)
            self.assertEqual(main.ctx.excluded_count, 2)  # .frockup.gdbm + file1.txt

        # --- Add `file2.txt`
        file2_path = os.path.join(dir3, 'file2.txt')
        shutil.copy2(os.path.join(dir3, '../dir2/file2.txt'), file2_path)

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 1)  # file2.txt
        self.assertEqual(main.ctx.excluded_count, 2)  # .frockup.gdbm + file1.txt

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 0)
        self.assertEqual(main.ctx.excluded_count, 3)  # .frockup.gdbm + file1.txt + file2.txt

        # --- Touch `file2.txt`
        os.utime(file2_path, (1, 1))

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 1)  # file2.txt
        self.assertEqual(main.ctx.excluded_count, 2)  # .frockup.gdbm + file1.txt

        # Check `old_archive_ids`
        db = self._get_db_copy(dir3)
        self.assertTrue('old_archive_ids' in db['file2.txt'])
        self.assertEqual(len(db['file2.txt']['old_archive_ids']), 1)

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 0)
        self.assertEqual(main.ctx.excluded_count, 3)  # .frockup.gdbm + file1.txt + file2.txt

        # Check `old_archive_ids`
        db = self._get_db_copy(dir3)
        self.assertTrue('old_archive_ids' in db['file2.txt'])
        self.assertEqual(len(db['file2.txt']['old_archive_ids']), 1)

        # --- Add data to `file2.txt`
        with open(file2_path, 'a') as f2_file_object:
            f2_file_object.write('\nA new Line\n')

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 1)  # file2.txt
        self.assertEqual(main.ctx.excluded_count, 2)  # .frockup.gdbm + file1.txt

        # Check `old_archive_ids`
        db = self._get_db_copy(dir3)
        self.assertTrue('old_archive_ids' in db['file2.txt'])
        self.assertEqual(len(db['file2.txt']['old_archive_ids']), 2)

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 0)
        self.assertEqual(main.ctx.excluded_count, 3)  # .frockup.gdbm + file1.txt + file2.txt

        # Check `old_archive_ids`
        db = self._get_db_copy(dir3)
        self.assertTrue('old_archive_ids' in db['file2.txt'])
        self.assertEqual(len(db['file2.txt']['old_archive_ids']), 2)

        logging.debug("Database at %s: %s", dir3,
            pprint.pformat(self._get_db_copy(dir3)))

    def test_glacier_ftp(self):

        def _wait_callback(buf):
            time.sleep(0.1)

        dir1 = self._get_test_subdir('dir1')
        self._remove_db_if_exists(dir1)
        main = Main(glacier=GlacierFtpBased)
        try:
            main.glacier.launch()
            main.glacier.wait_for_ftpserver()
            main.glacier.upload_file_ftp_callback = _wait_callback
            main.process_directory(dir1)
            main.close()
        finally:
            main.glacier.kill_ftp()

    def test_glacier_error_on_upload(self):

        dir1 = self._get_test_subdir('dir1')
        self._remove_db_if_exists(dir1)
        main = Main(glacier=GlacierErrorOnUploadMock)
        main.process_directory(dir1)
        main.close()
        logging.debug("Database at %s: %s", dir1,
            pprint.pformat(self._get_db_copy(dir1)))
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))

    def test_change_in_file_while_upload_is_detected(self):
        # FIXME: implement this test!
        pass


class ConfigLoadTest(unittest.TestCase):

    def _test_read_default_config_file(self):
        config = get_config()
        config.get("identity", "aws_access_key_id")
        config.get("identity", "aws_secret_access_key")
        config.get("defaults", "region")
        config.get("defaults", "vault_name")
        config.get("defaults", "vault_arn")


class GlacierTest(unittest.TestCase):

    def _test_list_vaults(self):
        config = get_config()
        from boto.glacier.layer1 import Layer1
        l1 = Layer1(config.get("identity", "aws_access_key_id"),
            config.get("identity", "aws_secret_access_key"))
        vaults = l1.list_vaults()
        # Things we should have...
        vaults['Marker']
        vaults['RequestId']
        vaults['VaultList']
        for a_vault in vaults['VaultList']:
            a_vault['CreationDate']
            a_vault['LastInventoryDate']
            a_vault['NumberOfArchives']
            a_vault['SizeInBytes']
            a_vault['VaultARN']
            a_vault['VaultName']
        l1.close()


class FileFilterTest(unittest.TestCase):

    def test_include(self):
        ctx = Context()
        ctx.set_include_extensions(('jpg', 'png'))  # Only include JPGs
        file_filter = FileFilter(ctx)
        INCLUDED = ('x.jpg', 'X.JPG', 'z.PNG')
        EXCLUDED = ('x.zip', 'X.ZIP', 'xjpg', 'XJPG', '.algojpg',
                    '.frockup', '.frockup-yadayadayada')
        for filename in INCLUDED:
            self.assertTrue(file_filter.include_file('/', filename),
                            "File {} should be included".format(filename))
        for filename in EXCLUDED:
            self.assertFalse(file_filter.include_file('/', filename),
                            "File {} should be excluded".format(filename))

    def test_exclude(self):
        ctx = Context()
        ctx.set_exclude_extensions(('jpg', 'png'))  # Include all, exclude JPGs
        file_filter = FileFilter(ctx)
        EXCLUDED = ('x.jpg', 'X.JPG', 'z.PNG', '.algojpg', '.frockup', '.frockup-yadayadayada')
        INCLUDED = ('x.zip', 'X.ZIP', 'xjpg', 'XJPG')
        for filename in INCLUDED:
            self.assertTrue(file_filter.include_file('/', filename),
                            "File {} should be included".format(filename))
        for filename in EXCLUDED:
            self.assertFalse(file_filter.include_file('/', filename),
                            "File {} should be excluded".format(filename))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
