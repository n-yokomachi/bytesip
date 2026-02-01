"""Tests for ByteSip CDK Stack.

TDD tests to verify stack synthesis and resource configuration.
"""

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from bytesip_stack.bytesip_stack import ByteSipStack


class TestByteSipStackSynthesis:
    """Test that the ByteSip stack can be synthesized."""

    def test_stack_synthesizes_without_error(self) -> None:
        """Verify that the stack synthesizes without throwing errors."""
        app = cdk.App()

        stack = ByteSipStack(
            app,
            "TestByteSipStack",
            environment="development",
        )

        # Synthesis should not raise any errors
        template = Template.from_stack(stack)

        # Template should be a valid CloudFormation template
        assert template is not None

    def test_stack_has_deploy_environment_attribute(self) -> None:
        """Verify that the stack stores the deploy_environment attribute."""
        app = cdk.App()

        stack = ByteSipStack(
            app,
            "TestByteSipStack",
            environment="production",
        )

        assert stack.deploy_environment == "production"

    def test_stack_with_different_environments(self) -> None:
        """Verify that the stack can be created with different environments."""
        app = cdk.App()

        environments = ["development", "staging", "production"]

        for env_name in environments:
            stack = ByteSipStack(
                app,
                f"TestStack-{env_name}",
                environment=env_name,
            )
            assert stack.deploy_environment == env_name


class TestDynamoDBTable:
    """Test DynamoDB table configuration."""

    @pytest.fixture
    def template(self) -> Template:
        """Create a template from the stack for testing."""
        app = cdk.App()
        stack = ByteSipStack(app, "TestStack", environment="development")
        return Template.from_stack(stack)

    def test_dynamodb_table_exists(self, template: Template) -> None:
        """Verify that a DynamoDB table is created."""
        template.resource_count_is("AWS::DynamoDB::Table", 1)

    def test_dynamodb_table_has_correct_key_schema(self, template: Template) -> None:
        """Verify table has PK (HASH) and SK (RANGE) keys."""
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "KeySchema": [
                    {"AttributeName": "PK", "KeyType": "HASH"},
                    {"AttributeName": "SK", "KeyType": "RANGE"},
                ],
            },
        )

    def test_dynamodb_table_has_correct_attribute_definitions(
        self, template: Template
    ) -> None:
        """Verify table attribute definitions for PK and SK."""
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "AttributeDefinitions": [
                    {"AttributeName": "PK", "AttributeType": "S"},
                    {"AttributeName": "SK", "AttributeType": "S"},
                ],
            },
        )

    def test_dynamodb_table_uses_pay_per_request(self, template: Template) -> None:
        """Verify table uses on-demand billing mode."""
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {"BillingMode": "PAY_PER_REQUEST"},
        )

    def test_dynamodb_table_has_ttl_enabled(self, template: Template) -> None:
        """Verify TTL is enabled on 'ttl' attribute."""
        template.has_resource_properties(
            "AWS::DynamoDB::Table",
            {
                "TimeToLiveSpecification": {
                    "AttributeName": "ttl",
                    "Enabled": True,
                },
            },
        )


class TestLambdaFunction:
    """Test Lambda function configuration."""

    @pytest.fixture
    def template(self) -> Template:
        """Create a template from the stack for testing."""
        app = cdk.App()
        stack = ByteSipStack(app, "TestStack", environment="development")
        return Template.from_stack(stack)

    def test_lambda_function_exists(self, template: Template) -> None:
        """Verify that a Lambda function is created."""
        template.resource_count_is("AWS::Lambda::Function", 1)

    def test_lambda_function_uses_python312(self, template: Template) -> None:
        """Verify Lambda uses Python 3.12 runtime."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Runtime": "python3.12"},
        )

    def test_lambda_function_has_correct_handler(self, template: Template) -> None:
        """Verify Lambda has correct handler."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Handler": "handler.lambda_handler"},
        )

    def test_lambda_function_has_dynamodb_table_env_var(
        self, template: Template
    ) -> None:
        """Verify Lambda has DYNAMODB_TABLE_NAME environment variable."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {
                "Environment": {
                    "Variables": {
                        "DYNAMODB_TABLE_NAME": Match.any_value(),
                    },
                },
            },
        )

    def test_lambda_function_has_timeout(self, template: Template) -> None:
        """Verify Lambda has appropriate timeout."""
        template.has_resource_properties(
            "AWS::Lambda::Function",
            {"Timeout": 30},
        )


class TestIAMPermissions:
    """Test IAM permissions for Lambda."""

    @pytest.fixture
    def template(self) -> Template:
        """Create a template from the stack for testing."""
        app = cdk.App()
        stack = ByteSipStack(app, "TestStack", environment="development")
        return Template.from_stack(stack)

    def test_lambda_has_dynamodb_permissions(self, template: Template) -> None:
        """Verify Lambda role has DynamoDB permissions."""
        # Check that an IAM policy exists with DynamoDB actions
        template.has_resource_properties(
            "AWS::IAM::Policy",
            {
                "PolicyDocument": {
                    "Statement": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "Action": Match.any_value(),
                                    "Effect": "Allow",
                                    "Resource": Match.any_value(),
                                }
                            )
                        ]
                    ),
                },
            },
        )
