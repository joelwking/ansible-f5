# ansible-f5
Ansible modules for managing F5 appliances using iControl REST

## Save Config Example
To get started, there is a playbook which simply saves the running config. Execute it by
<pre>
./save_F5_config.yml --ask-vault
</pre>
provided you have a file named passwords.yml with the variable "password" encrypted with Ansible Vault
