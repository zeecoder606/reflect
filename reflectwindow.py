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
from random import uniform
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GConf
from gi.repository import GdkPixbuf

from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon, EventIcon
from sugar3 import profile

import logging
_logger = logging.getLogger('reflect-window')

import utils
from graphics import Graphics

BUTTON_SIZE = 30
REFLECTION_WIDTH = 5 * style.GRID_CELL_SIZE


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

        self._reflections_grid = Gtk.Grid()
        self._reflections_grid.set_row_spacing(style.DEFAULT_SPACING)
        self._reflections_grid.set_column_spacing(style.DEFAULT_SPACING)

        self.set(xalign=0.5, yalign=0, xscale=0, yscale=0)
        self.add(self._reflections_grid)
        self._reflections_grid.show()

        self.activity.load_graphics_area(self)

        entry = Gtk.Entry()
        entry.props.placeholder_text = _('Add a reflection')
        # entry.set_size_request(style.GRID_CELL_SIZE * 4, -1)
        entry.connect('activate', self._entry_activate_cb)
        self._reflections_grid.attach(entry, 0, 0, 4, 1)
        entry.show()

        y = 1
        # TODO: WHERE DO THESE COME FROM?
        for r in ['a', 'b', 'c', 'd', 'e']:
            reflection = Reflection()
            reflection.set_title('This is a Title.')
            reflection.add_text('The quick brown fox')
            reflection.add_image('/usr/share/art4apps/images/fox.png')
            reflection.add_text('jumped over the lazy dog')
            reflection.add_image('/usr/share/art4apps/images/dog.png')
            reflection.add_activity('TurtleBlocks')
            reflection.add_activity('Pippy')
            reflection.set_stars(int(uniform(0, 6)))
            reflection.add_tag('#programming')
            reflection.add_tag('#art')
            reflection.add_tag('#math')
            reflection.add_comment('Teacher Comment: Nice work')
            self._reflections_grid.attach(
                reflection.get_graphics(), 0, y, 4, 1)
            reflection.refresh()
            y += 1

    def _entry_activate_cb(self, entry):
        reflection = Reflection()
        self._reflections_grid.insert_row(1)
        text = entry.props.text
        reflection.set_title(text)
        self._reflections_grid.attach(
            reflection.get_graphics(), 0, 1, 3, 1)
        reflection.refresh()
        entry.set_text('')

    def keypress_cb(self, widget, event):
        self.keyname = Gdk.keyval_name(event.keyval)


