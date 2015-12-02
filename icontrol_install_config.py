#!/usr/bin/env python

"""
     Copyright (c) 2015 World Wide Technology, Inc. 
     All rights reserved. 

     Revision history:
     2 December 2015  |  1.0 - initial release
 
"""

DOCUMENTATION = '''
---
module: icontrol_install_config.py
author: Joel W. King, World Wide Technology
version_added: "1.0"
short_description: foo
description:
    - Bar.


references:
      http://docs.ansible.com/

 
requirements:
    - none

options:
    host:
        description:
            - The IP address or hostname of the F5
        required: true

    username:
        description:
            - Login username
        required: true

    password:
        description:
            - Login password
        required: true

    debug:
        description:
            - debug switch
        required: false


'''

EXAMPLES = '''

      ansible localhost -m icontrol_install_config -a "uri=/mgmt/tm/ltm/node, host=192.0.2.1, username=admin, password=redacted, body='name=bogturtle.example.net,address=192.0.2.15,partition=Common,rateLimit=disabled'"


'''


import sys
import time
import json
import httplib
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
    def genericPOST(self, URI, body):
        """
            Use POST to create a new configuration object from a JSON body, 
            and use PUTor PATCH to edit an existing configuration object with a JSON body.
        """
        URI = "%s%s%s" % (self.transport, self.appliance, URI)
        body = json.dumps(body)
        try:
            r = requests.post(URI, auth=(self.username, self.password), data=body, headers=self.HEADER, verify=False)
        except requests.ConnectionError as e:
            return (False, e)
        try:
            content = json.loads(r.content)
        except ValueError as e:
            content = e                                    # ACI populates the field content, F5 apparently does not
        return (r.status_code, content)

# ---------------------------------------------------------------------------
# install_config
# ---------------------------------------------------------------------------

def install_config(F5, uri, body):
    """ 
        Issue a POST for a new configuration, PUT to edit an existing config.
        If the URI must have a slash as the first character, add it if missing.
        body is a string representation of a dictionary, e.g. "monitor=/Common/bigip,name=DC2_LTM,partition=Common"
   
    """
    ### Currently this logic only issues a POST and CHANGED is always TRUE ###
    changed = True
    response_requested = ""
                     
    body = dict(x.split('=') for x in body.split(','))

    if uri[0] != "/":
        uri = "/" + uri
    
    rc, response = F5.genericPOST(uri, body)
    if rc == 200:
        if F5.debug:                                    # when debug enabled, include
            response_requested = response               # response data in output 
        return (0, changed, "%s: %s %s" % (rc, httplib.responses[rc], response_requested))
    else:
        return (1, False, "%s: %s %s" % (rc, httplib.responses[rc], response))


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    "   "
    module = AnsibleModule(
        argument_spec = dict(
            host = dict(required=True),
            username = dict(required=True),
            password  = dict(required=True),
            uri = dict(required=True),
            body = dict(required=True),
            debug = dict(required=False, default=False, choices=BOOLEANS)
         ),
        check_invalid_arguments=False,
        add_file_common_args=True
    )

    F5 = Connection(host=module.params["host"], 
                    username=module.params["username"], 
                    password=module.params["password"],
                    debug=module.params["debug"])

    code, changed, response = install_config(F5, module.params["uri"], module.params["body"])
    if code == 1:
        module.fail_json(msg=response)
    else:
        module.exit_json(changed=changed, content=response)

    return code

from ansible.module_utils.basic import *
main()
