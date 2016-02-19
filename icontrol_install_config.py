#!/usr/bin/env python

"""
     Copyright (c) 2015 - 2016  World Wide Technology, Inc. 
     All rights reserved. 

     Revision history:
     2 December 2015  |  1.0 - initial release
     3 December 2015  |  1.1 - updates for testing GTM use case and added PATCH
     7 January 2016   |  1.2 - added logic to update existing objects (PUT or PATCH)
     8 January 2016   |  1.3 - added try/except when creating dictionary from body
     15 Jan    2016   |  1.4 - check that body is a string before jason.loads Ansible 2.0 upgrade issue
     12 Feb    2016   |  1.5 - added ability to specify method (PATCH), and refactor for phantom cyber app
     17 Feb    2016   |  1.6 - debugging parameters to AnsibleModule
     19 Feb    2016   |  1.7 - testing and document updates
 
"""

DOCUMENTATION = '''
---
module: icontrol_install_config.py
author: Joel W. King, World Wide Technology
version_added: "1.7"
short_description: Ansible module to PUT data to the REST API of an F5 appliance
description:
    - This module is a intended to be a demonstration and training module to update an F5 appliance configuration
      from Ansible. It provides similar functionallity to cURL, it is a first step in developing additional REST API
      capabilities using iControl REST API


references:
      http://docs.ansible.com/
      iControl(tm) REST API User Guide Version 12.0

 
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
    uri:
        description:
            - URI to PUT or POST
        required: true
    method:
        description:
            - allow specify PATCH as an override, POST is the default
        required: false
    body:
        description:
            - body the data PUT or POSTed to the F5, it is a string representation of a dictionary, 
                 e.g. "monitor=/Common/bigip,name=DC2_LTM,partition=Common"
              or a string representation of JSON
                 e.g. '{"name":"NEW_WIDEIP","pools":[{"name":"NEW_POOL","partition":"Common","order":0,"ratio":1}]}'

    debug:
        description:
            - debug switch
        required: false


'''

EXAMPLES = '''

      ansible localhost -m icontrol_install_config -a "uri=/mgmt/tm/ltm/node, host=192.0.2.1, username=admin, password=redacted, body='name=bogturtle.example.net,address=192.0.2.15,partition=Common,rateLimit=disabled'"

    - name: Update LTM node configuration, using PATCH
      icontrol_install_config:
          uri: "/mgmt/tm/ltm/node/bogturtle.example.net"
        body:  "partition=Common,rateLimit=disabled"
        host: "{{hostname}}"
        method: PATCH
        username: admin
        password: "{{password}}"

    - name: Create LTM Node using JSON, POST method is optional
      icontrol_install_config:
        uri: "/mgmt/tm/ltm/node"
        body: '{"name":"bluebird.example.net","address":"192.0.2.17"}'
        host: "{{hostname}}"
        username: admin
        password: "{{password}}"


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
        self.body = ""
        return



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
            return ("ConnectionError", e)
        try:
            content = json.loads(r.content)
        except ValueError as e:
            content = "F5 does not populate content in all conditions"
        return (r.status_code, content)



    def genericPATCH(self, URI, body):
        """
           PATCH to edit an existing configuration object with a JSON body.
           Need to formulate the URL with the name as part of the URL.
           Remove NAME from the body and attempt to PATCH, it may return a 400, 
           indicating that there are elements in the body which cannot be present to
           update the resource. In that case, we will not fail, but return that there
           is no change to the object.

        """
        URI = "%s%s%s" % (self.transport, self.appliance, URI)
        body = json.dumps(body)

        try:
            r = requests.patch(URI, auth=(self.username, self.password), data=body, headers=self.HEADER, verify=False)
        except requests.ConnectionError as e:
            return ("ConnectionError", e)
        try:
            content = json.loads(r.content)
        except ValueError as e:
            content = "F5 does not populate content in all conditions"
        return (r.status_code, content)



    def fix_body_url(self, URI, body):
        """
           if a POST fails with a 409, we modify the body by removing NAME and  and append to the URI, 
           this logic makes those modifications and returns a revised URI and body
        """
        try:
            name = body['name']
        except KeyError:
            # if name doesn't exist we can't change anything, return what we were sent
            return  URI, body

        # delete the name from the dictionary and add it to the URI
        del body['name']
        URI = "%s/%s" % (URI, name)
        self.body = body                                         # Save for debugging

        return URI, body



    def standarize_body_url(self, URI, body):
        """
            In your playbook, the body is a string representation of a dictionary, 
                body: "name=NEW_POOL,monitor=/Common/http"

            or a string representation of JSON    
                body: '{"name":"NEW_WIDEIP", "pools":[{"name":"NEW_POOL","partition":"Common","order":0,"ratio":1}]}'

            to determine which format, we will test for an equal sign.
            Add a slash to the beginning of the URI if missing.
        """
        if "=" in body:
            try:
                body = dict(x.split('=') for x in body.split(','))
            except ValueError:
                return (1, False, "syntax error creating dictionary from string in body")
        else:
            try:
                body = json.loads(body)                        # Ansible 1.9
            except TypeError:
                pass                                           # Ansible 2.0
        self.body = body                                       # Save for debugging

        if URI[0] != "/":
            URI = "/" + URI

        return URI, body



# ---------------------------------------------------------------------------
# install_config
# ---------------------------------------------------------------------------

def install_config(F5, uri, body):
    """ 
        Issue a POST for a new configuration, if that fails attempt to PATCH, which
        is updating an existing configuration
        
    """
                                 
    rc, response = F5.genericPOST(uri, body)              #  Attempt to create a new object, 
    if rc == 409:                                         #  409 means it exists, attempt a PATCH, it  modifies an existing object
        uri, body = F5.fix_body_url(uri, body)            #  remove the 'name' from the body and change the URL
        rc, response = F5.genericPATCH(uri, body)
        if rc == 400:                                     #  400 means the body contained elements we cannot update
            return (0, False, "rc %s: %s" % (rc, response))

    if rc == 200:
        return (0, True, "rc %s: %s" % (rc, response))
    else:
        return (1, False, "rc %s: %s" % (rc,  response))



# ---------------------------------------------------------------------------
# update_config
# ---------------------------------------------------------------------------

def update_config(F5, uri, body):
    """"
        we were called with a PATCH method, attempt to update the configuration
    """
    rc, response = F5.genericPATCH(uri, body)
    if rc == 200:
        return (0, True, "rc %s: %s" % (rc, response))
    else:
        return (1, False, "rc %s: %s" % (rc, response))



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
            method = dict(required=False, default="POST"),
            debug = dict(required=False, default=False, choices=BOOLEANS)
         ),
        check_invalid_arguments=False
    )



    F5 = Connection(host=module.params["host"], 
                    username=module.params["username"], 
                    password=module.params["password"],
                    debug=module.params["debug"])

    uri, body = F5.standarize_body_url(module.params["uri"], module.params["body"]) 

    if module.params["method"].upper() == "PATCH":
        code, changed, response = update_config(F5, uri, body)
    else:
        code, changed, response = install_config(F5, uri, body)
    if code == 1:
        module.fail_json(msg=response)
    else:
        module.exit_json(changed=changed, content=response)

    return code


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
