from cStringIO import StringIO

import contextlib
import logging
import os
import re
import yaml

from teuthology import misc as teuthology
from teuthology import contextutil
from ..orchestra import run 

log = logging.getLogger(__name__)
blktrace = '/usr/sbin/blktrace'
log_dir = '/tmp/cephtest/archive/performance/blktrace'
daemon_signal = 'kill'

@contextlib.contextmanager
def setup(ctx, config):
    osds = ctx.cluster.only(teuthology.is_type('osd'))
    for remote, roles_for_host in osds.remotes.iteritems():
        log.info('Creating %s on %s' % (log_dir,remote.name))
        proc = remote.run(
            args=['mkdir', '-p', '-m0755', '--', log_dir],
            wait=False,
            )
    yield

@contextlib.contextmanager
def execute(ctx, config):
    procs = []
#    type_ = 'blktrace'
    osds = ctx.cluster.only(teuthology.is_type('osd'))
    for remote, roles_for_host in osds.remotes.iteritems():
        roles_to_devs = ctx.disk_config.remote_to_roles_to_dev[remote]
        roles_to_journals = ctx.disk_config.remote_to_roles_to_journals[remote]
        for id_ in teuthology.roles_of_type(roles_for_host, 'osd'):
            if roles_to_devs.get(id_):
                dev = roles_to_devs[id_]
                log.info("running blktrace on %s: %s" % (remote.name, dev))

#                run_cmd=[
#                    'cd',
#                    log_dir,
#                    run.Raw(';'),
#                    '/tmp/cephtest/daemon-helper',
#                    daemon_signal,
#                    'sudo',
#                    blktrace,
#                    '-o',
#                    dev.rsplit("/", 1)[1],
#                    '-d',
#                    dev,
#                    ]
#
#                ctx.daemons.add_daemon(remote, type_, id_,
#                    args=run_cmd,
#                    stdin=run.PIPE,
#                    wait=False,
#                    )

                proc = remote.run(
                    args=[
                        'cd',
                        log_dir,
                        run.Raw(';'),
                        '/tmp/cephtest/daemon-helper',
                        daemon_signal,
                        'sudo',
                        blktrace,
                        '-o',
                        dev.rsplit("/", 1)[1],
                        '-d',
                        dev,
                        ],
                    wait=False,
                    stdin=run.PIPE,
                    )
                procs.append(proc)
    try:
        yield
    finally:
#        log.info('Shutting down %s daemons...' % type_)
#        exc_info = (None, None, None)
#        for daemon in ctx.daemons.iter_daemons_of_role(type_):
#            print "Test: %s, %s" % daemon.role, daemon.id_
#            try:
#                daemon.stop()
#            except (run.CommandFailedError,
#                    run.CommandCrashedError,
#                    run.ConnectionLostError):
#                exc_info = sys.exc_info()
#                log.exception('Saw exception from %s.%s', daemon.role, daemon.id_)
#        if exc_info != (None, None, None):
#            raise exc_info[0], exc_info[1], exc_info[2]

        osds = ctx.cluster.only(teuthology.is_type('osd'))
        for proc in procs:
            log.info('stopping all blktrace processes on %s' % proc)
            proc.stdin.close()

#        for remote, roles_for_host in osds.remotes.iteritems():
#            log.info('stopping all blktrace processes on %s' % (remote.name))
#            remote.run(args=['sudo', 'pkill', '-f', 'blktrace'])

@contextlib.contextmanager
def task(ctx, config):
    if config is None:
        config = dict(('client.{id}'.format(id=id_), None)
                  for id_ in teuthology.all_roles_of_type(ctx.cluster, 'client'))
    elif isinstance(config, list):
        config = dict.fromkeys(config)

    with contextutil.nested(
        lambda: setup(ctx=ctx, config=config),
        lambda: execute(ctx=ctx, config=config),
        ):
        yield

