# -*- coding: utf-8 -*-
# Copyright (c) 2014 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

import os
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GConf

from sugar3.graphics import style

import logging
_logger = logging.getLogger('reflect-window')

import utils
from graphics import Graphics


class ReflectWindow(Gtk.Alignment):

    def __init__(self, activity):
        ''' Initialize the task list '''
        Gtk.Alignment.__init__(self)
        self.activity = activity

        self.set_size_request(Gdk.Screen.width() - style.GRID_CELL_SIZE, -1)

        self._graphics_grid = Gtk.Grid()
        self._graphics_grid.set_row_spacing(style.DEFAULT_SPACING)
        self._graphics_grid.set_column_spacing(style.DEFAULT_SPACING)

        self.set(xalign=0.5, yalign=0, xscale=0, yscale=0)
        self.add(self._graphics_grid)
        self._graphics_grid.show()

        self.activity.load_graphics_area(self)

    def keypress_cb(self, widget, event):
        self.keyname = Gdk.keyval_name(event.keyval)
