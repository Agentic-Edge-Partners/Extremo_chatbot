#!/bin/bash
# ============================================================
# EC2 First-Time Setup Script
# Run this ONCE on a fresh Ubuntu 24.04 EC2 instance (t3.small+)
#
# Usage:
#   ssh -i your-key.pem ubuntu@<EC2_IP> 'bash -s' < scripts/ec2-setup.sh
# ============================================================
set -euo pipefail

echo "==> Installing Docker..."
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
sudo usermod -aG docker ubuntu

echo ""
echo "============================================================"
echo "  Docker installed! Now complete these steps manually:"
echo "============================================================"
echo ""
echo "1. Log out and back in (for docker group to take effect):"
echo "   exit"
echo "   ssh -i your-key.pem ubuntu@<EC2_IP>"
echo ""
echo "2. Clone your repo:"
echo "   git clone https://github.com/<YOUR_USER>/Agent-PDAI-A2.git ~/app"
echo ""
echo "3. Create the .env file:"
echo "   cat > ~/app/.env << 'EOF'"
echo "   OPENAI_API_KEY=sk-..."
echo "   GOOGLE_MAPS_API_KEY=..."
echo "   LANGCHAIN_TRACING_V2=true"
echo "   LANGCHAIN_PROJECT=extremoambiente-a2"
echo "   LANGSMITH_API_KEY=lsv2_..."
echo "   EOF"
echo ""
echo "4. Set the public URL and start:"
echo "   cd ~/app"
echo "   export NEXT_PUBLIC_API_URL=http://<EC2_PUBLIC_IP>:8123"
echo "   docker compose up -d --build"
echo ""
echo "5. Open in browser:"
echo "   Frontend: http://<EC2_PUBLIC_IP>:3000"
echo "   Backend API: http://<EC2_PUBLIC_IP>:8123"
echo ""
