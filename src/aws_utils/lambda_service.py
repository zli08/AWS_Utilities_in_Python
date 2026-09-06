"""
Lambda service wrapper.
"""

import json
from typing import List, Dict, Any, Optional, Union
from botocore.exceptions import ClientError
from .aws_service import AWSService, AWSConfig


class LambdaService(AWSService):
    """Wrapper for AWS Lambda operations."""

    def _create_client(self):
        return self.session.client('lambda')

    def invoke(self, function_name: str, payload: Dict[str, Any],
               invocation_type: str = 'RequestResponse',
               qualifier: Optional[str] = None) -> Optional[Union[Dict, int]]:
        """
        Invoke a Lambda function.
        - invocation_type: 'RequestResponse' (sync) or 'Event' (async)
        - Returns: For sync, the decoded response payload; for async, status code.
        """
        try:
            params = {
                'FunctionName': function_name,
                'InvocationType': invocation_type,
                'Payload': json.dumps(payload)
            }
            if qualifier:
                params['Qualifier'] = qualifier

            response = self.client.invoke(**params)

            if invocation_type == 'RequestResponse':
                payload_data = response['Payload'].read()
                result = json.loads(payload_data)
                logger.info(f"Lambda invoked (sync): {result}")
                return result
            else:
                status = response['StatusCode']
                logger.info(f"Lambda invoked (async): status {status}")
                return status
        except ClientError as e:
            self._handle_error('invoke', e)
            return None

    def list_functions(self) -> List[Dict[str, Any]]:
        """List all Lambda functions with basic info."""
        try:
            response = self.client.list_functions()
            functions = response.get('Functions', [])
            logger.info(f"Found {len(functions)} Lambda functions")
            return functions
        except ClientError as e:
            self._handle_error('list_functions', e)
            return []

    def get_function(self, function_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed configuration of a Lambda function."""
        try:
            response = self.client.get_function(FunctionName=function_name)
            return response
        except ClientError as e:
            self._handle_error('get_function', e)
            return None

    def update_function_code(self, function_name: str, zip_file: bytes,
                             publish: bool = False) -> Optional[Dict]:
        """Update Lambda function code with a ZIP file bytes."""
        try:
            response = self.client.update_function_code(
                FunctionName=function_name,
                ZipFile=zip_file,
                Publish=publish
            )
            logger.info(f"Updated function code for {function_name}")
            return response
        except ClientError as e:
            self._handle_error('update_function_code', e)
            return None

    def update_function_configuration(self, function_name: str,
                                      **kwargs) -> Optional[Dict]:
        """Update Lambda function configuration (memory, timeout, etc.)."""
        try:
            response = self.client.update_function_configuration(
                FunctionName=function_name,
                **kwargs
            )
            logger.info(f"Updated configuration for {function_name}")
            return response
        except ClientError as e:
            self._handle_error('update_function_configuration', e)
            return None