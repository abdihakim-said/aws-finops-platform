"""Destructive functions must be safe by default.

Runs the handlers against a fake EC2 client and asserts that no
modify/delete/release call is made unless DRY_RUN=false is set explicitly.
"""
import datetime
import os
import sys
from unittest import mock

import boto3
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lambda-functions"))

DESTRUCTIVE = {"modify_volume", "delete_snapshot", "delete_security_group", "release_address"}


class FakeEC2:
    def __init__(self):
        self.calls = []

    def __getattr__(self, name):
        def call(*args, **kwargs):
            self.calls.append((name, kwargs))
            if name == "describe_volumes":
                if "Filters" in kwargs:
                    return {"Volumes": [{"VolumeId": "vol-gp2", "Size": 10}]}
                raise Exception("InvalidVolume.NotFound")
            if name == "describe_snapshots":
                old = datetime.datetime(2020, 1, 1)
                return {"Snapshots": [
                    {"SnapshotId": "snap-orphan", "StartTime": old, "VolumeId": "vol-gone", "VolumeSize": 5},
                    {"SnapshotId": "snap-ami", "StartTime": old, "VolumeId": "vol-gone"},
                    {"SnapshotId": "snap-backup", "StartTime": old, "VolumeId": "vol-gone",
                     "Tags": [{"Key": "aws:backup:source-resource", "Value": "x"}]},
                ]}
            if name == "describe_images":
                return {"Images": [{"BlockDeviceMappings": [{"Ebs": {"SnapshotId": "snap-ami"}}]}]}
            if name == "describe_security_groups":
                return {"SecurityGroups": [
                    {"GroupId": "sg-eni", "GroupName": "attached-to-rds"},
                    {"GroupId": "sg-unused", "GroupName": "unused",
                     "IpPermissions": [{"UserIdGroupPairs": [{"GroupId": "sg-referenced"}]}]},
                    {"GroupId": "sg-referenced", "GroupName": "referenced"},
                ]}
            if name == "get_paginator":
                paginator = mock.Mock()
                paginator.paginate.return_value = [{"NetworkInterfaces": [{"Groups": [{"GroupId": "sg-eni"}]}]}]
                return paginator
            if name == "describe_addresses":
                return {"Addresses": [{"AllocationId": "eipalloc-1", "PublicIp": "203.0.113.1"}]}
            if name == "describe_load_balancers":
                return {"LoadBalancers": []}
            return {}
        return call


def run(env, event):
    ec2 = FakeEC2()
    with mock.patch.object(boto3, "client", lambda *a, **k: ec2), mock.patch.dict(os.environ, env, clear=False):
        import cost_optimizer
        import unused_resources_cleanup
        cost_optimizer.lambda_handler(event, None)
        unused_resources_cleanup.lambda_handler(event, None)
    return [(n, k) for n, k in ec2.calls if n in DESTRUCTIVE]


@pytest.mark.parametrize("env,event", [
    ({}, {}),                                  # default: dry run
    ({"DRY_RUN": "true"}, {}),
    ({"DRY_RUN": "false"}, {"dryRun": True}),  # event can force dry run
])
def test_no_destructive_calls_in_dry_run(env, event):
    with mock.patch.dict(os.environ, {"DRY_RUN": env.get("DRY_RUN", "true")}):
        assert run(env, event) == []


def test_live_mode_skips_protected_resources():
    calls = run({"DRY_RUN": "false"}, {})
    assert ("delete_snapshot", {"SnapshotId": "snap-orphan"}) in calls
    assert ("delete_snapshot", {"SnapshotId": "snap-ami"}) not in calls
    assert ("delete_snapshot", {"SnapshotId": "snap-backup"}) not in calls
    assert ("delete_security_group", {"GroupId": "sg-unused"}) in calls
    assert ("delete_security_group", {"GroupId": "sg-eni"}) not in calls
    assert ("delete_security_group", {"GroupId": "sg-referenced"}) not in calls
