import gi
import logging
import contextlib

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Pango

from ks_includes.screen_panel import ScreenPanel
from ks_includes.widgets.graph import HeaterGraph
from ks_includes.widgets.keypad import Keypad


def create_panel(*args):
    return TemperaturePanel(*args)


class TemperaturePanel(ScreenPanel):
    graph_update = None
    active_heater = None

    def __init__(self, screen, title, back=True):
        super().__init__(screen, title, back)
        self.popover_device = None
        self.h = 1
        self.tempdeltas = ["1", "5", "10", "25"]
        self.tempdelta = "10"
        self.show_preheat = False
        self.preheat_options = self._screen._config.get_preheat_options()
        logging.debug(f"Preheat options: {self.preheat_options}")
        self.grid = self._gtk.HomogeneousGrid()

    def initialize(self, panel_name):
        self._gtk.reset_temp_color()
        self.grid.attach(self.create_left_panel(), 0, 0, 1, 1)

        # When printing start in temp_delta mode and only select tools
        state = self._printer.get_state()
        logging.info(state)
        selection = []
        if "extruder" in self._printer.get_tools():
            selection.append("extruder")
        if state not in ["printing", "paused"]:
            self.show_preheat = True
            selection.extend(self._printer.get_heaters())

        # Select heaters
        for h in selection:
            if h.startswith("temperature_sensor "):
                continue
            name = h.split()[1] if len(h.split()) > 1 else h
            # Support for hiding devices by name
            if name.startswith("_"):
                continue
            if h not in self.active_heaters:
                self.select_heater(None, h)

        if self._screen.vertical_mode:
            self.grid.attach(self.create_right_panel(), 0, 1, 1, 1)
        else:
            self.grid.attach(self.create_right_panel(), 1, 0, 1, 1)

        self.content.add(self.grid)
        self.layout.show_all()

    def create_right_panel(self):

        cooldown = self._gtk.ButtonImage('cool-down', _('Cooldown'), "color4", .66, Gtk.PositionType.LEFT, False)
        adjust = self._gtk.ButtonImage('fine-tune', '', "color3", 1, Gtk.PositionType.LEFT, False)

        right = self._gtk.HomogeneousGrid()
        right.attach(cooldown, 0, 0, 2, 1)
        right.attach(adjust, 2, 0, 1, 1)
        if self.show_preheat:
            right.attach(self.preheat(), 0, 1, 3, 4)
        else:
            right.attach(self.delta_adjust(), 0, 1, 3, 4)

        cooldown.connect("clicked", self.set_temperature, "cooldown")
        adjust.connect("clicked", self.switch_preheat_adjust)

        return right

    def switch_preheat_adjust(self, widget):
        self.show_preheat ^= True
        if self._screen.vertical_mode:
            self.grid.remove_row(1)
            self.grid.attach(self.create_right_panel(), 0, 1, 1, 1)
        else:
            self.grid.remove_column(1)
            self.grid.attach(self.create_right_panel(), 1, 0, 1, 1)
        self.grid.show_all()

    def preheat(self):
        self.labels["preheat_grid"] = self._gtk.HomogeneousGrid()
        i = 0
        for option in self.preheat_options:
            if option != "cooldown":
                self.labels[option] = self._gtk.Button(option, f"color{(i % 4) + 1}")
                self.labels[option].connect("clicked", self.set_temperature, option)
                self.labels['preheat_grid'].attach(self.labels[option], (i % 2), int(i / 2), 1, 1)
                i += 1
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.labels["preheat_grid"])
        return scroll

    def delta_adjust(self):
        deltagrid = self._gtk.HomogeneousGrid()
        self.labels["increase"] = self._gtk.ButtonImage("increase", _("Increase"), "color1")
        self.labels["increase"].connect("clicked", self.change_target_temp_incremental, "+")
        self.labels["decrease"] = self._gtk.ButtonImage("decrease", _("Decrease"), "color3")
        self.labels["decrease"].connect("clicked", self.change_target_temp_incremental, "-")

        tempgrid = Gtk.Grid()
        for j, i in enumerate(self.tempdeltas):
            self.labels[f'deg{i}'] = self._gtk.ToggleButton(i)
            self.labels[f'deg{i}'].connect("clicked", self.change_temp_delta, i)
            ctx = self.labels[f'deg{i}'].get_style_context()
            if j == 0:
                ctx.add_class("distbutton_top")
            elif j == len(self.tempdeltas) - 1:
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if i == "10":
                ctx.add_class("distbutton_active")
            tempgrid.attach(self.labels[f'deg{i}'], j, 0, 1, 1)
        self.labels[f"deg{self.tempdelta}"].set_active(True)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(Gtk.Label(_("Temperature") + " (°C)"), False, False, 8)
        vbox.pack_end(tempgrid, True, True, 2)

        vsize = 2 if self._screen.vertical_mode else 3
        deltagrid.attach(self.labels["decrease"], 0, 0, 1, vsize)
        deltagrid.attach(self.labels["increase"], 1, 0, 1, vsize)
        deltagrid.attach(vbox, 0, vsize, 2, 2)
        return deltagrid

    def change_temp_delta(self, widget, tempdelta):
        if self.tempdelta == tempdelta:
            return
        logging.info(f"### tempdelta {tempdelta}")

        ctx = self.labels[f"deg{self.tempdelta}"].get_style_context()
        ctx.remove_class("distbutton_active")

        self.tempdelta = tempdelta
        ctx = self.labels[f"deg{self.tempdelta}"].get_style_context()
        ctx.add_class("distbutton_active")
        for i in self.tempdeltas:
            if i == self.tempdeltas:
                continue
            self.labels[f"deg{i}"].set_active(False)

    def change_target_temp_incremental(self, widget, direction):

        if len(self.active_heaters) == 0:
            self._screen.show_popup_message(_("Nothing selected"))
        else:
            for heater in self.active_heaters:
                target = self._printer.get_dev_stat(heater, "target")
                name = heater.split()[1] if len(heater.split()) > 1 else heater
                if direction == "+":
                    target += int(self.tempdelta)
                    max_temp = int(float(self._printer.get_config_section(heater)['max_temp']))
                    if target > max_temp:
                        target = max_temp
                        self._screen.show_popup_message(_("Can't set above the maximum:") + f' {target}')

                else:
                    target -= int(self.tempdelta)
                    target = max(target, 0)
                if heater.startswith('extruder'):
                    self._screen._ws.klippy.set_tool_temp(self._printer.get_tool_number(heater), target)
                elif heater.startswith('heater_bed'):
                    self._screen._ws.klippy.set_bed_temp(target)
                elif heater.startswith('heater_generic '):
                    self._screen._ws.klippy.set_heater_temp(name, target)
                elif heater.startswith("temperature_fan "):
                    self._screen._ws.klippy.set_temp_fan_temp(name, target)
                else:
                    logging.info(f"Unknown heater: {heater}")
                    self._screen.show_popup_message(_("Unknown Heater") + " " + heater)
                self._printer.set_dev_stat(heater, "target", int(target))
                logging.info(f"Setting {heater} to {target}")

    def activate(self):
        if self.graph_update is None:
            # This has a high impact on load
            self.graph_update = GLib.timeout_add_seconds(5, self.update_graph)

    def deactivate(self):
        if self.graph_update is not None:
            GLib.source_remove(self.graph_update)
            self.graph_update = None

    def select_heater(self, widget, device):

        if self.devices[device]["can_target"]:
            if device in self.active_heaters:
                self.active_heaters.pop(self.active_heaters.index(device))
                self.devices[device]['name'].get_style_context().remove_class("button_active")
                self.devices[device]['select'].set_label(_("Select"))
                logging.info(f"Deselecting {device}")
                return
            self.active_heaters.append(device)
            self.devices[device]['name'].get_style_context().add_class("button_active")
            self.devices[device]['select'].set_label(_("Deselect"))
            logging.info(f"Seselecting {device}")
        return

    def set_temperature(self, widget, setting):
        if len(self.active_heaters) == 0:
            self._screen.show_popup_message(_("Nothing selected"))
        else:
            for heater in self.active_heaters:
                target = None
                max_temp = float(self._printer.get_config_section(heater)['max_temp'])
                name = heater.split()[1] if len(heater.split()) > 1 else heater
                with contextlib.suppress(KeyError):
                    for i in self.preheat_options[setting]:
                        logging.info(f"{self.preheat_options[setting]}")
                        if i == name:
                            # Assign the specific target if available
                            target = self.preheat_options[setting][name]
                            logging.info(f"name match {name}")
                        elif i == heater:
                            target = self.preheat_options[setting][heater]
                            logging.info(f"heater match {heater}")
                if target is None and setting == "cooldown":
                    target = 0
                if heater.startswith('extruder'):
                    if self.validate(heater, target, max_temp):
                        self._screen._ws.klippy.set_tool_temp(self._printer.get_tool_number(heater), target)
                elif heater.startswith('heater_bed'):
                    if target is None:
                        with contextlib.suppress(KeyError):
                            target = self.preheat_options[setting]["bed"]
                    if self.validate(heater, target, max_temp):
                        self._screen._ws.klippy.set_bed_temp(target)
                elif heater.startswith('heater_generic '):
                    if target is None:
                        with contextlib.suppress(KeyError):
                            target = self.preheat_options[setting]["heater_generic"]
                    if self.validate(heater, target, max_temp):
                        self._screen._ws.klippy.set_heater_temp(name, target)
                elif heater.startswith('temperature_fan '):
                    if target is None:
                        with contextlib.suppress(KeyError):
                            target = self.preheat_options[setting]["temperature_fan"]
                    if self.validate(heater, target, max_temp):
                        self._screen._ws.klippy.set_temp_fan_temp(name, target)
            # This small delay is needed to properly update the target if the user configured something above
            # and then changed the target again using preheat gcode
            GLib.timeout_add(250, self.preheat_gcode, setting)

    def validate(self, heater, target=None, max_temp=None):
        if target is not None and max_temp is not None:
            if 0 <= target <= max_temp:
                self._printer.set_dev_stat(heater, "target", target)
                return True
            elif target > max_temp:
                self._screen.show_popup_message(_("Can't set above the maximum:") + f' {max_temp}')
                return False
        return False

    def preheat_gcode(self, setting):
        with contextlib.suppress(KeyError):
            self._screen._ws.klippy.gcode_script(self.preheat_options[setting]['gcode'])
        return False

    def add_device(self, device):

        logging.info(f"Adding device: {device}")

        temperature = self._printer.get_dev_stat(device, "temperature")
        if temperature is None:
            return False

        devname = device.split()[1] if len(device.split()) > 1 else device
        # Support for hiding devices by name
        if devname.startswith("_"):
            return False

        if device.startswith("extruder"):
            i = sum(d.startswith('extruder') for d in self.devices)
            image = f"extruder-{i}" if self._printer.extrudercount > 1 else "extruder"
            class_name = f"graph_label_{device}"
            dev_type = "extruder"
        elif device == "heater_bed":
            image = "bed"
            devname = "Heater Bed"
            class_name = "graph_label_heater_bed"
            dev_type = "bed"
        elif device.startswith("heater_generic"):
            self.h = sum("heater_generic" in d for d in self.devices)
            image = "heater"
            class_name = f"graph_label_sensor_{self.h}"
            dev_type = "sensor"
        elif device.startswith("temperature_fan"):
            f = 1 + sum("temperature_fan" in d for d in self.devices)
            image = "fan"
            class_name = f"graph_label_fan_{f}"
            dev_type = "fan"
        elif self._config.get_main_config().getboolean("only_heaters", False):
            return False
        else:
            self.h += sum("sensor" in d for d in self.devices)
            image = "heat-up"
            class_name = f"graph_label_sensor_{self.h}"
            dev_type = "sensor"

        rgb = self._gtk.get_temp_color(dev_type)

        can_target = self._printer.get_temp_store_device_has_target(device)
        self.labels['da'].add_object(device, "temperatures", rgb, False, True)
        if can_target:
            self.labels['da'].add_object(device, "targets", rgb, True, False)

        name = self._gtk.ButtonImage(image, devname.capitalize().replace("_", " "),
                                     None, .5, Gtk.PositionType.LEFT, False)
        name.connect('clicked', self.on_popover_clicked, device)
        name.set_alignment(0, .5)
        name.get_style_context().add_class(class_name)
        child = name.get_children()[0].get_children()[0].get_children()[1]
        child.set_ellipsize(Pango.EllipsizeMode.END)

        temp = self._gtk.Button("")
        temp.connect('clicked', self.select_heater, device)

        self.devices[device] = {
            "class": class_name,
            "name": name,
            "temp": temp,
            "can_target": can_target
        }

        if self.devices[device]["can_target"]:
            self.devices[device]['select'] = self._gtk.Button(label=_("Select"))
            self.devices[device]['select'].connect('clicked', self.select_heater, device)

        devices = sorted(self.devices)
        pos = devices.index(device) + 1

        self.labels['devices'].insert_row(pos)
        self.labels['devices'].attach(name, 0, pos, 1, 1)
        self.labels['devices'].attach(temp, 1, pos, 1, 1)
        self.labels['devices'].show_all()
        return True

    def change_target_temp(self, temp):
        name = self.active_heater.split()[1] if len(self.active_heater.split()) > 1 else self.active_heater
        max_temp = int(float(self._printer.get_config_section(self.active_heater)['max_temp']))
        if temp > max_temp:
            self._screen.show_popup_message(_("Can't set above the maximum:") + f' {max_temp}')
            return
        temp = max(temp, 0)

        if self.active_heater.startswith('extruder'):
            self._screen._ws.klippy.set_tool_temp(self._printer.get_tool_number(self.active_heater), temp)
        elif self.active_heater == "heater_bed":
            self._screen._ws.klippy.set_bed_temp(temp)
        elif self.active_heater.startswith('heater_generic '):
            self._screen._ws.klippy.set_heater_temp(name, temp)
        elif self.active_heater.startswith('temperature_fan '):
            self._screen._ws.klippy.set_temp_fan_temp(name, temp)
        else:
            logging.info(f"Unknown heater: {self.active_heater}")
            self._screen.show_popup_message(_("Unknown Heater") + " " + self.active_heater)
        self._printer.set_dev_stat(self.active_heater, "target", temp)

    def create_left_panel(self):

        self.labels['devices'] = Gtk.Grid()
        self.labels['devices'].get_style_context().add_class('heater-grid')
        self.labels['devices'].set_vexpand(False)

        name = Gtk.Label("")
        temp = Gtk.Label(_("Temp (°C)"))
        temp.set_size_request(round(self._gtk.get_font_size() * 7.7), -1)

        self.labels['devices'].attach(name, 0, 0, 1, 1)
        self.labels['devices'].attach(temp, 1, 0, 1, 1)

        self.labels['da'] = HeaterGraph(self._printer, self._gtk.get_font_size())
        self.labels['da'].set_vexpand(True)

        scroll = self._gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.labels['devices'])

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        box.add(scroll)
        box.add(self.labels['da'])

        self.labels['graph_settemp'] = self._gtk.Button(label=_("Set Temp"))
        self.labels['graph_settemp'].connect("clicked", self.show_numpad)
        self.labels['graph_hide'] = self._gtk.Button(label=_("Hide"))
        self.labels['graph_hide'].connect("clicked", self.graph_show_device, False)
        self.labels['graph_show'] = self._gtk.Button(label=_("Show"))
        self.labels['graph_show'].connect("clicked", self.graph_show_device)

        popover = Gtk.Popover()
        self.labels['popover_vbox'] = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        popover.add(self.labels['popover_vbox'])
        popover.set_position(Gtk.PositionType.BOTTOM)
        self.labels['popover'] = popover

        for d in self._printer.get_temp_store_devices():
            self.add_device(d)

        return box

    def graph_show_device(self, widget, show=True):
        logging.info(f"Graph show: {self.popover_device} {show}")
        self.labels['da'].set_showing(self.popover_device, show)
        if show:
            self.devices[self.popover_device]['name'].get_style_context().remove_class("graph_label_hidden")
            self.devices[self.popover_device]['name'].get_style_context().add_class(
                self.devices[self.popover_device]['class'])
        else:
            self.devices[self.popover_device]['name'].get_style_context().remove_class(
                self.devices[self.popover_device]['class'])
            self.devices[self.popover_device]['name'].get_style_context().add_class("graph_label_hidden")
        self.labels['da'].queue_draw()
        self.popover_populate_menu()
        self.labels['popover'].show_all()

    def hide_numpad(self, widget):
        self.devices[self.active_heater]['name'].get_style_context().remove_class("button_active")
        self.active_heater = None

        if self._screen.vertical_mode:
            self.grid.remove_row(1)
            self.grid.attach(self.create_right_panel(), 0, 1, 1, 1)
        else:
            self.grid.remove_column(1)
            self.grid.attach(self.create_right_panel(), 1, 0, 1, 1)
        self.grid.show_all()

    def on_popover_clicked(self, widget, device):
        self.popover_device = device
        po = self.labels['popover']
        po.set_relative_to(widget)
        self.popover_populate_menu()
        po.show_all()

    def popover_populate_menu(self):
        pobox = self.labels['popover_vbox']
        for child in pobox.get_children():
            pobox.remove(child)

        if self.labels['da'].is_showing(self.popover_device):
            pobox.pack_start(self.labels['graph_hide'], True, True, 5)
        else:
            pobox.pack_start(self.labels['graph_show'], True, True, 5)
        if self.devices[self.popover_device]["can_target"]:
            pobox.pack_start(self.labels['graph_settemp'], True, True, 5)
            pobox.pack_end(self.devices[self.popover_device]['select'], True, True, 5)

    def process_update(self, action, data):
        if action != "notify_status_update":
            return

        for x in self._printer.get_tools():
            self.update_temp(
                x,
                self._printer.get_dev_stat(x, "temperature"),
                self._printer.get_dev_stat(x, "target")
            )
        for h in self._printer.get_heaters():
            self.update_temp(
                h,
                self._printer.get_dev_stat(h, "temperature"),
                self._printer.get_dev_stat(h, "target")
            )
        return

    def show_numpad(self, widget):

        if self.active_heater is not None:
            self.devices[self.active_heater]['name'].get_style_context().remove_class("button_active")
        self.active_heater = self.popover_device
        self.devices[self.active_heater]['name'].get_style_context().add_class("button_active")

        if "keypad" not in self.labels:
            self.labels["keypad"] = Keypad(self._screen, self.change_target_temp, self.hide_numpad)
        self.labels["keypad"].clear()

        if self._screen.vertical_mode:
            self.grid.remove_row(1)
            self.grid.attach(self.labels["keypad"], 0, 1, 1, 1)
        else:
            self.grid.remove_column(1)
            self.grid.attach(self.labels["keypad"], 1, 0, 1, 1)
        self.grid.show_all()

        self.labels['popover'].popdown()

    def update_graph(self):
        self.labels['da'].queue_draw()
        return True

    def update_temp(self, device, temp, target):
        if device not in self.devices:
            return
        if self.devices[device]["can_target"] and target > 0:
            self.devices[device]["temp"].get_child().set_label(f"{temp:.1f} / {target:.0f}")
        else:
            self.devices[device]["temp"].get_child().set_label(f"{temp:.1f}")
