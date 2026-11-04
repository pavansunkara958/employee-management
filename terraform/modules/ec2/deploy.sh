#!/bin/bash
# Usage: /opt/app/deploy.sh <image-tag>
set -euo pipefail
TAG="${1:?usage: deploy.sh <image-tag>}"
source /opt/app/config.env
IMAGE="$ECR_REPO:$TAG"
CONTAINER=employee-app

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${ECR_REPO%%/*}" >/dev/null
docker pull "$IMAGE"

# Fetch DB credentials from Secrets Manager. Never echoed, never on the command line.
SECRET_JSON=$(aws secretsmanager get-secret-value --region "$AWS_REGION" \
  --secret-id "$DB_SECRET_ARN" --query SecretString --output text)
export DB_USER DB_PASSWORD DB_HOST DB_NAME
DB_USER=$(jq -r .username <<<"$SECRET_JSON")
DB_PASSWORD=$(jq -r .password <<<"$SECRET_JSON")
unset SECRET_JSON

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" --restart unless-stopped -p 8080:8080 \
  -e DB_HOST -e DB_PORT=5432 -e DB_NAME -e DB_USER -e DB_PASSWORD \
  --memory 700m \
  --log-driver awslogs \
  --log-opt awslogs-region="$AWS_REGION" \
  --log-opt awslogs-group="$LOG_GROUP" \
  --log-opt awslogs-stream="$CONTAINER-$TAG" \
  "$IMAGE" >/dev/null

for i in $(seq 1 36); do # up to 3 minutes
  if curl -fs http://localhost:8080/actuator/health | grep -q '"status":"UP"'; then
    echo "Deployed $IMAGE — healthy"
    docker image prune -af >/dev/null || true
    exit 0
  fi
  sleep 5
done
echo "Health check failed for $IMAGE" >&2
docker logs --tail 50 "$CONTAINER" >&2 || true
exit 1
