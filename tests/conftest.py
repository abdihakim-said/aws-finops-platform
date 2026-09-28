import os

import boto3
import pytest
from moto import mock_aws

REGION = "us-east-1"


@pytest.fixture(autouse=True)
def aws_env(monkeypatch):
    for k, v in {"AWS_ACCESS_KEY_ID": "testing", "AWS_SECRET_ACCESS_KEY": "testing",
                 "AWS_DEFAULT_REGION": REGION, "AWS_REGION": REGION,
                 "MOTO_EC2_LOAD_DEFAULT_AMIS": "false"}.items():
        monkeypatch.setenv(k, v)
    monkeypatch.delenv("AWS_PROFILE", raising=False)


@pytest.fixture
def aws():
    with mock_aws():
        yield boto3.Session(region_name=REGION)


class StubComputeOptimizer:
    """Compute Optimizer isn't mocked by moto."""

    def __init__(self, recommendations=None, error=None):
        self.recommendations = recommendations or []
        self.error = error

    def get_ec2_instance_recommendations(self, **kwargs):
        if self.error:
            raise self.error
        return {"instanceRecommendations": self.recommendations}


class StubbedSession:
    def __init__(self, session, compute_optimizer):
        self._session = session
        self._co = compute_optimizer

    def client(self, name, **kwargs):
        if name == "compute-optimizer":
            return self._co
        return self._session.client(name, **kwargs)


@pytest.fixture
def stub_session():
    def make(session, **kwargs):
        return StubbedSession(session, StubComputeOptimizer(**kwargs))
    return make


os.environ.setdefault("AWS_DEFAULT_REGION", REGION)


def attached_volume(ec2, size: int, volume_type: str = "gp2", **kwargs) -> str:
    vol = ec2.create_volume(Size=size, AvailabilityZone="us-east-1a", VolumeType=volume_type, **kwargs)["VolumeId"]
    instance = launch_instance(ec2)
    ec2.attach_volume(VolumeId=vol, InstanceId=instance, Device="/dev/sdf")
    return vol


def launch_instance(ec2) -> str:
    mapping = [{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 8}}]
    image = ec2.register_image(Name="test-image", RootDeviceName="/dev/sda1",
                               BlockDeviceMappings=mapping)["ImageId"]
    root = [{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 8, "VolumeType": "gp3"}}]
    instances = ec2.run_instances(ImageId=image, MinCount=1, MaxCount=1, BlockDeviceMappings=root)["Instances"]
    return instances[0]["InstanceId"]
