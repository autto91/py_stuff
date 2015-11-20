import argparse
import subprocess
import getpass
import os
import sys
import json
from time import sleep
from Crypto.PublicKey import RSA


class Deployment(object):

    def __init__(self, dhcp, static, user, playbook, env, interface, ssh_key, ssh_dir):
        self.working_dir = os.path.dirname(__file__)
        self.dhcp = dhcp
        self.static = static
        self.user = user
        self.playbook = playbook
        self.env = env
        self.interface = interface
        self.ssh_key = ssh_key
        self.ssh_dir = ssh_dir
        self.ansible_file = self.working_dir + '/hosts'

        if env == 'dev':
            self.branch = 'develop'
            self.vhost_cfg = 'example.dev.conf'
        elif env == 'qa':
            self.branch = 'develop'
            self.vhost_cfg = 'example.qa.conf'
        elif env == 'stage':
            self.branch = 'master'
            self.vhost_cfg = 'example.stage.conf'
        elif env == 'prod':
            self.branch = 'master'
            self.vhost_cfg = 'example.conf'

        # run though process for Deployment
        self.setup_ssh_keys()
        self.setup_ansible()
        self.change_ip()
        sleep(25)
        self.copy_static_key()
        self.run_playbook()

    def setup_ansible(self):
        with open(self.ansible_file, 'w') as host_file:
            host_file.write(self.dhcp)
            host_file.write("\n" + self.static)

    def setup_ssh_keys(self):
            if not os.path.isfile(self.ssh_key):
                os.mkdir(self.ssh_dir, 0700)
                os.chdir(self.ssh_dir)
                key = RSA.generate(2048)
                with open('id_rsa', 'w') as private_key:
                    os.chmod('id_rsa', 0600)
                    private_key.write(key.exportKey('PEM'))

                with open('id_rsa.pub', 'w') as public_key:
                    public_key.write(key.exportKey('OPENSSH'))

                subprocess.call([
                        'cat',
                        self.ssh_key,
                        ' | ',
                        'ssh',
                        self.user + '@' + self.dhcp,
                        '"mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"'
                            ], shell=True)
                self.setup_ssh_keys()

            else:
                copy_id = str(self.user + '@' + self.dhcp)
                subprocess.call(['ssh-copy-id', copy_id])

    def copy_static_key(self):
        copy_id = str(self.user + '@' + self.static)
        subprocess.call(['ssh-copy-id', copy_id])

    def change_ip(self):
        host = self.user + '@' + self.dhcp
        command = '''sudo echo %s | awk \'{$1=$1};1\' > new_interface && \n
        sudo mv new_interface /etc/network/interfaces && \n
        sudo reboot
        ''' % self.interface

        ssh_tunnel = subprocess.Popen([
            'ssh', '%s' % host, command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        result = ssh_tunnel.stdout.readlines()
        if result == []:
            error = ssh_tunnel.stderr.readlines()
            print >> sys.stderr, 'RESTARTING: %s' % error
        else:
            print result

    def run_playbook(self):
        www_env = '/var/www/' + self.env
        vhost_dir = self.working_dir + '/' + 'vhosts'
        playbook_vars = {
            'hosts' : self.static,
            'user' : self.user,
            'www_dir' : www_env,
            'branch' : self.branch,
            'vhost' : self.vhost_cfg,
            'vhost_path' : vhost_dir
        }
        with open('vars.json', 'w') as json_file:
            json.dump(playbook_vars, json_file)

        deploy_params = '{0} --extra-vars "@vars.json"'.format(
            str(self.playbook),
        )
        os.system('ansible-playbook %s' % deploy_params)
        os.remove('vars.json')
        os.remove(self.working_dir + '/hosts')



class Update(object):
    
    def __init__(self, static, user, playbook, env, ssh_key, ssh_dir):
        self.working_dir = os.path.dirname(__file__)
        self.static = static
        self.user = user
        self.playbook = playbook
        self.env = env
        self.ssh_key = ssh_key
        self.ssh_dir = ssh_dir
        self.ansible_file = self.working_dir + '/hosts'

        if env == 'dev':
            self.branch = 'develop'
            self.vhost_cfg = 'example.dev.conf'
        elif env == 'qa':
            self.branch = 'develop'
            self.vhost_cfg = 'example.qa.conf'
        elif env == 'stage':
            self.branch = 'master'
            self.vhost_cfg = 'example.stage.conf'
        elif env == 'prod':
            self.branch = 'master'
            self.vhost_cfg = 'example.conf'

        # actually run update
        self.setup_ansible()
        self.setup_ssh()
        self.run_update()

    def setup_ansible(self):
        with open(self.ansible_file, 'w') as host_file:
            host_file.write("\n" + self.static)

    def setup_ssh(self):
        keypath = False
        if os.path.isfile(self.ssh_key):
            keypath = True

        while keypath == False:
            os.mkdir(self.ssh_dir, 0700)
            os.chdir(self.ssh_dir)
            key = RSA.generate(2048)
            with open('id_rsa', 'w') as private_key:
                os.chmod('id_rsa', 0600)
                private_key.write(key.exportKey('PEM'))

            with open('id_rsa.pub', 'w') as public_key:
                public_key.write(key.exportKey('OPENSSH'))

            subprocess.call([
                    'cat',
                    self.ssh_key,
                    ' | ',
                    'ssh',
                    self.user + '@' + self.static,
                    '"mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"'
                        ], shell=True)
            keypath = True

        copy_id = str(self.user + '@' + self.static)
        subprocess.call(['ssh-copy-id', copy_id])

    def run_update(self):
        www_env = '/var/www/' + self.env
        vhost_dir = self.working_dir + '/' + 'vhosts'
        playbook_vars = {
            'hosts' : self.static,
            'user' : self.user,
            'www_dir' : www_env,
            'branch' : self.branch,
            'vhost' : self.vhost_cfg,
            'vhost_path' : vhost_dir
        }
        with open('vars.json', 'w') as json_file:
            json.dump(playbook_vars, json_file)

        deploy_params = '{0} --extra-vars "@vars.json"'.format(
            str(self.playbook),
        )
        os.system('ansible-playbook %s' % deploy_params)
        os.remove('vars.json')
        os.remove(self.working_dir + '/hosts')

class Arguments(object):

    def __init__(self):
        self.parser = argparse.ArgumentParser(description='Sample Deployment Utility')
        self.parser.add_argument(
            '-n',
            help='Use flag for new node',
            action='store_true',
            default=False
        )
        self.parser.add_argument(
            '-up',
            help='Use flag for update existing node',
            action='store_true',
            default=False
        )
        self.parser.add_argument(
            '-d',
            '--dhcp',
            help='DHCP address of new server',
            type=str
        )
        self.parser.add_argument(
            '-s',
            '--static',
            help='static ip to set for new server',
            type=str
        )
        self.parser.add_argument(
            '-u',
            '--user',
            help='username of remote user',
            type=str,
            default='someUser'
        )
        self.parser.add_argument(
            '-p',
            '--playbook',
            help='playbook yml file to run',
            type=str
        )
        self.parser.add_argument(
            '-e',
            '--env',
            help='environment to deploy (dev, qa, stage, prod)',
            type=str
        )

    def run(self):
        args = self.parser.parse_args()
        ssh_dir = '/home/' + getpass.getuser() + '/.ssh/'
        ssh_key = ssh_dir + 'id_rsa.pub'
        interface = '''\"auto lo\n
                    iface lo inet loopback\n
                    auto eth1\n
                    iface eth1 inet static\n
                    address %s\n netmask 255.255.0.0\n
                    gateway 192.168.0.1\n
                    dns-nameservers 192.168.0.1\"''' % args.static
        if args.static is None:
            print 'Static IP (-s) required'
            sys.exit(1)

        elif args.env is None:
            print 'Environment (-e) required'
            sys.exit(1)

        if args.playbook is None and args.n == True:
            args.playbook = os.path.dirname(__file__) + '/new_node.yml'

        elif args.playbook is None and args.up == True:
            args.playbook = os.path.dirname(__file__) + '/update_node.yml'

        else:
            print 'Playbook file required'
            sys.exit(1)

        if args.n == True:
            Deployment(
                dhcp=args.dhcp,
                static=args.static,
                user=args.user,
                playbook=args.playbook,
                env=args.env,
                ssh_dir=ssh_dir,
                ssh_key=ssh_key,
                interface=interface
            )

        if args.up == True:
            Update(
                static=args.static,
                user=args.user,
                playbook=args.playbook,
                env=args.env,
                ssh_dir=ssh_dir,
                ssh_key=ssh_key
            )
