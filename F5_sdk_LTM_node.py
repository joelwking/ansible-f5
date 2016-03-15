#!/usr/bin/env python

"""
     Copyright (c) 2016  World Wide Technology, Inc. 
     All rights reserved. 

     Revision history:
     14 March 2016  |  1.0 - initial release
     15 March 2016  |  1.1 - Added exception handling and fixed logic errors

 
"""

DOCUMENTATION = '''
---
module: F5_sdk_LTM_node.py
author: Joel W. King, World Wide Technology
version_added: "1.1"
short_description: Ansible module demonstrating the use of the F5 Python SDK
description:
    - This module is a intended to be a demonstration and training module to update an F5 appliance configuration
      from Ansible using the F5 Python SDK


references:
    - devcentral.f5.com/articles/f5-friday-python-sdk-for-big-ip-18233

 
requirements:
    - Python SDK for configuration and monitoring of F5 BigIP devices via the iControl REST API. f5-sdk.readthedocs.org

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

    partition:
        description:
            -  F5 partition
        required: false
    
    description:
        description:
            -  description of the node
        required: false

    name:
        description:
            -  F5 node name
        required: true

    address:
        description:
            -  IP address of the F5 node
        required: true

    state:
        description:
            -  either present or absent, add/update or delete
        required: true

'''

EXAMPLES = '''

    - name: F5_sdk_LTM_node
      F5_sdk_LTM_node:
        partition: Common
        state: present
        name: EasternMudTurtle.example.net
        address: 192.0.2.35
        description: Kinosternon subrubrum
        host: "{{hostname}}"
        username: admin
        password: "{{password}}"


'''

from f5.bigip import BigIP

class LTM(object):
    "Local Traffic Manager"

    def __init__(self, bigip, name, partition):
        self.bigip = bigip
        self.changed = False
        self.response = "no response specified"
        self.failed = 0
        self.name = name
        self.partition = partition

    def set_changed_flag(self, flag):
        self.changed = flag
        return

    def get_changed_flag(self):
        return self.changed

    def set_response(self, response):
        self.response = response
        return

    def get_response(self):
        return self.response

    def failure(self):
        return self.failed

    def delete_LTM(self):
        "Delete the LTM node"
        try:
            ltm = self.bigip.ltm.nodes.node.load(name=self.name, partition=self.partition)
            ltm.delete()
            self.set_changed_flag(True)
            self.response = "%s deleted: %s" % (self.name, ltm.deleted)
        except Exception as e:
            self.response = "Exception in delete_LTM  %s " % (e)
            self.failed = 1
        return

    def update_LTM(self, description):
        "Update the LTM node"
        # Add logic to update the LTM
        self.response = "Logic not implemented, update_LTM"
        self.failed = 1
        return

    def create_LTM(self, address, description):
        "Create the LTM node"
        try:
            ltm = self.bigip.ltm.nodes.node.create(name=self.name, partition=self.partition, address=address, description=description)
            self.set_changed_flag(True)
            self.response = "%s exists: %s" % (self.name, ltm.exists(name=self.name))
        except Exception as e:
            self.response = "Exception in create_LTM %s" % (e)
            self.failed = 1
        return

    def node_exists(self, name, partition):
        "Check if the node exists and we have a valid username, hostname and password"
        try:
            return self.bigip.ltm.nodes.node.exists(name=name, partition=partition)
        except Exception as e:
            self.response = "Exception in node_exists %s" % (e)
            self.failed = 1
            return False


def main():
    "   "
    module = AnsibleModule(
        argument_spec = dict(
            host = dict(required=True),
            username = dict(required=True),
            password  = dict(required=True),
            address = dict(required=False),
            name = dict(required=True),
            description = dict(required=False, default="updated by F5_sdk_LTM_node"),
            state = dict(required=True, choices=['present', 'absent']),
            partition = dict(default='Common', required=False)
         ),
        check_invalid_arguments=False
    )

    name = module.params["name"]
    partition = module.params["partition"]
    description = module.params["description"]
    address = module.params["address"]
    delete_node = False

    if module.params["state"]  == "absent":
        # Absent indicates a request to delete the node
        delete_node = True

    bigip = BigIP(module.params["host"], module.params["username"], module.params["password"])
    obj = LTM(bigip, name, partition)


    if delete_node:
        if obj.node_exists(name, partition):
            obj.delete_LTM()
        else:
            obj.set_response("Asked to delete a node which does not exist")
    else:
        #  State is present
        if obj.node_exists(name, partition):
            obj.update_LTM(description)
        else:
            obj.create_LTM(address, description)


    if obj.failure():
        module.fail_json(msg=obj.get_response())
    else:
        module.exit_json(changed=obj.get_changed_flag(), content=obj.get_response())

    return


from ansible.module_utils.basic import *

if __name__ == '__main__':
    main()
