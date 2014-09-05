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
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_path('style.css')
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)

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

        # Start with title, date, activity and scrolling window of entries
        align = Gtk.Alignment.new(xalign=0.5, yalign=0.5, xscale=0, yscale=0)
        button_grid = Gtk.Grid()
        button_grid.set_row_spacing(style.DEFAULT_SPACING)
        button_grid.set_column_spacing(style.DEFAULT_SPACING)
        button_grid.set_column_homogeneous(True)

        self._title_button = Gtk.Button(_('Title'), name='next-button')
        self._title_button.connect('clicked', self._title_button_cb, 'title')
        button_grid.attach(self._title_button, 0, 0, 1, 1)
        self._title_button.show()

        self.date_button = Gtk.Button(_('Date'), name='next-button')
        self.date_button.connect('clicked', self._date_button_cb)
        button_grid.attach(self.date_button, 1, 0, 1, 1)
        self.date_button.show()

        self._search_button = Gtk.Button(_('Search'), name='next-button')
        self._search_button.connect('clicked', self._search_button_cb, 'search')
        button_grid.attach(self._search_button, 2, 0, 1, 1)
        self._search_button.show()

        align.add(button_grid)
        button_grid.show()
        self._graphics_grid.attach(align, 1, 0, 1, 1)
        align.show()


    def keypress_cb(self, widget, event):
        self.keyname = Gdk.keyval_name(event.keyval)

    def _title_button_cb(self, button):
        logging.debug('title button pressed')

    def _date_button_cb(self, button):
        logging.debug('date button pressed')

    def _search_button_cb(self, button):
        logging.debug('search button pressed')
