#!/usr/bin/env python

"""
     Copyright (c) 2015 World Wide Technology, Inc. 
     All rights reserved. 

     Revision history:
     2 December 2015  |  1.0 - initial release
     3 December 2015  |  1.1 - cosmetic and best practices updates.
     14 December 2016 |  1.2 - address name conflict with 'items'
     20 April 2017    |  1.3 - https://github.com/joelwking/ansible-f5/issues/2

 
"""

DOCUMENTATION = '''
---
module: icontrol_gather_facts
author: Joel W. King (@joelwking)
version_added: "2.0"
short_description: Gathers Ansible facts from F5 appliance
description:
    - This module issues a REST API call to an F5 appliance and returns facts to the playbook for subsequent tasks.
      As an alternative to bigip_facts_module (http://docs.ansible.com/ansible/bigip_facts_module.html), this module
      uses REST API rather than SOAP API and allows the use to specify any valid URI on the command line


references:
      iControl REST API User Guide Version 12.0

requirements:
    - none

options:
    host:
        description:
            - The IP address or hostname of the F5 appliance
        required: true

    username:
        description:
            - Login username
        required: true

    password:
        description:
            - Login password
        required: true

    uri:
        description:
            - URI to query for facts
        required: true

    debug:
        description:
            - debug switch
        required: false


'''

EXAMPLES = '''

    - name: Get facts from an F5
      icontrol_gather_facts:
        uri: "/mgmt/tm/ltm/virtual"
        host: "{{inventory_hostname}}"
        username: admin
        password: "{{password}}"

    - name: debug output
      debug: msg="{{item.name}} {{item.fullPath}} {{item.pool}}"
      with_items: "{{bigip_items}}"


'''


import sys
import time
import json
import requests

# ---------------------------------------------------------------------------
# F5 icontrol REST Connection Class
# ---------------------------------------------------------------------------
class Connection(object):
    """
      Connection class for Python to F5 REST calls
 
    """
    def __init__(self, host="192.0.2.1", username="admin", password="redacted", debug=False):                    
        self.transport = "https://"
        self.appliance = host
        self.username = username
        self.password = password
        self.debug = debug
        self.HEADER = {"Content-Type": "application/json"}
        return
#
#
#
    def genericGET(self, URI):
        """
            We are using requests to issue a command similar to the following:
              curl -k -u admin:redacted -X GET https://192.0.2.1/mgmt/tm/ltm/virtual

        """
        URI = "%s%s%s" % (self.transport, self.appliance, URI)
        try:
            r = requests.get(URI, auth=(self.username, self.password), headers=self.HEADER, verify=False)
        except requests.ConnectionError as e:
            return (False, e)
        content = json.loads(r.content)
        return (r.status_code, content)


# ---------------------------------------------------------------------------
# get_facts
# ---------------------------------------------------------------------------

def get_facts(F5, uri):
    """ 
        Issue a GET of the URI specified to the F5 appliance and return the result as facts.
        If the URI must have a slash as the first character, add it if missing

        In Ansible 2.2 found name clashing
        http://stackoverflow.com/questions/40281706/cant-read-custom-facts-with-list-array-of-items
    """
    result = { 'ansible_facts': {} }
                     
    if uri[0] != "/":
        uri = "/" + uri
    
    status, result["ansible_facts"]  = F5.genericGET(uri)
    try:
        result["ansible_facts"]["bigip_items"] = result["ansible_facts"].pop("items")   # replace key name of 'items' with 'bigip_items'
    except:
        result["ansible_facts"]["bigip_items"] = dict()
    return status, result

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    "   "
    module = AnsibleModule(
        argument_spec = dict(
            host = dict(required=True),
            username = dict(required=True),
            password  = dict(required=True, no_log=True),
            uri  = dict(required=True),
            debug = dict(required=False)
         ),
        check_invalid_arguments=False,
        add_file_common_args=True
    )
    
    F5 = Connection(host=module.params["host"], username=module.params["username"], password=module.params["password"])
    code, response = get_facts(F5, module.params["uri"])

    if code == 200:
        module.exit_json(**response)
    else:
        module.fail_json(msg="status_code= %s %s" % (code, response))
    
from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
