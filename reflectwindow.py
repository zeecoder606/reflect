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
import time
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GConf

from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon, EventIcon
from sugar3 import profile

import logging
_logger = logging.getLogger('reflect-window')

import utils
from graphics import Graphics


def _luminance(color):
    ''' Calculate luminance value '''
    return int(color[1:3], 16) * 0.3 + int(color[3:5], 16) * 0.6 + \
        int(color[5:7], 16) * 0.1


def lighter_color(colors):
    ''' Which color is lighter? Use that one for the text nick color '''
    if _luminance(colors[0]) > _luminance(colors[1]):
        return 0
    return 1


def darker_color(colors):
    ''' Which color is darker? Use that one for the text background '''
    return 1 - lighter_color(colors)


class ReflectButtons(Gtk.Alignment):

    def __init__(self, activity):
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_path('style.css')
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)

        Gtk.Alignment.__init__(self)
        self.activity = activity

        self.set_size_request(Gdk.Screen.width() - style.GRID_CELL_SIZE,
                              style.GRID_CELL_SIZE)
        self._graphics_grid = Gtk.Grid()
        self._graphics_grid.set_row_spacing(style.DEFAULT_SPACING)
        self._graphics_grid.set_column_spacing(style.DEFAULT_SPACING)

        self.set(xalign=0.5, yalign=0, xscale=0, yscale=0)
        self.add(self._graphics_grid)
        self._graphics_grid.show()

        self.activity.load_button_area(self)

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

    def _title_button_cb(self, button):
        logging.debug('title button pressed')

    def _date_button_cb(self, button):
        logging.debug('date button pressed')

    def _search_button_cb(self, button):
        logging.debug('search button pressed')


class ReflectWindow(Gtk.Alignment):

    def __init__(self, activity):
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

        y = 1
        # TODO: WHERE DO THESE COME FROM?
        for r in ['a', 'b', 'c', 'd', 'e']:
            reflection = Reflection()
            self._graphics_grid.attach(reflection.get_thumbnail(), 0, y, 3, 1)
            reflection.refresh()
            y += 1

    def keypress_cb(self, widget, event):
        self.keyname = Gdk.keyval_name(event.keyval)


