import gi
import logging
import re

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.KlippyGcodes import KlippyGcodes
from ks_includes.screen_panel import ScreenPanel


def create_panel(*args):
    return FineTunePanel(*args)


class FineTunePanel(ScreenPanel):
    user_selecting = False

    bs = 0
    bs_delta = "0.05"
    bs_deltas = ["0.01", "0.05"]
    percent_delta = 1
    percent_deltas = ['1', '5', '10', '25']
    extrusion = 100
    speed = 100

    def initialize(self, panel_name):

        logging.debug("FineTunePanel")

        print_cfg = self._config.get_printer_config(self._screen.connected_printer)
        if print_cfg is not None:
            bs = print_cfg.get("z_babystep_values", "0.01, 0.05")
            if re.match(r'^[0-9,\.\s]+$', bs):
                bs = [str(i.strip()) for i in bs.split(',')]
                self.bs_deltas = bs if len(bs) <= 2 else [bs[0], bs[-1]]
                self.bs_delta = self.bs_deltas[0]

        # babystepping grid
        bsgrid = Gtk.Grid()
        for j, i in enumerate(self.bs_deltas):
            self.labels[i] = self._gtk.ToggleButton(i)
            self.labels[i].connect("clicked", self.change_bs_delta, i)
            ctx = self.labels[i].get_style_context()
            if j == 0:
                ctx.add_class("distbutton_top")
            elif j == len(self.bs_deltas) - 1:
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if i == self.bs_delta:
                ctx.add_class("distbutton_active")
            bsgrid.attach(self.labels[i], j, 0, 1, 1)
        # Grid for percentage
        deltgrid = Gtk.Grid()
        for j, i in enumerate(self.percent_deltas):
            self.labels[i] = self._gtk.ToggleButton(f"{i}%")
            self.labels[i].connect("clicked", self.change_percent_delta, i)
            ctx = self.labels[i].get_style_context()
            if j == 0:
                ctx.add_class("distbutton_top")
            elif j == len(self.percent_deltas) - 1:
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if i == "1":
                ctx.add_class("distbutton_active")
            deltgrid.attach(self.labels[i], j, 0, 1, 1)
        self.labels["1"].set_active(True)

        grid = self._gtk.HomogeneousGrid()
        grid.set_row_homogeneous(False)
        if self._screen.vertical_mode:
            self.labels['x+'] = self._gtk.ButtonImage("arrow-right", _("X+"), "color2")
            self.labels['x-'] = self._gtk.ButtonImage("arrow-left", _("X-"), "color2")
            self.labels['xoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color2", .6, Gtk.PositionType.LEFT, False)

            self.labels['y+'] = self._gtk.ButtonImage("arrow-up", _("Y+"), "color5")
            self.labels['y-'] = self._gtk.ButtonImage("arrow-down", _("Y-"), "color5")
            self.labels['yoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color5", .6, Gtk.PositionType.LEFT, False)

            self.labels['z+'] = self._gtk.ButtonImage("z-farther", _("Z+"), "color1")
            self.labels['z-'] = self._gtk.ButtonImage("z-closer", _("Z-"), "color1")
            self.labels['zoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color1", .6, Gtk.PositionType.LEFT, False)

            self.labels['speed+'] = self._gtk.ButtonImage("speed+", _("Speed +"), "color3")
            self.labels['speed-'] = self._gtk.ButtonImage("speed-", _("Speed -"), "color3")
            self.labels['speedfactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                               "color3", .6, Gtk.PositionType.LEFT, False)

            self.labels['extrude+'] = self._gtk.ButtonImage("flow+", _("Extrusion +"), "color4")
            self.labels['extrude-'] = self._gtk.ButtonImage("flow-", _("Extrusion -"), "color4")
            self.labels['extrudefactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                                 "color4", .6, Gtk.PositionType.LEFT, False)

            grid.attach(self.labels['z+'], 0, 0, 1, 1)
            grid.attach(self.labels['z-'], 1, 0, 1, 1)
            grid.attach(self.labels['zoffset'], 2, 0, 1, 1)

            grid.attach(self.labels['x+'], 0, 1, 1, 1)
            grid.attach(self.labels['x-'], 1, 1, 1, 1)
            grid.attach(self.labels['xoffset'], 2, 1, 1, 1)

            grid.attach(self.labels['y+'], 0, 2, 1, 1)
            grid.attach(self.labels['y-'], 1, 2, 1, 1)
            grid.attach(self.labels['yoffset'], 2, 2, 1, 1)
            grid.attach(bsgrid, 0, 3, 3, 1)

            grid.attach(self.labels['speed-'], 0, 4, 1, 1)
            grid.attach(self.labels['speed+'], 1, 4, 1, 1)
            grid.attach(self.labels['speedfactor'], 2, 4, 1, 1)

            grid.attach(self.labels['extrude-'], 0, 5, 1, 1)
            grid.attach(self.labels['extrude+'], 1, 5, 1, 1)
            grid.attach(self.labels['extrudefactor'], 2, 5, 1, 1)
            grid.attach(deltgrid, 0, 6, 3, 1)
        else:
            self.labels['x+'] = self._gtk.ButtonImage("arrow-right", _("X+"), "color2")
            self.labels['xoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color2", .6, Gtk.PositionType.LEFT, False)
            self.labels['x-'] = self._gtk.ButtonImage("arrow-left", _("X-"), "color2")

            self.labels['y+'] = self._gtk.ButtonImage("arrow-up", _("Y+"), "color5")
            self.labels['yoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color5", .6, Gtk.PositionType.LEFT, False)
            self.labels['y-'] = self._gtk.ButtonImage("arrow-down", _("Y-"), "color5")

            self.labels['z+'] = self._gtk.ButtonImage("z-farther", _("Z+"), "color1")
            self.labels['zoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color1", .6, Gtk.PositionType.LEFT, False)
            self.labels['z-'] = self._gtk.ButtonImage("z-closer", _("Z-"), "color1")

            self.labels['speed+'] = self._gtk.ButtonImage("speed+", _("Speed +"), "color3")
            self.labels['speedfactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                               "color3", .6, Gtk.PositionType.LEFT, False)
            self.labels['speed-'] = self._gtk.ButtonImage("speed-", _("Speed -"), "color3")

            self.labels['extrude+'] = self._gtk.ButtonImage("flow+", _("Extrusion +"), "color4")
            self.labels['extrudefactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                                 "color4", .6, Gtk.PositionType.LEFT, False)
            self.labels['extrude-'] = self._gtk.ButtonImage("flow-", _("Extrusion -"), "color4")

            grid.attach(self.labels['xoffset'], 0, 0, 1, 1)
            grid.attach(self.labels['x+'], 0, 1, 1, 1)
            grid.attach(self.labels['x-'], 0, 2, 1, 1)

            grid.attach(self.labels['yoffset'], 1, 0, 1, 1)
            grid.attach(self.labels['y+'], 1, 1, 1, 1)
            grid.attach(self.labels['y-'], 1, 2, 1, 1)

            grid.attach(self.labels['zoffset'], 2, 0, 1, 1)
            grid.attach(self.labels['z+'], 2, 1, 1, 1)
            grid.attach(self.labels['z-'], 2, 2, 1, 1)
            grid.attach(bsgrid, 0, 3, 3, 1)

            grid.attach(self.labels['speedfactor'], 3, 0, 1, 1)
            grid.attach(self.labels['speed+'], 3, 1, 1, 1)
            grid.attach(self.labels['speed-'], 3, 2, 1, 1)

            grid.attach(self.labels['extrudefactor'], 4, 0, 1, 1)
            grid.attach(self.labels['extrude+'], 4, 1, 1, 1)
            grid.attach(self.labels['extrude-'], 4, 2, 1, 1)
            grid.attach(deltgrid, 3, 3, 2, 1)

        self.labels['x+'].connect("clicked", self.change_babystepping_x, "+")
        self.labels['xoffset'].connect("clicked", self.change_babystepping_x, "reset")
        self.labels['x-'].connect("clicked", self.change_babystepping_x, "-")

        self.labels['y+'].connect("clicked", self.change_babystepping_y, "+")
        self.labels['yoffset'].connect("clicked", self.change_babystepping_y, "reset")
        self.labels['y-'].connect("clicked", self.change_babystepping_y, "-")

        self.labels['z+'].connect("clicked", self.change_babystepping_z, "+")
        self.labels['zoffset'].connect("clicked", self.change_babystepping_z, "reset")
        self.labels['z-'].connect("clicked", self.change_babystepping_z, "-")

        self.labels['speed+'].connect("clicked", self.change_speed, "+")
        self.labels['speedfactor'].connect("clicked", self.change_speed, "reset")
        self.labels['speed-'].connect("clicked", self.change_speed, "-")
        
        self.labels['extrude+'].connect("clicked", self.change_extrusion, "+")
        self.labels['extrudefactor'].connect("clicked", self.change_extrusion, "reset")
        self.labels['extrude-'].connect("clicked", self.change_extrusion, "-")

        self.content.add(grid)

    def process_update(self, action, data):

        if action != "notify_status_update":
            return

        if "gcode_move" in data:
            if "homing_origin" in data["gcode_move"]:
                self.labels['zoffset'].set_label(f'  {data["gcode_move"]["homing_origin"][2]:.2f}mm')
            if "homing_origin" in data["gcode_move"]:
                self.labels['xoffset'].set_label(f'  {data["gcode_move"]["homing_origin"][0]:.2f}mm')
            if "homing_origin" in data["gcode_move"]:
                self.labels['yoffset'].set_label(f'  {data["gcode_move"]["homing_origin"][1]:.2f}mm')
            if "extrude_factor" in data["gcode_move"]:
                self.extrusion = int(round(data["gcode_move"]["extrude_factor"] * 100))
                self.labels['extrudefactor'].set_label(f"  {self.extrusion:3}%")
            if "speed_factor" in data["gcode_move"]:
                self.speed = int(round(data["gcode_move"]["speed_factor"] * 100))
                self.labels['speedfactor'].set_label(f"  {self.speed:3}%")

    def change_babystepping_x(self, widget, direction):
        if direction == "reset":
            self._screen._ws.klippy.gcode_script("SET_GCODE_E1OFFSET X=0 MOVE=1")
        elif direction in ["+", "-"]:
            self._screen._ws.klippy.gcode_script(f"SET_GCODE_E1OFFSET X_ADJUST={direction}{self.bs_delta} MOVE=1")

    def change_babystepping_y(self, widget, direction):
        if direction == "reset":
            self._screen._ws.klippy.gcode_script("SET_GCODE_E1OFFSET Y=0 MOVE=1")
        elif direction in ["+", "-"]:
            self._screen._ws.klippy.gcode_script(f"SET_GCODE_E1OFFSET Y_ADJUST={direction}{self.bs_delta} MOVE=1")

    def change_babystepping_z(self, widget, direction):
        if direction == "reset":
            self._screen._ws.klippy.gcode_script("SET_GCODE_E1OFFSET Z=0 MOVE=1")
        elif direction in ["+", "-"]:
            self._screen._ws.klippy.gcode_script(f"SET_GCODE_E1OFFSET Z_ADJUST={direction}{self.bs_delta} MOVE=1")

    def change_bs_delta(self, widget, bs):
        if self.bs_delta == bs:
            return
        logging.info(f"### BabyStepping {bs}")

        ctx = self.labels[f"{self.bs_delta}"].get_style_context()
        ctx.remove_class("distbutton_active")

        self.bs_delta = bs
        ctx = self.labels[self.bs_delta].get_style_context()
        ctx.add_class("distbutton_active")
        for i in self.bs_deltas:
            if i == self.bs_delta:
                continue
            self.labels[i].set_active(False)

    def change_extrusion(self, widget, direction):
        if direction == "+":
            self.extrusion += int(self.percent_delta)
        elif direction == "-":
            self.extrusion -= int(self.percent_delta)
        elif direction == "reset":
            self.extrusion = 100

        self.extrusion = max(self.extrusion, 1)
        self._screen._ws.klippy.gcode_script(KlippyGcodes.set_extrusion_rate(self.extrusion))

    def change_speed(self, widget, direction):
        if direction == "+":
            self.speed += int(self.percent_delta)
        elif direction == "-":
            self.speed -= int(self.percent_delta)
        elif direction == "reset":
            self.speed = 100

        self.speed = max(self.speed, 1)
        self._screen._ws.klippy.gcode_script(KlippyGcodes.set_speed_rate(self.speed))

    def change_percent_delta(self, widget, delta):
        if self.percent_delta == delta:
            return
        logging.info(f"### Delta {delta}")

        ctx = self.labels[f"{self.percent_delta}"].get_style_context()
        ctx.remove_class("distbutton_active")

        self.percent_delta = delta
        ctx = self.labels[self.percent_delta].get_style_context()
        ctx.add_class("distbutton_active")
        for i in self.percent_deltas:
            if i == self.percent_delta:
                continue
            self.labels[f"{i}"].set_active(False)
