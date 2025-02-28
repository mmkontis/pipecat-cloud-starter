# Pipecat Cloud Starter Project

Template "hello world" voice agent for [Pipecat Cloud](https://www.daily.co/products/pipecat-cloud/)

[Documentation](https://docs.pipecat.daily.co/)

## Dependencies

- Python 3.10+
- Docker and a Docker repository (e.g. DockerHub )
- Linux or MacOS

## Install dependencies

1. Create a Pipecat Cloud account [here](https://pipecat.daily.co/)

2. setup repo, python and dependencies
> If you were so excited you skipped step 1, `pipecat auth login` will prompt you to signup

```bash
git clone https://github.com/pipecat-ai/pipecat-cloud-starter

python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

pip install pipecatcloud
pipecat auth login
```

3. acquire third party API keys
- `CARTESIA_API_KEY` can be found at [https://play.cartesia.ai/keys](https://play.cartesia.ai/keys)
- `DAILY_API_KEY` can be found at [https://pipecat.daily.co](https://pipecat.daily.co) > Settings > Daily
- `OPENAI_API_KEY` can be found at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Deploy and run

#### 1. export your variables for convenience
- not technically necessary, but makes for easy copy-pasta below
```bash
# docker related variables
export PCC_DOCKER_REPOSITORY="<my-docker-repo>"
export PCC_DOCKER_USERNAME="${PCC_DOCKER_REPOSITORY}"
export PCC_IMAGE_CREDENTIALS="${PCC_DOCKER_REPOSITORY}"
export PCC_IMAGE_VERSION="0.1"

# custom strings (can be whatever you like)
export PCC_AGENT_NAME="my-first-agent"
export PCC_PULL_SECRET="my-first-pull-secret"
export PCC_SECRET_SET="my-first-secret-set"
export PCC_ORG_KEY="my-first-organization-key"

# API keys for the services your agent uses
export PCC_CARTESIA_API_KEY="<CARTESIA_API_KEY>"
export PCC_DAILY_API_KEY="<DAILY_API_KEY>"
export PCC_OPENAI_API_KEY="<OPENAI_API_KEY>"
```

#### 2. setup secrets
```bash
# set voice agent app secrets
pipecat secrets set "${PCC_SECRET_SET}" \
CARTESIA_API_KEY="${PCC_CARTESIA_API_KEY}" \
DAILY_API_KEY="${PCC_DAILY_API_KEY}" \
OPENAI_API_KEY="${PCC_OPENAI_API_KEY}"
```

```bash
# set docker image pull secret
pipecat secrets image-pull-secret "${PCC_PULL_SECRET}" https://index.docker.io/v1/
```
then pass in your docker username and password.

> for example:
> ```bash
> $ pipecat secrets image-pull-secret my-pull-secret https://index.docker.io/v1/
> ? Username for image repository 'https://index.docker.io/v1/' ${PCC_DOCKER_USERNAME}
> ? Password for image repository 'https://index.docker.io/v1/' *********************
> ```

- check secrets
> secret values will not be shown
```bash
pipecat secrets list
```

> important!
update `secret_set` name in `pcc-deploy.toml`.  It must be a string literal (not an env var)

#### double-secret-step [optional] 3. run locally

- check config
```bash
pipecat --config
```

- check that things are working as expected
```bash
export CARTESIA_API_KEY="${PCC_CARTESIA_API_KEY}"
export DAILY_API_KEY="${PCC_DAILY_API_KEY}"
export OPENAI_API_KEY="${PCC_OPENAI_API_KEY}"
LOCAL_RUN=1 python bot.py
```

#### regular step 3. build and push to docker
> ensure Docker is running. also, this may take a minute aka coffee break opportunity.

```bash
docker build --platform linux/arm64 -t "${PCC_AGENT_NAME}" .
docker tag "${PCC_AGENT_NAME}":latest "${PCC_DOCKER_REPOSITORY}/${PCC_AGENT_NAME}:${IMAGE_VERSION}"
docker push "${PCC_DOCKER_REPOSITORY}/${PCC_AGENT_NAME}:${IMAGE_VERSION}"
```

#### 4. deploy
```bash
pipecat deploy "${PCC_AGENT_NAME}" \
"${PCC_DOCKER_REPOSITORY}/${PCC_AGENT_NAME}:${IMAGE_VERSION}" \
--credentials "${PCC_PULL_SECRET}"
```

- for example:
```bash
$ pipecat deploy my-first-agent \
dockerhub_name/my-first-agent:0.1 \
--credentials my-pull-secret
```

#### 5. Prepare to run your agent
```bash
pipecat agent logs "${PCC_AGENT_NAME}"
pipecat agent status "${PCC_AGENT_NAME}"

pipecat organizations keys create
pipecat organizations keys use
```

- for example:
```bash
pipecat organizations keys create
? Enter human readable name for API key e.g. 'Pipecat Key' 
=> my-first-organization-key
pipecat organizations keys use
```

#### 6. Run your agent

> [TEMPORARY NOTE] this is borked in pipecatcloud 0.0.8, so go to dashboard to start and talk to agent

> `--use-daily` will open a daily room for you to talk to your agent
```bash
pipecat agent start "${PCC_AGENT_NAME}" --use-daily
```

check on your voice agent
```bash
pipecat agent status "${PCC_AGENT_NAME}"
pipecat agent logs "${PCC_AGENT_NAME}"
```

> if you make changes to the bot.py file, repeat steps 5 & 6. to update the deployed bot.
