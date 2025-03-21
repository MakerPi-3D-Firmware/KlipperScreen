# -*- coding: utf-8 -*-
import contextlib
import gi
import logging
import os
import pathlib

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, Gio, Gtk, Pango


class KlippyGtk:
    labels = {}
    width_ratio = 16
    height_ratio = 9.375

    def __init__(self, screen, width, height, theme, cursor, fontsize_type):
        self.screen = screen
        self.width = width
        self.height = height
        self.themedir = os.path.join(pathlib.Path(__file__).parent.resolve().parent, "styles", theme, "images")

        self.font_ratio = [33, 49] if self.screen.vertical_mode else [43, 29]
        self.font_size = int(min(
            self.width / self.font_ratio[0],
            self.height / self.font_ratio[1]
        ))
        if fontsize_type == "small":
            self.font_size = round(self.font_size * 0.91)
        elif fontsize_type == "large":
            self.font_size = round(self.font_size * 1.09)
        self.header_size = int(round((self.width / self.width_ratio) / 1.33))
        self.titlebar_height = self.font_size * 2
        self.img_width = int(round(self.width / self.width_ratio))
        self.img_height = int(round(self.height / self.height_ratio))
        if self.screen.vertical_mode:
            self.action_bar_width = int(self.width)
            self.action_bar_height = int(self.height * .1)
        else:
            self.action_bar_width = int(self.width * .1)
            self.action_bar_height = int(self.height)
        self.cursor = cursor

        self.color_list = {}  # This is set by screen.py init_style()

        for key in self.color_list:
            if "base" in self.color_list[key]:
                rgb = [int(self.color_list[key]['base'][i:i + 2], 16) for i in range(0, 6, 2)]
                self.color_list[key]['rgb'] = rgb

        logging.debug(f"img width: {self.img_width} height: {self.img_height}")

    def get_action_bar_width(self):
        return self.action_bar_width

    def get_action_bar_height(self):
        return self.action_bar_height

    def get_content_width(self):
        return self.width - self.action_bar_width

    def get_content_height(self):
        if self.screen.vertical_mode:
            return self.height - self.titlebar_height - self.action_bar_height
        else:
            return self.height - self.titlebar_height

    def get_font_size(self):
        return self.font_size

    def get_titlebar_height(self):
        return self.titlebar_height

    def get_header_size(self):
        return self.header_size

    def get_image_width(self):
        return self.img_width

    def get_image_height(self):
        return self.img_height

    def get_keyboard_height(self):
        if (self.height / self.width) >= 3:
            # Ultra-tall
            return self.get_content_height() * 0.25
        else:
            return self.get_content_height() * 0.5

    def get_temp_color(self, device):
        # logging.debug("Color list %s" % self.color_list)
        if device not in self.color_list:
            return False, False

        if 'base' in self.color_list[device]:
            rgb = self.color_list[device]['rgb'].copy()
            if self.color_list[device]['state'] > 0:
                rgb[1] = rgb[1] + self.color_list[device]['hsplit'] * self.color_list[device]['state']
            self.color_list[device]['state'] += 1
            rgb = [x / 255 for x in rgb]
            # logging.debug(f"Assigning color: {device} {rgb}")
        else:
            colors = self.color_list[device]['colors']
            if self.color_list[device]['state'] >= len(colors):
                self.color_list[device]['state'] = 0
            color = colors[self.color_list[device]['state'] % len(colors)]
            rgb = [int(color[i:i + 2], 16) / 255 for i in range(0, 6, 2)]
            self.color_list[device]['state'] += 1
            # logging.debug(f"Assigning color: {device} {rgb} {color}")
        return rgb

    def reset_temp_color(self):
        for key in self.color_list:
            self.color_list[key]['state'] = 0

    @staticmethod
    def Label(label, style=None):
        la = Gtk.Label(label)
        if style is not None:
            la.get_style_context().add_class(style)
        return la

    def Image(self, image_name, scale=1.0):
        filename = os.path.join(self.themedir, f"{image_name}.svg")
        if os.path.exists(filename):
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(filename,
                                                             int(round(self.img_width * scale)),
                                                             int(round(self.img_height * scale)),
                                                             True)
            return Gtk.Image.new_from_pixbuf(pixbuf)
        else:
            logging.error(f"Unable to find image {filename}")
            return Gtk.Image()

    def PixbufFromFile(self, filename, width_scale=1, height_scale=1):
        return GdkPixbuf.Pixbuf.new_from_file_at_scale(
            filename,
            int(round(self.img_width * width_scale)),
            int(round(self.img_height * height_scale)),
            True
        )

    def PixbufFromHttp(self, resource, width_scale=1, height_scale=1):
        response = self.screen.apiclient.get_thumbnail_stream(resource)
        if response is False:
            return None
        stream = Gio.MemoryInputStream.new_from_data(response, None)
        return GdkPixbuf.Pixbuf.new_from_stream_at_scale(
            stream,
            int(round(self.img_width * width_scale)),
            int(round(self.img_height * height_scale)),
            True
        )

    def Button(self, label=None, style=None):
        b = Gtk.Button(label=label)
        b.set_hexpand(True)
        b.set_vexpand(True)
        b.set_can_focus(False)
        b.props.relief = Gtk.ReliefStyle.NONE

        if style is not None:
            b.get_style_context().add_class(style)
        b.connect("clicked", self.screen.reset_screensaver_timeout)
        return b

    def ButtonImage(self, image_name=None, label=None, style=None, scale=1.38,
                    position=Gtk.PositionType.TOP, word_wrap=True):

        b = Gtk.Button(label=label)
        b.set_hexpand(True)
        b.set_vexpand(True)
        b.set_can_focus(False)
        if image_name is not None:
            b.set_image(self.Image(image_name, scale))
        b.set_image_position(position)
        b.set_always_show_image(True)

        if word_wrap is True:
            with contextlib.suppress(Exception):
                # Get the label object
                child = b.get_children()[0].get_children()[0].get_children()[1]
                child.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
                child.set_line_wrap(True)
        if style is not None:
            b.get_style_context().add_class(style)
        b.connect("clicked", self.screen.reset_screensaver_timeout)
        return b

    def Dialog(self, screen, buttons, content, callback=None, *args):
        dialog = Gtk.Dialog()
        dialog.set_default_size(screen.width, screen.height)
        dialog.set_resizable(False)
        dialog.set_transient_for(screen)
        dialog.set_modal(True)

        for i, button in enumerate(buttons):
            dialog.add_button(button_text=button['name'], response_id=button['response'])
            button = dialog.get_children()[0].get_children()[0].get_children()[0].get_children()[i]
            button.get_child().set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
            button.get_child().set_line_wrap(True)
            button.set_size_request((screen.width - 30) / 3, screen.height / 5)

        dialog.connect("response", callback, *args)
        dialog.get_style_context().add_class("dialog")

        content_area = dialog.get_content_area()
        content_area.set_margin_start(15)
        content_area.set_margin_end(15)
        content_area.set_margin_top(15)
        content_area.set_margin_bottom(15)
        content_area.add(content)

        dialog.show_all()
        # Change cursor to blank
        if self.cursor:
            dialog.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.ARROW))
        else:
            dialog.get_window().set_cursor(Gdk.Cursor(Gdk.CursorType.BLANK_CURSOR))

        self.screen.dialogs.append(dialog)
        return dialog

    def ToggleButtonImage(self, image_name, label, style=None, scale=1.38):

        b = Gtk.ToggleButton(label=label)
        b.set_hexpand(True)
        b.set_vexpand(True)
        b.set_can_focus(False)
        b.set_image(self.Image(image_name, scale))
        b.set_image_position(Gtk.PositionType.TOP)
        b.set_always_show_image(True)

        if style is not None:
            ctx = b.get_style_context()
            ctx.add_class(style)

        b.connect("clicked", self.screen.reset_screensaver_timeout)
        return b

    @staticmethod
    def HomogeneousGrid(width=None, height=None):
        g = Gtk.Grid()
        g.set_row_homogeneous(True)
        g.set_column_homogeneous(True)
        if width is not None and height is not None:
            g.set_size_request(width, height)
        return g

    def ToggleButton(self, text):
        b = Gtk.ToggleButton(text)
        b.props.relief = Gtk.ReliefStyle.NONE
        b.set_hexpand(True)
        b.set_vexpand(True)
        b.connect("clicked", self.screen.reset_screensaver_timeout)
        return b

    @staticmethod
    def ScrolledWindow():
        scroll = Gtk.ScrolledWindow()
        scroll.set_property("overlay-scrolling", False)
        scroll.set_vexpand(True)
        scroll.add_events(Gdk.EventMask.TOUCH_MASK)
        scroll.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        return scroll
