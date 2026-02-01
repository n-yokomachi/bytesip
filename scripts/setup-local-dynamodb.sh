#!/bin/bash
# Setup DynamoDB Local for ByteSip development

set -e

# Configuration (can be overridden by environment variables)
ENDPOINT_URL="${DYNAMODB_ENDPOINT_URL:-http://localhost:8000}"
TABLE_NAME="${DYNAMODB_TABLE_NAME:-bytesip-news-cache}"
REGION="${AWS_REGION:-ap-northeast-1}"

echo "=== ByteSip DynamoDB Local Setup ==="
echo "Endpoint: $ENDPOINT_URL"
echo "Table: $TABLE_NAME"
echo "Region: $REGION"
echo ""

# Check if DynamoDB Local is running
echo "Checking DynamoDB Local connection..."
if ! aws dynamodb list-tables --endpoint-url "$ENDPOINT_URL" --region "$REGION" > /dev/null 2>&1; then
    echo "Error: DynamoDB Local is not running."
    echo "Please start it with: docker-compose up -d dynamodb-local"
    exit 1
fi

echo "DynamoDB Local is running."

# Check if table already exists
echo "Checking if table '$TABLE_NAME' exists..."
if aws dynamodb describe-table --table-name "$TABLE_NAME" --endpoint-url "$ENDPOINT_URL" --region "$REGION" > /dev/null 2>&1; then
    echo "Table '$TABLE_NAME' already exists."
    read -p "Do you want to delete and recreate it? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Deleting existing table..."
        aws dynamodb delete-table --table-name "$TABLE_NAME" --endpoint-url "$ENDPOINT_URL" --region "$REGION"
        echo "Waiting for table deletion..."
        sleep 2
    else
        echo "Keeping existing table."
        exit 0
    fi
fi

# Create table
echo "Creating table '$TABLE_NAME'..."
aws dynamodb create-table \
    --table-name "$TABLE_NAME" \
    --attribute-definitions \
        AttributeName=PK,AttributeType=S \
        AttributeName=SK,AttributeType=S \
    --key-schema \
        AttributeName=PK,KeyType=HASH \
        AttributeName=SK,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST \
    --endpoint-url "$ENDPOINT_URL" \
    --region "$REGION"

echo "Waiting for table to be active..."
aws dynamodb wait table-exists --table-name "$TABLE_NAME" --endpoint-url "$ENDPOINT_URL" --region "$REGION"

# Enable TTL (Note: DynamoDB Local doesn't enforce TTL, but we set it for consistency)
echo "Enabling TTL on 'ttl' attribute..."
aws dynamodb update-time-to-live \
    --table-name "$TABLE_NAME" \
    --time-to-live-specification "Enabled=true,AttributeName=ttl" \
    --endpoint-url "$ENDPOINT_URL" \
    --region "$REGION"

echo ""
echo "=== Setup Complete ==="
echo "Table Name: $TABLE_NAME"
echo "Endpoint: $ENDPOINT_URL"
echo ""
echo "Environment variables for local development:"
echo "  export DYNAMODB_TABLE_NAME=$TABLE_NAME"
echo "  export DYNAMODB_ENDPOINT_URL=$ENDPOINT_URL"
echo "  export AWS_REGION=$REGION"
echo ""
echo "To use in Python:"
echo "  from config import get_dynamodb_config"
echo "  config = get_dynamodb_config()"
