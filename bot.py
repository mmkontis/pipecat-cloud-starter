#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os

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

# Define flow configuration
flow_config: FlowConfig = {
    "initial_node": "greeting",
    "nodes": {
        "greeting": {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are a friendly hotel room service assistant. Keep responses professional yet warm."
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": "Welcome the guest and ask for their name."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_name",
                        "description": "Collect guest's name",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"}
                            },
                            "required": ["name"]
                        },
                        "transition_to": "confirm_name"
                    }
                }
            ]
        },
        "confirm_name": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Confirm the guest's name and ask for their room number."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_room",
                        "description": "Collect guest's room number",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "room_number": {"type": "string"}
                            },
                            "required": ["room_number"]
                        },
                        "transition_to": "confirm_room"
                    }
                }
            ]
        },
        "confirm_room": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Confirm the room number and ask for their food order."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_order",
                        "description": "Collect guest's food order",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "order": {"type": "string"}
                            },
                            "required": ["order"]
                        },
                        "transition_to": "confirm_order"
                    }
                }
            ]
        },
        "confirm_order": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Confirm the complete order and ask if they need anything else."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "end_conversation",
                        "description": "End the conversation",
                        "parameters": {"type": "object", "properties": {}},
                        "transition_to": "end"
                    }
                }
            ]
        },
        "end": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Thank the guest and provide the estimated delivery time."
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}]
        }
    }
}

async def main(room_url: str, token: str):
    """Main pipeline setup and execution function.

    Args:
        room_url: The Daily room URL
        token: The Daily room token
    """
    logger.debug("Starting bot in room: {}", room_url)

    transport = DailyTransport(
        room_url,
        token,
        "bot",
        DailyParams(
            audio_out_enabled=True,
            transcription_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel voice - natural, friendly female voice
        model_id="eleven_monolingual_v1",
        optimize_streaming_latency=2,  # Reduce latency
        stability=0.5,  # Balance between stability and variability
        similarity_boost=0.75,  # Higher voice clarity and similarity
        style=0.5,  # Balanced speaking style
        use_speaker_boost=True  # Enhance voice clarity
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        temperature=0.95,
        max_tokens=2048,
        top_p=0.95,
        frequency_penalty=0.5,
        presence_penalty=0.5,
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
