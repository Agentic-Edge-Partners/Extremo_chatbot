#!/bin/bash
# =============================================================================
# Extremo Ambiente — AWS Deployment Script
#
# Builds Docker images, pushes to ECR, and deploys the CloudFormation stack.
#
# Usage:
#   ./infra/deploy.sh --region eu-west-1 --stack extremo-chatbot
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - Docker installed and running
#   - .env file with OPENAI_API_KEY, GOOGLE_MAPS_API_KEY, etc.
# =============================================================================

set -euo pipefail

# ---- Defaults ---------------------------------------------------------------
REGION="eu-west-1"
STACK_NAME="extremo-chatbot"
PROFILE=""
ENV_FILE=".env"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ---- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)   REGION="$2"; shift 2 ;;
    --stack)    STACK_NAME="$2"; shift 2 ;;
    --profile)  PROFILE="$2"; shift 2 ;;
    --env-file) ENV_FILE="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--region REGION] [--stack STACK_NAME] [--profile AWS_PROFILE] [--env-file .env]"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

AWS_OPTS=""
if [[ -n "$PROFILE" ]]; then
  AWS_OPTS="--profile $PROFILE"
fi

# ---- Load .env file ---------------------------------------------------------
if [[ ! -f "$PROJECT_DIR/$ENV_FILE" ]]; then
  echo "Error: $ENV_FILE not found in $PROJECT_DIR"
  echo "Create one from .env.example and fill in your API keys."
  exit 1
fi

# Source env vars (only the ones we need)
set -a
source "$PROJECT_DIR/$ENV_FILE"
set +a

# Validate required vars
for VAR in OPENAI_API_KEY GOOGLE_MAPS_API_KEY; do
  if [[ -z "${!VAR:-}" ]]; then
    echo "Error: $VAR is not set in $ENV_FILE"
    exit 1
  fi
done

# ---- Get AWS account ID -----------------------------------------------------
ACCOUNT_ID=$(aws sts get-caller-identity $AWS_OPTS --query Account --output text)
echo "AWS Account: $ACCOUNT_ID"
echo "Region:      $REGION"
echo "Stack:       $STACK_NAME"
echo ""

# ---- ECR Login --------------------------------------------------------------
echo "==> Logging in to ECR..."
aws ecr get-login-password $AWS_OPTS --region "$REGION" | \
  docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com"

# ---- Create ECR repos if they don't exist ------------------------------------
for REPO in extremo-backend extremo-frontend; do
  if ! aws ecr describe-repositories $AWS_OPTS --region "$REGION" --repository-names "$REPO" &>/dev/null; then
    echo "==> Creating ECR repository: $REPO"
    aws ecr create-repository $AWS_OPTS --region "$REGION" --repository-name "$REPO" --image-scanning-configuration scanOnPush=true
  fi
done

# ---- Build & Push Backend Image ----------------------------------------------
BACKEND_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/extremo-backend:latest"
echo ""
echo "==> Building backend image..."
docker build -t extremo-backend "$PROJECT_DIR"

echo "==> Pushing backend image to ECR..."
docker tag extremo-backend:latest "$BACKEND_URI"
docker push "$BACKEND_URI"

# ---- Build & Push Frontend Image ---------------------------------------------
FRONTEND_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/extremo-frontend:latest"
echo ""
echo "==> Building frontend image..."
docker build -t extremo-frontend "$PROJECT_DIR/ui" \
  --build-arg NEXT_PUBLIC_API_URL=/api \
  --build-arg NEXT_PUBLIC_ASSISTANT_ID=agent

echo "==> Pushing frontend image to ECR..."
docker tag extremo-frontend:latest "$FRONTEND_URI"
docker push "$FRONTEND_URI"

# ---- Deploy CloudFormation Stack ---------------------------------------------
echo ""
echo "==> Deploying CloudFormation stack: $STACK_NAME"

if [[ -z "${DB_PASSWORD:-}" ]]; then
  DB_PASSWORD="$(openssl rand -base64 16 | tr -dc 'a-zA-Z0-9' | head -c 16)"
  echo ""
  echo "==========================================="
  echo "  GENERATED DB PASSWORD — SAVE THIS NOW!"
  echo "  DB_PASSWORD: $DB_PASSWORD"
  echo "==========================================="
  echo ""
  echo "Add this to your .env to reuse on future deploys:"
  echo "  echo 'DB_PASSWORD=$DB_PASSWORD' >> $PROJECT_DIR/$ENV_FILE"
  echo ""
fi

aws cloudformation deploy $AWS_OPTS \
  --region "$REGION" \
  --template-file "$SCRIPT_DIR/cloudformation.yaml" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Environment=production \
    DBPassword="$DB_PASSWORD" \
    OpenAIApiKey="$OPENAI_API_KEY" \
    GoogleMapsApiKey="$GOOGLE_MAPS_API_KEY" \
    LangSmithApiKey="${LANGSMITH_API_KEY:-}" \
    LangChainProject="${LANGCHAIN_PROJECT:-extremoambiente-a2}"

# ---- Wait for stack completion -----------------------------------------------
echo ""
echo "==> Waiting for stack to complete..."

STACK_STATUS=$(aws cloudformation describe-stacks $AWS_OPTS \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].StackStatus' \
  --output text 2>/dev/null || echo "UNKNOWN")

if [[ "$STACK_STATUS" == *"CREATE_IN_PROGRESS"* ]]; then
  aws cloudformation wait stack-create-complete $AWS_OPTS --region "$REGION" --stack-name "$STACK_NAME"
elif [[ "$STACK_STATUS" == *"UPDATE_IN_PROGRESS"* ]]; then
  aws cloudformation wait stack-update-complete $AWS_OPTS --region "$REGION" --stack-name "$STACK_NAME"
fi

# Verify final status
FINAL_STATUS=$(aws cloudformation describe-stacks $AWS_OPTS \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query 'Stacks[0].StackStatus' \
  --output text)

if [[ "$FINAL_STATUS" != *"COMPLETE"* ]] || [[ "$FINAL_STATUS" == *"ROLLBACK"* ]]; then
  echo "ERROR: Stack deployment failed with status: $FINAL_STATUS"
  echo "Check CloudFormation events for details:"
  echo "  aws cloudformation describe-stack-events $AWS_OPTS --region $REGION --stack-name $STACK_NAME --query 'StackEvents[?ResourceStatus==\`CREATE_FAILED\`||ResourceStatus==\`UPDATE_FAILED\`].[LogicalResourceId,ResourceStatusReason]' --output table"
  exit 1
fi

# ---- Print outputs -----------------------------------------------------------
echo ""
echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
echo ""

APP_URL=$(aws cloudformation describe-stacks $AWS_OPTS \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='ApplicationURL'].OutputValue" \
  --output text)

echo "Application URL: $APP_URL"
echo ""
echo "All stack outputs:"
aws cloudformation describe-stacks $AWS_OPTS \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" \
  --output table
