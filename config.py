#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""

Copyright (c) 2019 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.

"""

__author__ = "Gabriel Zapodeanu TME, ENB"
__email__ = "gzapodea@cisco.com"
__version__ = "0.1.0"
__copyright__ = "Copyright (c) 2019 Cisco and/or its affiliates."
__license__ = "Cisco Sample Code License, Version 1.1"

# This file contains the:
# Cisco DNA Center username and password, server info
# ServiceNow developer instance info, username and password
# IOS XE Device name, IP address, username and password


# Update this section with the DNA Center server info and user information
DNAC_URL = 'https://'
DNAC_USER = 'user'
DNAC_PASS = 'password'  # replace this with the provided password

# Update this section with the Service Now instance to be used for labs
SNOW_URL = 'https://devxxxxx.service-now.com/api/now'  # replace XXXXX with the instance number provided
SNOW_ADMIN = 'user'
SNOW_DEV = 'user'
SNOW_PASS = 'password'  # replace this with the provided password
SNOW_INSTANCE = 'devXXXXX'  # replace XXXXX with the instance number provided

# Update this section with the info for the CSR 1000V
IOS_XE_HOST = 'ip address'  # replace X with the Pod number
IOS_XE_USER = 'suer'
IOS_XE_PASS = 'C!sc0ws1'  # replace this with the provided password
IOS_XE_PORT = '830'
IOS_XE_HOSTNAME = 'CSR1Kv-01'  # replace X with your device number


# Mapping for NAT if required
NAT = {
    ,
}