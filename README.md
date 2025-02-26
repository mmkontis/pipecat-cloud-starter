# Pipecat Cloud Starter Project

Template agent for [Pipecat Cloud](https://www.daily.co/products/pipecat-cloud/)

[Documentation](https://docs.pipecat.daily.co/)

## Dependencies

- Python 3.10+
- Docker and a Docker repository (e.g. DockerHub )
- Linux or MacOS

## Installation

1. Create a Pipecat Cloud account [here](https://pipecat.daily.co/)

2. clone and setup this repo
```bash
git clone https://github.com/pipecat-ai/pipecat-cloud-starter
```

3. setup python and dependencies
> If you were so excited you skipped step 1, `pipecat auth login` will prompt you to signup

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

pip install pipecatcloud
pipecat auth login
```

5. export your variables for convenience
not technically necessary, but makes copy pasta down the line way easier
```bash
export MY_DOCKER_REPOSITORY="<my-docker-repo>"
export MY_IMAGE_CREDENTIALS="${MY_DOCKER_REPOSITORY}"
export MY_DOCKER_USERNAME="${MY_DOCKER_REPOSITORY}"
export MY_AGENT_NAME="my-first-agent"
export MY_PULL_SECRET="my-pull-secret"
export MY_SECRET_SET="my-first-agent-secret-set"
export MY_ORG_KEY="my-first-organization-key"
export CARTESIA_API_KEY="<MY_CARTESIA_API_KEY>"
export DAILY_API_KEY="<MY_DAILY_API_KEY>"
export OPENAI_API_KEY="<MY_OPENAI_API_KEY>"
```

4. setup secrets
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
pass in your docker username and password

for example:
```bash
$ pipecat secrets image-pull-secret my-pull-secret https://index.docker.io/v1/
? Username for image repository 'https://index.docker.io/v1/' ${MY_DOCKER_USERNAME}
? Password for image repository 'https://index.docker.io/v1/' *********************
```

- check secrets
> sshhhh. secret values will not be listed
```bash
pipecat secrets list
```

### optional
double-secret-step 5. run locally

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




5. push to docker
> ensure Docker is running.
```bash
docker build --platform linux/arm64 -t "${MY_AGENT_NAME}" .
docker tag "${MY_AGENT_NAME}":latest "${MY_DOCKER_REPOSITORY}"/"${MY_AGENT_NAME}":0.1
docker push "${MY_DOCKER_REPOSITORY}"/"${MY_AGENT_NAME}":0.1
```

6. deploy
```bash
pipecat deploy "${MY_AGENT_NAME}" "${MY_DOCKER_REPOSITORY}"/"${MY_AGENT_NAME}":0.1 --credentials "${MY_PULL_SECRET}"
```



6. talk to your agent
# wip. these are just guesses.
# check for errors
# get daily url from logs ?
```bash
pipecat agent logs "${MY_AGENT_NAME}"
pipecat agent status "${MY_AGENT_NAME}"

pipecat organizations keys create
? Enter human readable name for API key e.g. 'Pipecat Key' 
=> my-first-organization-key

pipecat organizations keys use
pipecat agent start "${MY_AGENT_NAME}"

pipecat agent status "${MY_AGENT_NAME}"
```

if you make changes to the bot.py file, repeat steps 5. & 6. to update the deployed bot.























