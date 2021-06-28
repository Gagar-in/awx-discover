# awx

* Enter AWX containter and make changes there so ansible can use nmap to discover hosts
**yum -y install nmap**

* Gagarin LLDP plugin
put it to **/usr/share/ansible/plugins/inventory/gagarin_lldp.py**

**vi /etc/ansible/ansible.cfg**
```
[defaults]
inventory      = inventory
inventory_plugins  = /usr/share/ansible/plugins/inventory
...
[inventory]
enable_plugins = nmap, constructed, gagarin_lldp
```

* Generate hostnames
```
for i in {1..199}; do printf "192.168.123.%d\tmgmt%03d\n" $i $i >> /etc/hosts; done
for i in {200..254}; do printf "192.168.123.%d\tcomp%03d\n" $i $i >> /etc/hosts; done
```

* In AWX create Inventory (Save), then go to Inventory Sources (Add), create "Sourced from Project" select inventory file as /(project root) and make sure to check "Update on project update" checkbox

* Sync the project and make sure the inventory gets updated

* In AWX container check ansible-inventory can discover the hosts
**ansible-inventory -i /var/lib/awx/projects/_8__test_get_inventory/inventory/ --graph -v --vars**

* In AWX create credential with username andrei or ansible and a private key

