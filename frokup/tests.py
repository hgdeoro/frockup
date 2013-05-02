'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import logging
import os
import unittest
import shelve
import uuid
import pprint
import shutil
import time

from frokup.main import Main
from frokup.glacier import GlacierFtpBased, GlacierMock, \
    GlacierErrorOnUploadMock


def _generate_local_metadata_db(directory, files, overwrite=False):
    assert os.path.exists(directory)
    # Create local metadata DB
    db_filename = os.path.join(directory, '.frokup.db')
    if overwrite and os.path.exists(db_filename):
        os.unlink(db_filename)
    assert not os.path.exists(db_filename)
    database = shelve.open(db_filename)
    created_metadata = {}
    for filename in files:
        assert os.path.isfile(os.path.join(directory, filename))
        file_stats = os.stat(os.path.join(directory, filename))
        data = {}
        data['archive_id'] = str(uuid.uuid4())
        data['stats.st_size'] = file_stats.st_size
        data['stats.st_mtime'] = file_stats.st_mtime
        database[filename] = data
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
            os.unlink(os.path.join(dirname, '.frokup.db'))
        except OSError:
            pass

    def _get_db_copy(self, dirname):
        """Returns a dict with a copy of the DB contents"""
        db = shelve.open(os.path.join(dirname, '.frokup.db'))
        copy = dict(db)
        db.close()
        return copy

    def test_dir1(self):
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
        db_filename = os.path.join(dir1, '.frokup.db')
        database = shelve.open(db_filename)
        logging.debug("Database at %s: %s", db_filename, pprint.pformat(database))
        for filename in ('file1.txt', 'file2.txt', 'file3.txt'):
            database[filename]['archive_id']
            database[filename]['stats.st_size']
            database[filename]['stats.st_mtime']

    def test_dir2(self):
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
        db_filename = os.path.join(dir2, '.frokup.db')
        database = shelve.open(db_filename)
        logging.debug("Database at %s: %s", db_filename, pprint.pformat(database))
        for filename in ('file1.txt', 'file2.txt', 'file3.txt'):
            self.assertDictEqual(database[filename],
                created_metadata[filename])

    def test_dir3(self):
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
        self.assertEqual(main.ctx.included_count, 1) # file1.txt
        self.assertEqual(main.ctx.excluded_count, 0)

        # --- Call process_directory() ---
        for _ in range(0, 2):
            main = Main(glacier=GlacierMock)
            main.process_directory(dir3)
            main.close()
            # Check statistics
            logging.debug("Log: %s", pprint.pformat(main.ctx.log))
            self.assertEqual(main.ctx.included_count, 0)
            self.assertEqual(main.ctx.excluded_count, 2) # .frokup.db + file1.txt

        # --- Add `file2.txt`
        file2_path = os.path.join(dir3, 'file2.txt')
        shutil.copy2(os.path.join(dir3, '../dir2/file2.txt'), file2_path)

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 1) # file2.txt
        self.assertEqual(main.ctx.excluded_count, 2) # .frokup.db + file1.txt

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 0)
        self.assertEqual(main.ctx.excluded_count, 3) # .frokup.db + file1.txt + file2.txt

        # --- Touch `file2.txt`
        os.utime(file2_path, (1, 1))

        # --- Call process_directory() ---
        main = Main(glacier=GlacierMock)
        main.process_directory(dir3)
        main.close()
        # Check statistics
        logging.debug("Log: %s", pprint.pformat(main.ctx.log))
        self.assertEqual(main.ctx.included_count, 1) # file2.txt
        self.assertEqual(main.ctx.excluded_count, 2) # .frokup.db + file1.txt

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
        self.assertEqual(main.ctx.excluded_count, 3) # .frokup.db + file1.txt + file2.txt

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
        self.assertEqual(main.ctx.included_count, 1) # file2.txt
        self.assertEqual(main.ctx.excluded_count, 2) # .frokup.db + file1.txt

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
        self.assertEqual(main.ctx.excluded_count, 3) # .frokup.db + file1.txt + file2.txt

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
        main.glacier = GlacierFtpBased(main.ctx)
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

    def test_change_in_file_while_upload_is_detected(self):
        # FIXME: implement this test!
        pass


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
