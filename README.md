# Pipecat Cloud Starter Project

[![Docs](https://img.shields.io/badge/Documentation-blue)](https://docs.pipecat.daily.co) [![Discord](https://img.shields.io/discord/1217145424381743145)](https://discord.gg/dailyco)

A template voice agent for [Pipecat Cloud](https://www.daily.co/products/pipecat-cloud/) that demonstrates building and deploying a conversational AI agent.

## Prerequisites

- Python 3.10+
- Linux, MacOS, or Windows Subsystem for Linux (WSL)
- [Docker](https://www.docker.com) and a Docker repository (e.g., [Docker Hub](https://hub.docker.com))
- A Docker Hub account (or other container registry account)
- [Pipecat Cloud](https://pipecat.daily.co) account

> **Note**: If you haven't installed Docker yet, follow the official installation guides for your platform ([Linux](https://docs.docker.com/engine/install/), [Mac](https://docs.docker.com/desktop/setup/install/mac-install/), [Windows](https://docs.docker.com/desktop/setup/install/windows-install/)). For Docker Hub, [create a free account](https://hub.docker.com/signup) and log in via terminal with `docker login`.

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/pipecat-ai/pipecat-cloud-starter
cd pipecat-cloud-starter
```

### 2. Set up Python environment

We recommend using a virtual environment to manage your Python dependencies.

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

### 5. Configure to run locally (optional)

You can test your agent locally before deploying to Pipecat Cloud:
- `DAILY_API_KEY` value can be found at [https://pipecat.daily.co](https://pipecat.daily.co) Under the `Settings` menu of your agent, in the `Daily` tab.

```bash
# Set environment variables with your API keys
export CARTESIA_API_KEY="your_cartesia_key"
export DAILY_API_KEY="your_daily_key"
export OPENAI_API_KEY="your_openai_key"
LOCAL_RUN=1 python bot.py
```

## Deploy & Run

### 1. Create a secret set for your API keys

```bash
pipecat secrets set my-first-agent-secrets \
  CARTESIA_API_KEY=your_cartesia_key \
  OPENAI_API_KEY=your_openai_key
```

### 2. Build and push your Docker image

```bash
# Build the image (targeting ARM architecture for cloud deployment)
docker build --platform=linux/arm64 -t my-first-agent:latest .

# Tag with your Docker username and version
docker tag my-first-agent:latest your-username/my-first-agent:0.1

# Push to Docker Hub
docker push your-username/my-first-agent:0.1
```

### 3. Deploy to Pipecat Cloud

```bash
pipecat deploy my-first-agent your-username/my-first-agent:0.1
```

> **Note (Optional)**: For a more maintainable approach, you can use the included `pcc-deploy.toml` file:
>
> ```toml
> agent_name = "my-first-agent"
> image = "your-username/my-first-agent:0.1"
> secret_set = "my-first-agent-secrets"
>
> [scaling]
>     min_instances = 0
> ```
>
> Then simply run `pipecat deploy` without additional arguments.

> **Note**: If your repository is private, you'll need to add credentials:
>
> ```bash
> # Create pull secret (you'll be prompted for credentials)
> pipecat secrets image-pull-secret pull-secret https://index.docker.io/v1/
>
> # Deploy with credentials
> pipecat deploy my-first-agent your-username/my-first-agent:0.1 --credentials pull-secret
> ```

### 4. Create an API key

```bash
# Create a public API key for accessing your agent
pipecat organizations keys create

# Set it as the default key to use with your agent
pipecat organizations keys use
```

### 5. Start your agent

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
