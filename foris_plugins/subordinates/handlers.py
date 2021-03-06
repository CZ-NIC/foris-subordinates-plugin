# Foris - web administration interface for OpenWrt
# Copyright (C) 2019 CZ.NIC, z.s.p.o. <http://www.nic.cz>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import base64
import bottle
import typing

from foris import fapi, validators
from foris.form import File, Hidden, Textbox
from foris.state import current_state
from foris.utils.translators import gettext as _, gettext_dummy as gettext

from foris.config_handlers.base import BaseConfigHandler
from foris.config_handlers.wifi import WifiEditForm


class SubordinatesConfigHandler(BaseConfigHandler):
    def get_form(self):
        form = fapi.ForisForm("suboridinates", self.data)

        section = form.add_section(name="main_section", title=_(self.userfriendly_title))

        section.add_field(File, name="token_file", label=_("Token file"), required=True)

        def form_cb(data):
            res = current_state.backend.perform(
                "subordinates",
                "add_sub",
                {"token": base64.b64encode(data["token_file"].file.read()).decode("utf-8")},
            )

            return "save_result", res

        form.add_callback(form_cb)
        return form

    def get_controller_id_form(self, data=None):
        controller_id_form = fapi.ForisForm("controller_id_form", data)
        controller_section = controller_id_form.add_section("controller_section", title=None)
        controller_section.add_field(Hidden, name="controller_id", label="", required=True)
        return controller_id_form


class SubordinatesEditForm(fapi.ForisAjaxForm):
    template_name = "subordinates/_subordinates_edit.html.j2"

    def __init__(self, data, controller_id=None):
        self.subordinate_controller_id = data["controller_id"]
        super().__init__(data, controller_id)
        self.title = _("Edit device '%(controller_id)s'") % dict(
            controller_id=data["controller_id"]
        )

    def convert_data_from_backend_to_form(self, backend_data):
        subordinates_list = backend_data["subordinates"]
        subordinates_map = {e["controller_id"]: e for e in subordinates_list}
        sub_record = subordinates_map.get(self.subordinate_controller_id, None)
        if not sub_record:
            raise bottle.HTTPError(
                404, f"Controller id {self.subordinate_controller_id} not found."
            )
        return sub_record["options"]

    def convert_data_from_form_to_backend(self, data):
        controller_id = data.pop("controller_id")
        return {"controller_id": controller_id, "options": data}

    def make_form(self, data: typing.Optional[dict]):

        form_data = self.convert_data_from_backend_to_form(
            current_state.backend.perform("subordinates", "list")
        )

        if data:
            form_data.update(data)

        sub_form = fapi.ForisForm("update_sub", form_data)
        sub_section = sub_form.add_section(
            "subordinate_section",
            title="",
            description=_(
                "You can edit managed devices here. These managed devices are directly connected to this "
                "device."
            ),
        )
        sub_section.add_field(
            Textbox,
            name="custom_name",
            label=_("Custom Name"),
            validators=[validators.LenRange(0, 30)],
            hint=_("Nicer name for your device '%(controller_id)s'.")
            % dict(controller_id=data["controller_id"]),
        )
        sub_section.add_field(Hidden, name="controller_id", required=True, title="")

        def form_cb(data):
            msg_data = self.convert_data_from_form_to_backend(data)
            res = current_state.backend.perform("subordinates", "update_sub", msg_data)
            return "save_result", res

        sub_form.add_callback(form_cb)

        return sub_form


class SubsubordinatesEditForm(fapi.ForisAjaxForm):
    template_name = "subordinates/_subordinates_edit.html.j2"

    def __init__(self, data, controller_id=None):
        self.subsubordinate_controller_id = data["controller_id"]
        super().__init__(data, controller_id)
        self.title = _("Edit managed device '%(controller_id)s'") % dict(
            controller_id=data["controller_id"]
        )

    def convert_data_from_backend_to_form(self, backend_data):
        subordinates_list = backend_data["subordinates"]
        subsubordinates_map = {
            e["controller_id"]: e for record in subordinates_list for e in record["subsubordinates"]
        }
        subsub_record = subsubordinates_map.get(self.subsubordinate_controller_id, None)
        if not subsub_record:
            raise bottle.HTTPError(
                404, f"Controller id {self.subsubordinate_controller_id} not found."
            )
        return subsub_record["options"]

    def convert_data_from_form_to_backend(self, data):
        controller_id = data.pop("controller_id")
        return {"controller_id": controller_id, "options": data}

    def make_form(self, data: typing.Optional[dict]):

        form_data = self.convert_data_from_backend_to_form(
            current_state.backend.perform("subordinates", "list")
        )

        if data:
            form_data.update(data)

        sub_form = fapi.ForisForm("update_subsub", form_data)
        sub_section = sub_form.add_section(
            "subsubordinate_section",
            title="",
            description=_(
                "You can edit managed devices here. These devices are not "
                "not directly connected to this device but "
                "they are connected through another managed device."
            ),
        )
        sub_section.add_field(Hidden, name="controller_id", required=True, title="")
        sub_section.add_field(
            Textbox,
            name="custom_name",
            label=_("Custom Name"),
            validators=[validators.LenRange(0, 30)],
            hint=_("Nicer name for your device with serial '%(controller_id)s'.")
            % dict(controller_id=self.subsubordinate_controller_id),
        )

        def form_cb(data):
            res = current_state.backend.perform(
                "subordinates",
                "update_subsub",
                {
                    "controller_id": data["controller_id"],
                    "options": {"custom_name": data["custom_name"]},
                },
            )
            return "save_result", res

        sub_form.add_callback(form_cb)

        return sub_form


class SubordinatesWifiEditForm(WifiEditForm):
    def make_form(self, data: typing.Optional[dict]) -> fapi.ForisForm:
        form = super().make_form(data)

        def store_command_cb(data):
            controller_id = data.get("_controller_id")
            ids = list(
                {int(e.split("-", 1)[0][len("radio") :]) for e in data if e.startswith("radio")}
            )

            # get netboot device list
            res = current_state.backend.perform("netboot", "list")

            # check controller_id
            if controller_id in [e["serial"] for e in res["devices"]]:

                update_data = self.convert_data_from_form_to_backend(data, ids)
                resp = current_state.backend.perform(
                    "netboot",
                    "command_set",
                    {
                        "controller_id": data["_controller_id"],
                        "command": {
                            "module": "wifi",
                            "action": "update_settings",
                            "data": update_data,
                        },
                    },
                )

                return "save_result", {"netboot_resp": resp}

            return "save_result", {}

        form.add_callback(store_command_cb)

        return form


class SubordinatesWifiHandler(BaseConfigHandler):
    def get_form(self):
        ajax_form = SubordinatesWifiEditForm(self.data)
        return ajax_form.foris_form


class NetbootConfigHandler(BaseConfigHandler):
    STATE_ACCEPTED = gettext("accepted")
    STATE_INCOMMING = gettext("incomming")

    userfriendly_title = gettext("Netboot")

    def get_form(self):

        form = fapi.ForisForm("netboot", {})
        form.add_section(name="main_section", title=self.userfriendly_title)

        def form_cb(data):
            return "save_result", {}

        form.add_callback(form_cb)
        return form

    def get_serial_form(self, data=None):
        generate_serial_form = fapi.ForisForm("serial_form", data)
        serial_section = generate_serial_form.add_section("serial_section", title=None)
        serial_section.add_field(
            Textbox, name="serial", label=" ", required=True, validators=[validators.MacAddress()]
        )
        return generate_serial_form