class ReflectionGrid(Gtk.EventBox):

    def __init__(self, title='', tags=[], activities=[], content=[],
                 stars=None, comments=[]):
        Gtk.EventBox.__init__(self)

        self.modify_bg(
            Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        color = profile.get_color()
        color_stroke = color.get_stroke_color()
        color_fill = color.get_fill_color()
        logging.debug(color_stroke)
        logging.debug(color_fill)

        lighter = lighter_color([color_stroke, color_fill])
        darker = 1 - lighter

        if darker == 0:
            title_color = color_stroke
        else:
            title_color = color_fill

        self._grid = Gtk.Grid()
        self.add(self._grid)
        self._grid.show()

        self._grid.set_row_spacing(style.DEFAULT_SPACING)
        self._grid.set_column_spacing(style.DEFAULT_SPACING)
        self._grid.set_column_homogeneous(True)
        self._grid.set_border_width(style.DEFAULT_PADDING)

        row = 0

        align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
        self._title = Gtk.Label('')
        self._title.set_use_markup(True)
        self._title.set_markup(
            '<span foreground="%s"><big><b>%s</b></big></span>' %
            (title_color, title))
        align.add(self._title)
        self._title.show()
        self._grid.attach(align, 0, row, 5, 1)
        align.show()
        row += 1

        label = ''
        for tag in tags:  # TODO: MAX
            if len(label) > 0:
                label += ', '
            label += tag

        align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
        tag_label = Gtk.Label(label)
        align.add(tag_label)
        tag_label.show()
        self._grid.attach(align, 0, row, 5, 1)
        align.show()
        row += 1

        column = 0
        grid = Gtk.Grid()
        self._activities = []
        for icon_name in activities:
            # TODO: WHENCE ICONS
            logging.error(icon_name)
            self._activities.append(CanvasIcon(icon_name=icon_name,
                                               pixel_size=30))
            # self._activities[-1].set_icon_name(icon_name)
            grid.attach(self._activities[-1], column, 0, 1, 1)
            self._activities[-1].show()
            column += 1
        self._grid.attach(grid, 0, row, 5, 1)
        grid.show()
        row += 1

        column = 0
        grid = Gtk.Grid()
        if stars is None:
            stars = 0
        for i in range(5):
            if i < stars:
                icon_name = 'star-filled'
            else:
                icon_name = 'star-empty'
            star_icon = EventIcon(icon_name=icon_name,
                                  pixel_size=30)
            # TODO: BUTTON PRESS
            grid.attach(star_icon, column, 0, 1, 1)
            star_icon.show()
            column += 1
        self._grid.attach(grid, 0, row, 5, 1)
        grid.show()
        row += 1

        for item in content:
            # Add edit and delete buttons
            if 'text' in item:
                # FIX ME: Text
                obj = Gtk.Label(item['text'])
            elif 'image' in item:
                # FIX ME: Whence images
                obj = Gtk.Image.new_from_file(item['image'])
            align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
            align.add(obj)
            obj.show()
            self._grid.attach(align, 0, row, 5, 1)
            align.show()
            row += 1

        self._row = row
        self._entry = Gtk.Entry()
        self._entry.props.placeholder_text = _('Write a reflection')
        self._entry.set_size_request(style.GRID_CELL_SIZE * 4, -1)
        self._entry.connect('activate', self._entry_activate_cb)
        self._grid.attach(self._entry, 0, row, 4, 1)
        self._entry.show()
        image_button = EventIcon(icon_name='activity-journal')
        image_button.set_icon_name('activity-journal')
        image_button.connect('button-press-event', self._image_button_cb)
        self._grid.attach(image_button, 4, row, 1, 1)
        image_button.show()
        row += 1

        for comment in comments:
            # FIX ME: Text, attribution
            obj = Gtk.Label(comment)
            align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
            align.add(obj)
            obj.show()
            self._grid.attach(align, 0, row, 5, 1)
            align.show()
            row += 1

    def _entry_activate_cb(self, entry):
        # TODO: SAVE
        text = entry.props.text
        logging.debug('%d: %s' % (self._row, text))
        obj = Gtk.Label(text)
        align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
        align.add(obj)
        obj.show()
        self._grid.insert_row(self._row)
        self._grid.attach(align, 0, self._row, 5, 1)
        self._row += 1
        align.show()
        self._entry.set_text('')
        self._entry.props.placeholder_text = _('Write a reflection')

    def _image_button_cb(self, button, event):
        logging.debug('image button press')


class Reflection():
    ''' A class to hold a reflection '''

    def __init__(self):
        self._title = _('Untitled')
        self._creation_data = None
        self._modification_data = None
        self._tags = []
        self._activities = []
        self._content = []
        self._comments = []
        self._stars = None

        self._title = 'This is a Title.'
        self._content.append({'text': 'The quick brown fox'})
        self._content.append({'image': 'fox.png'})
        self._content.append({'text': 'jumped over the lazy dog'})
        self._content.append({'image': 'dog.png'})
        self._activities.append('TurtleBlocks')
        self._activities.append('Pippy')
        self._stars = 3
        self._tags.append('#programming')
        self._tags.append('#art')
        self._tags.append('#math')
        self._comments.append('Nice work')

        self._thumbnail = ReflectionGrid(title=self._title,
                                         tags=self._tags,
                                         activities=self._activities,
                                         content=self._content,
                                         stars=self._stars,
                                         comments=self._comments)

    def set_title(self, title):
        self._title = title

    def set_creation_date(self):
        self._creation_date = time.time()

    def set_modification_date(self):
        self._modification_date = time.time()

    def add_tag(self, tag):
        self._tags.append(tag)

    def search_tags(self, tag):
        return tag in self._tags

    def add_activity(self, activity):
        self._activities.append(activity)

    def get_thumbnail(self):
        ''' return thumb-sized entry '''
        return self._thumbnail

    def get_fullscreen(self):
        ''' return full-sized entry '''
        return self._fullscreen

    def refresh(self, thumbnail=True):
        ''' redraw thumbname and fullscreen with updated content '''
        self._thumbnail.set_size_request(style.GRID_CELL_SIZE * 5,
                              style.GRID_CELL_SIZE * 3)

        '''
        self._fullscreen.set_size_request(
            Gdk.Screen.width() - style.GRID_CELL_SIZE,
            Gdk.Screen.height() - style.GRID_CELL_SIZE)
        self._fullscreen.set_row_spacing(style.DEFAULT_SPACING)
        self._fullscreen.set_column_spacing(style.DEFAULT_SPACING)
        self._fullscreen.set_column_homogeneous(True)
        '''

        if thumbnail:
            self._thumbnail.show()
        else:
            self._fullscreen.show()
