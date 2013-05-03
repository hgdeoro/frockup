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

logger = logging_.getLogger(__name__)


class FileFilter():
    """
    Service that filters files to include in backup based on the file's properties,
    like directory, extension, last modification time, etc. (but does NOT
    check file metadata nor knows if the file was already uploaded).
    """

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, directory, filename):
        """Returns True if the file must be included in the backup, False otherwise"""
        if filename == '.frockup.db':
            logger.debug("Excluding '%s/%s'", directory, filename)
            return False
        logger.debug("Including '%s/%s'", directory, filename)
        return True


class FileFilterMock():

    def __init__(self, ctx):
        self.ctx = ctx

    def include_file(self, directory, filename):
        return True
