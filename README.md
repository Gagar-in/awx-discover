# awx

Enter AWX containter and make changes there so ansible can use nmap to discover hosts
yum -y install nmap

vi /etc/ansible/ansible.cfg
[defaults]
inventory      = inventory
...
[inventory]
enable_plugins = host_list, ini, yaml, constructed, nmap

In AWX create Inventory (Save), then go to Inventory Sources (Add), create "Sourced from Project" select inventory file as /(project root) and make sure to check "Update on project update" checkbox
