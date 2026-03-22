import * as path from "path";
import * as agentcore from "@aws-cdk/aws-bedrock-agentcore-alpha";
import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

export interface AgentCoreConstructProps {
  /**
   * Deployment environment (development, staging, production)
   */
  readonly environment: string;

  /**
   * Lambda function for news fetching (Gateway target)
   */
  readonly newsFetcherFunction: lambda.IFunction;
}

/**
 * AgentCore resources for ByteSip agent.
 *
 * Creates:
 * - Memory (STM only, 30-day expiry)
 * - Runtime (direct code deploy, Python 3.12)
 * - Gateway (MCP protocol)
 * - Gateway Target (Lambda integration with fetch_news tool)
 */
export class AgentCoreConstruct extends Construct {
  public readonly memory: agentcore.Memory;
  public readonly runtime: agentcore.Runtime;
  public readonly gateway: agentcore.Gateway;

  constructor(scope: Construct, id: string, props: AgentCoreConstructProps) {
    super(scope, id);

    const { environment, newsFetcherFunction } = props;

    // Memory (STM only, 30-day event expiry)
    this.memory = new agentcore.Memory(this, "Memory", {
      memoryName: `bytesip_mem`,
      description: "ByteSip agent memory for session management",
      expirationDuration: cdk.Duration.days(30),
    });

    // Runtime artifact from agent source code (with dependency bundling)
    const agentSourcePath = path.join(__dirname, "..", "..", "..", "agent");
    const artifact = agentcore.AgentRuntimeArtifact.fromCodeAsset({
      path: agentSourcePath,
      runtime: agentcore.AgentCoreRuntime.PYTHON_3_12,
      entrypoint: ["opentelemetry-instrument", "entrypoint.py"],
      bundling: {
        image: cdk.DockerImage.fromRegistry("python:3.12"),
        command: [
          "bash",
          "-c",
          [
            "pip install . -t /asset-output",
            "cp entrypoint.py /asset-output/",
          ].join(" && "),
        ],
      },
    });

    // Runtime
    this.runtime = new agentcore.Runtime(this, "Runtime", {
      runtimeName: "bytesip",
      agentRuntimeArtifact: artifact,
      environmentVariables: {
        AGENTCORE_MEMORY_ID: this.memory.memoryId,
        BYTESIP_MEMORY_NAME: "bytesip_mem",
      },
    });

    // Grant memory access to runtime
    this.memory.grantRead(this.runtime);
    this.memory.grantWrite(this.runtime);

    // Grant Bedrock model invocation to runtime execution role
    this.runtime.role.addToPrincipalPolicy(
      new iam.PolicyStatement({
        actions: [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream",
        ],
        resources: ["*"],
      })
    );

    // Grant Lambda invocation to runtime (agent calls Lambda directly via boto3)
    newsFetcherFunction.grantInvoke(this.runtime);

    // Gateway (MCP protocol, IAM auth)
    this.gateway = new agentcore.Gateway(this, "Gateway", {
      gatewayName: "bytesip-gateway",
      description: "ByteSip news agent gateway",
      protocolConfiguration: agentcore.GatewayProtocol.mcp({
        supportedVersions: [agentcore.MCPProtocolVersion.MCP_2025_03_26],
        searchType: agentcore.McpGatewaySearchType.SEMANTIC,
      }),
      authorizerConfiguration: agentcore.GatewayAuthorizer.usingAwsIam(),
    });

    // Gateway Target (Lambda with fetch_news tool schema)
    this.gateway.addLambdaTarget("FetchNewsTarget", {
      gatewayTargetName: "bytesip-fetch-news",
      description:
        "Lambda target for fetching IT/AI news from Qiita, Zenn, and GitHub",
      lambdaFunction: newsFetcherFunction,
      toolSchema: agentcore.ToolSchema.fromInline([
        {
          name: "fetch_news",
          description:
            "Fetch IT/AI news from Qiita, Zenn, and GitHub. Results are cached for 24 hours.",
          inputSchema: {
            type: agentcore.SchemaDefinitionType.OBJECT,
            properties: {
              sources: {
                type: agentcore.SchemaDefinitionType.ARRAY,
                items: { type: agentcore.SchemaDefinitionType.STRING },
                description:
                  "Sources to fetch from: qiita, zenn, github. If not specified, fetches from all.",
              },
              tags: {
                type: agentcore.SchemaDefinitionType.ARRAY,
                items: { type: agentcore.SchemaDefinitionType.STRING },
                description:
                  "Technology tags to filter by (e.g., python, rust)",
              },
              force_refresh: {
                type: agentcore.SchemaDefinitionType.BOOLEAN,
                description:
                  "If true, bypass cache and fetch fresh data",
              },
            },
          },
        },
      ]),
    });

    // Lambda resource policy: allow Gateway to invoke
    newsFetcherFunction.addPermission("AgentCoreGatewayInvoke", {
      principal: new cdk.aws_iam.ServicePrincipal(
        "bedrock-agentcore.amazonaws.com"
      ),
      sourceArn: this.gateway.gatewayArn,
    });

    // CloudFormation outputs
    new cdk.CfnOutput(this, "MemoryId", {
      value: this.memory.memoryId,
      description: "AgentCore Memory ID",
    });

    new cdk.CfnOutput(this, "RuntimeArn", {
      value: this.runtime.agentRuntimeArn,
      description: "AgentCore Runtime ARN",
    });

    new cdk.CfnOutput(this, "GatewayUrl", {
      value: this.gateway.gatewayUrl ?? "",
      description: "AgentCore Gateway URL",
    });
  }
}
