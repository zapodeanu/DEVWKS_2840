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

import utils
import os
import os.path
import difflib
import time
import urllib3
import logging

import dnac_apis
import service_now_apis
import netconf_restconf

from requests.auth import HTTPBasicAuth  # for Basic Auth
from urllib3.exceptions import InsecureRequestWarning  # for insecure https warnings

from config import DNAC_PASS, DNAC_USER
from config import SNOW_DEV
from config import IOS_XE_USER, IOS_XE_PASS, IOS_XE_PORT
from config import IOS_XE_HOSTNAME

urllib3.disable_warnings(InsecureRequestWarning)  # disable insecure https warnings

DNAC_AUTH = HTTPBasicAuth(DNAC_USER, DNAC_PASS)


def compare_configs(cfg1, cfg2):
    """
    This function, using the unified diff function, will compare two config files and identify the changes.
    '+' or '-' will be prepended in front of the lines with changes
    :param cfg1: old configuration file path and filename
    :param cfg2: new configuration file path and filename
    :return: text with the configuration lines that changed. The return will include the configuration for the sections
    that include the changes
    """

    # open the old and new configuration fiels
    f1 = open(cfg1, 'r')
    old_cfg = f1.readlines()
    f1.close()

    f2 = open(cfg2, 'r')
    new_cfg = f2.readlines()
    f2.close()

    # compare the two specified config files {cfg1} and {cfg2}
    d = difflib.unified_diff(old_cfg, new_cfg, n=9)

    # create a diff_list that will include all the lines that changed
    # create a diff_output string that will collect the generator output from the unified_diff function
    diff_list = []
    diff_output = ''

    for line in d:
        diff_output += line
        if line.find('Current configuration') == -1:
            if line.find('Last configuration change') == -1:
                if (line.find('+++') == -1) and (line.find('---') == -1):
                    if (line.find('-!') == -1) and (line.find('+!') == -1):
                        if line.startswith('+'):
                            diff_list.append('\n' + line)
                        elif line.startswith('-'):
                            diff_list.append('\n' + line)

    # process the diff_output to select only the sections between '!' characters for the sections that changed,
    # replace the empty '+' or '-' lines with space
    diff_output = diff_output.replace('+!', '!')
    diff_output = diff_output.replace('-!', '!')
    diff_output_list = diff_output.split('!')

    all_changes = []

    for changes in diff_list:
        for config_changes in diff_output_list:
            if changes in config_changes:
                if config_changes not in all_changes:
                    all_changes.append(config_changes)

    # create a config_text string with all the sections that include changes
    config_text = ''
    for items in all_changes:
        config_text += items

    return config_text


