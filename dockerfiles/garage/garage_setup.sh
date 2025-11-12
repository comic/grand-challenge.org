#!/usr/bin/env bash

set -euo pipefail

GARAGE_CONTAINER_NAME="grand-challengeorg-garage.localhost-1"
GARAGE_MAIN_KEY_NAME="grand-challenge-development-key"
GARAGE_COMPONENTS_KEY_NAME="grand-challenge-components-key"
GARAGE_WEBSITE_BUCKET_NAME="garage"

DOCKER_EXEC="docker exec -i"

get_node_id() {
  local output node_id
  output=$($DOCKER_EXEC "${GARAGE_CONTAINER_NAME}" /garage node id -q)
  # strip trailing newline and take part before '@'
  node_id="${output%%@*}"
  printf '%s' "$node_id"
}

setup_layout() {
  local node_id
  node_id=$(get_node_id)

  $DOCKER_EXEC "${GARAGE_CONTAINER_NAME}" /garage layout assign -z dc1 -c 1G "$node_id"
  $DOCKER_EXEC "${GARAGE_CONTAINER_NAME}" /garage layout apply --version 1
}

create_main_key() {
  $DOCKER_EXEC "${GARAGE_CONTAINER_NAME}" /garage key import --yes -n "${GARAGE_MAIN_KEY_NAME}" \
    GKf64f851b810c99aac5d4c6b6 \
    3f908b5fc4b17f5d41112ff6888d99e195dd380594d810c0b3b17016bf25eba9
}

create_buckets() {
  local buckets=( \
    "grand-challenge-private" \
    "grand-challenge-protected" \
    "${GARAGE_WEBSITE_BUCKET_NAME}" \
    "grand-challenge-uploads" \
    "grand-challenge-components-inputs" \
    "grand-challenge-components-outputs" \
  )

  for bucket in "${buckets[@]}"; do
    $DOCKER_EXEC "${GARAGE_CONTAINER_NAME}" /garage bucket create "${bucket}"
    $DOCKER_EXEC "${GARAGE_CONTAINER_NAME}" /garage bucket allow \
      --read --write --owner "${bucket}" --key "${GARAGE_MAIN_KEY_NAME}"
  done
}

allow_public_access() {
  $DOCKER_EXEC "${GARAGE_CONTAINER_NAME}" /garage bucket website --allow "${GARAGE_WEBSITE_BUCKET_NAME}"
}

main() {
  setup_layout
  create_main_key
  create_buckets
  allow_public_access
}

main "$@"
