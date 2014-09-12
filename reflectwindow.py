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
ENTRY_WIDTH = 6 * style.GRID_CELL_SIZE
PICTURE_WIDTH = 6 * style.GRID_CELL_SIZE
PICTURE_HEIGHT = int(4.5 * style.GRID_CELL_SIZE)
REFLECTION_WIDTH = 8 * style.GRID_CELL_SIZE


class ReflectButtons(Gtk.Alignment):

    def __init__(self, activity):
        cssProvider = Gtk.CssProvider()
        cssProvider.load_from_path('style.css')
        screen = Gdk.Screen.get_default()
        styleContext = Gtk.StyleContext()
        styleContext.add_provider_for_screen(screen, cssProvider,
                                             Gtk.STYLE_PROVIDER_PRIORITY_USER)

        Gtk.Alignment.__init__(self)
        self._activity = activity

        self.set_size_request(Gdk.Screen.width() - style.GRID_CELL_SIZE,
                              style.GRID_CELL_SIZE)
        self._graphics_grid = Gtk.Grid()
        self._graphics_grid.set_row_spacing(style.DEFAULT_SPACING)
        self._graphics_grid.set_column_spacing(style.DEFAULT_SPACING)

        self.set(xalign=0.5, yalign=0, xscale=0, yscale=0)
        self.add(self._graphics_grid)
        self._graphics_grid.show()

        self._activity.load_button_area(self)

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
        self._activity = activity

        self.set_size_request(Gdk.Screen.width() - style.GRID_CELL_SIZE, -1)

        self._reflections_grid = Gtk.Grid()
        self._reflections_grid.set_row_spacing(style.DEFAULT_SPACING)
        self._reflections_grid.set_column_spacing(style.DEFAULT_SPACING)

        self.set(xalign=0.5, yalign=0, xscale=0, yscale=0)
        self.add(self._reflections_grid)
        self._reflections_grid.show()

        self._activity.load_graphics_area(self)

        entry = Gtk.Entry()
        entry.props.placeholder_text = _('Add a reflection')
        entry.connect('activate', self._entry_activate_cb)
        self._reflections_grid.attach(entry, 0, 0, 4, 1)
        entry.show()

    def load(self, reflection_data):
        y = 1
        for item in reflection_data:
            reflection = Reflection(item)
            self._reflections_grid.attach(
                reflection.get_graphics(), 0, y, 4, 1)
            reflection.refresh()
            y += 1

    def _entry_activate_cb(self, entry):
        text = entry.props.text
        self._activity.reflection_data.insert(0, {'title': text})
        reflection = Reflection(self._activity.reflection_data[-1])
        self._reflections_grid.insert_row(1)
        reflection.set_title(text)
        self._reflections_grid.attach(
            reflection.get_graphics(), 0, 1, 3, 1)
        reflection.refresh()
        entry.set_text('')

    def keypress_cb(self, widget, event):
        self.keyname = Gdk.keyval_name(event.keyval)


