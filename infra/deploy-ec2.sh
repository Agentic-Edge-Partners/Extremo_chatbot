#!/bin/bash
# =============================================================================
# Extremo Ambiente — Simple EC2 Deployment Script
#
# Deploys a single EC2 instance running Docker Compose (~$22/month).
# The instance auto-installs Docker, clones the repo, and starts all services.
#
# Usage:
#   ./infra/deploy-ec2.sh --region eu-west-1 --key-pair my-key
#
# Prerequisites:
#   - AWS CLI configured with appropriate credentials
#   - An existing EC2 key pair in the target region
#   - .env file with OPENAI_API_KEY, GOOGLE_MAPS_API_KEY
# =============================================================================

set -euo pipefail

# ---- Defaults ---------------------------------------------------------------
REGION="eu-west-1"
STACK_NAME="extremo-ec2"
PROFILE=""
ENV_FILE=".env"
KEY_PAIR=""
INSTANCE_TYPE="t3.small"
GIT_REPO="https://github.com/your-user/Extremo_chatbot.git"
SSH_CIDR="0.0.0.0/0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# ---- Parse arguments --------------------------------------------------------
while [[ $# -gt 0 ]]; do
  case $1 in
    --region)        REGION="$2"; shift 2 ;;
    --stack)         STACK_NAME="$2"; shift 2 ;;
    --profile)       PROFILE="$2"; shift 2 ;;
    --env-file)      ENV_FILE="$2"; shift 2 ;;
    --key-pair)      KEY_PAIR="$2"; shift 2 ;;
    --instance-type) INSTANCE_TYPE="$2"; shift 2 ;;
    --git-repo)      GIT_REPO="$2"; shift 2 ;;
    --ssh-cidr)      SSH_CIDR="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 --key-pair KEY_NAME [options]"
      echo ""
      echo "Required:"
      echo "  --key-pair NAME      EC2 key pair name (must exist in the region)"
      echo ""
      echo "Options:"
      echo "  --region REGION      AWS region (default: eu-west-1)"
      echo "  --stack NAME         CloudFormation stack name (default: extremo-ec2)"
      echo "  --profile NAME       AWS CLI profile"
      echo "  --env-file PATH      Path to .env file (default: .env)"
      echo "  --instance-type TYPE EC2 instance type (default: t3.small)"
      echo "  --git-repo URL       Git repository URL to clone"
      echo "  --ssh-cidr CIDR      CIDR for SSH access (default: 0.0.0.0/0)"
      exit 0 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

# Validate required args
if [[ -z "$KEY_PAIR" ]]; then
  echo "Error: --key-pair is required"
  echo "Run: $0 --help"
  exit 1
fi

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

set -a
source "$PROJECT_DIR/$ENV_FILE"
set +a

for VAR in OPENAI_API_KEY GOOGLE_MAPS_API_KEY; do
  if [[ -z "${!VAR:-}" ]]; then
    echo "Error: $VAR is not set in $ENV_FILE"
    exit 1
  fi
done

# ---- Verify key pair exists --------------------------------------------------
echo "==> Verifying key pair '$KEY_PAIR' exists in $REGION..."
if ! aws ec2 describe-key-pairs $AWS_OPTS --region "$REGION" --key-names "$KEY_PAIR" &>/dev/null; then
  echo "Error: Key pair '$KEY_PAIR' not found in $REGION"
  echo "Create one with: aws ec2 create-key-pair --key-name $KEY_PAIR --query KeyMaterial --output text > $KEY_PAIR.pem"
  exit 1
fi

# ---- Deploy CloudFormation ---------------------------------------------------
echo ""
echo "==> Deploying CloudFormation stack: $STACK_NAME"
echo "    Region:        $REGION"
echo "    Instance type:  $INSTANCE_TYPE"
echo "    Key pair:       $KEY_PAIR"
echo "    Git repo:       $GIT_REPO"
echo ""

aws cloudformation deploy $AWS_OPTS \
  --region "$REGION" \
  --template-file "$SCRIPT_DIR/cloudformation-ec2.yaml" \
  --stack-name "$STACK_NAME" \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    InstanceType="$INSTANCE_TYPE" \
    KeyPairName="$KEY_PAIR" \
    OpenAIApiKey="$OPENAI_API_KEY" \
    GoogleMapsApiKey="$GOOGLE_MAPS_API_KEY" \
    LangSmithApiKey="${LANGSMITH_API_KEY:-}" \
    LangChainProject="${LANGCHAIN_PROJECT:-extremoambiente-a2}" \
    GitRepoURL="$GIT_REPO" \
    AllowedSSHCidr="$SSH_CIDR"

# ---- Wait for stack completion -----------------------------------------------
echo ""
echo "==> Waiting for stack to complete (this takes 3-5 minutes)..."

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
  echo "Check CloudFormation events:"
  echo "  aws cloudformation describe-stack-events $AWS_OPTS --region $REGION --stack-name $STACK_NAME"
  exit 1
fi

# ---- Print outputs -----------------------------------------------------------
echo ""
echo "========================================="
echo "  Deployment Complete!"
echo "========================================="
echo ""

FRONTEND_URL=$(aws cloudformation describe-stacks $AWS_OPTS \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='FrontendURL'].OutputValue" \
  --output text)

PUBLIC_IP=$(aws cloudformation describe-stacks $AWS_OPTS \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='PublicIP'].OutputValue" \
  --output text)

echo "Frontend URL: $FRONTEND_URL"
echo "Public IP:    $PUBLIC_IP"
echo ""
echo "SSH:          ssh -i $KEY_PAIR.pem ubuntu@$PUBLIC_IP"
echo ""
echo "NOTE: The instance is building Docker images on first boot."
echo "      It may take 5-10 minutes before the frontend is accessible."
echo "      Check progress with: ssh -i $KEY_PAIR.pem ubuntu@$PUBLIC_IP 'tail -f /var/log/user-data.log'"
echo ""

aws cloudformation describe-stacks $AWS_OPTS \
  --region "$REGION" \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[].[OutputKey,OutputValue]" \
  --output table
