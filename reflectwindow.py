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
from gi.repository import Pango

from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon, EventIcon
from sugar3 import profile
from sugar3 import util

import logging
_logger = logging.getLogger('reflect-window')

import utils
from graphics import Graphics

BUTTON_SIZE = 30
STAR_SIZE = 20
NUMBER_OF_STARS = 5
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
        self._title_button.connect('clicked', self._title_button_cb)
        button_grid.attach(self._title_button, 0, 0, 1, 1)
        self._title_button.show()

        self.date_button = Gtk.Button(_('Date'), name='next-button')
        self.date_button.connect('clicked', self._date_button_cb)
        button_grid.attach(self.date_button, 1, 0, 1, 1)
        self.date_button.show()

        self._stars_button = Gtk.Button(_('Stars'), name='next-button')
        self._stars_button.connect('clicked', self._stars_button_cb)
        button_grid.attach(self._stars_button, 2, 0, 1, 1)
        self._stars_button.show()

        # FIX ME: Need a tag to search on
        self._search_button = Gtk.Button(_('Search'), name='next-button')
        self._search_button.connect('clicked', self._search_button_cb)
        button_grid.attach(self._search_button, 3, 0, 1, 1)
        self._search_button.show()

        align.add(button_grid)
        button_grid.show()
        self._graphics_grid.attach(align, 1, 0, 1, 1)
        align.show()

    def _title_button_cb(self, button):
        ''' sort by title '''
        self._activity.busy_cursor()
        GObject.idle_add(self._title_sort)

    def _title_sort(self):
        sorted_data = sorted(self._activity.reflection_data,
                             key=lambda item: item['title'].lower())
        self._activity.reload_data(sorted_data)
        self._activity.reset_cursor()

    def _date_button_cb(self, button):
        ''' sort by modification date '''
        self._activity.busy_cursor()
        GObject.idle_add(self._date_sort)

    def _date_sort(self):
        sorted_data = sorted(self._activity.reflection_data,
                             key=lambda item: int(item['modification_time']),
                             reverse=True)
        self._activity.reload_data(sorted_data)
        self._activity.reset_cursor()

    def _stars_button_cb(self, button):
        ''' sort by number of stars '''
        self._activity.busy_cursor()
        GObject.idle_add(self._stars_sort)

    def _stars_sort(self):
        sorted_data = sorted(self._activity.reflection_data,
                             key=lambda item: item['stars'], reverse=True)
        self._activity.reload_data(sorted_data)
        self._activity.reset_cursor()

    def _search_button_cb(self, button):
        ''' search by #tag '''
        logging.debug('search button pressed')


