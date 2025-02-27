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

## Deploy and run

#### 1. export your variables for convenience
- not technically necessary, but makes for easy copy-pasta below
```bash
# docker related variables
export MY_DOCKER_REPOSITORY="<my-docker-repo>"
export MY_DOCKER_USERNAME="${MY_DOCKER_REPOSITORY}"
export MY_IMAGE_CREDENTIALS="${MY_DOCKER_REPOSITORY}"
export IMAGE_VERSION="0.1"

# custom strings (can be whatever you like)
export MY_AGENT_NAME="my-first-agent"
export MY_PULL_SECRET="my-first-pull-secret"
export MY_SECRET_SET="my-first-agent-secret-set"
export MY_ORG_KEY="my-first-organization-key"

# API keys for the services your agent uses
export CARTESIA_API_KEY="<MY_CARTESIA_API_KEY>"
export DAILY_API_KEY="<MY_DAILY_API_KEY>"
export OPENAI_API_KEY="<MY_OPENAI_API_KEY>"
```

#### 2. setup secrets
- `CARTESIA_API_KEY` can be found at [https://play.cartesia.ai/keys](https://play.cartesia.ai/keys)
- `DAILY_API_KEY` can be found at [https://pipecat.daily.co](https://pipecat.daily.co) > Settings > Daily
- `OPENAI_API_KEY` can be found at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)

```bash
# set voice agent app secrets
pipecat secrets set "${MY_SECRET_SET}" \
CARTESIA_API_KEY="${CARTESIA_API_KEY}" \
DAILY_API_KEY="${DAILY_API_KEY}" \
OPENAI_API_KEY="${OPENAI_API_KEY}"
```

```bash
# set docker image pull secret
pipecat secrets image-pull-secret "${MY_PULL_SECRET}" https://index.docker.io/v1/
```
then pass in your docker username and password.

> for example:
> ```bash
> $ pipecat secrets image-pull-secret my-pull-secret https://index.docker.io/v1/
> ? Username for image repository 'https://index.docker.io/v1/' ${MY_DOCKER_USERNAME}
> ? Password for image repository 'https://index.docker.io/v1/' *********************
> ```

- check secrets
> secret values will not be shown
```bash
pipecat secrets list
```

#### double-secret-step [optional] 3. run locally

- check config
```bash
pipecat --config
```

- check that things are working as expected
```bash
export CARTESIA_API_KEY="${CARTESIA_API_KEY}"
export DAILY_API_KEY="${DAILY_API_KEY}"
export OPENAI_API_KEY="${OPENAI_API_KEY}"
LOCAL_RUN=1 python bot.py
```

#### regular step 3. push to docker
> ensure Docker is running.
```bash
docker build --platform linux/arm64 -t "${MY_AGENT_NAME}" .
docker tag "${MY_AGENT_NAME}":latest "${MY_DOCKER_REPOSITORY}"/"${MY_AGENT_NAME}":"${IMAGE_VERSION}"
docker push "${MY_DOCKER_REPOSITORY}"/"${MY_AGENT_NAME}":"${IMAGE_VERSION}"
```

#### 4. deploy
```bash
pipecat deploy "${MY_AGENT_NAME}" \
"${MY_DOCKER_REPOSITORY}"/"${MY_AGENT_NAME}":"${IMAGE_VERSION}" \
--credentials "${MY_PULL_SECRET}"
```

- for example:
```bash
$ pipecat deploy my-first-agent \
dockerhub_name/my-first-agent:0.1 \
--credentials my-pull-secret
```

#### 5. Prepare to run your agent
```bash
pipecat agent logs "${MY_AGENT_NAME}"
pipecat agent status "${MY_AGENT_NAME}"

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

> this is borked in pipecatcloud 0.0.8, so go to dashboard to start and talk to agent
```bash
pipecat agent start "${MY_AGENT_NAME}"
```

check on your voice agent
```bash
pipecat agent status "${MY_AGENT_NAME}"
pipecat agent logs "${MY_AGENT_NAME}"
```

> if you make changes to the bot.py file, repeat steps 5 & 6. to update the deployed bot.
