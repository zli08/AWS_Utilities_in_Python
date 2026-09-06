#!/usr/bin/env python3
"""
Example script demonstrating usage of the AWS utilities library.

Place this file in your src/ folder alongside the aws_utils/ directory.
Run from the project root: python -m src.example_usage
Or from the src/ folder: python example_usage.py
"""

import sys
import logging
import datetime
from pathlib import Path

# Add the project root to sys.path if running this script directly
# This allows importing from 'src.aws_utils'
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Now we can import from src.aws_utils
from src.aws_utils import (
    AWSConfig,
    EC2Service,
    SNSService,
    SQSService,
    LambdaService,
    CloudWatchService
)

# Configure logging to see what the library is doing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def run_workflow(region: str = 'us-east-1'):
    """
    A complete workflow that demonstrates all services:
    1. List EC2 instances and publish count to CloudWatch
    2. Create an SNS topic and publish a status message
    3. Create an SQS queue, send/receive/delete a message
    4. Invoke a Lambda function if one exists
    5. Create a CloudWatch alarm (optional)
    """
    logger.info("=" * 60)
    logger.info("Starting AWS workflow with the reusable library")
    logger.info("=" * 60)

    # 1. Configure the AWS session
    config = AWSConfig(region_name=region)
    logger.info(f"Using AWS region: {region}")

    # 2. Initialize all service clients
    ec2 = EC2Service(config)
    sns = SNSService(config)
    sqs = SQSService(config)
    lambda_svc = LambdaService(config)
    cw = CloudWatchService(config)

    # ------------------------------------------------------------------
    # Part 1: EC2 - List instances and publish a custom metric
    # ------------------------------------------------------------------
    logger.info("\n[1] Listing EC2 instances...")
    instances = ec2.list_instances()
    instance_count = len(instances)
    for inst in instances[:3]:  # show first 3 instances
        logger.info(f"  - {inst['InstanceId']} ({inst['State']}) - {inst['InstanceType']}")
    if len(instances) > 3:
        logger.info(f"  ... and {len(instances) - 3} more")

    # Publish instance count to CloudWatch
    logger.info(f"[1a] Publishing instance count ({instance_count}) to CloudWatch...")
    success = cw.put_metric(
        namespace='MyApp/Monitoring',
        metric_name='EC2InstanceCount',
        value=instance_count,
        unit='Count',
        dimensions=[{'Name': 'Environment', 'Value': 'Demo'}]
    )
    if success:
        logger.info("Metric published successfully")
    else:
        logger.warning("Metric publishing failed (check permissions)")

    # ------------------------------------------------------------------
    # Part 2: SNS - Create topic and publish a notification
    # ------------------------------------------------------------------
    logger.info("\n[2] Setting up SNS topic...")
    topic_name = f"MyWorkflowTopic-{datetime.datetime.now().strftime('%Y%m%d')}"
    topic_arn = sns.create_topic(topic_name)
    if topic_arn:
        logger.info(f"Created topic: {topic_arn}")
        # Publish a message
        msg_id = sns.publish(
            topic_arn,
            message=f"Workflow started. Found {instance_count} EC2 instances.",
            subject="AWS Workflow Status"
        )
        logger.info(f"Published SNS message ID: {msg_id}")

        # (Optional) Subscribe an email - uncomment and replace with your email
        # sub_arn = sns.subscribe(topic_arn, 'email', 'your-email@example.com')
        # logger.info(f"Subscription ARN: {sub_arn}")

    else:
        logger.warning("SNS topic creation failed. Skipping SNS steps.")

    # ------------------------------------------------------------------
    # Part 3: SQS - Create queue, send, receive, delete a message
    # ------------------------------------------------------------------
    logger.info("\n[3] Setting up SQS queue...")
    queue_name = f"MyWorkflowQueue-{datetime.datetime.now().strftime('%Y%m%d')}"
    queue_url = sqs.create_queue(queue_name)
    if queue_url:
        logger.info(f"Created queue: {queue_url}")

        # Send a message
        payload = {
            'action': 'process_instances',
            'instance_count': instance_count,
            'timestamp': datetime.datetime.utcnow().isoformat()
        }
        msg_id = sqs.send_message(queue_url, payload)
        logger.info(f"Sent SQS message ID: {msg_id}")

        # Receive and process messages
        messages = sqs.receive_messages(queue_url, max_messages=1, wait_time_seconds=5)
        for msg in messages:
            logger.info(f"Received message: {msg['Body']}")
            # In a real app you'd process the message here
            # Delete it after processing
            delete_success = sqs.delete_message(queue_url, msg['ReceiptHandle'])
            logger.info(f"Message deleted: {delete_success}")

        # Clean up the queue (optional)
        # sqs.delete_queue(queue_url)
    else:
        logger.warning("SQS queue creation failed. Skipping SQS steps.")

    # ------------------------------------------------------------------
    # Part 4: Lambda - Invoke a function (if any exist)
    # ------------------------------------------------------------------
    logger.info("\n[4] Checking for Lambda functions to invoke...")
    functions = lambda_svc.list_functions()
    if functions:
        # Use the first function found, or a specific one by name
        func_name = functions[0]['FunctionName']
        logger.info(f"Found Lambda function: {func_name}")

        # Invoke it synchronously with a test payload
        response = lambda_svc.invoke(
            func_name,
            payload={'workflow': 'test', 'instance_count': instance_count},
            invocation_type='RequestResponse'  # or 'Event' for async
        )
        if response:
            logger.info(f"Lambda response: {response}")
        else:
            logger.warning("Lambda invocation returned None (check permissions/function)")
    else:
        logger.info("No Lambda functions found. Skipping invocation.")

    # ------------------------------------------------------------------
    # Part 5: CloudWatch - Create an alarm
    # ------------------------------------------------------------------
    logger.info("\n[5] Creating a CloudWatch alarm...")
    if instances:
        instance_id = instances[0]['InstanceId']
        alarm_name = f"HighCPU-{instance_id}-Demo"
        alarm_actions = [topic_arn] if topic_arn else None

        success = cw.put_alarm(
            alarm_name=alarm_name,
            namespace='AWS/EC2',
            metric_name='CPUUtilization',
            dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            threshold=80.0,
            comparison_operator='GreaterThanThreshold',
            evaluation_periods=2,
            period=300,
            statistic='Average',
            description='Demo alarm for high CPU utilization',
            alarm_actions=alarm_actions
        )
        if success:
            logger.info(f"Alarm '{alarm_name}' created successfully")
        else:
            logger.warning("Alarm creation failed (check permissions)")
    else:
        logger.info("No EC2 instances found; skipping alarm creation.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    logger.info("\n" + "=" * 60)
    logger.info("Workflow completed successfully!")
    logger.info("Summary:")
    logger.info(f"  - EC2 instances: {instance_count}")
    logger.info(f"  - SNS topic: {topic_arn if topic_arn else 'Failed'}")
    logger.info(f"  - SQS queue: {queue_url if queue_url else 'Failed'}")
    logger.info(f"  - Lambda functions found: {len(functions)}")
    logger.info("=" * 60)


if __name__ == "__main__":
    # You can change the region or pass it via command line
    import argparse
    parser = argparse.ArgumentParser(description='Run AWS workflow demo.')
    parser.add_argument('--region', default='us-east-1', help='AWS region (default: us-east-1)')
    args = parser.parse_args()

    run_workflow(region=args.region)