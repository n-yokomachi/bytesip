import * as cdk from "aws-cdk-lib";
import { Template, Match } from "aws-cdk-lib/assertions";
import { ByteSipStack } from "../lib/bytesip-stack";

describe("ByteSipStack Synthesis", () => {
  test("synthesizes without error", () => {
    const app = new cdk.App();
    const stack = new ByteSipStack(app, "TestStack", {
      environment: "development",
    });

    const template = Template.fromStack(stack);
    expect(template).toBeDefined();
  });

  test("has deployEnvironment attribute", () => {
    const app = new cdk.App();
    const stack = new ByteSipStack(app, "TestStack", {
      environment: "production",
    });

    expect(stack.deployEnvironment).toBe("production");
  });

  test("works with different environments", () => {
    const app = new cdk.App();
    const environments = ["development", "staging", "production"];

    for (const env of environments) {
      const stack = new ByteSipStack(app, `TestStack-${env}`, {
        environment: env,
      });
      expect(stack.deployEnvironment).toBe(env);
    }
  });
});

describe("DynamoDB Table", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new ByteSipStack(app, "TestStack", {
      environment: "development",
    });
    template = Template.fromStack(stack);
  });

  test("exists", () => {
    template.resourceCountIs("AWS::DynamoDB::Table", 1);
  });

  test("has correct key schema", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      KeySchema: [
        { AttributeName: "PK", KeyType: "HASH" },
        { AttributeName: "SK", KeyType: "RANGE" },
      ],
    });
  });

  test("has correct attribute definitions", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      AttributeDefinitions: [
        { AttributeName: "PK", AttributeType: "S" },
        { AttributeName: "SK", AttributeType: "S" },
      ],
    });
  });

  test("uses pay per request", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      BillingMode: "PAY_PER_REQUEST",
    });
  });

  test("has TTL enabled", () => {
    template.hasResourceProperties("AWS::DynamoDB::Table", {
      TimeToLiveSpecification: {
        AttributeName: "ttl",
        Enabled: true,
      },
    });
  });
});

describe("Lambda Function", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new ByteSipStack(app, "TestStack", {
      environment: "development",
    });
    template = Template.fromStack(stack);
  });

  test("exists", () => {
    template.resourceCountIs("AWS::Lambda::Function", 1);
  });

  test("uses Python 3.12", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Runtime: "python3.12",
    });
  });

  test("has correct handler", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Handler: "handler.lambda_handler",
    });
  });

  test("has DYNAMODB_TABLE_NAME environment variable", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Environment: {
        Variables: {
          DYNAMODB_TABLE_NAME: Match.anyValue(),
        },
      },
    });
  });

  test("has timeout", () => {
    template.hasResourceProperties("AWS::Lambda::Function", {
      Timeout: 30,
    });
  });
});

describe("Secrets Manager", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new ByteSipStack(app, "TestStack", {
      environment: "development",
    });
    template = Template.fromStack(stack);
  });

  test("creates two secrets", () => {
    template.resourceCountIs("AWS::SecretsManager::Secret", 2);
  });

  test("creates Qiita secret with correct name", () => {
    template.hasResourceProperties("AWS::SecretsManager::Secret", {
      Name: "bytesip/development/qiita-access-token",
    });
  });

  test("creates GitHub secret with correct name", () => {
    template.hasResourceProperties("AWS::SecretsManager::Secret", {
      Name: "bytesip/development/github-access-token",
    });
  });
});

describe("IAM Permissions", () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new ByteSipStack(app, "TestStack", {
      environment: "development",
    });
    template = Template.fromStack(stack);
  });

  test("Lambda has DynamoDB permissions", () => {
    template.hasResourceProperties("AWS::IAM::Policy", {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Action: Match.anyValue(),
            Effect: "Allow",
            Resource: Match.anyValue(),
          }),
        ]),
      },
    });
  });
});
