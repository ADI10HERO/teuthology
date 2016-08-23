from teuthology.config import config as teuth_config

from .. import console


class TestConsole(object):
    pass


class TestPhysicalConsole(TestConsole):
    klass = console.PhysicalConsole
    ipmi_cmd_templ = 'ipmitool -H {h}.{d} -I lanplus -U {u} -P {p} {c}'
    conserver_cmd_templ = 'console -M {m} -p {p} {h}'

    def setup(self):
        self.hostname = 'host'
        teuth_config.ipmi_domain = 'ipmi_domain'
        teuth_config.ipmi_user = 'ipmi_user'
        teuth_config.ipmi_password = 'ipmi_pass'
        teuth_config.conserver_master = 'conserver_master'
        teuth_config.conserver_port = 3109

    def test_console_command_conserver(self):
        cons = self.klass(
            self.hostname,
            teuth_config.ipmi_user,
            teuth_config.ipmi_password,
            teuth_config.ipmi_domain,
        )
        cons.has_conserver = True
        console_cmd = cons._console_command()
        assert console_cmd == self.conserver_cmd_templ.format(
            m=teuth_config.conserver_master,
            p=teuth_config.conserver_port,
            h=self.hostname,
        )

    def test_console_command_ipmi(self):
        teuth_config.conserver_master = None
        cons = self.klass(
            self.hostname,
            teuth_config.ipmi_user,
            teuth_config.ipmi_password,
            teuth_config.ipmi_domain,
        )
        sol_cmd = cons._console_command()
        assert sol_cmd == self.ipmi_cmd_templ.format(
            h=self.hostname,
            d=teuth_config.ipmi_domain,
            u=teuth_config.ipmi_user,
            p=teuth_config.ipmi_password,
            c='sol activate',
        )

    def test_build_command_ipmi(self):
        cons = self.klass(
            self.hostname,
            teuth_config.ipmi_user,
            teuth_config.ipmi_password,
            teuth_config.ipmi_domain,
        )
        pc_cmd = cons._build_command('power cycle')
        assert pc_cmd == self.ipmi_cmd_templ.format(
            h=self.hostname,
            d=teuth_config.ipmi_domain,
            u=teuth_config.ipmi_user,
            p=teuth_config.ipmi_password,
            c='power cycle',
        )

