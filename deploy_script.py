#!/usr/bin/python
import argparse
import subprocess
import getpass
import os
import sys
from time import sleep
from Crypto.PublicKey import RSA


class Deploy:

    def get_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('dhcp_ip', help='Enter DHCP address of new server', type=str)
        parser.add_argument('static_ip', help='Enter static ip to set for new server', type=str)
        parser.add_argument('remote_user', help='Enter username of remote user', type=str)
        parser.add_argument('playbook', help='Enter playbook yml file to run', type=str)
        parser.add_argument('env', help='Set environment you wish to deploy (dev, qa, stage, prod)', type=str)
        args = parser.parse_args()
        self.dhcp_ip = args.dhcp_ip
        self.static_ip = args.static_ip
        self.remote_user = args.remote_user
        self.playbook_file = args.playbook
        self.deploy_env = args.env
        self.local_user = getpass.getuser()
        self.ssh_key_dir = '/home/' + self.local_user + '/.ssh/'
        self.ssh_pub_key = self.ssh_key_dir + 'id_rsa.pub'
        self.ansible_host_file = '/etc/ansible/hosts'
        self.new_interface_setting = '''\"auto lo\n
                                    iface lo inet loopback\n
                                    auto eth1\n
                                    iface eth1 inet static\n
                                    address %s\n netmask 255.255.0.0\n
                                    gateway 10.0.0.1\n
                                    dns-nameservers 10.0.0.1\"''' % self.static_ip

    def set_env(self):
        json_params = '_params.json'

        if self.deploy_env == 'dev' or 'qa' or 'stage' or 'prod':
            self.deploy_file = self.deploy_env + json_params
            return (self.ansible_host_file +
                    self.new_interface_setting +
                    self.ssh_key_dir +
                    self.ssh_pub_key +
                    self.deploy_file)
        else:
            print "error: missing/wrong environment"

    def setup_ssh_keys(self):
        if not os.path.isfile(self.ssh_pub_key):
            os.mkdir(self.ssh_key_dir, 0700)
            os.chdir(self.ssh_key_dir)
            key = RSA.generate(2048)
            with open('id_rsa', 'w') as private_key:
                os.chmod('id_rsa', 0600)
                private_key.write(key.exportKey('PEM'))

            with open('id_rsa.pub', 'w') as public_key:
                public_key.write(key.exportKey('OPENSSH'))

            subprocess.call([
                    'cat',
                    self.ssh_pub_key,
                    ' | ',
                    'ssh',
                    self.remote_user + '@' + self.dhcp_ip,
                    '"mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"'
                        ], shell=True)
            self.setup_ssh_keys()

        else:
            copy_id = str(self.remote_user + '@' + self.dhcp_ip)
            subprocess.call(['ssh-copy-id', copy_id])

    def copy_static_key(self):
        copy_id = str(self.remote_user + '@' + self.static_ip)
        subprocess.call(['ssh-copy-id', copy_id])

    def setup_ansible(self):
        if not os.path.exists(self.ansible_host_file):
            subprocess.call([  # fix for to pip
                'sudo',
                'yum',
                '-y',
                'install',
                'ansible'
            ])
            self.setup_ansible()

        else:
            with open(self.ansible_host_file, 'w') as host_file:
                host_file.write(self.dhcp_ip)
                host_file.write("\n" + self.static_ip)

    def change_ip(self):
        host = self.remote_user + '@' + self.dhcp_ip
        command = '''sudo echo %s | awk \'{$1=$1};1\' > new_interface && \n
        sudo mv new_interface /etc/network/interfaces && \n
        sudo reboot
        ''' % self.new_interface_setting

        ssh_tunnel = subprocess.Popen([
            'ssh', '%s' % host, command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        result = ssh_tunnel.stdout.readlines()
        if result == []:
            error = ssh_tunnel.stderr.readlines()
            print >> sys.stderr, 'ERROR: %s' % error
        else:
            print result

    # running playbook via raw shell command (need to fix)
    def run_playbook(self):
        deploy_params = '{0} --extra-vars "@{1}"'.format(str(self.playbook_file), str(self.deploy_file))
        os.system('ansible-playbook %s' % deploy_params)

    def main(self):
        self.get_args()
        self.set_env()
        self.setup_ssh_keys()
        self.setup_ansible()
        self.change_ip()
        sleep(25)
        self.copy_static_key()
        self.run_playbook()

if __name__ == '__main__':
    Deploy().main()