class ReflectWindow(Gtk.Alignment):

    def __init__(self, activity):
        Gtk.Alignment.__init__(self)
        self._activity = activity
        self._reflections = []

        self.set_size_request(Gdk.Screen.width() - style.GRID_CELL_SIZE, -1)

        self._reflections_grid = Gtk.Grid()
        self._reflections_grid.set_row_spacing(style.DEFAULT_SPACING)
        self._reflections_grid.set_column_spacing(style.DEFAULT_SPACING)

        self.set(xalign=0.5, yalign=0, xscale=0, yscale=0)
        self.add(self._reflections_grid)
        self._reflections_grid.show()

        self._activity.load_graphics_area(self)

        if self._activity.initiating:
            entry = Gtk.Entry()
            entry.props.placeholder_text = _('Add a reflection')
            entry.connect('activate', self._entry_activate_cb)
            self._reflections_grid.attach(entry, 0, 0, 4, 1)
            entry.show()

    def reload(self, reflection_data):
        self.load(reflection_data)

    def load(self, reflection_data):
        if self._activity.initiating:
            row = 1  # 0 is the entry for new reflections
        else:
            row = 0

        for item in reflection_data:
            reflection = Reflection(self._activity, item)
            reflection.set_obj_id()
            self._reflections_grid.attach(
                reflection.get_graphics(), 0, row, 4, 1)
            reflection.refresh()
            self._reflections.append(reflection)
            row += 1

        # Add an empty box at the end to expand the scrolled window
        eb = Gtk.EventBox()
        eb.modify_bg(Gtk.StateType.NORMAL,
                     self._activity.bg_color.get_gdk_color())
        box = Gtk.Box()
        box.set_size_request(ENTRY_WIDTH, int(Gdk.Screen.height() / 2))
        eb.add(box)
        box.show()
        self._reflections_grid.attach(eb, 0, row, 4, 1)
        eb.show()

    def insert_comment(self, obj_id, comment):
        for item in self._reflections:
            if item.obj_id == obj_id:
                item.graphics.add_new_comment(comment)
                break

    def _entry_activate_cb(self, entry):
        text = entry.props.text
        self._activity.reflection_data.insert(0, {'title': text})
        reflection = Reflection(
            self._activity,
            self._activity.reflection_data[0])
        reflection.set_title(text)
        reflection.set_creation_time()
        reflection.set_obj_id(generate=True)
        reflection.add_activity(
            utils.bundle_id_to_icon('org.sugarlabs.Reflect'))
        reflection.set_stars(0)
        self._reflections_grid.insert_row(1)
        self._reflections_grid.attach(
            reflection.get_graphics(), 0, 1, 3, 1)
        reflection.refresh()
        self._reflections.append(reflection)
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
        self._title_color = self._reflection.activity.fg_color.get_html()

        self._grid = Gtk.Grid()
        self.add(self._grid)
        self._grid.show()

        self._grid.set_row_spacing(style.DEFAULT_PADDING)
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
        self._title = Gtk.TextView()
        self._title.set_size_request(ENTRY_WIDTH, -1)
        self._title.set_wrap_mode(Gtk.WrapMode.WORD)
        title_tag = self._title.get_buffer().create_tag(
            'title', foreground=self._title_color, weight=Pango.Weight.BOLD,
            size=12288)
        iter_text = self._title.get_buffer().get_iter_at_offset(0)
        self._title.get_buffer().insert_with_tags(
            iter_text, self._reflection.data['title'], title_tag)
        if self._reflection.activity.initiating:
            self._title.connect('focus-out-event', self._title_focus_out_cb)
        else:
            self._title.set_editable(False)
        self._title_align.add(self._title)
        self._title.show()
        self._grid.attach(self._title_align, 1, row, 5, 1)
        self._title_align.show()
        row += 1

        self._time_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        self._time = Gtk.Label()
        self._time.set_size_request(ENTRY_WIDTH, -1)
        self._time.set_justify(Gtk.Justification.LEFT)
        self._time.set_use_markup(True)
        try:
            time_string = util.timestamp_to_elapsed_string(
                int(self._reflection.data['modification_time']))
        except Exception as e:
            logging.error('Could not convert modification time %s: %s' %
                          (self._reflection.data['modification_time'], e))
            self._reflection.data['modification_time'] = \
                self._reflection.data['creation_time']
            time_string = util.timestamp_to_elapsed_string(
                int(self._reflection.data['modification_time']))
        self._time.set_markup(
            '<span foreground="#808080"><small><b>%s</b></small></span>' %
            time_string)
        self._time_align.add(self._time)
        self._time.show()
        self._grid.attach(self._time_align, 1, row, 5, 1)
        self._time_align.show()
        row += 1

        label = ''
        if 'tags' in self._reflection.data:
            for tag in self._reflection.data['tags']:
                if len(label) > 0:
                    label += ', '
                label += tag
        if self._reflection.activity.initiating and label == '':
            label = _('Add a #tag')
        self._tag_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        tag_view = Gtk.TextView()
        tag_view.set_size_request(ENTRY_WIDTH, -1)
        tag_view.set_wrap_mode(Gtk.WrapMode.WORD)
        tag_view.get_buffer().set_text(label)
        if self._reflection.activity.initiating:
            tag_view.get_buffer().connect('insert-text', self._insert_tag_cb)
            tag_view.connect('focus-in-event', self._tag_focus_in_cb,
                             _('Add a #tag'))
            tag_view.connect('focus-out-event', self._tags_focus_out_cb)
        else:
            tag_view.set_editable(False)
        self._tag_align.add(tag_view)
        tag_view.show()
        self._grid.attach(self._tag_align, 1, row, 5, 1)
        row += 1

        self._activities_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        self._make_activities_grid()
        self._grid.attach(self._activities_align, 1, row, 5, 1)
        self._activities_align.show()

        if self._reflection.activity.initiating:
            self._new_activity = EventIcon(icon_name='add-item',
                                           pixel_size=BUTTON_SIZE)
            self._new_activity.connect('button-press-event',
                                       self._activity_button_cb)
            self._grid.attach(self._new_activity, 6, row, 1, 1)
            self._new_activity.show()
        row += 1

        self._stars_align = Gtk.Alignment.new(
            xalign=0, yalign=0.5, xscale=0, yscale=0)
        grid = Gtk.Grid()
        if 'stars' in self._reflection.data:
            stars = self._reflection.data['stars']
        else:
            stars = 0
        self._star_icons = []
        for i in range(NUMBER_OF_STARS):
            if i < stars:
                icon_name = 'star-filled'
            else:
                icon_name = 'star-empty'
            self._star_icons.append(EventIcon(icon_name=icon_name,
                                              pixel_size=STAR_SIZE))
            if self._reflection.activity.initiating:
                self._star_icons[-1].connect('button-press-event',
                                             self._star_button_cb, i)
            grid.attach(self._star_icons[-1], i, 0, 1, 1)
            self._star_icons[-1].show()
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
                    if self._reflection.activity.initiating:
                        obj.connect('focus-in-event', self._text_focus_in_cb)
                        obj.connect(
                            'focus-out-event', self._text_focus_out_cb, i)
                    else:
                        obj.set_editable(False)
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

        self._row = row
        if self._reflection.activity.initiating:
            self._new_entry = Gtk.Entry()
            self._new_entry.props.placeholder_text = _('Write a reflection')
            self._new_entry.connect('activate', self._entry_activate_cb)
            self._grid.attach(self._new_entry, 1, row, 5, 1)
            self._content_we_always_show.append(self._new_entry)
            self._new_image = EventIcon(icon_name='add-picture',
                                        pixel_size=BUTTON_SIZE)
            self._new_image.connect('button-press-event', self._image_button_cb)
            self._grid.attach(self._new_image, 6, row, 1, 1)
            self._content_we_always_show.append(self._new_image)

        for align in self._content_we_always_show:
            align.show()
        row += 1

        self._comment_row = row
        self._comment_aligns = []
        if 'comments' in self._reflection.data:
            for comment in self._reflection.data['comments']:
                # TODO: Add icon
                obj = Gtk.TextView()
                obj.set_editable(False)
                obj.set_size_request(ENTRY_WIDTH, -1)
                obj.set_wrap_mode(Gtk.WrapMode.WORD)
                obj.get_buffer().set_text(comment)

                align = Gtk.Alignment.new(
                    xalign=0, yalign=0.5, xscale=0, yscale=0)
                align.add(obj)
                obj.show()
                self._grid.attach(align, 1, self._comment_row, 5, 1)
                self._comment_aligns.append(align)
                self._comment_row += 1
        self._new_comment = Gtk.Entry()
        self._new_comment.props.placeholder_text = _('Make a comment')
        self._new_comment.connect('activate', self._comment_activate_cb)
        self._grid.attach(self._new_comment, 1, self._comment_row, 5, 1)

    def _star_button_cb(self, button, event, n):
        if 'stars' in self._reflection.data:
            oldn = self._reflection.data['stars']
        else:
            oldn = 0
        if n < oldn:  # Erase stars, including one that was clicked
            for i in range(NUMBER_OF_STARS):
                if i < n:
                    icon_name = 'star-filled'
                else:
                    icon_name = 'star-empty'
                self._star_icons[i].set_icon_name(icon_name)
            self._reflection.data['stars'] = n
        else:  # Add stars, including one that was clicked
            for i in range(NUMBER_OF_STARS):
                if i <= n:
                    icon_name = 'star-filled'
                else:
                    icon_name = 'star-empty'
                self._star_icons[i].set_icon_name(icon_name)
            self._reflection.data['stars'] = n + 1
        self._reflection.set_modification_time()

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
        self._reflection.set_modification_time()

    def _title_focus_out_cb(self, widget, event):
        bounds = widget.get_buffer().get_bounds()
        text = widget.get_buffer().get_text(bounds[0], bounds[1], True)
        self._reflection.data['title'] = text
        self._reflection.set_modification_time()

    def _comment_activate_cb(self, entry):
        text = entry.props.text
        if not 'comments' in self._reflection.data:
            self._reflection.data['comments'] = []
        self._reflection.data['comments'].append(text)
        self.add_new_comment(text)
        # Send the comment
        if self._reflection.activity.sharing:
            self._reflection.activity.send_event(
                'c|%s|%s' % (self._reflection.data['obj_id'], text))
        entry.set_text('')

    def add_new_comment(self, text):
        obj = Gtk.TextView()
        obj.set_size_request(ENTRY_WIDTH, -1)
        obj.set_wrap_mode(Gtk.WrapMode.WORD)
        obj.get_buffer().set_text(text)
        align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
        align.add(obj)
        obj.show()
        self._grid.insert_row(self._comment_row)
        self._grid.attach(align, 1, self._comment_row, 5, 1)
        self._comment_row += 1
        align.show()

    def _entry_activate_cb(self, entry):
        text = entry.props.text
        if not 'content' in self._reflection.data:
            self._reflection.data['content'] = []
        self._reflection.data['content'].append({'text': text})
        self._reflection.set_modification_time()
        i = len(self._reflection.data['content'])
        obj = Gtk.TextView()
        obj.set_size_request(ENTRY_WIDTH, -1)
        obj.set_wrap_mode(Gtk.WrapMode.WORD)
        obj.get_buffer().set_text(text)
        obj.connect('focus-in-event', self._text_focus_in_cb)
        obj.connect('focus-out-event', self._text_focus_out_cb, i - 1)
        align = Gtk.Alignment.new(xalign=0, yalign=0.5, xscale=0, yscale=0)
        align.add(obj)
        obj.show()
        self._grid.insert_row(self._row)
        self._grid.attach(align, 1, self._row, 5, 1)
        self._row += 1
        align.show()
        entry.set_text('')

    def _activity_button_cb(self, button, event):
        self._reflection.activity.busy_cursor()
        GObject.idle_add(self._choose_activity)

    def _choose_activity(self):
        if not hasattr(self, '_activity_sw'):
            grid = Gtk.Grid()
            self._reflection.activity.load_overlay_area(grid)
            grid.show()

            bundle_icons = utils.get_bundle_icons()
            x = 0
            y = 0
            for bundle_id in bundle_icons.keys():
                icon_path = bundle_icons[bundle_id]
                if icon_path is None:
                    continue
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    icon_path, style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)
                image = Gtk.Image.new_from_pixbuf(pixbuf)
                button = Gtk.ToolButton()
                button.set_icon_widget(image)
                image.show()
                button.connect('clicked', self._insert_activity, bundle_id)
                grid.attach(button, x, y, 1, 1)
                button.show()
                x += 1
                if x > 6:
                    y += 1
                    x = 0
        self._reflection.activity.show_overlay_area()
        self._reflection.activity.reset_cursor()

    def _insert_activity(self, widget, bundle_id):
        logging.debug(bundle_id)
        # self._activity_sw.hide()
        self._reflection.activity.hide_overlay_area()

        if not 'activities' in self._reflection.data:
            self._reflection.data['activities'] = []
        self._reflection.data['activities'].append(
            utils.bundle_id_to_icon(bundle_id))
        self._reflection.set_modification_time()
        self._activities_align.remove(self._activities_grid)
        self._make_activities_grid()

    def _make_activities_grid(self):
        column = 0
        self._activities_grid = Gtk.Grid()
        self._activities = []
        if 'activities' in self._reflection.data:
            for icon_path in self._reflection.data['activities']:
                if icon_path is None:
                    continue
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        icon_path, BUTTON_SIZE, BUTTON_SIZE)
                except Exception as e:
                    logging.error('Could not find icon %s: %s' %
                                  (icon_path, e))
                    continue
                self._activities.append(Gtk.Image.new_from_pixbuf(pixbuf))
                self._activities_grid.attach(
                    self._activities[-1], column, 0, 1, 1)
                self._activities[-1].show()
                column += 1
        else:
            label = Gtk.Label('Add an activity')
            self._activities_grid.attach(label, 0, 0, 5, 1)
            label.show()
        self._activities_align.add(self._activities_grid)
        self._activities_grid.show()

    def _image_button_cb(self, button, event):
        self._reflection.activity.busy_cursor()
        GObject.idle_add(self._choose_image)

    def _choose_image(self):
        from sugar3.graphics.objectchooser import ObjectChooser
        try:
            from sugar3.graphics.objectchooser import FILTER_TYPE_GENERIC_MIME
        except:
            FILTER_TYPE_GENERIC_MIME = 'generic_mime'
        from sugar3 import mime

        chooser = None
        name = None

        if hasattr(mime, 'GENERIC_TYPE_IMAGE'):
            # See #2398
            if 'image/svg+xml' not in \
                    mime.get_generic_type(mime.GENERIC_TYPE_IMAGE).mime_types:
                mime.get_generic_type(
                    mime.GENERIC_TYPE_IMAGE).mime_types.append('image/svg+xml')
            try:
                chooser = ObjectChooser(parent=self._reflection.activity,
                                        what_filter=mime.GENERIC_TYPE_IMAGE,
                                        filter_type=FILTER_TYPE_GENERIC_MIME,
                                        show_preview=True)
            except:
                chooser = ObjectChooser(parent=self._reflection.activity,
                                        what_filter=mime.GENERIC_TYPE_IMAGE)
        else:
            try:
                chooser = ObjectChooser(parent=self, what_filter=None)
            except TypeError:
                chooser = ObjectChooser(
                    None, self._reflection.activity,
                    Gtk.DialogFlags.MODAL |
                    Gtk.DialogFlags.DESTROY_WITH_PARENT)

        if chooser is not None:
            try:
                result = chooser.run()
                if result == Gtk.ResponseType.ACCEPT:
                    jobject = chooser.get_selected_object()
                    if jobject and jobject.file_path:
                        name = jobject.metadata['title']
                        mime_type = jobject.metadata['mime_type']
                        _logger.debug('result of choose: %s (%s)' %
                                      (name, str(mime_type)))
            finally:
                chooser.destroy()
                del chooser

            if name is not None:
                obj = None
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        jobject.file_path, PICTURE_WIDTH, PICTURE_HEIGHT)
                    obj = Gtk.Image.new_from_pixbuf(pixbuf)
                except:
                    logging.error('could not open %s' % jobject.file_path)

                if obj is not None:
                    align = Gtk.Alignment.new(
                        xalign=0, yalign=0.5, xscale=0, yscale=0)
                    align.add(obj)
                    obj.show()
                    self._grid.insert_row(self._row)
                    self._grid.attach(align, 1, self._row, 5, 1)
                    self._row += 1
                    align.show()
                    if not 'content' in self._reflection.data:
                        self._reflection.data['content'] = []
                    self._reflection.data['content'].append(
                        {'image': jobject.file_path})
                    self._reflection.set_modification_time()

        self._reflection.activity.reset_cursor()

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
        for align in self._comment_aligns:
            align.show()
        self._new_comment.show()

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
        for align in self._comment_aligns:
            align.hide()
        self._new_comment.hide()

class Reflection():
    ''' A class to hold a reflection '''

    def __init__(self, activity, data):
        self.activity = activity
        self.data = data  # dictionary entry for this reflection
        self.creation_time = None
        self.modification_time = None
        self.obj_id = None

    def set_title(self, title):
        self.data['title'] = title

    def set_obj_id(self, generate=False):
        if generate:
            self.data['obj_id'] = 'obj-%d' % int(uniform(0, 10000))
        self.obj_id = self.data['obj_id']

    def set_creation_time(self):
        self.data['creation_time'] = int(time.time())
        if not 'modification_time' in self.data:
            self.data['modification_time'] = self.data['creation_time']

    def set_modification_time(self):
        self.data['modification_time'] = int(time.time())

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
        if not 'activities' in self.data:
            self.data['activities'] = []
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
        self.graphics = ReflectionGrid(self)
        return self.graphics

    def refresh(self):
        ''' redraw graphics with updated content '''
        self.graphics.set_size_request(REFLECTION_WIDTH, -1)
        self.graphics.show()
