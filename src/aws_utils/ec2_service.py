"""
EC2 service wrapper.
"""

from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from .aws_service import AWSService, AWSConfig


class EC2Service(AWSService):
    """Wrapper for Amazon EC2 operations."""

    def _create_client(self):
        return self.session.client('ec2')

    def _create_resource(self):
        return self.session.resource('ec2')

    def list_instances(self) -> List[Dict[str, Any]]:
        """Return list of all EC2 instances with basic info."""
        try:
            response = self.client.describe_instances()
            instances = []
            for reservation in response['Reservations']:
                for instance in reservation['Instances']:
                    instances.append({
                        'InstanceId': instance['InstanceId'],
                        'State': instance['State']['Name'],
                        'InstanceType': instance['InstanceType'],
                        'LaunchTime': str(instance['LaunchTime']),
                        'PublicIp': instance.get('PublicIpAddress', 'N/A'),
                        'PrivateIp': instance.get('PrivateIpAddress', 'N/A')
                    })
            return instances
        except ClientError as e:
            self._handle_error('list_instances', e)
            return []

    def create_instance(self, image_id: str, instance_type: str = 't2.micro',
                        key_name: Optional[str] = None,
                        security_group_ids: Optional[List[str]] = None,
                        subnet_id: Optional[str] = None,
                        min_count: int = 1, max_count: int = 1,
                        **kwargs) -> Optional[str]:
        """Launch a new EC2 instance. Returns instance ID or None."""
        try:
            params = {
                'ImageId': image_id,
                'InstanceType': instance_type,
                'MinCount': min_count,
                'MaxCount': max_count,
            }
            if key_name:
                params['KeyName'] = key_name
            if security_group_ids:
                params['SecurityGroupIds'] = security_group_ids
            if subnet_id:
                params['SubnetId'] = subnet_id
            params.update(kwargs)

            instances = self.resource.create_instances(**params)
            instance_id = instances[0].id
            logger.info(f"EC2 instance created: {instance_id}")
            return instance_id
        except ClientError as e:
            self._handle_error('create_instance', e)
            return None

    def start_instance(self, instance_id: str) -> bool:
        """Start an EC2 instance. Returns True on success."""
        try:
            self.client.start_instances(InstanceIds=[instance_id])
            logger.info(f"Started instance {instance_id}")
            return True
        except ClientError as e:
            self._handle_error('start_instance', e)
            return False

    def stop_instance(self, instance_id: str) -> bool:
        """Stop an EC2 instance. Returns True on success."""
        try:
            self.client.stop_instances(InstanceIds=[instance_id])
            logger.info(f"Stopped instance {instance_id}")
            return True
        except ClientError as e:
            self._handle_error('stop_instance', e)
            return False

    def terminate_instance(self, instance_id: str) -> bool:
        """Terminate an EC2 instance. Returns True on success."""
        try:
            self.client.terminate_instances(InstanceIds=[instance_id])
            logger.info(f"Terminated instance {instance_id}")
            return True
        except ClientError as e:
            self._handle_error('terminate_instance', e)
            return False

    def get_instance_state(self, instance_id: str) -> Optional[str]:
        """Return the current state (e.g., 'running', 'stopped') or None."""
        try:
            response = self.client.describe_instances(InstanceIds=[instance_id])
            if not response['Reservations']:
                return None
            instance = response['Reservations'][0]['Instances'][0]
            return instance['State']['Name']
        except ClientError as e:
            self._handle_error('get_instance_state', e)
            return None