import json
import boto3
import time
import datetime
from botocore.exceptions import ClientError

# Initialize clients
ec2_client = boto3.client('ec2')
ec2_resource = boto3.resource('ec2')
sns_client = boto3.client('sns')
sqs_client = boto3.client('sqs')
lambda_client = boto3.client('lambda')
cloudwatch_client = boto3.client('cloudwatch')


# ============================================
# 1. EC2 Operations
# ============================================

def list_ec2_instances():
    """List all EC2 instances with their states"""
    try:
        response = ec2_client.describe_instances()
        instances = []
        for reservation in response['Reservations']:
            for instance in reservation['Instances']:
                instances.append({
                    'InstanceId': instance['InstanceId'],
                    'State': instance['State']['Name'],
                    'InstanceType': instance['InstanceType'],
                    'LaunchTime': str(instance['LaunchTime'])
                })
        return instances
    except ClientError as e:
        print(f"Error listing EC2 instances: {e}")
        return []


def create_ec2_instance():
    """Create a new EC2 instance"""
    try:
        instance = ec2_resource.create_instances(
            ImageId='ami-0abcdef1234567890',  # Replace with your AMI ID
            MinCount=1,
            MaxCount=1,
            InstanceType='t2.micro',
            KeyName='your-key-pair',  # Replace with your key pair name
            SecurityGroupIds=['sg-xxxxxxxxxx'],  # Replace with your security group ID
            SubnetId='subnet-xxxxxxxxxx'  # Replace with your subnet ID
        )
        print(f"EC2 instance created: {instance[0].id}")
        return instance[0].id
    except ClientError as e:
        print(f"Error creating EC2 instance: {e}")
        return None


def start_stop_ec2_instance(instance_id, action='start'):
    """Start or stop an EC2 instance"""
    try:
        if action == 'start':
            response = ec2_client.start_instances(InstanceIds=[instance_id])
            print(f"Starting instance {instance_id}")
        elif action == 'stop':
            response = ec2_client.stop_instances(InstanceIds=[instance_id])
            print(f"Stopping instance {instance_id}")
        return response
    except ClientError as e:
        print(f"Error {action}ing instance: {e}")
        return None


# ============================================
# 2. SNS Operations
# ============================================

def create_sns_topic(topic_name):
    """Create an SNS topic"""
    try:
        response = sns_client.create_topic(Name=topic_name)
        topic_arn = response['TopicArn']
        print(f"SNS Topic created: {topic_arn}")
        return topic_arn
    except ClientError as e:
        print(f"Error creating SNS topic: {e}")
        return None


def publish_sns_message(topic_arn, message, subject=None):
    """Publish a message to an SNS topic"""
    try:
        response = sns_client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=subject or 'Notification from Python Script'
        )
        print(f"Message published with ID: {response['MessageId']}")
        return response['MessageId']
    except ClientError as e:
        print(f"Error publishing SNS message: {e}")
        return None


def subscribe_email_to_sns(topic_arn, email):
    """Subscribe an email address to an SNS topic"""
    try:
        response = sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email
        )
        print(f"Email {email} subscribed to topic. Subscription ARN: {response['SubscriptionArn']}")
        return response['SubscriptionArn']
    except ClientError as e:
        print(f"Error subscribing to SNS topic: {e}")
        return None


# ============================================
# 3. SQS Operations
# ============================================

def create_sqs_queue(queue_name):
    """Create an SQS queue"""
    try:
        response = sqs_client.create_queue(
            QueueName=queue_name,
            Attributes={
                'DelaySeconds': '0',
                'MessageRetentionPeriod': '86400'  # 1 day
            }
        )
        queue_url = response['QueueUrl']
        print(f"SQS Queue created: {queue_url}")
        return queue_url
    except ClientError as e:
        print(f"Error creating SQS queue: {e}")
        return None


