# -*- coding: utf-8 -*-
#Copyright (c) 2014 Walter Bender

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# You should have received a copy of the GNU General Public License
# along with this library; if not, write to the Free Software
# Foundation, 51 Franklin Street, Suite 500 Boston, MA 02110-1335 USA

import dbus
import os
from ConfigParser import ConfigParser
from gettext import gettext as _

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import GConf

from gi.repository import SugarExt

from sugar3.activity import activity
from sugar3.activity.widgets import StopButton
from sugar3.activity.widgets import ActivityToolbarButton
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbarbox import ToolbarButton
from sugar3.graphics import style
from sugar3 import profile
from sugar3.datastore import datastore

from reflectwindow import ReflectButtons, ReflectWindow
from graphics import Graphics, FONT_SIZES
import utils

import logging
_logger = logging.getLogger('reflect-activity')


class ReflectActivity(activity.Activity):
    ''' An activity for reflecting on one's work '''

    def __init__(self, handle):
        ''' Initialize the toolbar '''
        try:
            super(ReflectActivity, self).__init__(handle)
        except dbus.exceptions.DBusException as e:
            _logger.error(str(e))

        self.connect('realize', self.__realize_cb)

        self.font_size = 8
        self.zoom_level = self.font_size / float(len(FONT_SIZES))
        _logger.debug('zoom level is %f' % self.zoom_level)

        self._setup_toolbars()

        color = profile.get_color()
        color_stroke = color.get_stroke_color()
        color_fill = color.get_fill_color()
        logging.debug(color_stroke)
        logging.debug(color_fill)

        lighter = utils.lighter_color([color_stroke, color_fill])
        darker = 1 - lighter

        if lighter == 0:
            bg_color = style.Color(color_stroke)
        else:
            bg_color = style.Color(color_fill)

        self.modify_bg(Gtk.StateType.NORMAL, bg_color.get_gdk_color())

        self.bundle_path = activity.get_bundle_path()
        self.tmp_path = os.path.join(activity.get_activity_root(), 'tmp')

        self._copy_entry = None
        self._paste_entry = None
        self._about_panel_visible = False
        self._webkit = None
        self._clipboard_text = ''
        self._fixed = None

        self._open_reflect_windows()

        self.busy_cursor()
        GObject.idle_add(self._load_reflections)

    def _load_reflections(self):
        self._reflection_data = [
            {'title': 'A fox tale',
             'stars': 3,
             'comments': ['Teacher says good work'],
             'content': [{'text': 'The quick brown fox'},
                         {'image': '/usr/share/art4apps/images/fox.png'},
                         {'text': 'jumped over the lazy dog.'},
                         {'image': '/usr/share/art4apps/images/dog.png'}],
             'activities': ['TurtleBlocks', 'Pippy'],
             'tags': ['#programming', '#art']},
            {'title': 'Fruit cake',
             'stars': 1,
             'comments': ['Teacher says needs more work'],
             'content': [{'text': 'An apple a day'},
                         {'image': '/usr/share/art4apps/images/apple.png'},
                         {'text': 'keeps the doctor away.'}],
             'activities': ['TurtleBlocks'],
             'tags': ['#programming', '#art']}
            ]

        self._find_starred()
        self._reflect_window.load(self._reflection_data)
        self.reset_cursor()

    def _found_obj_id(self, obj_id):
        for item in self._reflection_data:
            if 'obj_id' in item and item['obj_id'] == obj_id:
                return True
        return False

    def _find_starred(self):
        ''' Find all the _stars in the Journal. '''
        self.dsobjects, self._nobjects = datastore.find({'keep': '1'})
        for dsobj in self.dsobjects:
            if self._found_obj_id(dsobj.object_id):
                continue  # Already have this object -- TODO: update it
            self._reflection_data.append({
                'title': _('Untitled'), 'obj_id': dsobj.object_id})
            if hasattr(dsobj, 'metadata'):
                if 'title' in dsobj.metadata:
                    self._reflection_data[-1]['title'] = \
                        dsobj.metadata['title']
                if 'description' in dsobj.metadata:
                    self._reflection_data[-1]['content'] = \
                        [{'text': dsobj.metadata['description']}]
                else:
                    self._reflection_data[-1]['content'] = []
                '''
                if 'comments' in dsobj.metadata:
                    try:
                        comment = json.loads(dsobj.metadata['comments'])
                        _logger.debug(comment)
                    except:
                        comment = []
                '''
                if 'mime_type' in dsobj.metadata and \
                   dsobj.metadata['mime_type'][0:5] == 'image':
                    self._reflection_data[-1]['content'].append(
                        {'image': dsobj.file_path})
                elif 'preview' in dsobj.metadata:
                    pixbuf = utils.get_pixbuf_from_journal(dsobj, 300, 225)
                    if pixbuf is not None:
                        path = os.path.join(self.tmp_path,
                                            dsobj.object_id + '.png')
                        utils.save_pixbuf_to_file(pixbuf, path)
                        self._reflection_data[-1]['content'].append(
                            {'image': path})

    def busy_cursor(self):
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))

    def reset_cursor(self):
        self.get_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.LEFT_PTR))

    def _open_reflect_windows(self):
        # Most things need only be done once
        if self._fixed is None:
            self._fixed = Gtk.Fixed()
            self._fixed.set_size_request(Gdk.Screen.width(),
                                         Gdk.Screen.height())

            # Offsets from the bottom of the screen
            dy1 = 2 * style.GRID_CELL_SIZE
            dy2 = 1 * style.GRID_CELL_SIZE

            self._button_area = Gtk.Alignment.new(0.5, 0, 0, 0)
            self._button_area.set_size_request(Gdk.Screen.width(),
                                               style.GRID_CELL_SIZE)
            self._fixed.put(self._button_area, 0, 0)
            self._button_area.show()

            self._scrolled_window = Gtk.ScrolledWindow()
            self._scrolled_window.set_size_request(
                Gdk.Screen.width(), Gdk.Screen.height() - dy1)
            self._set_scroll_policy()
            self._graphics_area = Gtk.Alignment.new(0.5, 0, 0, 0)
            self._scrolled_window.add_with_viewport(self._graphics_area)
            self._graphics_area.show()
            self._fixed.put(self._scrolled_window, 0, dy2)
            self._scrolled_window.show()

            self._reflect_buttons = ReflectButtons(self)
            self._reflect_buttons.show()

            self._reflect_window = ReflectWindow(self)
            self._reflect_window.show()

            Gdk.Screen.get_default().connect('size-changed',
                                             self._configure_cb)
            self._toolbox.connect('hide', self._resize_hide_cb)
            self._toolbox.connect('show', self._resize_show_cb)

            self._reflect_window.set_events(Gdk.EventMask.KEY_PRESS_MASK)
            self._reflect_window.connect('key_press_event',
                                      self._reflect_window.keypress_cb)
            self._reflect_window.set_can_focus(True)
            self._reflect_window.grab_focus()

        self.set_canvas(self._fixed)
        self._fixed.show()

    def reset_scrolled_window_adjustments(self):
        adj = self._scrolled_window.get_hadjustment()
        if adj is not None:
            adj.set_value(0)
        adj = self._scrolled_window.get_vadjustment()
        if adj is not None:
            adj.set_value(0)

    def load_graphics_area(self, widget):
        self._graphics_area.add(widget)

    def load_button_area(self, widget):
        self._button_area.add(widget)

    def _load_intro_graphics(self, file_name='generic-problem.html',
                             message=None):
        center_in_panel = Gtk.Alignment.new(0.5, 0, 0, 0)
        url = os.path.join(self.bundle_path, 'html-content', file_name)
        graphics = Graphics()
        if message is None:
            graphics.add_uri('file://' + url)
        else:
            graphics.add_uri('file://' + url + '?MSG=' +
                             utils.get_safe_text(message))
        graphics.set_zoom_level(0.667)
        center_in_panel.add(graphics)
        graphics.show()
        self.set_canvas(center_in_panel)
        center_in_panel.show()

    def _resize_hide_cb(self, widget):
        self._resize_canvas(widget, True)

    def _resize_show_cb(self, widget):
        self._resize_canvas(widget, False)

    def _configure_cb(self, event):
        self._fixed.set_size_request(Gdk.Screen.width(), Gdk.Screen.height())
        self._set_scroll_policy()
        self._resize_canvas(None)
        self._reflect_window.reload_graphics()

    def _resize_canvas(self, widget, fullscreen=False):
        # When a toolbar is expanded or collapsed, resize the canvas
        if hasattr(self, '_reflect_window'):
            if self.toolbar_expanded():
                dy1 = 3 * style.GRID_CELL_SIZE
                dy2 = 2 * style.GRID_CELL_SIZE
            else:
                dy1 = 2 * style.GRID_CELL_SIZE
                dy2 = 1 * style.GRID_CELL_SIZE

            if fullscreen:
                dy1 -= 2 * style.GRID_CELL_SIZE
                dy2 -= 2 * style.GRID_CELL_SIZE

            self._scrolled_window.set_size_request(
                Gdk.Screen.width(), Gdk.Screen.height() - dy2)
            self._fixed.move(self._button_area, 0, 0)

        self._about_panel_visible = False

    def toolbar_expanded(self):
        if self.activity_button.is_expanded():
            return True
        elif self.edit_toolbar_button.is_expanded():
            return True
        elif self.view_toolbar_button.is_expanded():
            return True
        return False

    def get_activity_version(self):
        info_path = os.path.join(self.bundle_path, 'activity', 'activity.info')
        try:
            info_file = open(info_path, 'r')
        except Exception as e:
            _logger.error('Could not open %s: %s' % (info_path, e))
            return 'unknown'

        cp = ConfigParser()
        cp.readfp(info_file)

        section = 'Activity'

        if cp.has_option(section, 'activity_version'):
            activity_version = cp.get(section, 'activity_version')
        else:
            activity_version = 'unknown'
        return activity_version

    def get_uid(self):
        if len(self.volume_data) == 1:
            return self.volume_data[0]['uid']
        else:
            return 'unknown'

    def write_file(self, file_path):
        self.metadata['font_size'] = str(self.font_size)

    def _setup_toolbars(self):
        ''' Setup the toolbars. '''
        self.max_participants = 1  # No sharing

        self._toolbox = ToolbarBox()

        self.activity_button = ActivityToolbarButton(self)
        self.activity_button.connect('clicked', self._resize_canvas)
        self._toolbox.toolbar.insert(self.activity_button, 0)
        self.activity_button.show()

        self.set_toolbar_box(self._toolbox)
        self._toolbox.show()
        self.toolbar = self._toolbox.toolbar

        view_toolbar = Gtk.Toolbar()
        self.view_toolbar_button = ToolbarButton(
            page=view_toolbar,
            label=_('View'),
            icon_name='toolbar-view')
        self.view_toolbar_button.connect('clicked', self._resize_canvas)
        self._toolbox.toolbar.insert(self.view_toolbar_button, 1)
        view_toolbar.show()
        self.view_toolbar_button.show()

        button = ToolButton('view-fullscreen')
        button.set_tooltip(_('Fullscreen'))
        button.props.accelerator = '<Alt>Return'
        view_toolbar.insert(button, -1)
        button.show()
        button.connect('clicked', self._fullscreen_cb)

        self._zoom_in = ToolButton('zoom-in')
        self._zoom_in.set_tooltip(_('Increase size'))
        view_toolbar.insert(self._zoom_in, -1)
        self._zoom_in.show()
        self._zoom_in.connect('clicked', self._zoom_in_cb)

        self._zoom_out = ToolButton('zoom-out')
        self._zoom_out.set_tooltip(_('Decrease size'))
        view_toolbar.insert(self._zoom_out, -1)
        self._zoom_out.show()
        self._zoom_out.connect('clicked', self._zoom_out_cb)

        self._zoom_eq = ToolButton('zoom-original')
        self._zoom_eq.set_tooltip(_('Restore original size'))
        view_toolbar.insert(self._zoom_eq, -1)
        self._zoom_eq.show()
        self._zoom_eq.connect('clicked', self._zoom_eq_cb)

        self._set_zoom_buttons_sensitivity()

        edit_toolbar = Gtk.Toolbar()
        self.edit_toolbar_button = ToolbarButton(
            page=edit_toolbar,
            label=_('Edit'),
            icon_name='toolbar-edit')
        self.edit_toolbar_button.connect('clicked', self._resize_canvas)
        self._toolbox.toolbar.insert(self.edit_toolbar_button, 1)
        edit_toolbar.show()
        self.edit_toolbar_button.show()

        self._copy_button = ToolButton('edit-copy')
        self._copy_button.set_tooltip(_('Copy'))
        self._copy_button.props.accelerator = '<Ctrl>C'
        edit_toolbar.insert(self._copy_button, -1)
        self._copy_button.show()
        self._copy_button.connect('clicked', self._copy_cb)
        self._copy_button.set_sensitive(False)

        self._paste_button = ToolButton('edit-paste')
        self._paste_button.set_tooltip(_('Paste'))
        self._paste_button.props.accelerator = '<Ctrl>V'
        edit_toolbar.insert(self._paste_button, -1)
        self._paste_button.show()
        self._paste_button.connect('clicked', self._paste_cb)
        self._paste_button.set_sensitive(False)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self._toolbox.toolbar.insert(separator, -1)
        separator.show()

        stop_button = StopButton(self)
        stop_button.props.accelerator = '<Ctrl>q'
        self._toolbox.toolbar.insert(stop_button, -1)
        stop_button.show()

    def __realize_cb(self, window):
        self.window_xid = window.get_window().get_xid()

    def set_copy_widget(self, webkit=None, text_entry=None):
        # Each task is responsible for setting a widget for copy
        if webkit is not None:
            self._webkit = webkit
        else:
            self._webkit = None
        if text_entry is not None:
            self._copy_entry = text_entry
        else:
            self._copy_entry = None

        self._copy_button.set_sensitive(webkit is not None or
                                        text_entry is not None)

    def _copy_cb(self, button):
        if self._copy_entry is not None:
            self._copy_entry.copy_clipboard()
        elif self._webkit is not None:
            self._webkit.copy_clipboard()
        else:
            _logger.debug('No widget set for copy.')

    def set_paste_widget(self, text_entry=None):
        # Each task is responsible for setting a widget for paste
        if text_entry is not None:
            self._paste_entry = text_entry
        self._paste_button.set_sensitive(text_entry is not None)

    def _paste_cb(self, button):
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self.clipboard_text = clipboard.wait_for_text()
        if self._paste_entry is not None:
            self._paste_entry.paste_clipboard()
        else:
            _logger.debug('No widget set for paste (%s).' %
                          self.clipboard_text)

    def _fullscreen_cb(self, button):
        ''' Hide the Sugar toolbars. '''
        self.fullscreen()

    def _set_zoom_buttons_sensitivity(self):
        if self.font_size < len(FONT_SIZES) - 1:
            self._zoom_in.set_sensitive(True)
        else:
            self._zoom_in.set_sensitive(False)
        if self.font_size > 0:
            self._zoom_out.set_sensitive(True)
        else:
            self._zoom_out.set_sensitive(False)

        if hasattr(self, '_scrolled_window'):
            self._set_scroll_policy()

    def _set_scroll_policy(self):
        if Gdk.Screen.width() < Gdk.Screen.height() or self.zoom_level > 0.667:
            self._scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                             Gtk.PolicyType.AUTOMATIC)
        else:
            self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                             Gtk.PolicyType.AUTOMATIC)

    def _zoom_eq_cb(self, button):
        self.font_size = 8
        self.zoom_level = 0.667
        self._set_zoom_buttons_sensitivity()
        self._reflect_window.reload_graphics()

    def _zoom_in_cb(self, button):
        if self.font_size < len(FONT_SIZES) - 1:
            self.font_size += 1
            self.zoom_level *= 1.1
        self._set_zoom_buttons_sensitivity()
        self._reflect_window.reload_graphics()

    def _zoom_out_cb(self, button):
        if self.font_size > 0:
            self.font_size -= 1
            self.zoom_level /= 1.1
        self._set_zoom_buttons_sensitivity()
        self._reflect_window.reload_graphics()

    def _remove_alert_cb(self, alert, response_id):
        self.remove_alert(alert)

    def _close_alert_cb(self, alert, response_id):
        self.remove_alert(alert)
        if response_id is Gtk.ResponseType.OK:
            self.close()
