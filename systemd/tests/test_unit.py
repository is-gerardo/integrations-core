# (C) Datadog, Inc. 2018
# All rights reserved
# Licensed under a 3-clause BSD style license (see LICENSE)

import six

import pytest

from datadog_checks.systemd import SystemdCheck

import mock
from six import iteritems


def test_config_options(instance):
    check = SystemdCheck('systemd', {}, [instance])

    assert check.report_status is False
    assert check.report_processes is True
    assert len(check.units_watched) == 3


def test_bad_config(instance):
    """
    Check creation will fail if more than one `instance` is passed to the
    constructor
    """
    with pytest.raises(Exception):
        SystemdCheck('systemd', {}, [instance, instance])


def test_cache(instance):
    check = SystemdCheck('systemd', {}, [instance])
    # check that the cache is empty when at the beginning
    assert len(check.unit_cache) == 0
    current_unit_status = {'ssh.service': 'active', 'cron.service': 'active', 'networking.service': 'inactive'}
    assert check.list_status_change(current_unit_status) is not None
    assert len(check.list_status_change(current_unit_status)) == 3

    # we fill the cache and test a change of unit state
    check.unit_cache = {'ssh.service': 'active', 'cron.service': 'active', 'networking.service': 'inactive'}
    current_unit_status = {'ssh.service': 'active', 'cron.service': 'inactive', 'networking.service': 'inactive'}

    # check that we are getting changed units - returned_units is a tuple of 3 elements
    changed_units, created_units, deleted_units = check.list_status_change(current_unit_status)
    assert changed_units is not None
    assert changed_units['cron.service'] == 'inactive'
    assert len(created_units) == 0
    assert len(deleted_units) == 0

    # we fill the cache and test a unit that can no longer be found
    check.unit_cache = {'ssh.service': 'active', 'cron.service': 'active', 'networking.service': 'inactive'}
    current_unit_status = {'ssh.service': 'active', 'networking.service': 'inactive'}
    # check that we are getting deleted units
    changed_units, created_units, deleted_units = check.list_status_change(current_unit_status)
    assert deleted_units is not None
    assert deleted_units['cron.service'] == 'active'
    assert len(created_units) == 0
    assert len(changed_units) == 0



def test_active_inactive(aggregator, instance):

    all_unit_status = {
        'ssh.service': 'active',
        'networking.service': 'active',
        'cron.service': 'inactive',
        'systemd-journald.service': 'inactive',
        'setvtrgb.service': 'active'
    }

    units = {
        'systemd.units.active': 3,
        'systemd.units.inactive': 2
    }

    with mock.patch('datadog_checks.systemd.systemd.pystemd') as mock_pystemd_units:
        mock_pystemd_units.pystemd.units.info = list_unit_files_mock
        check = SystemdCheck('systemd', {}, [instance])
        unit_status = check.get_all_unit_status()
        assert len(unit_status) > 0
        """
        check.report_statuses(unit_status, tags)
        
        for _, m in iteritems(aggregator._metrics):
            assert bytes(units[m[0].name]) == m[0].value
        """