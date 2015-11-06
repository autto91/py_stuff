#!/usr/bin/python
import argparse
import subprocess
import getpass
import os
import sys
from time import sleep
from Crypto.PublicKey import RSA
from fabric.api import run, settings
from fabric.tasks import execute


parser = argparse.ArgumentParser()
parser.add_argument('dhcp_ip', help='Enter DHCP address of new server', type=str)
parser.add_argument('static_ip', help='Enter static ip to set for new server', type=str)
parser.add_argument('remote_user', help='Enter username of remote user', type=str)
parser.add_argument('playbook', help='Enter playbook yml file to run', type=str)
parser.add_argument('env', help='Set environment you wish to deploy (dev, qa, stage, prod)', type=str)

args = parser.parse_args()
dhcp_ip = args.dhcp_ip
static_ip = args.static_ip
remote_user = args.remote_user
playbook_file = args.playbook
deploy_env = args.env
local_user = getpass.getuser()
ansible_host_file = '/etc/ansible/hosts'
# new interface config file contents
new_interface_setting = '''\"auto lo\n
                            iface lo inet loopback\n
                            auto eth1\n
                            iface eth1 inet static\n
                            address %s\n netmask 255.255.0.0\n
                            gateway 10.0.0.1\n
                            dns-nameservers 10.0.0.1\"''' % static_ip

ssh_key_dir = '/home/' + local_user + '/.ssh/'
ssh_pub_key = ssh_key_dir + 'id_rsa.pub'

json_params = '_params.json'
if deploy_env == 'dev':
    deploy_file = deploy_env + json_params
elif deploy_env == 'qa':
    deploy_file = deploy_env + json_params
elif deploy_env == 'stage':
    deploy_file = deploy_env + json_params
elif deploy_env == 'prod':
    deploy_file = deploy_env + json_params
else:
    print "error: missing/wrong environment"
    sys.exit(1)

def setup_ssh_keys():
    if not os.path.isfile(ssh_pub_key):
        os.mkdir(ssh_key_dir, 0700)
        os.chdir(ssh_key_dir)
        key = RSA.generate(2048)
        with open('id_rsa', 'w') as private_key:
            os.chmod('id_rsa', 0600)
            private_key.write(key.exportKey('PEM'))

        with open('id_rsa.pub', 'w') as public_key:
            public_key.write(key.exportKey('OPENSSH'))

        subprocess.call([
                'cat',
                ssh_pub_key,
                ' | ',
                'ssh',
                remote_user + '@' + dhcp_ip,
                '"mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"'
                    ], shell=True)
        setup_ssh_keys()

    else:
        copy_id = str(remote_user + '@' + dhcp_ip)
        subprocess.call(['ssh-copy-id', copy_id])


def copy_static_key():
    copy_id = str(remote_user + '@' + static_ip)
    subprocess.call(['ssh-copy-id', copy_id])


def setup_ansible():
    if not os.path.exists(ansible_host_file):
        subprocess.call([ # fix for to pip
            'sudo',
            'yum',
            '-y',
            'install',
            'ansible'
        ])
        setup_ansible()

    else:
        with open(ansible_host_file, 'w') as host_file:
            host_file.write(dhcp_ip)
            host_file.write("\n" + static_ip)


def change_ip():
    with settings(warn_only=True):
        run('echo %s | awk \'{$1=$1};1\' > new_interface' % new_interface_setting)
        run('sudo mv new_interface /etc/network/interfaces')
        run('sudo reboot')

# running playbook via raw shell command (need to fix)
def run_playbook():
    deploy_params = '{0} --extra-vars "@{1}"'.format(str(playbook_file), str(deploy_file))
    os.system('ansible-playbook %s' % deploy_params)


setup_ssh_keys()
setup_ansible()

# If statement required to use fabric
if __name__ == "__main__":
    execute(change_ip, hosts=[remote_user + '@' + dhcp_ip])

# time out to wait for reboot
reboot_time = sleep(20)
copy_static_key()
run_playbook()
sys.exit(0)
