import * as path from "path";
import * as cdk from "aws-cdk-lib";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as secretsmanager from "aws-cdk-lib/aws-secretsmanager";
import { Construct } from "constructs";

export interface ByteSipStackProps extends cdk.StackProps {
  /**
   * Deployment environment (development, staging, production)
   * @default "development"
   */
  readonly environment?: string;
}

/**
 * ByteSip Infrastructure Stack
 *
 * Creates the core AWS resources for ByteSip News Agent:
 * - DynamoDB table for news cache
 * - Lambda function for news fetching
 * - Secrets Manager for API tokens
 */
export class ByteSipStack extends cdk.Stack {
  public readonly deployEnvironment: string;
  public readonly newsCacheTable: dynamodb.Table;
  public readonly qiitaSecret: secretsmanager.ISecret;
  public readonly githubSecret: secretsmanager.ISecret;
  public readonly newsFetcherFunction: lambda.Function;

  constructor(scope: Construct, id: string, props?: ByteSipStackProps) {
    super(scope, id, props);

    this.deployEnvironment = props?.environment ?? "development";

    // DynamoDB table for news cache
    this.newsCacheTable = this.createDynamoDBTable();

    // Secrets Manager secrets for API tokens
    const secrets = this.createSecrets();
    this.qiitaSecret = secrets.qiitaSecret;
    this.githubSecret = secrets.githubSecret;

    // Lambda function for news fetching
    this.newsFetcherFunction = this.createLambdaFunction();

    // Grant Lambda permissions
    this.newsCacheTable.grantReadWriteData(this.newsFetcherFunction);
    this.qiitaSecret.grantRead(this.newsFetcherFunction);
    this.githubSecret.grantRead(this.newsFetcherFunction);
  }

  private createDynamoDBTable(): dynamodb.Table {
    return new dynamodb.Table(this, "NewsCacheTable", {
      tableName: `bytesip-news-cache-${this.deployEnvironment}`,
      partitionKey: {
        name: "PK",
        type: dynamodb.AttributeType.STRING,
      },
      sortKey: {
        name: "SK",
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "ttl",
      removalPolicy:
        this.deployEnvironment === "development"
          ? cdk.RemovalPolicy.DESTROY
          : cdk.RemovalPolicy.RETAIN,
    });
  }

  private createSecrets(): {
    qiitaSecret: secretsmanager.ISecret;
    githubSecret: secretsmanager.ISecret;
  } {
    const qiitaToken = process.env.QIITA_ACCESS_TOKEN;
    const githubToken = process.env.GITHUB_ACCESS_TOKEN;

    const qiitaSecretName = `bytesip/${this.deployEnvironment}/qiita-access-token`;
    const githubSecretName = `bytesip/${this.deployEnvironment}/github-access-token`;

    // Only create/update secrets if tokens are provided via environment variables
    // Otherwise, just reference existing secrets
    if (qiitaToken) {
      const qiitaCfnSecret = new secretsmanager.CfnSecret(
        this,
        "QiitaAccessToken",
        {
          name: qiitaSecretName,
          secretString: qiitaToken,
        }
      );
      if (this.deployEnvironment === "development") {
        qiitaCfnSecret.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);
      }
    }

    if (githubToken) {
      const githubCfnSecret = new secretsmanager.CfnSecret(
        this,
        "GitHubAccessToken",
        {
          name: githubSecretName,
          secretString: githubToken,
        }
      );
      if (this.deployEnvironment === "development") {
        githubCfnSecret.applyRemovalPolicy(cdk.RemovalPolicy.DESTROY);
      }
    }

    // Import secrets for grant operations (assumes secrets exist)
    const qiitaSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "QiitaSecretRef",
      qiitaSecretName
    );
    const githubSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      "GitHubSecretRef",
      githubSecretName
    );

    return { qiitaSecret, githubSecret };
  }

  private createLambdaFunction(): lambda.Function {
    const lambdaBasePath = path.join(__dirname, "..", "..", "lambda");
    const lambdaCodePath = path.join(lambdaBasePath, "bytesip_news_fetcher");

    return new lambda.Function(this, "NewsFetcherFunction", {
      functionName: `bytesip-news-fetcher-${this.deployEnvironment}`,
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.lambda_handler",
      code: lambda.Code.fromAsset(lambdaBasePath, {
        bundling: {
          image: lambda.Runtime.PYTHON_3_12.bundlingImage,
          command: [
            "bash",
            "-c",
            [
              "pip install requests feedparser -t /asset-output",
              "cp -r bytesip_news_fetcher/* /asset-output/",
            ].join(" && "),
          ],
        },
      }),
      timeout: cdk.Duration.seconds(30),
      memorySize: 256,
      environment: {
        // AWS_REGION is automatically set by Lambda runtime
        DYNAMODB_TABLE_NAME: this.newsCacheTable.tableName,
        QIITA_SECRET_NAME: this.qiitaSecret.secretName,
        GITHUB_SECRET_NAME: this.githubSecret.secretName,
      },
    });
  }
}
