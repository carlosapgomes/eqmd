# Docker Compose Command Reference

This guide summarizes the recommended compose commands for each common use case.

## Development (full stack)

Start the dev app and database only:

```bash
docker compose -f docker-compose.yml up -d eqmd-dev postgres
```

Note: `eqmd` (production) has a `prod` profile and will not start unless you
pass `--profile prod`. The coding agent runs from `docker-compose.agent.yml`.

Stop and remove containers:

```bash
docker compose -f docker-compose.yml down
```

## Development (hardened services)

Apply the hardening overlay on top of the dev stack:

```bash
docker compose -f docker-compose.yml -f docker-compose.hardened.yml up -d
```

## Coding Agent (separate compose + shared network)

Start the dev stack first so the `eqmd_net` network exists:

```bash
docker compose -f docker-compose.yml up -d eqmd-dev postgres
```

Then start the agent stack:

```bash
export DOCKER_SOCKET_PATH=/run/user/1000/docker.sock
docker compose -f docker-compose.agent.yml up -d
```

Stop the agent stack:

```bash
docker compose -f docker-compose.agent.yml down
```

## Deployment (production stack)

Start production services:

```bash
docker compose -f docker-compose.deploy.yml up -d
```

Run the static file initialization job:

```bash
docker compose -f docker-compose.deploy.yml --profile init run --rm static-init
```

Stop production services:

```bash
docker compose -f docker-compose.deploy.yml down
```

## Matrix services

Matrix services start by default in the deployment compose file. If you are not
using Matrix yet, comment out or remove the `matrix-synapse` and `element-web`
services in `docker-compose.deploy.yml` before deploying.

## Install/upgrade scripts

`install.sh` and `upgrade.sh` use the default compose file by default.
If you want them to use `docker-compose.deploy.yml`, run them with:

```bash
COMPOSE_FILE=docker-compose.deploy.yml sudo ./install.sh
COMPOSE_FILE=docker-compose.deploy.yml sudo ./upgrade.sh
```