class ReflectionGrid(Gtk.EventBox):

    def __init__(self, parent):
        Gtk.EventBox.__init__(self)

        self._reflection = parent
        self._collapse = True
        self._collapse_id = None

        self.modify_bg(
            Gtk.StateType.NORMAL, style.COLOR_WHITE.get_gdk_color())

        color = profile.get_color()
        color_stroke = color.get_stroke_color()
        color_fill = color.get_fill_color()

        lighter = utils.lighter_color([color_stroke, color_fill])
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
        self._title.set_size_request(ENTRY_WIDTH, -1)
        self._title.set_use_markup(True)
        self._title.set_markup(
            '<span foreground="%s"><big><b>%s</b></big></span>' %
            (self._title_color, self._reflection.data['title']))

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
        if 'tags' in self._reflection.data:
            for tag in self._reflection.data['tags']:
                if len(label) > 0:
                    label += ', '
                label += tag
        if label == '':
            label = _('Add a #tag')
        self._tag_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        tag_view = Gtk.TextView()
        tag_view.set_size_request(ENTRY_WIDTH, -1)
        tag_view.set_wrap_mode(Gtk.WrapMode.WORD)
        tag_view.get_buffer().set_text(label)
        tag_view.get_buffer().connect('insert-text', self._insert_tag_cb)
        tag_view.connect('focus-in-event', self._tag_focus_in_cb,
                         _('Add a #tag'))
        tag_view.connect('focus-out-event', self._tags_focus_out_cb)
        self._tag_align.add(tag_view)
        tag_view.show()
        self._grid.attach(self._tag_align, 1, row, 5, 1)
        row += 1

        column = 0
        self._activities_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        grid = Gtk.Grid()
        self._activities = []
        if 'activities' in self._reflection.data:
            for icon_path in self._reflection.data['activities']:
                if icon_path is None:
                    continue
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    icon_path, BUTTON_SIZE, BUTTON_SIZE)
                self._activities.append(Gtk.Image.new_from_pixbuf(pixbuf))
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
        self._activities_align.show()
        row += 1

        column = 0
        self._stars_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        grid = Gtk.Grid()
        if 'stars' in self._reflection.data:
            stars = self._reflection.data['stars']
        else:
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
        first_text = True
        first_image = True
        self._content_we_always_show = []
        if 'content' in self._reflection.data:
            for i, item in enumerate(self._reflection.data['content']):
                # Add edit and delete buttons
                align = Gtk.Alignment.new(
                    xalign=0, yalign=0.5, xscale=0, yscale=0)
                obj = None
                if 'text' in item:
                    obj = Gtk.TextView()
                    obj.set_size_request(ENTRY_WIDTH, -1)
                    obj.set_wrap_mode(Gtk.WrapMode.WORD)

                    obj.get_buffer().set_text(item['text'])
                    obj.connect('focus-in-event', self._text_focus_in_cb)
                    obj.connect('focus-out-event', self._text_focus_out_cb, i)

                    if first_text:
                        self._content_we_always_show.append(align)
                        first_text = False
                elif 'image' in item:
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                            item['image'], PICTURE_WIDTH, PICTURE_HEIGHT)
                        obj = Gtk.Image.new_from_pixbuf(pixbuf)
                        if first_image:
                            self._content_we_always_show.append(align)
                            first_image = False
                    except:
                        logging.error('could not open %s' % item['image'])
                if obj is not None:
                    align.add(obj)
                    obj.show()
                    self._grid.attach(align, 1, row, 5, 1)
                    self._content_aligns.append(align)
                    row += 1

        for align in self._content_we_always_show:
            align.show()

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
        if 'comments' in self._reflection.data:
            for comment in self._reflection.data['comments']:
                # FIX ME: Text, attribution
                obj = Gtk.Label(comment)
                align = Gtk.Alignment.new(
                    xalign=0, yalign=0.5, xscale=0, yscale=0)
                align.add(obj)
                obj.show()
                self._grid.attach(align, 1, row, 5, 1)
                self._comment_aligns.append(align)
                row += 1

    def _insert_tag_cb(self, textbuffer, textiter, text, length):
        if '\12' in text:
            bounds = textbuffer.get_bounds()
            text = textbuffer.get_text(bounds[0], bounds[1], True)
            self._process_tags(textbuffer, text)

    def _text_focus_in_cb(self, widget, event):
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue = 0.9, 0.9, 0.9
        rgba.alpha = 1.
        widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)

    def _text_focus_out_cb(self, widget, event, entry):
        bounds = widget.get_buffer().get_bounds()
        text = widget.get_buffer().get_text(bounds[0], bounds[1], True)
        self._reflection.data['content'][entry]['text'] = text
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue = 1., 1., 1.
        rgba.alpha = 1.
        widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)

    def _tag_focus_in_cb(self, widget, event, prompt=None):
        bounds = widget.get_buffer().get_bounds()
        text = widget.get_buffer().get_text(bounds[0], bounds[1], True)
        if text == prompt:
            widget.get_buffer().set_text('')
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue = 0.9, 0.9, 0.9
        rgba.alpha = 1.
        widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)

    def _tags_focus_out_cb(self, widget, event):
        bounds = widget.get_buffer().get_bounds()
        text = widget.get_buffer().get_text(bounds[0], bounds[1], True)
        self._process_tags(widget.get_buffer(), text)
        rgba = Gdk.RGBA()
        rgba.red, rgba.green, rgba.blue = 1., 1., 1.
        rgba.alpha = 1.
        widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)

    def _process_tags(self, text_buffer, text):
        self._reflection.data['tags'] = []
        label = ''
        tags = text.split()
        for tag in tags:
            if len(label) > 0:
                label += ', '
            tag = tag.rstrip(',')
            tag = tag.rstrip(';')
            if tag[0] == '#':
                self._reflection.data['tags'].append(tag)
                label += tag
            else:
                self._reflection.data['tags'].append('#' + tag)
                label += '#' + tag
        text_buffer.set_text(label.replace('\12', ''))

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
        self._reflection.data['title'] = text

    def _entry_activate_cb(self, entry):
        text = entry.props.text
        obj = Gtk.Label(text)
        align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
        align.add(obj)
        obj.show()
        self._grid.insert_row(self._row)
        self._grid.attach(align, 1, self._row, 5, 1)
        self._row += 1
        align.show()
        entry.set_text('')
        if not 'content' in self._reflection.data:
            self._reflection.data['content'] = []
        self._reflection.data['content'].append({'text': text})

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
        self._stars_align.hide()
        for align in self._content_aligns:
            if not align in self._content_we_always_show:
                align.hide()
        self._new_entry.hide()
        self._new_image.hide()
        for align in self._comment_aligns:
            align.hide()

class Reflection():
    ''' A class to hold a reflection '''

    def __init__(self, data):
        self.data = data  # dictionary entry for this reflection
        self.creation_data = None
        self.modification_data = None

    def set_title(self, title):
        self.data['title'] = title

    def set_creation_date(self):
        self.creation_date = time.time()

    def set_modification_date(self):
        self.modification_date = time.time()

    def add_tag(self, tag):
        ''' a #tag '''
        self.data['tags'].append(tag)

    def add_text(self, text):
        ''' simple text '''
        self.data['content'].append({'text': text})

    def add_comment(self, text):
        ''' simple text '''
        self.data['comments'].append(text)

    def add_image(self, image):
        ''' an image file pathname '''
        self.data['content'].append({'image': image})

    def add_activity(self, activity):
        ''' an activity icon '''
        self.data['activities'].append(activity)

    def search_tags(self, tag):
        return tag in self.data['tags']

    def add_activity(self, activity):
        self.data['activities'].append(activity)

    def set_stars(self, n):
        ''' # of stars to highlight '''
        if n < 0:
            n = 0
        elif n > 5:
            n = 5
        self.data['stars'] = n

    def get_graphics(self):
        ''' return resizable entry '''
        self._graphics = ReflectionGrid(self)
        return self._graphics

    def refresh(self):
        ''' redraw graphics with updated content '''
        self._graphics.set_size_request(REFLECTION_WIDTH, -1)
        self._graphics.show()
