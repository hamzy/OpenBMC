#!/usr/bin/env python

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

import sys
import pdb
import requests
import json

# Sadly a way to fit the line into 78 characters mainly
JSON_HEADERS = {"Content-Type": "application/json"}

class HTTPError(Exception):
    def __init__(self, url, status_code, data = None):
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
        return self.status_code

class OpenBMC(object):
    def __init__(self,
                 hostname,
                 user,
                 password):
        self.session = None
        self.hostname = hostname
        self.verbose = False

        # Create a http session
        session = requests.Session()

        # Log in with a special URL and JSON data structure
        url = "https://%s/login" % (hostname, )
        login_data = json.dumps({"data": [ user, password ]})
        response = session.post (url,
                                 data=login_data,
                                 verify=False,
                                 headers=JSON_HEADERS)

        if response.status_code != 200:
            err_str = ("Error: Response code to login is not 200!"
                       " (%d)" % (response.status_code, ))
            print >> sys.stderr, err_str

            raise HTTPError(url,
                            response.status_code,
                            data=login_data)

        self.session = session

    def set_verbose(self, value):
        self.verbose = value

    def enumerate(self, key):
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
        if key.startswith("/"):
            path = key[1:]
        else:
            path = key

        url = "https://%s/%s" % (self.hostname, path, )

        if self.verbose:
            print "GET %s" % (url, )

        response = self.session.get (url,
                                     verify=False,
                                     headers=JSON_HEADERS)

        if response.status_code != 200:
            err_str = ("Error: Response code to get %s enumerate is not 200!"
                       " (%d)" % (key, response.status_code, ))
            print >> sys.stderr, err_str

            raise HTTPError(url, response.status_code)

        return response.json()["data"]

    def get_power_chassis_mappings(self):
        # Enumerate the inventory of the system's control hardware
        mappings = {}
        filter_list = ["/power", "/chassis"]

        try:
            items = self.enumerate("/org/openbmc/control/").items()
        except HTTPError as e:
            if e.status_code == 404:
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
                print "Found:"
                print item_key
                print item_value

            # Add the entry into our mappings
            for fltr in filter_list:
                idx = item_key.find(fltr)
                if idx > -1:
                    # Get the identity (the rest of the string)
                    ident = item_key[idx+len(fltr):]
                    # Create a new map for the first time
                    if not mappings.has_key(ident):
                        mappings[ident] = {}
                    # Save both the full filename and map contents
                    mappings[ident][fltr] = (item_key, item_value)

        return mappings

    def power_on(self):
        # Query /org/openbmc/control for power and chassis entries
        mappings = self.get_power_chassis_mappings()
        if mappings is None:
            return False

        # Loop through the found power & chassis entries
        for (ident, ident_mappings) in mappings.items():
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
            (power_url, power_mapping) = ident_mappings["/power"]
            (chassis_url, chassis_mapping) = ident_mappings["/chassis"]

            if self.verbose:
                msg = "Current state of %s is %s" % (power_url,
                                                     power_mapping["state"], )
                print msg

            url = None
            jdata = None

            if power_mapping["state"] == 0:
                # power_on called and machine is off
                url = "https://%s%s/action/powerOn" % (self.hostname,
                                                       chassis_url, )
                jdata = json.dumps({"data": []})
            elif power_mapping["state"] == 1:
                # power_on called and machine is on
                return False

            if url is not None:
                if self.verbose:
                    print "POST %s with %s" % (url, jdata, )

                response = self.session.post (url,
                                              data=jdata,
                                              verify=False,
                                              headers=JSON_HEADERS)

                if response.status_code != 200:
                    err_str = ("Error: Response code to PUT is not 200!"
                               " (%d)" % (response.status_code, ))
                    print >> sys.stderr, err_str

                    raise HTTPError(url, response.status_code, data=jdata)

        return True

    def power_off(self):
        # Query /org/openbmc/control for power and chassis entries
        mappings = self.get_power_chassis_mappings()
        if mappings is None:
            return False

        # Loop through the found power & chassis entries
        for (ident, ident_mappings) in mappings.items():
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
            (power_url, power_mapping) = ident_mappings["/power"]
            (chassis_url, chassis_mapping) = ident_mappings["/chassis"]

            if self.verbose:
                msg = "Current state of %s is %s" % (power_url,
                                                     power_mapping["state"], )
                print msg

            url = None
            jdata = None

            if power_mapping["state"] == 0:
                # power_off called and machine is off
                return False
            elif power_mapping["state"] == 1:
                # power_off called and machine is on
                url = "https://%s%s/action/powerOff" % (self.hostname,
                                                        chassis_url, )
                jdata = json.dumps({"data": []})

            if url is not None:
                if self.verbose:
                    print "POST %s with %s" % (url, jdata, )

                response = self.session.post (url,
                                              data=jdata,
                                              verify=False,
                                              headers=JSON_HEADERS)

                if response.status_code != 200:
                    err_str = ("Error: Response code to PUT is not 200!"
                               " (%d)" % (response.status_code, ))
                    print >> sys.stderr, err_str

                    raise HTTPError(url, response.status_code, data=jdata)

        return True
