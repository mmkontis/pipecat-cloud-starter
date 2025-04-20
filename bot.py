#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import json

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments
from pipecat_flows import FlowManager, FlowConfig, FlowArgs, FlowResult
from pipecat.transports.services.helpers.daily_rest import (
    DailyMeetingTokenParams,
    DailyMeetingTokenProperties,
    DailyRESTHelper,
    DailyRoomProperties,
)

# Check if we're in local development mode
LOCAL_RUN = os.getenv("LOCAL_RUN")
if LOCAL_RUN:
    import asyncio
    import webbrowser

    try:
        from local_runner import configure
    except ImportError:
        logger.error("Could not import local_runner module. Local development mode may not work.")

# Load environment variables
load_dotenv(override=True)

# Load flow configuration from JSON file
try:
    with open("flow_config.json", "r") as f:
        flow_config: FlowConfig = json.load(f)
except FileNotFoundError:
    logger.error("flow_config.json not found. Please ensure the file exists.")
    # Provide a default empty config or raise an error to prevent running without a flow
    flow_config: FlowConfig = {"initial_node": None, "nodes": {}}
except json.JSONDecodeError as e:
    logger.error(f"Error decoding flow_config.json: {e}")
    # Provide a default empty config or raise an error
    flow_config: FlowConfig = {"initial_node": None, "nodes": {}}

async def main(room_url: str, token: str):
    """Main pipeline setup and execution function.

    Args:
        room_url: The Daily room URL
        token: The Daily room token (will be replaced with owner token)
    """
    logger.debug("Starting bot in room: {}", room_url)

    # First update the room configuration to enable cloud recording
    # This should persist even if our token approach doesn't work
    async with aiohttp.ClientSession() as session:
        try:
            # Initialize REST helper with the API key
            daily_rest_helper = DailyRESTHelper(
                daily_api_key=os.getenv("DAILY_API_KEY"),
                daily_api_url=os.getenv("DAILY_API_URL", "https://api.daily.co/v1"),
                aiohttp_session=session,
            )
            
            # Get the room name from the URL
            room_name = daily_rest_helper.get_name_from_url(room_url)
            
            # Update the room's properties to enable cloud recording by default
            # Note: This is a PUT request to update existing room
            url = f"https://api.daily.co/v1/rooms/{room_name}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('DAILY_API_KEY')}"
            }
            data = {
                "properties": {
                    "enable_recording": "cloud"
                }
            }
            
            async with session.put(url, headers=headers, json=data) as response:
                resp_json = await response.json()
                if response.status == 200:
                    logger.info(f"Successfully updated room {room_name} to enable cloud recording")
                else:
                    logger.error(f"Failed to update room properties: {resp_json}")
            
            # Now generate a new owner token for maximum permissions
            new_token = await daily_rest_helper.get_token(
                room_url=room_url,
                owner=True,  # This ensures the token has owner privileges
                expiry_time=3600,  # 1 hour
                params=DailyMeetingTokenParams(
                    properties=DailyMeetingTokenProperties(
                        user_name="AI Greece Host",
                        enable_recording="cloud",  # Enable recording in token
                        start_cloud_recording=True,  # Auto-start cloud recording
                        is_owner=True  # Double ensure owner status
                    )
                )
            )
            
            logger.info("Generated new owner token with recording permissions")
            
            # Use the new token instead of the provided one
            token = new_token
            
        except Exception as e:
            logger.error(f"Error setting up room recording: {e}")
            # Continue with original token if there's an error

    # Use this token with the transport
    transport = DailyTransport(
        room_url,
        token,  # Using the owner token we created
        "bot",
        DailyParams(
            audio_out_enabled=True,
            transcription_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            start_cloud_recording=True,  # Belt and suspenders approach
        ),
    )

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice - professional, authoritative male voice
        model_id="eleven_monolingual_v1",
        optimize_streaming_latency=2,  # Reduce latency
        stability=0.7,  # Increase stability for more consistent delivery
        similarity_boost=0.7,  # Balanced voice clarity
        style=0.3,  # More businesslike speaking style
        use_speaker_boost=True  # Enhance voice clarity
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        temperature=0.7,  # Lower temperature for more focused responses
        max_tokens=1024,  # Shorter responses
        top_p=0.9,
        frequency_penalty=0.3,  # Reduce repetition
        presence_penalty=0.6,  # Encourage more direct questions
    )

    context = OpenAILLMContext()
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            report_only_initial_ttfb=True,
        ),
    )

    # Initialize flow manager
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        tts=tts,
        flow_config=flow_config,
    )

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info("First participant joined: {}", participant["id"])
        await transport.capture_participant_transcription(participant["id"])
        await flow_manager.initialize()

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info("Participant left: {}", participant)
        await task.cancel()

    runner = PipelineRunner()

    await runner.run(task)


async def bot(args: DailySessionArguments):
    """Main bot entry point compatible with the FastAPI route handler.

    Args:
        room_url: The Daily room URL
        token: The Daily room token
        body: The configuration object from the request body
        session_id: The session ID for logging
    """
    logger.info(f"Bot process initialized {args.room_url} {args.token}")

    try:
        await main(args.room_url, args.token)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
        raise


# Local development functions
async def local_main():
    """Function for local development testing."""
    try:
        async with aiohttp.ClientSession() as session:
            (room_url, token) = await configure(session)
            logger.warning("_")
            logger.warning("_")
            logger.warning(f"Talk to your voice agent here: {room_url}")
            logger.warning("_")
            logger.warning("_")
            webbrowser.open(room_url)
            await main(room_url, token)
    except Exception as e:
        logger.exception(f"Error in local development mode: {e}")


# Local development entry point
if LOCAL_RUN and __name__ == "__main__":
    try:
        asyncio.run(local_main())
    except Exception as e:
        logger.exception(f"Failed to run in local mode: {e}")
