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

# tbd on this step
```bash
cp example.pcc-deploy.toml pcc-deploy.toml
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

4. setup secrets
```bash
cp example.pcc-deploy.toml pcc-deploy.toml

# set secrets
pipecat secrets set my-first-agent-secret-set \
DAILY_API_KEY="${DAILY_API_KEY}" \
ELEVENLABS_API_KEY="${ELEVENLABS_API_KEY}" \
OPENAI_API_KEY="${OPENAI_API_KEY}"
```

- check secrets
> sshhhh. secret values will not be listed
```bash
pipecat secrets list my-first-agent-secret-set
```

5. run locally
# check that things are working as expected
```bash
export DAILY_API_KEY="${DAILY_API_KEY}"
export ELEVENLABS_API_KEY="${ELEVENLABS_API_KEY}"
export OPENAI_API_KEY="${OPENAI_API_KEY}"
LOCAL_RUN=1 python bot.py 
```


5. export your variables for convenience
```bash
export MY_DOCKER_REPOSITORY="my-docker-repo"
export MY_AGENT_NAME="my-first-agent"
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
pipecat deploy "${MY_AGENT_NAME}" "${MY_DOCKER_REPOSITORY}"/"${MY_AGENT_NAME}":0.1
```

6. talk to your agent
# wip. these are just guesses.
# check for errors
# get daily url from logs ?
pipecat agent logs "${MY_AGENT_NAME}"
pipecat agent status "${MY_AGENT_NAME}"

pipecat organizations keys create
pipecat organizations keys use
pipecat agent start "${MY_AGENT_NAME}"

pipecat agent status "${MY_AGENT_NAME}"
```

# navigate to daily room url to try deployed agent
