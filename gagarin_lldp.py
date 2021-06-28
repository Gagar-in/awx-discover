# TODO: Add caching support
# https://docs.ansible.com/ansible/latest/dev_guide/developing_inventory.html#developing-inventory

DOCUMENTATION = '''
    author: Andrei Tutolmin (gagar-in.com)
    name: gagarin_lldp
    short_description: Uses LLDP to discover hosts on the network
    description:
        - Uses a YAML configuration file with a valid YAML extension.
    extends_documentation_fragment:
      - constructed
      - inventory_cache
    requirements:
      - lldpctl installed on a switch
      - ansible user with sudo privileges on a switch
    options:
        plugin:
            description: token that ensures this is a source file for the 'gagarin_lldp' plugin.
            required: True
            choices: ['gagarin_lldp']
        sw_addr:
            description: IPv4 address of the switch which has lldpd running
            required: True
'''
EXAMPLES = '''
# inventory.config file in YAML format
plugin: gagarin_lldp
sw_addr: 192.168.188.161
'''

import os
import re
import json

from subprocess import Popen, PIPE

from ansible import constants as C
from ansible.errors import AnsibleParserError
from ansible.module_utils._text import to_native, to_text
# from ansible.plugins.inventory import BaseInventoryPlugin
from ansible.plugins.inventory import BaseInventoryPlugin, Constructable, Cacheable
from ansible.module_utils.common.process import get_bin_path

# class InventoryModule(BaseInventoryPlugin):
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

    NAME = 'gagarin_lldp'  # used internally by Ansible, it should match the file name but not required
    find_mac = re.compile(r'^1c:a0:ef(:([0-9A-Fa-f]{2})){3}$')

    def __init__(self):
        self._ssh = None
        super(InventoryModule, self).__init__()

    def _populate(self, hosts):
        # Use constructed if applicable
        strict = self.get_option('strict')

        for host in hosts:
            hostname = host['name']
            self.inventory.add_host(hostname)
            for var, value in host.items():
#                print( f"{var} {value}")
                self.inventory.set_variable(hostname, var, value)

            # Composed variables
            self._set_composite_vars(self.get_option('compose'), host, hostname, strict=strict)

            # Complex groups based on jinja2 conditionals, hosts that meet the conditional are added to group
            self._add_host_to_composed_groups(self.get_option('groups'), host, hostname, strict=strict)

            # Create groups based on variable values and add the corresponding hosts to it
            self._add_host_to_keyed_groups(self.get_option('keyed_groups'), host, hostname, strict=strict)

    def verify_file(self, path):

        valid = False
        if super(InventoryModule, self).verify_file(path):
            file_name, ext = os.path.splitext(path)

            if not ext or ext in C.YAML_FILENAME_EXTENSIONS:
                valid = True

        return valid

    def is_bmc(self, hits):
        N = hits.group(2)
        l = len(N)

        # check if the last digit
        # is either '0', '2', '4',
        # '6', '8', 'A'(=10),
        # 'C'(=12) or 'E'(=14)
        if (N[l - 1] == '0'or N[l - 1] == '2'or
            N[l - 1] == '4'or N[l - 1] == '6'or
            N[l - 1] == '8'or N[l - 1] == 'a'or
            N[l - 1] == 'c'or N[l - 1] == 'e'):
            return False
        else:
            return True

    def parse(self, inventory, loader, path, cache=True):

        # check if ssh binary is available
        self._ssh = get_bin_path('ssh')
        if self._ssh == None:
            raise AnsibleParserError('gagarin_lldp inventory plugin requires the ssh cli tool to work: {0}')

#        print(f"self._ssh={self._ssh}")

        # call base method to ensure properties are available for use with other helper methods
        super(InventoryModule, self).parse(inventory, loader, path, cache)

        self._read_config_data(path)

        # setup command
        cmd = [self._ssh]
        cmd.append(self._options['sw_addr'])
        cmd.append('sudo lldpctl -f json')

#        print(f"cmd={cmd}")

        try:
            # execute
            p = Popen(cmd, stdout=PIPE, stderr=PIPE)
            stdout, stderr = p.communicate()
            if p.returncode != 0:
                raise AnsibleParserError('Failed to run ssh, rc=%s: %s' % (p.returncode, to_native(stderr)))

#            print(f"stdout={stdout}")
#            print(f"stderr={stderr}")

        except Exception as e:
            raise AnsibleParserError("failed to parse %s: %s " % (to_native(path), to_native(e)))

        # parse results
        host = None
        mac = None
        ip = None
        bmcs = []
        srvs = []

        try:
            t_stdout = to_text(stdout, errors='surrogate_or_strict')
        except UnicodeError as e:
            raise AnsibleParserError('Invalid (non unicode) input returned: %s' % to_native(e))

#        print(f"t_stdout={t_stdout}")

        dictData = json.loads( t_stdout)

#        print(f"lldp={dictData['lldp'][0]}")

        for record in dictData['lldp'][0]['interface']:

            mac = record['port'][0]['id'][0]['value']
#            print(f"port: {record['name']} connected to {record['chassis'][0]['name'][0]['value']} with IPv4 {record['chassis'][0]['mgmt-ip'][0]['value']} ({record['port'][0]['id'][0]['value']})")

            hits = self.find_mac.match(mac)
            if hits:
#                print(f"match {hits.group(2)}")
#                print(dir(hits))

                if self.is_bmc(hits):
#                    print( f"BMC")
                    bmcs.append(dict())
                    bmcs[-1]['is_bmc'] = True 
                    bmcs[-1]['name'] = record['chassis'][0]['mgmt-ip'][0]['value']
                    bmcs[-1]['ip'] = record['chassis'][0]['mgmt-ip'][0]['value']
                else:
#                    print( f"Host")
                    srvs.append(dict())
                    srvs[-1]['is_host'] = True 
                    srvs[-1]['name'] = record['chassis'][0]['mgmt-ip'][0]['value']
                    srvs[-1]['ip'] = record['chassis'][0]['mgmt-ip'][0]['value']

        self._populate(bmcs)
        self._populate(srvs)
