from ansible.playbook import PlayBook
from ansible import callbacks
from ansible import utils
from tempfile import NamedTemporaryFile
import jinja2
import os


class AnsiblePlaybook:
    def __init__(self):
        utils.VERBOSITY = 0
        self.playbook_cb = callbacks.PlaybookCallbacks(verbose=utils.VERBOSITY)
        self.stats = callbacks.AggregateStats()
        self.runner_cb = callbacks.PlaybookRunnerCallbacks(self.stats, verbose=utils.VERBOSITY)

    def __setup_inventory(self, ip):
        inventory = """
        [default]
        {{ ip_address }}
        """

        inventory_template = jinja2.Template(inventory)
        rendered_inventory = inventory_template.render({
            'ip_address': ip
        })

        self.hosts = NamedTemporaryFile(delete=False)
        self.hosts.write(rendered_inventory)
        self.hosts.close()

    def __setup_params(self):
        # Add extra parameters for playbook here
        self.params = {
            'example': 'example'
        }

    def __run_playbook(self, ip, playbook):
        pb_file = os.path.join('playbooks', playbook)
        pb = PlayBook(
            playbook=pb_file,
            host_list=self.hosts.name,
            callbacks=self.playbook_cb,
            runner_callbacks=self.runner_cb,
            stats=self.stats,
            extra_vars=self.params
        )

        results = pb.run()
        self.playbook_cb.on_stats(pb.stats)

        print(results)

    def run(self, ip, playbook, env):
        return(
            self.__setup_inventory(ip),
            self.__setup_params(),
            self.__run_playbook(ip, playbook)
        )