def send_sqs_message(queue_url, message_body, message_attributes=None):
    """Send a message to an SQS queue"""
    try:
        response = sqs_client.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps(message_body),
            MessageAttributes=message_attributes or {}
        )
        print(f"SQS message sent with ID: {response['MessageId']}")
        return response['MessageId']
    except ClientError as e:
        print(f"Error sending SQS message: {e}")
        return None


def receive_sqs_messages(queue_url, max_messages=10, wait_time=20):
    """Receive messages from an SQS queue"""
    try:
        response = sqs_client.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=max_messages,
            WaitTimeSeconds=wait_time,
            AttributeNames=['All'],
            MessageAttributeNames=['All']
        )
        messages = response.get('Messages', [])
        print(f"Received {len(messages)} messages from SQS")
        return messages
    except ClientError as e:
        print(f"Error receiving SQS messages: {e}")
        return []


def delete_sqs_message(queue_url, receipt_handle):
    """Delete a message from an SQS queue after processing"""
    try:
        sqs_client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        print("SQS message deleted")
        return True
    except ClientError as e:
        print(f"Error deleting SQS message: {e}")
        return False


# ============================================
# 4. Lambda Operations
# ============================================

def invoke_lambda_function(function_name, payload, invocation_type='RequestResponse'):
    """Invoke a Lambda function"""
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType=invocation_type,  # 'RequestResponse' or 'Event' (async)
            Payload=json.dumps(payload)
        )

        if invocation_type == 'RequestResponse':
            response_payload = json.loads(response['Payload'].read())
            print(f"Lambda invoked successfully. Response: {response_payload}")
            return response_payload
        else:
            print(f"Lambda invoked asynchronously. Status: {response['StatusCode']}")
            return response['StatusCode']
    except ClientError as e:
        print(f"Error invoking Lambda function: {e}")
        return None


def list_lambda_functions():
    """List all Lambda functions"""
    try:
        response = lambda_client.list_functions()
        functions = [func['FunctionName'] for func in response['Functions']]
        print(f"Found {len(functions)} Lambda functions")
        return functions
    except ClientError as e:
        print(f"Error listing Lambda functions: {e}")
        return []


# ============================================
# 5. CloudWatch Operations
# ============================================

def put_custom_metric(namespace, metric_name, value, unit='Count', dimensions=None):
    """Publish a custom metric to CloudWatch"""
    try:
        metric_data = [
            {
                'MetricName': metric_name,
                'Value': value,
                'Unit': unit,
                'Timestamp': datetime.datetime.utcnow()
            }
        ]

        if dimensions:
            metric_data[0]['Dimensions'] = dimensions

        response = cloudwatch_client.put_metric_data(
            Namespace=namespace,
            MetricData=metric_data
        )
        print(f"Metric {metric_name} published to CloudWatch")
        return response
    except ClientError as e:
        print(f"Error publishing metric to CloudWatch: {e}")
        return None


def get_cloudwatch_metrics(namespace, metric_name, dimensions, start_time, end_time, period=300, statistic='Average'):
    """Retrieve CloudWatch metrics"""
    try:
        response = cloudwatch_client.get_metric_statistics(
            Namespace=namespace,
            MetricName=metric_name,
            Dimensions=dimensions,
            StartTime=start_time,
            EndTime=end_time,
            Period=period,
            Statistics=[statistic]
        )
        datapoints = response['Datapoints']
        print(f"Retrieved {len(datapoints)} datapoints for {metric_name}")
        return datapoints
    except ClientError as e:
        print(f"Error retrieving CloudWatch metrics: {e}")
        return []


