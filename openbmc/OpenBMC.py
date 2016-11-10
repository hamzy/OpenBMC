#!/usr/bin/env python

"""
Object library to interact with an OpenBMC controller.
"""

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#
# Documentation:
#
# OpenBMC cheatsheet
# https://github.com/openbmc/docs/blob/master/cheatsheet.md
#
# OpenBMC REST API
# https://github.com/openbmc/docs/blob/master/rest-api.md
#
# OpenBMC DBUS API
# https://github.com/openbmc/docs/blob/master/dbus-interfaces.md
#
# https://github.com/openbmc/openbmc-test-automation/blob/master/lib/utils.robot
#
# https://github.com/causten/tools/tree/master/obmc
#

# pylint: disable=too-many-arguments
# pylint: disable=too-few-public-methods

from __future__ import print_function

import json
import os
import sys
import requests

# Sadly a way to fit the line into 78 characters mainly
JSON_HEADERS = {"Content-Type": "application/json"}


class HTTPError(Exception):
    """Custom HTTP error exception"""

    def __init__(self, url, status_code, data=None):
        super(HTTPError, self).__init__("%s - %s - %s" % (url,
                                                          status_code,
                                                          data, ))
        self.url = url
        self.status_code = status_code
        self.data = data

    def __str__(self):
        if self.data is not None:
            return "HTTP Error %s: %s %s" % (self.status_code,
                                             self.url,
                                             self.data, )
        else:
            return "HTTP Error %s: %s" % (self.status_code,
                                          self.url, )

    def __repr__(self):
        return self.__str__()

    def get_status_code(self):
        """Return the status code"""
        return self.status_code


def safe_filename(filename):
    """Turn a URL into a safe filename"""

    filename = filename.replace(':', "%"+hex(ord(':')))
    filename = filename.replace('/', "%"+hex(ord('/')))
    return filename


def load_response_from_file(filename,
                            url,
                            verify,
                            headers,
                            data=None):
    """Loads a response from a saved file"""

    print("load_response_from_file (%s)" % (filename, ))

    # import pdb
    # pdb.set_trace()

    if os.path.isfile(filename):
        with open(filename, "r") as fpl:
            json_data = fpl.read()
        saved = json.loads(json_data)

        if ((data is not None) and
                (saved["data"] != data)):
            return None

        if (saved["url"] == url and
                saved["verify"] == verify and
                saved["headers"] == headers):
            response = CachedResponse(saved["status_code"],
                                      saved["json_struct"])

            return response

    return None


def write_response_to_file(filename,
                           url,
                           verify,
                           headers,
                           status_code,
                           json_struct,
                           data=None):
    """Saves a file containing the response"""

    to_save = {}
    to_save["url"] = url
    if data is not None:
        to_save["data"] = data
    to_save["verify"] = verify
    to_save["headers"] = headers
    to_save["status_code"] = status_code
    to_save["json_struct"] = json_struct

    json_data = json.dumps(to_save)

    msg = "CachedSession:post:OUT: json_data = %s" % (json_data, )
    print(msg)

    # What is with [invalid-name] Invalid variable name "fp"
    with open(filename, "w") as fpl:
        fpl.write(json_data)


class CachedSession(object):
    """online or offline support for a requests.Session()"""

    def __init__(self, online):
        self.session = requests.Session()
        self.online = online

    def post(self, url, data, verify, headers):
        """Replaces session.post()"""

        msg = ("CachedSession:post:IN: url = %s, data = %s, verify = %s,"
               " headers = %s") % (url, data, verify, headers, )
        print(msg)

        filename = safe_filename(url)

        ret = None

        if self.online:
            response = self.session.post(url,
                                         data=data,
                                         verify=verify,
                                         headers=headers)

            ret = CachedResponse(response)
        else:
            ret = load_response_from_file(filename,
                                          url,
                                          verify,
                                          headers,
                                          data)

        if ret is None:
            raise Exception("Danger Will Robinson!")

        msg = "CachedSession:post:OUT: ret = %s" % (ret, )
        print(msg)

        if self.online:
            write_response_to_file(filename,
                                   url,
                                   verify,
                                   headers,
                                   response.status_code,
                                   response.json(),
                                   data)

        return ret

    def get(self, url, verify, headers):
        """Replaces session.get()"""

        msg = ("CachedSession:get:IN: url = %s, verify = %s,"
               " headers = %s") % (url, verify, headers, )
        print(msg)

        filename = safe_filename(url)
        ret = None

        if self.online:
            response = self.session.get(url,
                                        verify=verify,
                                        headers=headers)

            ret = CachedResponse(response)
        else:
            ret = load_response_from_file(filename,
                                          url,
                                          verify,
                                          headers)

        if ret is None:
            raise Exception("Danger Will Farrel!")

        msg = "CachedSession:get:OUT: ret = %s" % (ret, )
        print(msg)

        if self.online:
            write_response_to_file(filename,
                                   url,
                                   verify,
                                   headers,
                                   response.status_code,
                                   response.json())

        return ret


