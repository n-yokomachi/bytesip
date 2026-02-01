#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { ByteSipStack } from "../lib/bytesip-stack";

const app = new cdk.App();

const environment = app.node.tryGetContext("environment") ?? "development";

new ByteSipStack(app, `ByteSipStack-${environment}`, {
  environment,
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "ap-northeast-1",
  },
});
