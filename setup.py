#!/usr/bin/env python

# Copyright (c) 2016 IBM Corporation.
#
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

from distutils.core import setup

VERSION = "1.2"
setup(name="openbmc",
      version=VERSION,
      description="library for OpenBMC calls",
      author = "Mark Hamzy",
      author_email = 'hamy@us.ibm.com',
      url="https://github.com/hamzy/openbmc",
      download_url="https://github.com/hamzy/OpenBMC/tarball/v"+VERSION,
      keywords = ["OpenBMC"],
      py_modules=["openbmc/__init__", "openbmc/OpenBMC"],
      scripts=["openbmc/openBmcTool"],
      install_requires=[
          "requests",
      ],
     )
