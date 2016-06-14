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
     28 Mar    2016   |  1.8 - style changes to satisfy Phantom cyber compilation
     31 May    2016   |  2.0 - type="bool" on debug  Ansible 2.1
     31 May    2016   |  2.1 - JSON expects double quotes around key, value pairs
      2 June   2016   |  2.2 - JSON
      2 June   2016   |  3.0 - cyber5 branch re-write
      8 June   2016   |  3.1 - modified trailing slash logic
      8 June   2016   |  3.2 - body can be either a string or a dictionary added isinstance
      9 June   2016   |  3.3 - documentation update, corrected default value for body, flake8 style updates
     10 June   2016   |  3.4 - added _POST_ method option, which does not fall back to PATCH
     14 June   2016   |  3.5 - flake8 cosmetic changes

"""

DOCUMENTATION = '''
---
module: icontrol_install_config.py
author: Joel W. King, World Wide Technology
version_added: "3.5"
short_description: Ansible module to POST, DELETE and PATCH (update) using the REST API of an F5 BIG_IP
description:
    - This module is a intended to be a demonstration and training module to update an F5 BIG_IP configuration
      from Ansible playbooks. It is intended to provide means where the URL and body (in JSON) from Chrome
      Postman or the cURL examples in the F5 API documentation can be used in a playbook to demonstrate how to
      create playbooks.

      If the user has specified POST (which is the default value) and the object exists, we modify the URL and
      body and issue a PATCH instead. If _POST_ is specified as the method, do not fallback to PATCH.

      This module is also used in the Phantom Cyber F5 app.


references:
      http://docs.ansible.com/
      iControl(tm) REST API User Guide Version 12.0


requirements:
    - none

options:
    host:
        description:
            - The IP address or hostname of the F5 BIG_IP
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
            - URI
        required: true
    method:
        description:
            - PATCH (update), DELETE, _POST_ or POST. POST is the default.
        required: false
    body:
        description:
            -  string representation of JSON
                 e.g. '{"name":"NEW_WIDEIP","pools":[{"name":"NEW_POOL","partition":"Common","order":0,"ratio":1}]}'
        required: false
    debug:
        description:
            - debug  switch, for future use.
        required: false


'''

EXAMPLES = '''

  - name: 20 Create LTM Node (default method of POST)
    icontrol_install_config:
      uri: "/mgmt/tm/ltm/node"
      body: '{"name": "foo", "address": "192.0.2.63"}'
      host: "{{ltm.hostname}}"
      username: admin
      password: "{{password}}"

  - name: 21 Create LTM Node (_POST_)
    icontrol_install_config:
      uri: "/mgmt/tm/ltm/node"
      body: '{"name":"{{item.name}}", "address":"{{item.address}}" }'
      method: "_post_"
      host: "{{ltm.hostname}}"
      username: admin
      password: "{{password}}"
    with_items: "{{spreadsheet}}"

  - name: 30 Update LTM Node using PATCH
    icontrol_install_config:
      uri: "/mgmt/tm/ltm/node/foo"
      body: '{"description": "the quick brown fox jumped."}'
      method: PATCH
      host: "{{ltm.hostname}}"
      username: admin
      password: "{{password}}"

  - name: 41 Delete LTM Node, body not specified
    icontrol_install_config:
      uri: "/mgmt/tm/ltm/node/bar"
      method: DELETE
      host: "{{ltm.hostname}}"
      username: admin
      password: "{{password}}"

  - name: 50 Create LTM Pool, specify POST method
    icontrol_install_config:
      uri: "/mgmt/tm/ltm/pool/"
      body: '{"name": "NEW_POOL", "monitor": "/Common/http"}'
      method: "POST"
      host: "{{ltm.hostname}}"
      username: admin
      password: "{{password}}"

    # Given these variables, note how the JSON string in body is coded
    spreadsheet:
        - name: foo
          address: "192.0.2.65"
    boolean_true: true

  - name: 80 Test body with boolean
    icontrol_install_config:
      uri: "/mgmt/tm/net/vlan/~Common~1.3/interfaces"
      # Note the string variable for name has double quotes, the boolean value of tagged does not
      body: '{"name":"{{spreadsheet[0].name}}","tagged":{{boolean_true}}}'
      method: POST
      host: "{{ltm.hostname}}"
      username: admin
      password: "{{password}}"

'''

import json
import requests
import requests.packages.urllib3
requests.packages.urllib3.disable_warnings()

# ---------------------------------------------------------------------------
# F5 icontrol REST Connection Class
# ---------------------------------------------------------------------------


class BIG_IP(object):
    """
      Connection class for Python to F5 BIG-IP iControl REST calls

    """
    HEADER = {"Content-Type": "application/json"}
    TRANSPORT = "https://"

    def __init__(self, host="192.0.2.1", username="admin", password="redacted", uri="/", method="POST", debug=False):
        self.BIG_IP_host = host
        self.username = username
        self.password = password
        self.uri = self.validate_uri(uri)
        self.method = method
        self.response = None
        self.status_code = 0
        self.changed = False
        self.debug = debug

        return

    def validate_uri(self, uri):
        " make certain the uri has a leading and trailing slash"

        if uri[0] != "/":                                  # check leading slash
            uri = "/" + uri

        if uri[-1] != "/":                                 # check trailing slash
            uri = uri + "/"

        return uri

    def genericDELETE(self):
        """ Delete a resource from F5 BIG_IP, return True if deleted successfully, return False if
            not. A return code of 200 does not populate the response, a 404 errors means the node
            was not found, but the response is populated.
            To delete a virtual server named foo, use https://192.0.2.1/mgmt/tm/ltm/virtual/foo
        """
        URI = "%s%s%s" % (BIG_IP.TRANSPORT, self.BIG_IP_host, self.uri)
        try:
            r = requests.delete(URI, auth=(self.username, self.password), headers=BIG_IP.HEADER, verify=False)
        except requests.ConnectionError as e:
            self.status_code = 599
            self.response = str(e)
            return None
        self.status_code = r.status_code
        try:
            self.response = r.json()                       # r.json() returns a dictionary
        except ValueError:                                 # If you get a 200, throws a ValueError exception
            self.response = None                           # there may not be a response

        if r.status_code == 200:                           # a 200 means we successfully deleted
            self.changed = True                            # we changed the state
            return True
        if r.status_code == 404:                           # a 404 error means the requested node was not found
            return True                                    # because this is the desired state, return True
        return False

    def genericGET(self, uri=None):
        """ Issue a GET request and return the results
            We are using requests to issue a command similar to the following:
              curl -k -u admin:redacted -X GET https://192.0.2.1/mgmt/tm/ltm/virtual
        """
        if not uri:
            uri = self.uri

        URI = "%s%s%s" % (BIG_IP.TRANSPORT, self.BIG_IP_host, uri)
        try:
            r = requests.get(URI, auth=(self.username, self.password), headers=BIG_IP.HEADER, verify=False)
        except requests.ConnectionError as e:
            self.status_code = 599
            self.response = str(e)
            return None
        self.status_code = r.status_code
        try:
            self.response = r.json()                       # r.json() returns a dictionary
        except ValueError:                                 # If you get a 404 error, throws a ValueError exception
            self.response = None

        if r.status_code == 200:
            return True
        return False

    def genericPOST(self, body):
        """
            Use POST to create a new configuration object from a JSON body.
        """
        URI = "%s%s%s" % (BIG_IP.TRANSPORT, self.BIG_IP_host, self.uri)
        try:
            r = requests.post(URI, auth=(self.username, self.password), data=body, headers=BIG_IP.HEADER, verify=False)
        except requests.ConnectionError as e:
            self.status_code = 599
            self.response = str(e)
            return None
        self.status_code = r.status_code
        try:
            self.response = r.json()
        except ValueError:
            self.response = None

        if r.status_code == 200:
            self.changed = True
            return True
        return False

    def genericPATCH(self, body):
        """
           PATCH to edit an existing configuration object with a JSON body.
           Need to formulate the URL with the name as part of the URL and NAME must not be in the body
        """
        URI = "%s%s%s" % (BIG_IP.TRANSPORT, self.BIG_IP_host, self.uri)
        try:
            r = requests.patch(URI, auth=(self.username, self.password), data=body, headers=BIG_IP.HEADER, verify=False)
        except requests.ConnectionError as e:
            self.status_code = 599
            self.response = str(e)
            return None
        self.status_code = r.status_code
        try:
            self.response = r.json()
        except ValueError:
            self.response = None

        if r.status_code == 200:
            self.changed = True
            return True
        return False

    def node_exists(self, body):
        """ Return true or false if the node specified in the URL exists- status_code is a 404 if not found
            Need to formulate a new URL by determining the name from the body and appending it to the URL
        """
        try:
            body = json.loads(body)
        except ValueError:
            return None

        try:
            name = body["name"]
        except KeyError:
            return None

        uri = self.uri + name                              # Now create a new URL with the uri and the name from the body.
        return self.genericGET(uri=uri)

    def modify_url_and_body(self, body):
        "Manipulate the URL and body to permit issueing a PATCH"

        try:
            body = json.loads(body)                        # JSON string to dictiionary
        except ValueError:
            pass                                           # body assumed to be a dictionary

        self.uri = self.uri + body['name']                 # add name to uri
        del body['name']                                   # delete name from dictionary
        body = json.dumps(body)                            # dictionary to JSON string

        return body

# ---------------------------------------------------------------------------
# icontrol_install_config methods
# ---------------------------------------------------------------------------


def install_config(F5, body):
    """
        If the node exists, attempt to issue PATCH, otherwise, issue POST. User has either specified
        a POST or defaulted to POST.
    """
    if F5.node_exists(body):
        body = F5.modify_url_and_body(body)
        return F5.genericPATCH(body)
    else:
        return F5.genericPOST(body)


def update_config(F5, body):
    " Called with a PATCH method, attempt to update the configuration"
    return F5.genericPATCH(body)


def delete_config(F5, body):
    " Attempt to delete the configuration specified by the URL, ignore the body"
    return F5.genericDELETE()


def POST_config(F5, body):
    " POST command which does not fail back to PATCH if node exists"
    return F5.genericPOST(body)


def main():
    "   "
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(required=True),
            username=dict(required=True),
            password=dict(required=True),
            uri=dict(required=True),
            body=dict(required=False, default=dict(), type="raw"),
            method=dict(required=False, default="POST"),
            debug=dict(required=False, default=False, type="bool")
          ),
        check_invalid_arguments=False
    )

    F5 = BIG_IP(host=module.params["host"],
                username=module.params["username"],
                password=module.params["password"],
                uri=module.params["uri"],
                method=module.params["method"].upper(),
                debug=module.params["debug"])

    # Case structure of the supported functions
    functions = {"PATCH": update_config,
                 "POST": install_config,
                 "_POST_": POST_config,
                 "DELETE": delete_config}

    try:
        run_function = functions[module.params["method"].upper()]
    except KeyError:
        module.fail_json(msg="Invalid method")

    body = module.params["body"]                           # body is a str when body: '{"name": "foo", "address": "192.0.2.63"}'
    if isinstance(body, dict):                             # body is a dict when body: '{"name": "{{item.name}}"}'
        body = json.dumps(body)

    ret_code = run_function(F5, body)

    if ret_code:
        module.exit_json(changed=F5.changed, content=F5.response)
    else:
        module.fail_json(msg="%s %s" % (F5.status_code, F5.response))
    return

try:
    from ansible.module_utils.basic import *
except ImportError:
    pass                                                   # Also used outside Ansible framework

if __name__ == '__main__':
    " Main program logic."
    main()