class CachedResponse(object):
    """online or offline support for a session response object"""

    def __init__(self, *args, **_):
        # args -- tuple of anonymous arguments
        # _/kwargs -- dictionary of named arguments
        self.status_code = None
        self.json_struct = None

        if len(args) == 1:
            if isinstance(args[0], requests.models.Response):
                response = args[0]
                self.status_code = response.status_code
                self.json_struct = response.json()
        elif len(args) == 2:
            if (isinstance(args[0],
                           int) and
                    isinstance(args[1],
                               dict)):
                self.status_code = args[0]
                self.json_struct = args[1]

        if self.status_code is None or self.json_struct is None:
            raise Exception("ruhroh")

    def __getattribute__(self, name):
        # We may need to call the base's getattribute to return
        # stuff we support because we are limiting what you can
        # ask for here.
        if name in ['status_code', 'json', 'json_struct']:
            return object.__getattribute__(self, name)
        else:
            raise AttributeError(name)

    def json(self):
        """Return the JSON data"""

        return self.json_struct


class OpenBMC(object):
    """Operations against a controller running OpenBMC"""

    def __init__(self,
                 hostname,
                 user,
                 password,
                 online):
        self.session = None
        self.hostname = hostname
        self.verbose = False

        session = CachedSession(online)

        # Log in with a special URL and JSON data structure
        url = "https://%s/login" % (hostname, )
        login_data = json.dumps({"data": [user, password]})
        response = session.post(url,
                                data=login_data,
                                verify=False,
                                headers=JSON_HEADERS)

        if response.status_code != 200:
            err_str = ("Error: Response code to login is not 200!"
                       " (%d)" % (response.status_code, ))
            print(err_str, file=sys.stderr)

            raise HTTPError(url,
                            response.status_code,
                            data=login_data)

        self.session = session

    def set_verbose(self, value):
        """Set the verbosity to value"""

        self.verbose = value

    def enumerate(self, key):
        """Enumerate the provided key"""

        if key.startswith("/"):
            path = key[1:]
        else:
            path = key

        if path.endswith("/"):
            path = path + "enumerate"
        else:
            path = path + "/enumerate"

        return self.get(path)

    def get(self, key):
        """Get the value for the provided key"""

        if key.startswith("/"):
            path = key[1:]
        else:
            path = key

        url = "https://%s/%s" % (self.hostname, path, )

        if self.verbose:
            print("GET %s" % (url, ))

        response = self.session.get(url,
                                    verify=False,
                                    headers=JSON_HEADERS)

        if response.status_code != 200:
            err_str = ("Error: Response code to get %s enumerate is not 200!"
                       " (%d)" % (key, response.status_code, ))
            print(err_str, file=sys.stderr)

            raise HTTPError(url, response.status_code)

        return response.json()["data"]

    def _filter_org_openbmc_control(self, filter_list):
        """Filter /org/openbmc/control against the provided filter list"""

        # Enumerate the inventory of the system's control hardware
        mappings = {}

        try:
            items = self.enumerate("/org/openbmc/control/").items()
        except HTTPError as ex:
            if ex.get_status_code() == 404:
                # @BUG
                # There is no /org/openbmc/control entry?!
                entries = self.get("/org/openbmc/")
                msg = "Error: no /org/openbmc/control in %s" % (entries, )
                raise Exception(msg)
            else:
                raise

        # Loop through the returned map items
        for (item_key, item_value) in items:
            # We only care about filter entries
            if not any(x in item_key for x in filter_list):
                continue

            if self.verbose:
                print("Found:")
                print(item_key)
                print(item_value)

            # Add the entry into our mappings
            for fltr in filter_list:
                idx = item_key.find(fltr)
                if idx > -1:
                    # Get the identity (the rest of the string)
                    ident = item_key[idx+len(fltr):]
                    # Create a new map for the first time
                    if ident not in mappings:
                        mappings[ident] = {}
                    # Save both the full filename and map contents
                    mappings[ident][fltr] = (item_key, item_value)

        return mappings

    def _power_common(self, with_state_do):
        # Query /org/openbmc/control for power and chassis entries
        filter_list = ["control/power", "control/chassis"]
        mappings = self._filter_org_openbmc_control(filter_list)
        if mappings is None:
            return False

        # Loop through the found power & chassis entries
        for (_, ident_mappings) in mappings.items():
            # { '/power':
            #     ( u'/org/openbmc/control/power0',
            #       {u'pgood': 1,
            #        u'poll_interval': 3000,
            #        u'pgood_timeout': 10,
            #        u'heatbeat': 0,
            #        u'state': 1
            #       }
            #     ),
            #   '/chassis':
            #     ( u'/org/openbmc/control/chassis0',
            #       {u'reboot': 0,
            #        u'uuid': u'24340d83aa784d858468993286b390a5'
            #       }
            #     )
            # }

            # Grab our information back out of the mappings
            (power_url, power_mapping) = ident_mappings["control/power"]
            (chassis_url, _) = ident_mappings["control/chassis"]

            if self.verbose:
                msg = "Current state of %s is %s" % (power_url,
                                                     power_mapping["state"], )
                print(msg)

            (url, jdata) = with_state_do(power_mapping["state"],
                                         self.hostname,
                                         chassis_url)

            if url is None:
                return False

            if self.verbose:
                print("POST %s with %s" % (url, jdata, ))

            response = self.session.post(url,
                                         data=jdata,
                                         verify=False,
                                         headers=JSON_HEADERS)

            if response.status_code != 200:
                err_str = ("Error: Response code to PUT is not 200!"
                           " (%d)" % (response.status_code, ))
                print(err_str, file=sys.stderr)

                raise HTTPError(url, response.status_code, data=jdata)

        return True

    def power_on(self):
        """Turn the power on"""

        def with_state_off_do(state,
                              hostname,
                              chassis_url):
            """Do something with the state"""

            url = None
            jdata = None

            if state == 0:
                # power_on called and machine is off
                url = "https://%s%s/action/powerOn" % (hostname,
                                                       chassis_url, )
                jdata = json.dumps({"data": []})
            elif state == 1:
                # power_on called and machine is on
                pass

            return (url, jdata)
        return self._power_common(with_state_off_do)

    def power_off(self):
        """Turn the power off"""

        def with_state_on_do(state,
                             hostname,
                             chassis_url):
            """Do something with the state"""

            url = None
            jdata = None

            if state == 0:
                # power_off called and machine is off
                pass
            elif state == 1:
                # power_off called and machine is on
                url = "https://%s%s/action/powerOff" % (hostname,
                                                        chassis_url, )
                jdata = json.dumps({"data": []})
            return (url, jdata)
        return self._power_common(with_state_on_do)

    def get_power_state(self):
        """Return the state of the power"""

        # Query /org/openbmc/control for power and chassis entries
        filter_list = ["control/chassis"]
        mappings = self._filter_org_openbmc_control(filter_list)
        if mappings is None:
            return False

        # Loop through the found power & chassis entries
        for (_, ident_mappings) in mappings.items():
            # Grab our information back out of the mappings
            (chassis_url, _) = ident_mappings["control/chassis"]

            url = "https://%s/%s/action/getPowerState" % (self.hostname,
                                                          chassis_url, )
            jdata = json.dumps({"data": []})

            if self.verbose:
                print("POST %s with %s" % (url, jdata, ))

            response = self.session.post(url,
                                         data=jdata,
                                         verify=False,
                                         headers=JSON_HEADERS)

            if response.status_code != 200:
                err_str = ("Error: Response code to PUT is not 200!"
                           " (%d)" % (response.status_code, ))
                print(err_str, file=sys.stderr)

                raise HTTPError(url, response.status_code, data=jdata)

            return response.json()["data"]

        return None

    def trigger_warm_reset(self):
        """Force a warm reset"""

        filter_list = ["control/bmc"]
        mappings = self._filter_org_openbmc_control(filter_list)
        if mappings is None:
            return False

        # Loop through the found bmc entries
        for (_, ident_mappings) in mappings.items():
            # Grab our information back out of the mappings
            (bmc_url, _) = ident_mappings["control/bmc"]

            url = "https://%s%s/action/warmReset" % (self.hostname,
                                                     bmc_url, )
            jdata = json.dumps({"data": []})

            if self.verbose:
                print("POST %s with %s" % (url, jdata, ))

            response = self.session.post(url,
                                         data=jdata,
                                         verify=False,
                                         headers=JSON_HEADERS)

            if response.status_code != 200:
                err_str = ("Error: Response code to PUT is not 200!"
                           " (%d)" % (response.status_code, ))
                print(err_str, file=sys.stderr)

                raise HTTPError(url, response.status_code, data=jdata)

        return True

    def get_flash_bios(self):
        """Get the flash BIOS"""

        return self.get("/org/openbmc/control/flash/bios")

    def get_bmc_state(self):
        """Get the state of the OpenBMC controller"""

        path = "org/openbmc/managers/System"
        url = "https://%s/%s/action/getSystemState" % (self.hostname,
                                                       path, )
        jdata = json.dumps({"data": []})

        if self.verbose:
            print("POST %s with %s" % (url, jdata, ))

        response = self.session.post(url,
                                     data=jdata,
                                     verify=False,
                                     headers=JSON_HEADERS)

        if response.status_code != 200:
            err_str = ("Error: Response code to PUT is not 200!"
                       " (%d)" % (response.status_code, ))
            print(err_str, file=sys.stderr)

            raise HTTPError(url, response.status_code, data=jdata)

        return response.json()["data"]
