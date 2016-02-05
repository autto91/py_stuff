from ovirtsdk.api import API
from ovirtsdk.xml import params


class RHEV:
    def __init__(self, username, password):
        self._username = username
        self._password = password

    def __entrypoint(self):
        try:
            url = 'https://rhevserver.com'
            api = API(
                url=url,
                username=self._username,
                password=self._password,
                ca_file='ca.crt'
            )

            return api

        except Exception as ex:
            print('Error: %s' % ex)

    def __new_vm_base(self, name, template, ram):
        memory = 1024 ** 3 * ram  # convert from bytes to GB
        cluster = self.__entrypoint().clusters.get(name='Default')
        template = self.__entrypoint().templates.get(name=template)
        os = params.OperatingSystem(boot=[params.Boot(dev='hd')])

        vm_params = params.VM(
            name=name,
            memory=memory,
            cluster=cluster,
            template=template,
            os=os,
            type_='Server'
        )

        try:
            self.__entrypoint().vms.add(vm=vm_params)
            print('added vm %s' % name)

        except Exception as ex:
            print('Unexpected error: %s' % ex)

    def __new_nic(self, name, network):
        vm = self.__entrypoint().vms.get(name=name)
        nic_name = 'eth1'
        nic_interface = 'virtio'
        nic_network = self.__entrypoint().networks.get(name=network)
        nic_params = params.NIC(
            name=nic_name,
            interface=nic_interface,
            network=nic_network
        )

        try:
            nic = vm.nics.add(nic_params)
            print('Network interface %s added to %s' % (nic.get_name(), vm.get_name()))

        except Exception as ex:
            print('Unexpected error: %s' % ex)

    def __new_disk(self, size, name):
        disk_size = 1024 ** 2 * size
        disk_type = 'system'
        disk_interface = 'virtio'
        disk_format = 'cow'
        disk_bootable = True
        vm = self.__entrypoint().vms.get(name=name)
        sd = params.StorageDomains(
            storage_domain=[self.__entrypoint().storagedomains.get(name='STORAGE_DOMAIN')]
        )
        disk_params = params.Disk(
            storage_domains=sd,
            size=disk_size,
            type_=disk_type,
            interface=disk_interface,
            format=disk_format,
            bootable=disk_bootable
        )

        try:
            d = vm.disks.add(disk=disk_params)
            print('Disk %s added to %s' % (d.get_name(), vm.get_name()))
        except Exception as ex:
            print('Unexpected Error: %s' % ex)

    def __start_vm(self, name):
        vm = self.__entrypoint().vms.get(name=name)

        try:
            vm.start()
            print('Starting up %s' % vm.get_name())

        except Exception as ex:
            print('Unexpected error: %s' % ex)

    def __stop_vm(self, name):
        vm = self.__entrypoint().vms.get(name=name)
        try:
            vm.stop()
            print('Stopped %s' % vm.get_name())

        except Exception as ex:
            print('Unexpected error: %s' % ex)

    def __destroy_vm(self, name):
        vm = self.__entrypoint().vms.get(name=name)
        try:
            vm.delete()
            print('Destroyed %s' % vm.get_name())

        except Exception as ex:
            print('Unexpected error: %s' % ex)

    def __get_vm_ip(self, name):
        vm_name = name
        vm_list = self.__entrypoint().vms.list()

        try:
            for instance in vm_list:
                address = []
                if instance.status.state == 'up' and instance.name == vm_name:
                    ips = instance.get_guest_info().get_ips().get_ip()
                    for ip in ips:
                        address.append(ip.get_address())
                    return address[0]

        except Exception as ex:
            print('Unexpected error: %s' % ex)

    def __create_vm_snapshot(self, name):
        api = self.__entrypoint()
        api.vms.get(name).snapshots.add()

    def entrypoint(self):
        return self.__entrypoint()

    def create_vm(self, name, template, ram, network, disk_size=None):
        if template != 'Blank':
            return(
                self.__new_vm_base(name=name, ram=ram, template=template),
                self.__new_nic(name=name, network=network)
            )

        else:
            return(
                self.__new_vm_base(name=name, ram=ram, template=template),
                self.__new_nic(name=name, network=network),
                self.__new_disk(name=name, size=disk_size)
            )

    def start(self, name):
        return self.__start_vm(name=name)

    def stop(self, name):
        return self.__stop_vm(name=name)

    def destroy(self, name):
        return self.__destroy_vm(name=name)

    def get_ip(self, name):
        return self.__get_vm_ip(name=name)