def create_cloudwatch_alarm(alarm_name, namespace, metric_name, dimensions, threshold,
                            comparison_operator='GreaterThanThreshold', evaluation_periods=1, period=300,
                            statistic='Average', sns_topic_arn=None):
    """Create a CloudWatch alarm"""
    try:
        alarm_config = {
            'AlarmName': alarm_name,
            'AlarmDescription': f'Alarm for {metric_name}',
            'ActionsEnabled': True,
            'MetricName': metric_name,
            'Namespace': namespace,
            'Statistic': statistic,
            'Dimensions': dimensions,
            'Period': period,
            'EvaluationPeriods': evaluation_periods,
            'Threshold': threshold,
            'ComparisonOperator': comparison_operator
        }

        if sns_topic_arn:
            alarm_config['AlarmActions'] = [sns_topic_arn]

        response = cloudwatch_client.put_metric_alarm(**alarm_config)
        print(f"CloudWatch alarm {alarm_name} created")
        return response
    except ClientError as e:
        print(f"Error creating CloudWatch alarm: {e}")
        return None


# ============================================
# 6. Combined Example - Monitoring Workflow
# ============================================

def monitoring_workflow():
    """
    A complete workflow that demonstrates all services:
    1. List EC2 instances
    2. Publish instance count to CloudWatch
    3. Create an SNS topic and subscribe an email
    4. Create an SQS queue and send a message
    5. Invoke a Lambda function to process the SQS message
    6. Create a CloudWatch alarm for CPU utilization
    """
    print("=" * 60)
    print("Starting AWS Monitoring Workflow")
    print("=" * 60)

    # Step 1: EC2 - List instances and count them
    print("\n[1] Listing EC2 instances...")
    instances = list_ec2_instances()
    instance_count = len(instances)
    for inst in instances:
        print(f"  - {inst['InstanceId']} ({inst['State']})")

    # Step 2: CloudWatch - Publish custom metric (instance count)
    print(f"\n[2] Publishing instance count ({instance_count}) to CloudWatch...")
    put_custom_metric(
        namespace='MyApp/Monitoring',
        metric_name='EC2InstanceCount',
        value=instance_count,
        unit='Count'
    )

    # Step 3: SNS - Create topic and subscribe
    print("\n[3] Setting up SNS notifications...")
    topic_arn = create_sns_topic('MyMonitoringTopic')
    if topic_arn:
        # Uncomment to subscribe an email (replace with your email)
        # subscribe_email_to_sns(topic_arn, 'your-email@example.com')
        publish_sns_message(topic_arn, f'Workflow started. Found {instance_count} EC2 instances.', 'Workflow Status')

    # Step 4: SQS - Create queue and send message
    print("\n[4] Setting up SQS queue...")
    queue_url = create_sqs_queue('MyWorkflowQueue')
    if queue_url:
        send_sqs_message(
            queue_url,
            {'action': 'process_instances', 'instance_count': instance_count,
             'timestamp': str(datetime.datetime.utcnow())}
        )

        # Receive and process messages
        messages = receive_sqs_messages(queue_url, max_messages=5)
        for msg in messages:
            print(f"  - Processing message: {msg['Body']}")
            # Delete after processing
            delete_sqs_message(queue_url, msg['ReceiptHandle'])

    # Step 5: Lambda - Invoke a function (replace with your function name)
    print("\n[5] Invoking Lambda function...")
    lambda_functions = list_lambda_functions()
    if lambda_functions:
        # Invoke the first Lambda function found
        invoke_lambda_function(
            lambda_functions[0],
            {'action': 'monitoring_check', 'instance_count': instance_count}
        )

    # Step 6: CloudWatch - Create an alarm (example)
    print("\n[6] Creating CloudWatch alarm...")
    create_cloudwatch_alarm(
        alarm_name='HighCPUUtilization-Alarm',
        namespace='AWS/EC2',
        metric_name='CPUUtilization',
        dimensions=[{'Name': 'InstanceId', 'Value': 'i-xxxxxxxxxx'}],  # Replace with actual instance ID
        threshold=80.0,
        comparison_operator='GreaterThanThreshold',
        evaluation_periods=2,
        period=300,
        statistic='Average',
        sns_topic_arn=topic_arn
    )

    print("\n" + "=" * 60)
    print("Workflow completed successfully!")
    print("=" * 60)


# ============================================
# Main execution
# ============================================

if __name__ == "__main__":
    monitoring_workflow()