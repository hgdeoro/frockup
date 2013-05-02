'''
Created on May 1, 2013

@author: Horacio G. de Oro
'''

import logging
import os
import unittest

from frokup.main import Main


class BaseTest(unittest.TestCase):

    def test(self):
        module_dir = os.path.abspath(os.path.split(__file__)[0])
        root_dir = os.path.abspath(os.path.split(module_dir)[0])
        test_dir = os.path.join(root_dir, 'tests')
        dir1 = os.path.join(test_dir, 'dir1')
        try:
            os.unlink(os.path.join(dir1, '.frokup.db'))
        except OSError:
            pass
        main = Main()
        main.process_directory(dir1)
        main.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
