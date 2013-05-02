'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import logging
import os
import unittest

from frokup.main import Main
import shelve
import uuid
import pprint


class BaseTest(unittest.TestCase):

    def test_dir1(self):
        """Tests that metadata is created when don't exists"""
        module_dir = os.path.abspath(os.path.split(__file__)[0])
        root_dir = os.path.abspath(os.path.split(module_dir)[0])
        test_dir = os.path.join(root_dir, 'tests')
        dir1 = os.path.join(test_dir, 'dir1')
        # Remove DB if exists (of previous run of the tests)
        try:
            os.unlink(os.path.join(dir1, '.frokup.db'))
        except OSError:
            pass
        # Call process_directory()
        main = Main()
        main.process_directory(dir1)
        main.close()
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
        module_dir = os.path.abspath(os.path.split(__file__)[0])
        root_dir = os.path.abspath(os.path.split(module_dir)[0])
        test_dir = os.path.join(root_dir, 'tests')
        dir2 = os.path.join(test_dir, 'dir2')
        self.assertTrue(os.path.exists(dir2))
        # Create local metadata DB
        db_filename = os.path.join(dir2, '.frokup.db')
        database = shelve.open(db_filename)
        created_metadata = {}
        for filename in ('file1.txt', 'file2.txt', 'file3.txt'):
            file_stats = os.stat(os.path.join(dir2, filename))
            data = {}
            data['archive_id'] = str(uuid.uuid4())
            data['stats.st_size'] = file_stats.st_size
            data['stats.st_mtime'] = file_stats.st_mtime
            database[filename] = data
            database.sync()
            created_metadata[filename] = {}
            created_metadata[filename].update(data)
        database.close()
        # Call process_directory()
        main = Main()
        main.process_directory(dir2)
        main.close()
        # Check that local metadata wasn't changed
        database = shelve.open(db_filename)
        logging.debug("Database at %s: %s", db_filename, pprint.pformat(database))
        for filename in ('file1.txt', 'file2.txt', 'file3.txt'):
            self.assertDictEqual(database[filename],
                created_metadata[filename])


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
