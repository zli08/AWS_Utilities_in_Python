"""
CloudWatch service wrapper.
"""

import datetime
from typing import List, Dict, Any, Optional
from botocore.exceptions import ClientError
from .aws_service import AWSService, AWSConfig


class CloudWatchService(AWSService):
    """Wrapper for Amazon CloudWatch operations."""

    def _create_client(self):
        return self.session.client('cloudwatch')

    def put_metric(self, namespace: str, metric_name: str, value: float,
                   unit: str = 'Count', dimensions: Optional[List[Dict[str, str]]] = None,
                   timestamp: Optional[datetime.datetime] = None) -> bool:
        """Publish a single custom metric. Returns True on success."""
        try:
            metric_data = [{
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': timestamp or datetime.datetime.utcnow()
            }]
            if dimensions:
                metric_data[0]['Dimensions'] = dimensions

            self.client.put_metric_data(
                Namespace=namespace,
                MetricData=metric_data
            )
            logger.info(f"Metric {metric_name}={value} published to CloudWatch")
            return True
        except ClientError as e:
            self._handle_error('put_metric', e)
            return False

    def put_metric_data(self, namespace: str,
                        metric_data: List[Dict]) -> bool:
        """Publish multiple metric data points."""
        try:
            self.client.put_metric_data(Namespace=namespace, MetricData=metric_data)
            logger.info(f"Published {len(metric_data)} metrics to CloudWatch")
            return True
        except ClientError as e:
            self._handle_error('put_metric_data', e)
            return False

    def get_metric_statistics(self, namespace: str, metric_name: str,
                              dimensions: List[Dict[str, str]],
                              start_time: datetime.datetime,
                              end_time: datetime.datetime,
                              period: int = 300,
                              statistics: List[str] = ['Average']) -> List[Dict]:
        """Retrieve metric statistics for a given time range."""
        try:
            response = self.client.get_metric_statistics(
                Namespace=namespace,
                MetricName=metric_name,
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=period,
                Statistics=statistics
            )
            datapoints = response.get('Datapoints', [])
            logger.info(f"Retrieved {len(datapoints)} datapoints for {metric_name}")
            return datapoints
        except ClientError as e:
            self._handle_error('get_metric_statistics', e)
            return []

    def put_alarm(self, alarm_name: str, namespace: str, metric_name: str,
                  dimensions: List[Dict[str, str]],
                  threshold: float,
                  comparison_operator: str = 'GreaterThanThreshold',
                  evaluation_periods: int = 1,
                  period: int = 300,
                  statistic: str = 'Average',
                  description: Optional[str] = None,
                  alarm_actions: Optional[List[str]] = None,
                  insufficient_data_actions: Optional[List[str]] = None,
                  ok_actions: Optional[List[str]] = None) -> bool:
        """Create or update a CloudWatch alarm. Returns True on success."""
        try:
            params = {
                'AlarmName': alarm_name,
                'AlarmDescription': description or f'Alarm for {metric_name}',
                'ActionsEnabled': True,
                'MetricName': metric_name,
                'Namespace': namespace,
                'Statistic': statistic,
                'Dimensions': dimensions,
                'Period': period,
                'EvaluationPeriods': evaluation_periods,
                'Threshold': threshold,
                'ComparisonOperator': comparison_operator,
            }
            if alarm_actions:
                params['AlarmActions'] = alarm_actions
            if insufficient_data_actions:
                params['InsufficientDataActions'] = insufficient_data_actions
            if ok_actions:
                params['OKActions'] = ok_actions

            self.client.put_metric_alarm(**params)
            logger.info(f"CloudWatch alarm {alarm_name} created/updated")
            return True
        except ClientError as e:
            self._handle_error('put_alarm', e)
            return False

    def delete_alarm(self, alarm_name: str) -> bool:
        """Delete a CloudWatch alarm."""
        try:
            self.client.delete_alarms(AlarmNames=[alarm_name])
            logger.info(f"Deleted alarm {alarm_name}")
            return True
        except ClientError as e:
            self._handle_error('delete_alarm', e)
            return False

    def list_metrics(self, namespace: Optional[str] = None,
                     metric_name: Optional[str] = None,
                     dimensions: Optional[List[Dict[str, str]]] = None) -> List[Dict]:
        """List available CloudWatch metrics."""
        try:
            params = {}
            if namespace:
                params['Namespace'] = namespace
            if metric_name:
                params['MetricName'] = metric_name
            if dimensions:
                params['Dimensions'] = dimensions
            response = self.client.list_metrics(**params)
            return response.get('Metrics', [])
        except ClientError as e:
            self._handle_error('list_metrics', e)
            return []