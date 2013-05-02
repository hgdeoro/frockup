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
        main = Main()
        main.process_directory(module_dir)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
