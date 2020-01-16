# (C) Datadog, Inc. 2010-present
# All rights reserved
# Licensed under Simplified BSD License (see LICENSE)
import mock
import pytest
import re

from datadog_checks.apache import Apache

from .common import (
    APACHE_GAUGES,
    APACHE_RATES,
    APACHE_VERSION,
    AUTO_CONFIG,
    BAD_CONFIG,
    HOST,
    NO_METRIC_CONFIG,
    PORT,
    STATUS_CONFIG,
)


VERSION_REGEX = re.compile(r'^Apache/(\d+(?:\.\d+)*)')


@pytest.mark.usefixtures("dd_environment")
def test_connection_failure(aggregator, check):
    check = check(BAD_CONFIG)
    with pytest.raises(Exception):
        check.check(BAD_CONFIG)

    sc_tags = ['host:localhost', 'port:1234']
    aggregator.assert_service_check('apache.can_connect', Apache.CRITICAL, tags=sc_tags)
    assert len(aggregator._metrics) == 0


@pytest.mark.usefixtures("dd_environment")
def test_no_metrics_failure(aggregator, check):
    check = check(NO_METRIC_CONFIG)
    with pytest.raises(Exception) as excinfo:
        check.check(NO_METRIC_CONFIG)

    assert str(excinfo.value) == (
        "No metrics were fetched for this instance. Make sure that http://localhost:18180 " "is the proper url."
    )

    sc_tags = ['host:localhost', 'port:18180']
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)
    assert len(aggregator._metrics) == 0


@pytest.mark.usefixtures("dd_environment")
def test_check(aggregator, check):
    """
    This test will try and fail with `/server-status` url first then fallback on `/server-status??auto`
    """
    check = check(STATUS_CONFIG)
    check._submit_metadata = mock.MagicMock()
    check.check(STATUS_CONFIG)

    tags = STATUS_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags, count=1)

    sc_tags = ['host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()

    check._submit_metadata.assert_called_once()


@pytest.mark.usefixtures("dd_environment")
def test_check_auto(aggregator, check):
    check = check(AUTO_CONFIG)
    check.check(AUTO_CONFIG)

    tags = AUTO_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags, count=1)

    sc_tags = ['host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.e2e
def test_e2e(dd_agent_check):
    aggregator = dd_agent_check(STATUS_CONFIG, rate=True)

    tags = STATUS_CONFIG['tags']
    for mname in APACHE_GAUGES + APACHE_RATES:
        aggregator.assert_metric(mname, tags=tags)

    sc_tags = ['host:' + HOST, 'port:' + PORT] + tags
    aggregator.assert_service_check('apache.can_connect', Apache.OK, tags=sc_tags)

    aggregator.assert_all_metrics_covered()


@pytest.mark.usefixtures("dd_environment")
def test_metadata_in_content(check, datadog_agent):
    check = check(AUTO_CONFIG)
    check.check_id = 'test:123'
    major, minor, patch = APACHE_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': APACHE_VERSION,
    }

    check.check(AUTO_CONFIG)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


@pytest.mark.usefixtures("dd_environment")
def test_metadata_in_header(check, datadog_agent, mock_hide_server_version):
    """For older Apache versions, the version is not in the output. This test asserts that
    the check can fallback to the headers."""
    check = check(AUTO_CONFIG)
    check.check_id = 'test:123'
    major, minor, patch = APACHE_VERSION.split('.')
    version_metadata = {
        'version.scheme': 'semver',
        'version.major': major,
        'version.minor': minor,
        'version.patch': patch,
        'version.raw': APACHE_VERSION,
    }

    check.check(AUTO_CONFIG)
    datadog_agent.assert_metadata('test:123', version_metadata)
    datadog_agent.assert_metadata_count(len(version_metadata))


def test_invalid_version(check):
    check = check({})
    check.log = mock.MagicMock()

    check._submit_metadata("invalid_version")

    check.log.info.assert_called_once_with("Cannot parse the complete Apache version from %s.", "invalid_version")

@pytest.mark.parametrize(
        'version, pattern, expected_parts',
        [
            (
                'Apache/2.4.2 (Unix) PHP/4.2.2 MyMod/1.2',
                VERSION_REGEX,
                {'major': '2', 'minor': '4', 'patch': '2'},
            ),
            (
                'Apache',
                VERSION_REGEX,
                None,
            ),
            (
                'Apache/2.4.2',
                VERSION_REGEX,
                {'major': '2', 'minor': '4', 'patch': '2'},
            )
        ],
        ids=['full_version', 'prod_version', 'min_version'],
)
def test_version_regex(check, version, pattern, expected_parts, datadog_agent):
    # TODO: test other invalid versions
    """
    major_version = 'Apache/2'
    minor_version = "Apache/2.4"
    os_version = "Apache/2.4.2 (Unix)"
    """
    check = check({})
    check.check_id = 'test:123'
    
    check._submit_metadata(version)

    if len(expected_parts) == 3:
        version_metadata = {
            'version.scheme': 'semver',
            'version.major': expected_parts['major'],
            'version.minor': expected_parts['minor'],
            'version.patch': expected_parts['patch'],
        }

        datadog_agent.assert_metadata('test:123', version_metadata)
