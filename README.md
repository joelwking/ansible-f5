# ansible-f5
Ansible modules for managing F5 appliances. These modules are used for training and demonstrations of network programmability of F5 devices at the World Wide Technology, Inc. Advanced Technology Center.

## F5_sdk_LTM_node
This module and the playbook ```F5_sdk_LTM_node.yml``` use the F5 Python SDK released in March 2016.

## icontrol_install_config and icontrol_gather_facts
These modules illustrate the use of iControl REST API.

### Save Config Example
To get started, there is a playbook which simply saves the running config. Execute it by
<pre>
./save_F5_config.yml --ask-vault
</pre>
provided you have a file named passwords.yml with the variable "password" encrypted with Ansible Vault

## bigip_check
This module is used to optionally save the running config and reload the Big-IP device, and check if reachable. It also returns ansible_facts describing the characteristics of the device; name, platformId, version, timeZone, etc.
