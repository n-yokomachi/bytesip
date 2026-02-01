"""ByteSip Infrastructure Stack.

This stack defines the core AWS resources for ByteSip:
- DynamoDB table for news cache
- Lambda function for news fetching
- SSM parameter references for API tokens
"""

from pathlib import Path

from aws_cdk import Duration, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_ssm as ssm
from constructs import Construct


class ByteSipStack(Stack):
    """Main infrastructure stack for ByteSip News Agent."""

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        environment: str = "development",
        **kwargs,
    ) -> None:
        """Initialize the ByteSip stack.

        Args:
            scope: CDK scope
            construct_id: Stack ID
            environment: Deployment environment (development, staging, production)
            **kwargs: Additional stack arguments
        """
        super().__init__(scope, construct_id, **kwargs)

        self.deploy_environment = environment

        # DynamoDB table for news cache
        self.news_cache_table = self._create_dynamodb_table()

        # Lambda function for news fetching
        self.news_fetcher_function = self._create_lambda_function()

        # Grant Lambda permissions to access DynamoDB
        self.news_cache_table.grant_read_write_data(self.news_fetcher_function)

    def _create_dynamodb_table(self) -> dynamodb.Table:
        """Create DynamoDB table for news cache.

        Table schema:
        - PK: SOURCE#<source_name> (e.g., SOURCE#qiita)
        - SK: ITEM#<item_id> or META

        Returns:
            DynamoDB Table construct
        """
        table = dynamodb.Table(
            self,
            "NewsCacheTable",
            table_name=f"bytesip-news-cache-{self.deploy_environment}",
            partition_key=dynamodb.Attribute(
                name="PK",
                type=dynamodb.AttributeType.STRING,
            ),
            sort_key=dynamodb.Attribute(
                name="SK",
                type=dynamodb.AttributeType.STRING,
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            time_to_live_attribute="ttl",
            removal_policy=(
                RemovalPolicy.DESTROY
                if self.deploy_environment == "development"
                else RemovalPolicy.RETAIN
            ),
        )
        return table

    def _create_lambda_function(self) -> lambda_.Function:
        """Create Lambda function for news fetching.

        Returns:
            Lambda Function construct
        """
        # Path to Lambda code (relative to CDK project root)
        lambda_code_path = Path(__file__).parent.parent.parent / "lambda" / "bytesip_news_fetcher"

        # SSM parameter names for API tokens
        qiita_token_param = f"/bytesip/{self.deploy_environment}/qiita-access-token"
        github_token_param = f"/bytesip/{self.deploy_environment}/github-access-token"

        function = lambda_.Function(
            self,
            "NewsFetcherFunction",
            function_name=f"bytesip-news-fetcher-{self.deploy_environment}",
            runtime=lambda_.Runtime.PYTHON_3_12,
            handler="handler.lambda_handler",
            code=lambda_.Code.from_asset(str(lambda_code_path)),
            timeout=Duration.seconds(30),
            memory_size=256,
            environment={
                "DYNAMODB_TABLE_NAME": self.news_cache_table.table_name,
                "QIITA_ACCESS_TOKEN_PARAM": qiita_token_param,
                "GITHUB_ACCESS_TOKEN_PARAM": github_token_param,
            },
        )

        # Grant read access to SSM parameters
        qiita_param = ssm.StringParameter.from_secure_string_parameter_attributes(
            self,
            "QiitaTokenParam",
            parameter_name=qiita_token_param,
        )
        github_param = ssm.StringParameter.from_secure_string_parameter_attributes(
            self,
            "GitHubTokenParam",
            parameter_name=github_token_param,
        )
        qiita_param.grant_read(function)
        github_param.grant_read(function)

        return function
