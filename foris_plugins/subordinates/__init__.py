#
# foris-subordinates-plugin
# Copyright (C) 2019 CZ.NIC, z.s.p.o. (http://www.nic.cz/)
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA
#

import bottle
import os
import typing

from foris import fapi
from foris.config import ConfigPageMixin, add_config_page, JoinedPages
from foris.plugins import ForisPlugin
from foris.state import current_state
from foris.utils import messages
from foris.utils.routing import reverse
from foris.utils.translators import gettext_dummy as gettext, gettext as _

from . import handlers


class CommonPage(ConfigPageMixin):
    def _prepare_render_args(self, args):
        args["PLUGIN_NAME"] = SubordinatesPlugin.PLUGIN_NAME
        args["PLUGIN_STYLES"] = SubordinatesPlugin.PLUGIN_STYLES
        args["PLUGIN_STATIC_SCRIPTS"] = SubordinatesPlugin.PLUGIN_STATIC_SCRIPTS
        args["PLUGIN_DYNAMIC_SCRIPTS"] = SubordinatesPlugin.PLUGIN_DYNAMIC_SCRIPTS

    def render(self, **kwargs):
        self._prepare_render_args(kwargs)
        return super().render(**kwargs)


class SubordinatesSetupPage(CommonPage, handlers.SubordinatesConfigHandler):
    slug = "subordinates-setup"
    menu_order = 1  # submenu

    template = "subordinates/subordinates_setup"
    menu_title = gettext("Set up")
    userfriendly_title = gettext("Managed devices: Set up")
    template_type = "jinja2"

    def render(self, **kwargs):
        data = current_state.backend.perform("subordinates", "list")
        kwargs["subordinates"] = data["subordinates"]
        return super().render(**kwargs)

    def save(self, *args, **kwargs):
        super(SubordinatesSetupPage, self).save(no_messages=True, *args, **kwargs)
        data = self.form.callback_results
        if data["result"]:
            messages.success(
                _(
                    "Token was successfully added and client '%(controller_id)s' "
                    "should be visible in a moment."
                )
                % dict(controller_id=data["controller_id"])
            )
        else:
            messages.error(_("Failed to add token."))

        return data["result"]

    def _check_and_get_controller_id(self):
        if bottle.request.method != "POST":
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="remote"))

        form = self.get_controller_id_form(bottle.request.POST.decode())
        if not form.data["controller_id"]:
            raise bottle.HTTPError(404, "controller_id not found")
        return form.data["controller_id"]

    def _ajax_list_subordinates(self):
        data = current_state.backend.perform("subordinates", "list")
        return bottle.template(
            "subordinates/_subordinates_list_setup.html.j2",
            subordinates=data["subordinates"],
            template_adapter=bottle.Jinja2Template,
        )

    def _ajax_delete(self):
        controller_id = self._check_and_get_controller_id()
        res = current_state.backend.perform("subordinates", "del", {"controller_id": controller_id})
        if res["result"]:
            return bottle.template(
                "config/_message.html.j2",
                message={
                    "classes": ["success"],
                    "text": _("Subordinate '%(controller_id)s' was successfully deleted.")
                    % dict(controller_id=controller_id),
                },
                template_adapter=bottle.Jinja2Template,
            )
        else:
            return bottle.template(
                "config/_message.html.j2",
                message={
                    "classes": ["error"],
                    "text": _("Failed to delete subordinate '%(controller_id)s'.")
                    % dict(controller_id=controller_id),
                },
                template_adapter=bottle.Jinja2Template,
            )

    def _ajax_set_enabled(self, enabled):
        controller_id = self._check_and_get_controller_id()
        res = current_state.backend.perform(
            "subordinates", "set_enabled", {"controller_id": controller_id, "enabled": enabled}
        )
        if res["result"]:
            if enabled:
                message = {
                    "classes": ["success"],
                    "text": _("Subordinate '%(controller_id)s' was sucessfuly enabled.")
                    % dict(controller_id=controller_id),
                }
            else:
                message = {
                    "classes": ["success"],
                    "text": _("Subordinate '%(controller_id)s' was sucessfuly disabled.")
                    % dict(controller_id=controller_id),
                }
        else:
            if enabled:
                message = {
                    "classes": ["error"],
                    "text": _("Failed to enable subordinate '%(controller_id)s'.")
                    % dict(controller_id=controller_id),
                }
            else:
                message = {
                    "classes": ["error"],
                    "text": _("Failed to disable subordinate '%(controller_id)s'.")
                    % dict(controller_id=controller_id),
                }

        return bottle.template(
            "config/_message.html.j2", message=message, template_adapter=bottle.Jinja2Template
        )

    def call_ajax_action(self, action):
        if action == "list":
            return self._ajax_list_subordinates()
        elif action == "disable":
            return self._ajax_set_enabled(False)
        elif action == "enable":
            return self._ajax_set_enabled(True)
        elif action == "delete":
            return self._ajax_delete()
        raise ValueError("Unknown AJAX action.")

    @classmethod
    def is_visible(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_enabled_static(cls)

    def get_page_form(
        self, form_name: str, data: dict, controller_id: str
    ) -> typing.Tuple[fapi.ForisAjaxForm, typing.Callable[[dict], typing.Tuple["str", "str"]]]:
        """Returns appropriate foris form and handler to generate response
        """
        form: fapi.ForisAjaxForm
        if form_name == "sub-form":
            form = handlers.SubordinatesEditForm(data)

            def prepare_message(results: dict) -> dict:
                if results["result"]:
                    message = {
                        "classes": ["success"],
                        "text": _("Device '%(controller_id)s' was sucessfully updated.")
                        % dict(controller_id=data["controller_id"]),
                    }

                else:
                    message = {
                        "classes": ["error"],
                        "text": _("Failed to update subordinate '%(controller_id)s'.")
                        % dict(controller_id=data["controller_id"]),
                    }
                return message

            form.url = reverse(
                "config_ajax_form", page_name="subordinates-setup", form_name="sub-form"
            )
            return form, prepare_message

        elif form_name == "subsub-form":
            form = handlers.SubsubordinatesEditForm(data)

            def prepare_message(results: dict) -> dict:
                if results["result"]:
                    message = {
                        "classes": ["success"],
                        "text": _("Subsubordinate '%(controller_id)s' was sucessfully updated.")
                        % dict(controller_id=data["controller_id"]),
                    }

                else:
                    message = {
                        "classes": ["error"],
                        "text": _("Failed to update subsubordinate '%(controller_id)s'.")
                        % dict(controller_id=data["controller_id"]),
                    }
                return message

            form.url = reverse(
                "config_ajax_form", page_name="subordinates-setup", form_name="subsub-form"
            )
            return form, prepare_message

        raise bottle.HTTPError(404, "No form '%s' not found." % form_name)


class SubordinatesWifiPage(CommonPage):
    slug = "subordinates-wifi"
    menu_order = 2  # submenu

    template = "subordinates/subordinates_wifi"
    menu_title = gettext("Wi-Fi")
    userfriendly_title = gettext("Managed devices: Wi-Fi")
    template_type = "jinja2"

    def render(self, **kwargs):
        data = current_state.backend.perform("subordinates", "list")
        kwargs["subordinates"] = data["subordinates"]
        return super().render(**kwargs)

    @classmethod
    def is_visible(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_enabled_static(cls)

    def _ajax_list_subordinates(self):
        data = current_state.backend.perform("subordinates", "list")
        return bottle.template(
            "subordinates/_subordinates_list_wifi.html.j2",
            subordinates=data["subordinates"],
            template_adapter=bottle.Jinja2Template,
        )

    def call_ajax_action(self, action):
        if action == "list":
            return self._ajax_list_subordinates()
        raise ValueError("Unknown AJAX action.")

    def get_page_form(
        self, form_name: str, data: dict, controller_id: str
    ) -> typing.Tuple[fapi.ForisAjaxForm, typing.Callable[[dict], typing.Tuple["str", "str"]]]:
        """Returns appropriate foris form and handler to generate response
        """
        if form_name == "wifi-form":
            form = handlers.SubordinatesWifiEditForm(
                data, controller_id=controller_id, enable_guest=False
            )

            def prepare_message(results: dict) -> dict:
                if results["result"]:
                    message = {
                        "classes": ["success"],
                        "text": _("Wifi settings was sucessfully updated."),
                    }

                else:
                    message = {"classes": ["error"], "text": _("Failed to update Wifi settings.")}
                return message

            form.url = reverse(
                "config_ajax_form", page_name="subordinates-wifi", form_name="wifi-form"
            )
            return form, prepare_message

        raise bottle.HTTPError(404, "No form '%s' not found." % form_name)


# This represents a plugin page
class SubordinatesNetbootPage(CommonPage, handlers.NetbootConfigHandler):
    slug = "subordinates-netboot"
    menu_order = 3
    template = "subordinates/subordinates_netboot"
    template_type = "jinja2"

    def save(self, *args, **kwargs):
        # Handle form result here
        return super().save(*args, **kwargs)

    def render(self, **kwargs):
        self._prepare_render_args(kwargs)
        return super().render(**kwargs)

    def _action_list(self):
        res = current_state.backend.perform("netboot", "list")

        return bottle.template(
            "subordinates/_subordinates_list_netboot.html.j2",
            records=res["devices"],
            template_adapter=bottle.Jinja2Template,
        )

    def _action_generic(self, action):
        if bottle.request.method != "POST":
            messages.error(_("Wrong HTTP method."))
            bottle.redirect(reverse("config_page", page_name="remote"))
        form = self.get_serial_form(bottle.request.POST.decode())
        if not form.data["serial"]:
            raise bottle.HTTPError(404, "serial not found")

        res = current_state.backend.perform("netboot", action, {"serial": form.data["serial"]})

        bottle.response.set_header("Content-Type", "application/json")
        return res

    def _action_revoke(self):
        return self._action_generic("revoke")

    def _action_accept(self):
        return self._action_generic("accept")

    def call_ajax_action(self, action):
        if action == "list":
            return self._action_list()
        if action == "revoke":
            return self._action_revoke()
        if action == "accept":
            return self._action_accept()

        raise ValueError("Unknown AJAX action.")


class SubordinatesJoinedPage(JoinedPages):
    userfriendly_title = gettext("Managed devices")
    slug = "subordinates"
    no_url = True

    subpages: typing.Iterable[typing.Type["ConfigPageMixin"]] = [
        SubordinatesSetupPage,
        SubordinatesWifiPage,
        SubordinatesNetbootPage,
    ]

    @classmethod
    def is_visible(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_visible_static(cls)

    @classmethod
    def is_enabled(cls):
        if current_state.backend.name != "mqtt":
            return False
        return ConfigPageMixin.is_enabled_static(cls)


# plugin definition
class SubordinatesPlugin(ForisPlugin):
    PLUGIN_NAME = "subordinates"
    DIRNAME = os.path.dirname(os.path.abspath(__file__))

    PLUGIN_STYLES: typing.List[str] = []

    PLUGIN_STATIC_SCRIPTS: typing.List[str] = ["js/subordinates.js"]  # static js file

    PLUGIN_DYNAMIC_SCRIPTS: typing.List[str] = [
        "subordinates.js"  # dynamic js file (a template which will be rendered to javascript)
    ]

    def __init__(self, app):
        super(SubordinatesPlugin, self).__init__(app)
        add_config_page(SubordinatesJoinedPage)
