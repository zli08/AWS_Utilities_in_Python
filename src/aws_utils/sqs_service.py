"""
SQS service wrapper.
"""

import json
from typing import List, Dict, Any, Optional, Union
from botocore.exceptions import ClientError
from .aws_service import AWSService, AWSConfig


class SQSService(AWSService):
    """Wrapper for Amazon SQS operations."""

    def _create_client(self):
        return self.session.client('sqs')

    def _create_resource(self):
        return self.session.resource('sqs')

    def create_queue(self, queue_name: str,
                     attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Create an SQS queue. Returns queue URL or None."""
        try:
            params = {'QueueName': queue_name}
            if attributes:
                params['Attributes'] = attributes
            response = self.client.create_queue(**params)
            queue_url = response['QueueUrl']
            logger.info(f"SQS queue created: {queue_url}")
            return queue_url
        except ClientError as e:
            self._handle_error('create_queue', e)
            return None

    def delete_queue(self, queue_url: str) -> bool:
        """Delete an SQS queue. Returns True on success."""
        try:
            self.client.delete_queue(QueueUrl=queue_url)
            logger.info(f"Deleted SQS queue {queue_url}")
            return True
        except ClientError as e:
            self._handle_error('delete_queue', e)
            return False

    def send_message(self, queue_url: str, message_body: Union[str, Dict],
                     message_attributes: Optional[Dict[str, Any]] = None,
                     delay_seconds: int = 0) -> Optional[str]:
        """Send a message to an SQS queue. Returns message ID or None."""
        try:
            if isinstance(message_body, dict):
                message_body = json.dumps(message_body)
            params = {
                'QueueUrl': queue_url,
                'MessageBody': message_body,
                'DelaySeconds': delay_seconds
            }
            if message_attributes:
                params['MessageAttributes'] = message_attributes
            response = self.client.send_message(**params)
            logger.info(f"SQS message sent: {response['MessageId']}")
            return response['MessageId']
        except ClientError as e:
            self._handle_error('send_message', e)
            return None

    def receive_messages(self, queue_url: str, max_messages: int = 10,
                         wait_time_seconds: int = 20,
                         visibility_timeout: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Receive messages from an SQS queue.
        Returns a list of messages (each contains 'Body', 'ReceiptHandle', etc.).
        """
        try:
            params = {
                'QueueUrl': queue_url,
                'MaxNumberOfMessages': max_messages,
                'WaitTimeSeconds': wait_time_seconds,
                'AttributeNames': ['All'],
                'MessageAttributeNames': ['All']
            }
            if visibility_timeout is not None:
                params['VisibilityTimeout'] = visibility_timeout
            response = self.client.receive_message(**params)
            messages = response.get('Messages', [])
            logger.info(f"Received {len(messages)} messages from SQS")
            return messages
        except ClientError as e:
            self._handle_error('receive_messages', e)
            return []

    def delete_message(self, queue_url: str, receipt_handle: str) -> bool:
        """Delete a message from an SQS queue. Returns True on success."""
        try:
            self.client.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            logger.info("SQS message deleted")
            return True
        except ClientError as e:
            self._handle_error('delete_message', e)
            return False

    def get_queue_url(self, queue_name: str) -> Optional[str]:
        """Get the URL of a queue by name."""
        try:
            response = self.client.get_queue_url(QueueName=queue_name)
            return response['QueueUrl']
        except ClientError as e:
            self._handle_error('get_queue_url', e)
            return None