def main():
    """
    This script will monitor device configuration changes. It could be executed on demand,
    periodically (every 60 minutes, for example) or continuously.
    It will collect the configuration file for each DNA Center managed device, compare with the existing cached file,
    and detect if any changes.
    When changes detected, identify the last user that configured the device, and create a new ServiceNow incident.
    Automatically roll back all non-compliant configurations, or save new configurations if approved in ServiceNow.
    Device configuration files managemnt using RESTCONF and NETCONF
    Compliance checks at this time:
    - no Access Control Lists changes
    - no logging changes
    - no duplicated IPv4 addresses
    """

    # run the demo continuously, looping

    print('Application config_mon.py started')
    # create a local directory for all the configuration files
    # check if 'Config_Files' folder exists and create one if it does not

    if not os.path.exists('Config_Files'):
        os.makedirs('Config_Files')

    os.chdir('Config_Files')

    # logging, debug level, to file {application_run.log}
    logging.basicConfig(
        filename='application_run.log',
        level=logging.DEBUG,
        format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    while True:

        # get the DNA C auth token
        dnac_token = dnac_apis.get_dnac_jwt_token(DNAC_AUTH)

        temp_run_config = 'temp_run_config.txt'

        # get the DNA C managed devices list (excluded wireless, for one location)
        all_devices_info = dnac_apis.get_all_device_info(dnac_token)
        all_devices_hostnames = []
        for device in all_devices_info:
            if device['family'] == 'Switches and Hubs' or device['family'] == 'Routers':
                if IOS_XE_HOSTNAME in device['hostname']:
                    all_devices_hostnames.append(device['hostname'])

        # get the config files, compare with existing (if one existing). Save new config if file not existing.
        for device in all_devices_hostnames:
            device_run_config = dnac_apis.get_output_command_runner('show running-config', device, dnac_token)
            filename = str(device) + '_run_config.txt'

            # save the running config to a temp file

            f_temp = open(temp_run_config, 'w')
            f_temp.write(device_run_config)
            f_temp.seek(0)  # reset the file pointer to 0
            f_temp.close()

            # check if device has an existing configuration file (to account for newly discovered DNA C devices)
            # if yes, run the diff function
            # if not, save the device configuration to the local device database
            # this will create the local "database" of configs, one file/device

            if os.path.isfile(filename):
                diff = compare_configs(filename, temp_run_config)

                if diff != '':

                    # retrieve the device location using DNA C REST APIs
                    location = dnac_apis.get_device_location(device, dnac_token)

                    # find the users that made configuration changes
                    with open(temp_run_config, 'r') as f:
                        user_info = 'User info no available'
                        for line in f:
                            if 'Last configuration change' in line:
                                user_info = line


                    # define the incident description and comment
                    short_description = 'Configuration Change Alert - ' + device
                    comment = 'The device with the name: ' + device + '\nhas detected a Configuration Change'

                    print(comment)

                    # create ServiceNow incident using ServiceNow APIs
                    incident = service_now_apis.create_incident(short_description, comment, SNOW_DEV, 3)

                    # get the device health from DNA Center
                    current_time_epoch = utils.get_epoch_current_time()
                    device_details = dnac_apis.get_device_health(device, current_time_epoch, dnac_token)

                    device_sn = device_details['serialNumber']
                    device_mngmnt_ip_address = device_details['managementIpAddr']
                    device_family = device_details['platformId']
                    device_os_info = device_details['osType'] + ',  ' + device_details['softwareVersion']
                    device_health = device_details['overallHealth']

                    updated_comment = '\nDevice location: ' + location
                    updated_comment += '\nDevice family: ' + device_family
                    updated_comment += '\nDevice OS info: ' + device_os_info
                    updated_comment += '\nDevice S/N: ' + device_sn
                    updated_comment += '\nDevice Health: ' + str(device_health) + '/10'
                    updated_comment += '\nDevice management IP address: ' + device_mngmnt_ip_address

                    print(updated_comment)

                    # update ServiceNow incident
                    service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)

                    updated_comment = '\nThe configuration changes are\n' + diff + '\n\n' + user_info

                    print(updated_comment)

                    # update ServiceNow incident
                    service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)

                    # start the compliance validation
                    # ACL changes
                    validation_result = 'Pass'
                    validation_comment = ''
                    if ('+access-list' in diff) or ('-access-list' in diff):
                        updated_comment = '\nValidation against ACL changes failed'
                        service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)
                        validation_result = 'Failed'
                    else:
                        validation_comment = '\nPassed ACL Policy'

                    # logging changes
                    if ('+logging' in diff) or ('-logging' in diff):
                        updated_comment = '\nValidation against logging changes failed'
                        service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)
                        validation_result = 'Failed'
                    else:
                        validation_comment += '\nPassed Logging Policy'

                    # IPv4 duplicates
                    diff_list = diff.split('\n')
                    diff_config = '!\n'
                    for command in diff_list:
                        if 'ip address' in command:
                            diff_config += command.replace('+', '') + '\n!'

                    # save the diff config that include only IP addresses in a file
                    f_diff = open('temp_config_file.txt', 'w')
                    f_diff.write(diff_config)
                    f_diff.seek(0)  # reset the file pointer to 0
                    f_diff.close()

                    duplicate_ip_result = dnac_apis.check_ipv4_duplicate('temp_config_file.txt')
                    if duplicate_ip_result:
                        updated_comment = '\nValidation against duplicated IPv4 addresses failed'
                        service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)
                        validation_result = 'Failed'
                    else:
                        validation_comment += '\nPassed Duplicate IPv4 Prevention'

                    print(updated_comment)

                    # procedure to restore configurations as policy validations failed
                    if validation_result == 'Failed':
                        updated_comment = '\nConfiguration changes do not pass validation,\nConfiguration roll back initiated'
                        service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)

                        print(updated_comment)

                        # start the config roll back
                        baseline_config = 'flash:/config_mon_baseline'
                        netconf_restconf.restconf_rollback_to_saved_config(baseline_config, device_mngmnt_ip_address, IOS_XE_USER, IOS_XE_PASS)

                        # check if rollback is successful after 5 seconds
                        time.sleep(5)
                        device_run_config = dnac_apis.get_output_command_runner('show running-config', device, dnac_token)
                        filename = str(device) + '_run_config.txt'

                        # save the running config to a temp file
                        f_temp = open(temp_run_config, 'w')
                        f_temp.write(device_run_config)
                        f_temp.seek(0)  # reset the file pointer to 0
                        f_temp.close()

                        diff = compare_configs(filename, temp_run_config)
                        if diff != ' ':
                            updated_comment = '\nConfiguration rolled back successfully'
                            service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)
                            # close ServiceNow incident
                            service_now_apis.close_incident(incident,SNOW_DEV)
                        else:
                            updated_comment = '\nConfiguration rolled back not successful'
                            service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)

                    # start procedure to ask for approval as validation passed
                    else:
                        service_now_apis.update_incident(incident, 'Approve these changes (YES/NO)?\n' + validation_comment, SNOW_DEV)
                        service_now_apis.update_incident(incident, 'Waiting for Management Approval', SNOW_DEV)

                        print('\nConfiguration changes pass compliance checks, approval waiting')

                        # start the approval YES/NO procedure
                        # start a loop to check for 2 min if approved of not
                        approval = 'NO'
                        timer_count = 0
                        while timer_count <= 5:
                            if service_now_apis.find_comment(incident, 'YES'):

                                # start the save of running config to new baseline on device
                                # flash:/config_mon_baseline

                                netconf_restconf.netconf_save_running_config_to_file('flash:/config_mon_baseline',
                                                                                     device_mngmnt_ip_address,
                                                                                     IOS_XE_PORT, IOS_XE_USER,
                                                                                     IOS_XE_PASS)

                                print('New baseline configuration saved on network device: ' + device)

                                # establish new baseline config on server
                                time.sleep(5)
                                device_run_config = dnac_apis.get_output_command_runner('show running-config', device, dnac_token)
                                filename = str(device) + '_run_config.txt'

                                # save the running config to the device config file
                                f_temp = open(filename, 'w')
                                f_temp.write(device_run_config)
                                f_temp.seek(0)  # reset the file pointer to 0
                                f_temp.close()

                                approval = 'YES'

                                # update ServiceNow incident
                                updated_comment = '\nApproval received, saved device configuration, established new baseline configuration'
                                print(updated_comment)

                                service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)
                                service_now_apis.close_incident(incident, SNOW_DEV)
                                break
                            elif service_now_apis.find_comment(incident, 'NO'):
                                break
                            else:
                                timer_count += 1
                                time.sleep(10)
                                if timer_count == 5:
                                    service_now_apis.update_incident(incident, 'Approval Timeout', SNOW_DEV)

                        # check if Approval is 'NO' at the end of the timer
                        if approval == 'NO':

                            # start the config roll back
                            baseline_config = 'flash:/config_mon_baseline'
                            netconf_restconf.restconf_rollback_to_saved_config(baseline_config,
                                                                               device_mngmnt_ip_address, IOS_XE_USER,
                                                                               IOS_XE_PASS)

                            # check if rollback is successful after 3 seconds
                            time.sleep(5)
                            device_run_config = dnac_apis.get_output_command_runner('show running-config', device,
                                                                                    dnac_token)
                            # save the running config to a temp file
                            f_temp = open(temp_run_config, 'w')
                            f_temp.write(device_run_config)
                            f_temp.seek(0)  # reset the file pointer to 0
                            f_temp.close()

                            filename = str(device) + '_run_config.txt'

                            diff = compare_configs(filename, temp_run_config)
                            if diff != ' ':
                                updated_comment = '\nConfiguration changes not approved,\nConfiguration rolled back successfully'
                                print(updated_comment)

                                service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)
                                service_now_apis.close_incident(incident, SNOW_DEV)
                            else:
                                updated_comment = '\nConfiguration changes not approved,\nConfiguration rolled back not successful'
                                service_now_apis.update_incident(incident, updated_comment, SNOW_DEV)

                else:
                    print('Device: ' + device + ' - No configuration changes detected')

            else:
                # new device discovered, save the running configuration to a file in the folder with the name
                # {Config_Files}

                f_config = open(filename, 'w')
                f_config.write(device_run_config)
                f_config.seek(0)
                f_config.close()

                # retrieve the device management IP address

                device_mngmnt_ip_address = dnac_apis.get_device_management_ip(device, dnac_token)

                # Save the running configuration as a baseline configuration local on each device
                # flash:/config_mon_baseline

                netconf_restconf.netconf_save_running_config_to_file('flash:/config_mon_baseline', device_mngmnt_ip_address,
                                                                    IOS_XE_PORT, IOS_XE_USER, IOS_XE_PASS)

                print('Device: ' + device + ' - New device discovered')

        print('Wait for 10 seconds and start again')
        time.sleep(10)

    print('\n\nEnd of Application Run')


if __name__ == '__main__':
    main()
