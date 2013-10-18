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
import os
import logging
import ConfigParser

EXCLUDED_BY_FILE_FILTER = 'file-filter'
EXCLUDED_BY_LOCAL_METADATA = 'local-metadata'
FLAG_FILE_CHANGED_WHILE_UPLOADING = 'file-changed'


class Context(dict):
    """Context to share state between all the components"""

    def __init__(self, config=None):
        self.log = {}
        self.excluded_count = 0
        self.included_count = 0
        self.error_count = 0
        self.include_extensions = []
        self.exclude_extensions = []
        self.config = config or get_config()

    def add_log(self, directory, filename, **kwargs):
        self.log[directory] = self.log.get(directory, dict())
        self.log[directory][filename] = self.log[directory].get(filename, dict())
        self.log[directory][filename].update(**kwargs)

    def add_excluded(self, directory, filename, reason):
        self.add_log(directory, filename, excluded=True,
            excluded_reason=reason)
        self.excluded_count += 1

    def add_included(self, directory, filename):
        self.add_log(directory, filename, included=True)
        self.included_count += 1

    def add_error(self, directory, filename, error_type, error_message):
        self.add_log(directory, filename, error=True, error_type=error_type,
            error_message=error_message)
        self.error_count += 1

    def set_include_extensions(self, extensions):
        assert isinstance(extensions, (list, tuple))
        self.include_extensions = [tmp.lower() for tmp in extensions]

    def set_exclude_extensions(self, extensions):
        assert isinstance(extensions, (list, tuple))
        self.exclude_extensions = [tmp.lower() for tmp in extensions]

    def get_log_processed(self):
        #    self.log = {
        #        '/path/to/directory': {
        #            '.frockup.db': {
        #                'excluded': True,
        #                'excluded_reason': 'file-filter'
        #            },
        #           'fome-file.txt': {
        #               'excluded': True,
        #               'excluded_reason': 'local-metadata'
        #            },
        #           'some-other-file.txt': {
        #               'excluded': True,
        #                'excluded_reason': 'local-metadata'
        #            },
        #        }
        #    }
        excluded = []
        included = []
        for directory, entries in self.log.iteritems():
            for filename, stat_dict in entries.iteritems():
                if stat_dict.get('included', False):
                    included.append([directory, filename])
                elif stat_dict.get('excluded', False):
                    excluded.append([directory, filename])
        return included, excluded


def get_config(filename=None):
    """Loads configuration and returns instance of ConfigParser"""
    config_file = os.path.expanduser(filename or '~/.frockup/frockup.conf')
    logging.debug("Loading config from %s", config_file)
    assert os.path.exists(config_file), \
        "The configuration file {0} does not exists".format(config_file)
    assert os.path.isfile(config_file), \
        "The configuration {0} is not a regular file".format(config_file)
    config = ConfigParser.ConfigParser()
    config.read(config_file)
    return config
