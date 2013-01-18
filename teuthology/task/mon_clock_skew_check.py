import logging
import contextlib
import ceph_manager
import time
import gevent
import json
from teuthology import misc as teuthology

log = logging.getLogger(__name__)

class ClockSkewCheck:
  """
  Periodically check if there are any clock skews among the monitors in the
  quorum. By default, assume no skews are supposed to exist; that can be
  changed using the 'expect-skew' option. If 'fail-on-skew' is set to false,
  then we will always succeed and only report skews if any are found.

  This class does not spawn a thread. It assumes that, if that is indeed
  wanted, it should be done by a third party (for instance, the task using
  this class). We intend it as such in order to reuse this class if need be.

  This task accepts the following options:

   interval     amount of seconds to wait in-between checks. (default: 30.0)
   max-skew     maximum skew, in seconds, that is considered tolerable before
                issuing a warning. (default: 0.05)
   expect-skew  'true' or 'false', to indicate whether to expect a skew during
                the run or not. If 'true', the test will fail if no skew is
                found, and succeed if a skew is indeed found; if 'false', it's
                the other way around. (default: false)
   never-fail   Don't fail the run if a skew is detected and we weren't
                expecting it, or if no skew is detected and we were expecting
                it. (default: False)

  Example:
    Expect a skew higher than 0.05 seconds, but only report it without failing
    the teuthology run.

    - mon_clock_skew_check:
        interval: 30
        max-skew: 0.05
        expect_skew: true
        never-fail: true
  """

  def __init__(self, ctx, manager, config, logger):
    self.ctx = ctx
    self.manager = manager;

    self.stopping = False
    self.logger = logger
    self.config = config

    if self.config is None:
      self.config = dict()

    self.check_interval = float(self.config.get('interval', 30.0))
    self.max_skew = float(self.config.get('max-skew', 0.05))
    self.expect_skew = self.config.get('expect-skew', False)
    self.never_fail = self.config.get('never-fail', False)

  def info(self, x):
    self.logger.info(x)

  def warn(self, x):
    self.logger.warn(x)

  def finish(self):
    self.stopping = True

  def do_check(self):
    self.info('start checking for clock skews')
    skews = dict()
    while not self.stopping:
      quorum_size = len(teuthology.get_mon_names(self.ctx))
      self.manager.wait_for_mon_quorum_size(quorum_size)

      health = self.manager.get_mon_health(True)
      for timecheck in health['timechecks']:
        mon_skew = float(timecheck['skew'])
        mon_health = timecheck['health']
        mon_id = timecheck['name']
        if mon_skew > self.max_skew:
          assert mon_health == 'HEALTH_WARN', \
              'mon.{id} health is \'{health}\' but skew {s} > max {ms}'.format(
                  id=mon_id,s=mon_skew,ms=self.max_skew)

          log_str = 'mon.{id} with skew {s} > max {ms}'.format(
            id=mon_id,s=mon_skew,ms=self.max_skew)

          """ add to skew list """
          details = timecheck['details']
          skews[mon_id] = {'skew': mon_skew, 'details': details}

          if self.expect_skew:
            self.info('expected skew: {str}'.format(str=log_str))
          else:
            self.warn('unexpected skew: {str}'.format(str=log_str))

      if (self.check_interval > 0.0):
        time.sleep(self.check_interval)

    total = len(skews)
    if total > 0:
      self.info('---------- found {n} skews ----------'.format(n=total))
      for mon_id,values in skews.iteritems():
        self.info('mon.{id}: {v}'.format(id=mon_id,v=values))
      self.info('-------------------------------------')
    else:
      self.info('---------- no skews were found ----------')

    error_str = ''
    found_error = False

    if self.expect_skew:
      if total == 0:
        error_str = 'We were expecting a skew, but none was found!'
        found_error = True
    else:
      if total > 0:
        error_str = 'We were not expecting a skew, but we did find it!'
        found_error = True

    if found_error:
      self.info(error_str)
      if not self.never_fail:
        assert False, error_str

@contextlib.contextmanager
def task(ctx, config):
  """
  Use clas ClockSkewCheck to check for clock skews on the monitors.
  This task will spawn a thread running ClockSkewCheck's do_check().

  All the configuration will be directly handled by ClockSkewCheck,
  so please refer to the class documentation for further information.
  """
  if config is None:
    config = {}
  assert isinstance(config, dict), \
      'mon_clock_skew_check task only accepts a dict for configuration'
  log.info('Beginning mon_clock_skew_check...')
  first_mon = teuthology.get_first_mon(ctx, config)
  (mon,) = ctx.cluster.only(first_mon).remotes.iterkeys()
  manager = ceph_manager.CephManager(
      mon,
      ctx=ctx,
      logger=log.getChild('ceph_manager'),
      )

  skew_check = ClockSkewCheck(ctx,
      manager, config,
      logger=log.getChild('mon_clock_skew_check'))
  skew_check_thread = gevent.spawn(skew_check.do_check)
  try:
    yield
  finally:
    log.info('joining mon_clock_skew_check')
    skew_check.finish()
    skew_check_thread.get()


