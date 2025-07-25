#!/usr/bin/env python
# -*- coding: UTF-8 -*
# Copyright (c) 2022 OceanBase
# OceanBase Diagnostic Tool is licensed under Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.

"""
@time: 2024/01/17
@file: cpu_high.py
@desc:
"""
import os

from src.common.ssh_client.ssh import SshClient
from src.handler.gather.gather_component_log import GatherComponentLogHandler
from src.common.stdio import SafeStdio
from src.handler.gather.gather_obstack2 import GatherObstack2Handler
from src.handler.gather.gather_perf import GatherPerfHandler
from src.handler.gather.step.sql import StepSQLHandler


class CPUHigh(SafeStdio):
    def init(self, context, scene_name, report_path, task_variable_dict=None, env={}):
        self.context = context
        self.stdio = context.stdio
        if task_variable_dict is None:
            self.task_variable_dict = {}
        else:
            self.task_variable_dict = task_variable_dict
        self.report_path = report_path
        self.env = self.context.get_variable("env") or {}
        self.is_ssh = True
        self.nodes = self.context.cluster_config['servers']
        self.cluster = self.context.cluster_config
        self.ob_nodes = self.context.cluster_config['servers']

    def execute(self):
        self.__gather_obstack()
        self.__gather_perf()
        self.__gather_current_clocksource()
        self.__gather_log()
        self.__get_processlist()

    def __gather_obstack(self):
        self.stdio.print("gather obstack start")
        obstack = GatherObstack2Handler(self.context, self.report_path, is_scene=True)
        obstack.handle()
        self.stdio.print("gather obstack end")

    def __gather_perf(self):
        self.stdio.print("gather perf start")
        perf_sample_count = self.env.get("perf_count")
        if perf_sample_count:
            self.context.set_variable('gather_perf_sample_count', perf_sample_count)
        perf = GatherPerfHandler(self.context, self.report_path, is_scene=True)
        perf.handle()
        self.stdio.print("gather perf end")

    def __gather_current_clocksource(self):
        try:
            self.stdio.print("gather current_clocksource start")
            for node in self.nodes:
                ssh_client = SshClient(self.context, node)
                cmd = 'cat /sys/devices/system/clocksource/clocksource0/current_clocksource'
                self.stdio.verbose("gather current_clocksource, run cmd = [{0}]".format(cmd))
                result = ssh_client.exec_cmd(cmd)
                file_path = os.path.join(self.report_path, "current_clocksource_{ip}_result.txt".format(ip=str(node.get("ip")).replace('.', '_')))
                self.report(file_path, cmd, result)
            self.stdio.print("gather current_clocksource end")
        except Exception as e:
            self.stdio.error("SshHandler init fail. Please check the node conf. Exception : {0} .".format(e))

    def __gather_log(self):
        try:
            self.stdio.print("gather observer log start")
            handler = GatherComponentLogHandler()
            handler.init(self.context, store_dir=self.report_path, target="observer", is_scene=True)
            handler.handle()
            self.stdio.print("gather observer log end")
        except Exception as e:
            self.stdio.error("gather observer log failed, error: {0}".format(e))
            raise Exception("gather observer log failed, error: {0}".format(e))

    def report(self, file_path, command, data):
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write('\n\n' + 'shell > ' + command + '\n')
                f.write(data + '\n')
        except Exception as e:
            self.stdio.error("report sql result to file: {0} failed, error: ".format(file_path))

    def __get_processlist(self):
        try:
            self.stdio.print("gather processlist start")
            step = {'global': 'true', 'type': 'sql', 'sql': 'show full processlist'}
            handler = StepSQLHandler(self.context, step, self.cluster, self.report_path, self.task_variable_dict, self.env)
            handler.execute()
            self.stdio.print("gather processlist end")
        except Exception as e:
            self.stdio.error("gather processlist failed, error: {0}".format(e))
            raise Exception("gather processlist failed, error: {0}".format(e))


cpu_high = CPUHigh()
