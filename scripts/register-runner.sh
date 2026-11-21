#!/usr/bin/env bash
# S0: register a lab host as a self-hosted GitHub Actions runner.
# Usage: scripts/register-runner.sh [role]   (default: app)
# Runner label: lab-<role> (contracts/runtime.yaml)
set -euo pipefail
export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1 AWS_PAGER=""

role="${1:-app}"
label="lab-${role}"
root="$(cd "$(dirname "$0")/.." && pwd)"
runner_version="2.329.0"

echo "== Registering self-hosted runner for role: $role ($label)"

instance_id=$(terraform -chdir="$root/infra/live" output -raw "${role}_instance_id" 2>/dev/null || true)
if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
  instance_id=$(aws ec2 describe-instances \
    --filters "Name=tag:role,Values=$role" "Name=tag:project,Values=mlops-lab" "Name=instance-state-name,Values=running" \
    --query "Reservations[0].Instances[0].InstanceId" --output text 2>/dev/null || true)
fi

if [[ -z "$instance_id" || "$instance_id" == "None" ]]; then
  echo "Error: could not find a running EC2 instance for role '$role'" >&2
  exit 1
fi

repo=$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null) || {
  echo "Error: gh repo view failed. Ensure 'gh auth status' is valid." >&2
  exit 1
}

echo "Target instance: $instance_id in $repo"

token=$(gh api --method POST -H "Accept: application/vnd.github+json" \
  "repos/$repo/actions/runners/registration-token" --jq .token 2>/dev/null) || {
  echo "Error: failed to generate GitHub Actions registration token." >&2
  exit 1
}

# Wait for host bootstrap script to finish
echo "Waiting for instance to complete cloud-init / lab-setup..."
for _ in $(seq 1 60); do
  status=$(aws ec2 describe-instance-status --instance-ids "$instance_id" \
    --query "InstanceStatuses[0].InstanceStatus.Status" --output text 2>/dev/null || true)
  if [[ "$status" == "ok" ]]; then
    break
  fi
  sleep 5
done

# Execute SSM registration script on instance without echoing the token
echo "Sending registration command to $instance_id via SSM..."
ssm_params=$(mktemp)
trap 'rm -f "$ssm_params"' EXIT
chmod 600 "$ssm_params"

cat >"$ssm_params" <<EOF
{
  "commands": [
    "set -euo pipefail",
    "while [ ! -f /var/lib/lab-setup-done ]; do sleep 2; done",
    "cd /opt/actions-runner",
    "if [ ! -f .version ] || [ \"\$(cat .version 2>/dev/null)\" != \"${runner_version}\" ]; then curl -fsSL -o runner.tar.gz https://github.com/actions/runner/releases/download/v${runner_version}/actions-runner-linux-arm64-${runner_version}.tar.gz && tar xzf runner.tar.gz && echo ${runner_version} > .version && rm -f runner.tar.gz; fi",
    "sudo ./svc.sh stop 2>/dev/null || true",
    "sudo ./svc.sh uninstall 2>/dev/null || true",
    "sudo -u runner ./config.sh --url https://github.com/$repo --token $token --name $label --labels $label --unattended --replace",
    "sudo ./svc.sh install runner",
    "sudo ./svc.sh start"
  ]
}
EOF

cmd_id=$(aws ssm send-command \
  --instance-ids "$instance_id" \
  --document-name "AWS-RunShellScript" \
  --comment "Register runner $label" \
  --parameters "file://$ssm_params" \
  --query "Command.CommandId" --output text)

echo "SSM command sent ($cmd_id). Waiting for completion..."
aws ssm wait command-executed --command-id "$cmd_id" --instance-id "$instance_id"

status=$(aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$instance_id" \
  --query "Status" --output text)

if [[ "$status" == "Success" ]]; then
  echo "Runner registration succeeded on $instance_id."
else
  echo "Runner registration status: $status" >&2
  aws ssm get-command-invocation --command-id "$cmd_id" --instance-id "$instance_id" \
    --query "StandardErrorContent" --output text >&2
  exit 1
fi
