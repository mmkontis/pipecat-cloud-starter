# Pipecat Cloud Starter Project

[![PyPI](https://img.shields.io/pypi/v/pipecatcloud)](https://pypi.org/project/pipecatcloud) [![Docs](https://img.shields.io/badge/Documentation-blue)](https://docs.pipecat.daily.co) [![Discord](https://img.shields.io/discord/1217145424381743145)](https://discord.gg/dailyco)

A template voice agent for [Pipecat Cloud](https://www.daily.co/products/pipecat-cloud/) that demonstrates building and deploying a conversational AI agent.

## Prerequisites

- Python 3.10+
- [Docker](https://www.docker.com) and a Docker repository (e.g., [DockerHub](https://hub.docker.com))
- Linux, MacOS, or Windows Subsystem for Linux (WSL)
- [Pipecat Cloud](https://pipecat.daily.co) account

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/pipecat-ai/pipecat-cloud-starter
cd pipecat-cloud-starter
```

### 2. Set up Python environment

```bash
# Create a virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install pipecatcloud
```

### 3. Authenticate with Pipecat Cloud

```bash
pipecat auth login
```

### 4. Acquire required API keys

This starter requires the following API keys:

- **OpenAI API Key**: Get from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **Cartesia API Key**: Get from [play.cartesia.ai/keys](https://play.cartesia.ai/keys)
- **Daily API Key**: Automatically provided through your Pipecat Cloud account

### 5. Run locally (optional)

You can test your agent locally before deploying to Pipecat Cloud:

```bash
# Set environment variables with your API keys
export CARTESIA_API_KEY="your_cartesia_key"
export OPENAI_API_KEY="your_openai_key"
LOCAL_RUN=1 python bot.py
```

## Deploy & Run

### 1. Create a secret set for your API keys

```bash
pipecat secrets set my-first-secret-set \
  CARTESIA_API_KEY=your_cartesia_key \
  OPENAI_API_KEY=your_openai_key
```

### 2. Update deployment configuration

Edit the `pcc-deploy.toml` file to use your secret set:

```toml
agent_name = "my-first-agent"
image = "your-username/my-first-agent:latest"
secret_set = "my-first-secret-set"

[scaling]
    min_instances = 1
```

> **Important**: The `secret_set` value must match the name you used when creating your secrets.

### 3. Build and push your Docker image

```bash
# Build the image (targeting ARM architecture for cloud deployment)
docker build --platform linux/arm64 -t my-first-agent .

# Tag with your Docker username
docker tag my-first-agent your-username/my-first-agent:latest

# Push to Docker Hub
docker push your-username/my-first-agent:latest
```

### 4. Deploy to Pipecat Cloud

```bash
pipecat deploy my-first-agent your-username/my-first-agent:latest
```

> Note: (Optional) If you're using a private Docker repository, add credentials:
>
> ```bash
> # Create pull secret (do this once)
> pipecat secrets image-pull-secret pull-secret https://index.docker.io/v1/
>
> # Deploy with credentials
> pipecat deploy my-first-agent your-username/my-first-agent:latest --credentials pull-secret
> ```

### 5. Create an API key

```bash
# Create a public API key for accessing your agent
pipecat organizations keys create

# Set it as the default key to use with your agent
pipecat organizations keys use
```

### 6. Start your agent

```bash
# Start a session with your agent in a Daily room
pipecat agent start my-first-agent --use-daily
```

This will return a URL, which you can use to connect to your running agent.

## Documentation

For more details on Pipecat Cloud and its capabilities:

- [Pipecat Cloud Documentation](https://docs.pipecat.daily.co)
- [Pipecat Project Documentation](https://docs.pipecat.ai)

## Support

Join our [Discord community](https://discord.gg/dailyco) for help and discussions.
