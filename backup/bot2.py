#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
import json
from deepgram import LiveOptions

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
from pipecat.services.google import GoogleLLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
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
        "Greek Bot",  # Changed name to indicate Greek language
        DailyParams(
            audio_out_enabled=True,
            transcription_enabled=False,  # Disable transcription in transport
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
            vad_audio_passthrough=True,  # Pass audio through to STT service
            start_cloud_recording=True,  # Belt and suspenders approach
        ),
    )

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id=os.getenv("ELEVENLABS_MINAS_VOICE_ID"),  # Get voice ID from env var or use default
        model_id="eleven_flash_v2_5",  # Changed to multilingual model for Greek support
        optimize_streaming_latency="2",  # String format for latency setting
        stability=0.7,  # Increase stability for more consistent delivery
        similarity_boost=0.7,  # Balanced voice clarity
        style=0.3,  # More businesslike speaking style
        use_speaker_boost=True  # Enhance voice clarity
    )

    # Add STT service for Greek language
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        live_options=LiveOptions(
            language="el",  # Greek language code
            model="nova-2-general",
        )
    )

    # Use Google Gemini LLM Service
    llm = GoogleLLMService(
        api_key="AIzaSyCNdv-mYxjvOiSgZta_nGiijQ5IdHDy8iw",  # Use the provided Google API key
        model="gemini-1.5-flash-latest",  # Or another suitable Gemini model
        temperature=0.7,  # Optional: Adjust parameters as needed
        max_tokens=1024,
        top_p=0.9,
    )

    context = OpenAILLMContext(messages=[
        {
            "role": "system",
            "content": "Είσαι ένα φιλικό και εξυπηρετικό ρομπότ για την εταιρεία AI Greece. Ο στόχος σου είναι να επιδείξεις τις δυνατότητές σου με σύντομο τρόπο. Η έξοδός σου θα μετατραπεί σε ήχο, οπότε μην συμπεριλαμβάνεις ειδικούς χαρακτήρες στις απαντήσεις σου. Απάντησε σε αυτό που είπε ο χρήστης με δημιουργικό και χρήσιμο τρόπο, αλλά κράτησε τις απαντήσεις σου σύντομες. ΠΟΛΥ ΣΗΜΑΝΤΙΚΟ: Απαντάς ΠΑΝΤΑ στα Ελληνικά. Ξεκίνα με το να συστηθείς."
        }
    ])
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            stt,  # STT service processes audio first
            context_aggregator.user(), # Then context aggregator gets text
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

    @transport.event_handler("on_recording_started")
    async def on_recording_started(transport, recording_info):
        recording_id = recording_info.get("recordingId")
        if recording_id:
            logger.info(f"Cloud recording started with ID: {recording_id}")
        else:
            logger.warning("Recording started event received, but no recording ID found.")

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
