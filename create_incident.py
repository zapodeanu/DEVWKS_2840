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


import requests
import json
import logging
import netconf_restconf
import config

from config import SNOW_URL, SNOW_DEV, SNOW_PASS
from config import IOS_XE_HOST, IOS_XE_USER, IOS_XE_PASS

from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)  # Disable insecure https warnings


def get_user_sys_id(username):

    # find the ServiceNow user_id for the specified user

    url = SNOW_URL + '/table/sys_user?sysparm_limit=1&name=' + username
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    response = requests.get(url, auth=(SNOW_DEV, SNOW_PASS), headers=headers)
    user_json = response.json()
    return user_json['result'][0]['sys_id']


def create_incident(description, comment, username, severity):

    # This function will create a new incident with the {description}, {comments}, severity for the {user}

    caller_sys_id = get_user_sys_id(username)
    print('\nAPIUSER ServiceNow sysid is: ' + caller_sys_id)
    url = SNOW_URL + '/table/incident'
    payload = {'short_description': description,
               'comments': (comment + ', \nIncident created using APIs by caller ' + username),
               'caller_id': caller_sys_id,
               'urgency': severity
               }
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    logging.debug('Create new incident')
    response = requests.post(url, auth=(SNOW_DEV, SNOW_PASS), data=json.dumps(payload), headers=headers)
    print('\nServiceNow REST API call response: ' + str(response.status_code))
    incident_json = response.json()
    incident_number = incident_json['result']['number']
    logging.debug('Incident created: ' + incident_number)
    return incident_number


# main application

logging.basicConfig(
    filename='application_run.log',
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S')

device_name = netconf_restconf.restconf_get_hostname(IOS_XE_HOST, IOS_XE_USER, IOS_XE_PASS)

comment = '\n\nThe device with the management IP address: ' + IOS_XE_HOST + ' has the name: ' + device_name

print(comment)

incident = create_incident('Device Notification - ' + str(device_name), comment, SNOW_DEV, 3)

print('Created ServiceNow Incident with the number: ', str(incident))

print('\nEnd Application Run')
