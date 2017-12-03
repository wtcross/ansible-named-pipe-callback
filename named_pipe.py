# Copyright Tyler Cross 2017
# Author(s): Tyler Cross <tyler@cross.solutions>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import datetime
import json
import os
import socket
import uuid

from ansible.plugins.callback import CallbackBase


class CallbackModule(CallbackBase):
    """
    This ansible callback plugin is for writing status updates as JSON
    to a named pipe.

    This plugin makes use of the following env variables:
        ANSIBLE_NAMED_PIPE (required): path to the named pipe where status updates
                                       should be written
        ANSIBLE_SESSION_ID (optional): id for this session, defaults to a uuid

    """
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'notification'
    CALLBACK_NAME = 'named_pipe'
    CALLBACK_NEEDS_WHITELIST = True

    def __init__(self):
        super(CallbackModule, self).__init__()

        pipe_path = os.getenv('ANSIBLE_NAMED_PIPE', None)
        if pipe_path is None:
            self._display.warning(
                'Path to the named pipe to write to must be contained by '
                'the `ANSIBLE_NAMED_PIPE` environment variable')
            self.disabled = True

        self.pipe = open(pipe_path, "w", 0600)
        self.session = os.getenv('ANSIBLE_SESSION_ID', str(uuid.uuid1()))
        self.hostname = socket.gethostname()
        self.uuid = None
        self.errors = 0
        self.start_time = datetime.utcnow()

    def __del__(self):
        self.pipe.close()
    
    def write_to_pipe(self, data):
        self.pipe.write('%s\n' % json.dumps(data))

    def v2_playbook_on_play_start(self, play):
        self.playbook = play.name
        self.uuid = play._uuid
        data = {
            'status': "OK",
            'host': self.hostname,
            'session': self.session,
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_type': 'start',
        }
        self.write_to_pipe(data)

    def v2_playbook_on_stats(self, stats):
        """Display info about playbook statistics"""
        hosts = sorted(stats.processed.keys())

        for host in hosts:
            stat = stats.summarize(host)
            data = {
                'host': self.hostname,
                'ansible_host': host,
                'playbook_id': self.uuid,
                'playbook_name': self.playbook,
                'stats': stat
            }
            self.write_to_pipe(data)

        if self.errors > 0:
            status = 'FAILED'
        else:
            status = 'OK'

        data = {
            'playbook_id': self.uuid,
            'playbook_name': self.playbook,
            'status': status
        }
        self.write_to_pipe(data)

    def v2_runner_on_ok(self, result, **kwargs):
        host = result._host.get_name()
        data = {
            'status': "OK",
            'host': self.hostname,
            'ansible_host': host,
            'session': self.session,
            'ansible_type': "task",
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)

    def v2_runner_on_failed(self, result, **kwargs):
        self.errors += 1
        data = {
            'status': "FAILED",
            'host': self.hostname,
            'playbook_id': self.uuid,
            'session': self.session,
            'ansible_type': "task",
            'playbook_name': self.playbook,
            'ansible_host': result._host.name,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)

    def v2_runner_on_unreachable(self, result):
        host = result._host.get_name()
        self.errors += 1
        data = {
            'status': "UNREACHABLE",
            'host': self.hostname,
            'session': self.session,
            'ansible_type': "task",
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_host': host,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)

    def v2_runner_on_async_failed(self, result):
        self.errors += 1
        data = {
            'status': "FAILED",
            'host': self.hostname,
            'session': self.session,
            'ansible_type': "task",
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_host': result._host.name,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)

    def v2_runner_item_on_ok(self, result):
        data = {
            'status': "OK",
            'host': self.hostname,
            'session': self.session,
            'ansible_type': "item",
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_host': result._host.name,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)

    def v2_runner_item_on_failed(self, result):
        data = {
            'status': "FAILED",
            'host': self.hostname,
            'session': self.session,
            'ansible_type': "item",
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_host': result._host.name,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)

    def v2_runner_item_on_skipped(self, result):
        data = {
            'status': "SKIPPED",
            'host': self.hostname,
            'session': self.session,
            'ansible_type': "item",
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_host': result._host.name,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)

    def v2_runner_item_on_retry(self, result):
        data = {
            'status': "RETRY",
            'host': self.hostname,
            'session': self.session,
            'ansible_type': "item",
            'playbook_name': self.playbook,
            'playbook_id': self.uuid,
            'ansible_host': result._host.name,
            'ansible_task': str(result._task),
            'ansible_result': self._dump_results(result._result)
        }
        self.write_to_pipe(data)