class ReflectionGrid(Gtk.EventBox):

    def __init__(self, title='', tags=[], activities=[], content=[],
                 stars=None, comments=[]):
        Gtk.EventBox.__init__(self)

        self._collapse = True
        self._collapse_id = None

        self.modify_bg(
            Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        color = profile.get_color()
        color_stroke = color.get_stroke_color()
        color_fill = color.get_fill_color()

        lighter = lighter_color([color_stroke, color_fill])
        darker = 1 - lighter

        if darker == 0:
            self._title_color = color_stroke
        else:
            self._title_color = color_fill

        self._grid = Gtk.Grid()
        self.add(self._grid)
        self._grid.show()

        self._grid.set_row_spacing(0)
        self._grid.set_column_spacing(style.DEFAULT_SPACING)
        self._grid.set_column_homogeneous(True)
        self._grid.set_border_width(style.DEFAULT_PADDING)

        row = 0

        self._expand_button = EventIcon(icon_name='expand',
                                        pixel_size=BUTTON_SIZE)
        self._collapse_id = self._expand_button.connect('button-press-event',
                                           self._expand_cb)
        self._grid.attach(self._expand_button, 0, row, 1, 1)
        self._expand_button.show()

        self._title_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)

        self._title = Gtk.Label()
        self._title.set_size_request(style.GRID_CELL_SIZE * 4, -1)
        self._title.set_use_markup(True)
        self._title.set_markup(
            '<span foreground="%s"><big><b>%s</b></big></span>' %
            (self._title_color, title))

        self._title_align.add(self._title)
        self._title.show()
        self._grid.attach(self._title_align, 1, row, 5, 1)
        self._title_align.show()

        button = EventIcon(icon_name='edit', pixel_size=BUTTON_SIZE)
        button.connect('button-press-event', self._edit_title_cb)
        self._grid.attach(button, 6, row, 1, 1)
        button.show()
        row += 1

        label = ''
        for tag in tags:  # TODO: MAX
            if len(label) > 0:
                label += ', '
            label += tag

        if label == '':
            label = _('Add a #tag')

        self._tag_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        tag_label = Gtk.Label(label)
        self._tag_align.add(tag_label)
        tag_label.show()
        self._grid.attach(self._tag_align, 1, row, 5, 1)
        row += 1

        column = 0
        self._activities_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        grid = Gtk.Grid()
        self._activities = []
        if len(activities) > 0:
            for icon_name in activities:
                # TODO: WHENCE ICONS
                self._activities.append(CanvasIcon(icon_name=icon_name,
                                                   pixel_size=BUTTON_SIZE))
                grid.attach(self._activities[-1], column, 0, 1, 1)
                self._activities[-1].show()
                column += 1
        else:
            label = Gtk.Label('Add an activity')
            grid.attach(label, 0, row, 5, 1)
            label.show()
        self._activities_align.add(grid)
        grid.show()
        self._grid.attach(self._activities_align, 1, row, 5, 1)
        row += 1

        column = 0
        self._stars_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        grid = Gtk.Grid()
        if stars is None:
            stars = 0
        for i in range(5):
            if i < stars:
                icon_name = 'star-filled'
            else:
                icon_name = 'star-empty'
            star_icon = EventIcon(icon_name=icon_name,
                                  pixel_size=BUTTON_SIZE)
            # TODO: BUTTON PRESS
            grid.attach(star_icon, column, 0, 1, 1)
            star_icon.show()
            column += 1
        self._stars_align.add(grid)
        grid.show()
        self._grid.attach(self._stars_align, 1, row, 5, 1)
        row += 1

        self._content_aligns = []
        for item in content:
            # Add edit and delete buttons
            if 'text' in item:
                # FIX ME: Text
                obj = Gtk.Label(item['text'])
            elif 'image' in item:
                # FIX ME: Whence images
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    item['image'], style.GRID_CELL_SIZE * 4,
                    style.GRID_CELL_SIZE * 3)
                obj = Gtk.Image.new_from_pixbuf(pixbuf)
            align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
            align.add(obj)
            obj.show()
            self._grid.attach(align, 1, row, 5, 1)
            self._content_aligns.append(align)
            row += 1

        self._row = row
        self._new_entry = Gtk.Entry()
        self._new_entry.props.placeholder_text = _('Write a reflection')
        # entry.set_size_request(style.GRID_CELL_SIZE * 4, -1)
        self._new_entry.connect('activate', self._entry_activate_cb)
        self._grid.attach(self._new_entry, 1, row, 5, 1)
        self._new_image = EventIcon(icon_name='activity-journal',
                                 pixel_size=BUTTON_SIZE)
        self._new_image.set_icon_name('activity-journal')
        self._new_image.connect('button-press-event', self._image_button_cb)
        self._grid.attach(self._new_image, 6, row, 1, 1)
        row += 1

        self._comment_aligns = []
        for comment in comments:
            # FIX ME: Text, attribution
            obj = Gtk.Label(comment)
            align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
            align.add(obj)
            obj.show()
            self._grid.attach(align, 1, row, 5, 1)
            self._comment_aligns.append(align)
            row += 1

        if len(content) == 0:
            self._expand_cb(self._expand_button, None)

    def _edit_title_cb(self, button, event):
        entry = Gtk.Entry()
        entry.set_text(self._title.get_text())
        entry.connect('activate', self._title_activate_cb)
        self._title_align.remove(self._title)
        self._title_align.add(entry)
        entry.show()

    def _title_activate_cb(self, entry):
        # TODO: SAVE NEW TITLE
        text = entry.props.text
        self._title.set_markup(
            '<span foreground="%s"><big><b>%s</b></big></span>' %
            (self._title_color, text))
        self._title_align.remove(entry)
        self._title_align.add(self._title)

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
        entry.set_text('')

    def _image_button_cb(self, button, event):
        logging.debug('image button press')

    def _expand_cb(self, button, event):
        self._grid.set_row_spacing(style.DEFAULT_SPACING)
        if self._collapse_id is not None:
            button.disconnect(self._collapse_id)
        button.set_icon_name('collapse')
        self._collapse_id = button.connect('button-press-event',
                                           self._collapse_cb)
        self._tag_align.show()
        self._activities_align.show()
        self._stars_align.show()
        for align in self._content_aligns:
            align.show()
        self._new_entry.show()
        self._new_image.show()
        for align in self._comment_aligns:
            align.show()

    def _collapse_cb(self, button, event):
        self._grid.set_row_spacing(0)
        if self._collapse_id is not None:
            button.disconnect(self._collapse_id)
        button.set_icon_name('expand')
        self._collapse_id = button.connect('button-press-event',
                                           self._expand_cb)
        self._tag_align.hide()
        self._activities_align.hide()
        self._stars_align.hide()
        for align in self._content_aligns:
            align.hide()
        self._new_entry.hide()
        self._new_image.hide()
        for align in self._comment_aligns:
            align.hide()

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

    def set_title(self, title):
        logging.debug(title)
        self._title = title

    def set_creation_date(self):
        self._creation_date = time.time()

    def set_modification_date(self):
        self._modification_date = time.time()

    def add_tag(self, tag):
        ''' a #tag '''
        self._tags.append(tag)

    def add_text(self, text):
        ''' simple text '''
        self._content.append({'text': text})

    def add_comment(self, text):
        ''' simple text '''
        self._comments.append(text)

    def add_image(self, image):
        ''' an image file pathname '''
        self._content.append({'image': image})

    def add_activity(self, activity):
        ''' an activity icon '''
        self._activities.append(activity)

    def search_tags(self, tag):
        return tag in self._tags

    def add_activity(self, activity):
        self._activities.append(activity)

    def set_stars(self, n):
        ''' # of stars to highlight '''
        if n < 0:
            n = 0
        elif n > 5:
            n = 5
        self._stars = n
        logging.debug(self._stars)

    def get_graphics(self):
        ''' return resizable entry '''
        self._graphics = ReflectionGrid(title=self._title,
                                        tags=self._tags,
                                        activities=self._activities,
                                        content=self._content,
                                        stars=self._stars,
                                        comments=self._comments)
        return self._graphics

    def get_fullscreen(self):
        ''' return full-sized entry '''
        return self._fullscreen

    def refresh(self):
        ''' redraw graphics with updated content '''
        self._graphics.set_size_request(REFLECTION_WIDTH,
                                        style.GRID_CELL_SIZE * 3)
        self._graphics.show()
