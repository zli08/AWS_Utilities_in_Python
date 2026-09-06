"""
SNS service wrapper.
"""

import json
from typing import List, Dict, Any, Optional, Union
from botocore.exceptions import ClientError
from .aws_service import AWSService, AWSConfig


class SNSService(AWSService):
    """Wrapper for Amazon SNS operations."""

    def _create_client(self):
        return self.session.client('sns')

    def create_topic(self, topic_name: str,
                     attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Create an SNS topic. Returns topic ARN or None."""
        try:
            params = {'Name': topic_name}
            if attributes:
                params['Attributes'] = attributes
            response = self.client.create_topic(**params)
            topic_arn = response['TopicArn']
            logger.info(f"SNS topic created: {topic_arn}")
            return topic_arn
        except ClientError as e:
            self._handle_error('create_topic', e)
            return None

    def delete_topic(self, topic_arn: str) -> bool:
        """Delete an SNS topic. Returns True on success."""
        try:
            self.client.delete_topic(TopicArn=topic_arn)
            logger.info(f"Deleted SNS topic {topic_arn}")
            return True
        except ClientError as e:
            self._handle_error('delete_topic', e)
            return False

    def publish(self, topic_arn: str, message: Union[str, Dict],
                subject: Optional[str] = None,
                message_attributes: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Publish a message to an SNS topic. Returns message ID or None."""
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            params = {
                'TopicArn': topic_arn,
                'Message': message,
            }
            if subject:
                params['Subject'] = subject
            if message_attributes:
                params['MessageAttributes'] = message_attributes
            response = self.client.publish(**params)
            logger.info(f"Published SNS message: {response['MessageId']}")
            return response['MessageId']
        except ClientError as e:
            self._handle_error('publish', e)
            return None

    def subscribe(self, topic_arn: str, protocol: str, endpoint: str,
                  attributes: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Subscribe an endpoint (email, HTTP, SQS, etc.) to the topic.
        Returns subscription ARN or None."""
        try:
            params = {
                'TopicArn': topic_arn,
                'Protocol': protocol,
                'Endpoint': endpoint,
            }
            if attributes:
                params['Attributes'] = attributes
            response = self.client.subscribe(**params)
            subscription_arn = response['SubscriptionArn']
            logger.info(f"Subscribed {endpoint} to {topic_arn}: {subscription_arn}")
            return subscription_arn
        except ClientError as e:
            self._handle_error('subscribe', e)
            return None

    def list_subscriptions(self, topic_arn: str) -> List[Dict[str, Any]]:
        """List all subscriptions for a given topic."""
        try:
            response = self.client.list_subscriptions_by_topic(TopicArn=topic_arn)
            return response.get('Subscriptions', [])
        except ClientError as e:
            self._handle_error('list_subscriptions', e)
            return []