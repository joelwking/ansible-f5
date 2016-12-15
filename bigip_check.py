#!/usr/bin/python
#
"""
     Copyright (c) 2016 World Wide Technology, Inc.
     All rights reserved.

     Revision history:

     6 December 2016  |  1.0 - initial release
     14 December 2016 |  1.1 - Output device information
     14 December 2016 |  1.2 - added import logic for Ansible Tower

"""
DOCUMENTATION = '''

---

module: bigip_check
author: Joel W. King, World Wide Technology
version_added: "1.2"
short_description: check if BIG_IP device is ready for configuration

description:
    - Check if the BIG_IP device is responds to iControl API calls, optionally save the config and reload the device.
    - The timeout value is the dead interval, the interval value is a time between connection attempts.
    - Using the default values of 10 and 40, the four attempts are made, 10 seconds apart.
    - Output are ansible facts describing the device.

requirements:
    -  ansible-f5/icontrol_install_config.py from https://github.com/joelwking

options:
    host:
        description:
            - IP address (or hostname) of BIG_IP device
        required: true

    password:
        description:
            - password for authentication
        required: true

    username:
        description:
            - username for authentication
        required: false
        default: "admin"

    reload:
        description:
            - boolean indicating if the device should be reloaded
        required: false
        default: false

    save_config:
        description:
            - boolean indicating if the device configuration should be saved
            - the config will be saved before the option reload is attempted
        required: false
        default: false

    timeout:
        description:
            - timeout of API calls
        required: false
        default: 40

    interval:
        description:
            - time waited between checks
        required: false
        default: 10
'''

EXAMPLES = '''

  - name: check if the big_ip is ready
    bigip_check:
       host: "{{inventory_hostname}}"
       password: "{{password}}"
       username: admin    # these  arguments are optional, default values shown
       reload: false
       save_config: false
       timeout: 40
       interval: 10

  - name: show facts output
    debug: msg="version is {{bigip.version}} {{bigip.marketingName}} {{bigip.build}} {{bigip.chassisId}}"

'''

class Check(object):

    def __init__(self):
        self.changed = 0
        self.save_command = '{"command":"save"}'
        self.reload_command =  '{"command":"reboot"}'

    def save_config(self, device):
        device.uri =  device.validate_uri("/mgmt/tm/sys/config/")
        if device.genericPOST(self.save_command):
            return True

        return False

    def reload_device(self, device):
        device.uri =  device.validate_uri("/mgmt/tm/sys/config/")
        if device.genericPOST(self.reload_command):
            return True

        return False

    def test_ready(self, device):
        """ test if the BIG-IP is ready

        Mark's recommendation is to issue GET https://10.255.111.29/mgmt/tm/services
        and in the 'items' look for 'name' 'tmm' and 'mcpd' and 'isActive' of true

        """
        device.uri =  device.validate_uri("/mgmt/tm/cm/device/")
        return device.genericGET()

    def device_changed(self):
        ""
        if self.changed:
            return True
        return False

    def build_facts(self, response):
        "Format the output of the module as Ansible facts"
        try:
            return response["items"][0]
        except:
            return dict(error="Response not valid")


def main():
    module = AnsibleModule(
        argument_spec=dict(
        host=dict(required=True),
        username=dict(default='admin'),
        password=dict(required=True),
        save_config=dict(default=False, type='bool'),
        reload=dict(default=False, type='bool'),
        timeout=dict(default=40, type='int'),
        interval=dict(default=10, type='int')
        )
    )

    #  When running under Ansible Tower, put this module in /usr/share/ansbile
    #  and modify your ansible.cfg file to include
    #   library = /usr/share/ansible/
    try:
        import icontrol_install_config as iControl
    except ImportError:
        sys.path.append("/usr/share/ansible")

    try:
        import icontrol_install_config as iControl
    except ImportError:
        module.fail_json(msg="icontrol_install_config required for this module")
    import time

    f5 = iControl.BIG_IP(host=module.params["host"], username=module.params["username"], password=module.params["password"])
    me = Check()

    if module.params["save_config"]:
        if me.save_config(f5):
            me.changed += 1
        else:
            module.fail_json(msg="Save config failed")

    if module.params["reload"]:
        if me.reload_device(f5):
            me.changed += 1
        else:
            module.fail_json(msg="Reload failed")

    for increment in range(0, module.params["timeout"], module.params["interval"]):
        if me.test_ready(f5):
            facts = me.build_facts(f5.response)
            module.exit_json(changed=me.device_changed(), msg="Ready", ansible_facts=dict(bigip=facts))         
        time.sleep(module.params["interval"])

    module.fail_json(msg="Device not ready")

from ansible.module_utils.basic import *
main()
#