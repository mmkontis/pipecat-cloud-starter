#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os
from typing import List
from typing import List, TypedDict
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
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments
from pipecat_flows import FlowManager, FlowConfig, FlowArgs, FlowResult
from pipecat_flows import (
    ContextStrategy,
    ContextStrategyConfig,
    FlowArgs,
    FlowConfig,
    FlowManager,
    FlowResult,
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


# Type definitions
class Prescription(TypedDict):
    medication: str
    dosage: str


class Allergy(TypedDict):
    name: str


class Condition(TypedDict):
    name: str


class VisitReason(TypedDict):
    name: str


# Result types for each handler
class BirthdayVerificationResult(FlowResult):
    verified: bool


class PrescriptionRecordResult(FlowResult):
    count: int


class AllergyRecordResult(FlowResult):
    count: int


class ConditionRecordResult(FlowResult):
    count: int


class VisitReasonRecordResult(FlowResult):
    count: int



# Function handlers
async def verify_birthday(args: FlowArgs) -> BirthdayVerificationResult:
    """Handler for birthday verification."""
    birthday = args["birthday"]
    # In a real app, this would verify against patient records
    is_valid = birthday == "1983-01-01"
    return BirthdayVerificationResult(verified=is_valid)


async def record_prescriptions(args: FlowArgs) -> PrescriptionRecordResult:
    """Handler for recording prescriptions."""
    prescriptions: List[Prescription] = args["prescriptions"]
    # In a real app, this would store in patient records
    return PrescriptionRecordResult(count=len(prescriptions))


async def record_allergies(args: FlowArgs) -> AllergyRecordResult:
    """Handler for recording allergies."""
    allergies: List[Allergy] = args["allergies"]
    # In a real app, this would store in patient records
    return AllergyRecordResult(count=len(allergies))


async def record_conditions(args: FlowArgs) -> ConditionRecordResult:
    """Handler for recording medical conditions."""
    conditions: List[Condition] = args["conditions"]
    # In a real app, this would store in patient records
    return ConditionRecordResult(count=len(conditions))


async def record_visit_reasons(args: FlowArgs) -> VisitReasonRecordResult:
    """Handler for recording visit reasons."""
    visit_reasons: List[VisitReason] = args["visit_reasons"]
    # In a real app, this would store in patient records
    return VisitReasonRecordResult(count=len(visit_reasons))


flow_config: FlowConfig = {
    "initial_node": "start",
    "nodes": {
        "start": {
            "role_messages": [
                {
                    "role": "system",
                    "content": " youre name is minas marios, from greece, an agent for Tri-County Health Services. You must ALWAYS use one of the available functions to progress the conversation. Be professional but friendly.",
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": "Start by introducing yourself to Chad Bailey,. then ask for their date of birth, including the year. Once they provide their birthday, use verify_birthday to check it. If verified (1983-01-01), proceed to prescriptions.",
                }
            ],
            "functions": [
                {
                    "function_declarations": [
                        {
                            "name": "verify_birthday",
                            "handler": verify_birthday,
                            "description": "Verify the user has provided their correct birthday. Once confirmed, the next step is to recording the user's prescriptions.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "birthday": {
                                        "type": "string",
                                        "description": "The user's birthdate (convert to YYYY-MM-DD format)",
                                    }
                                },
                                "required": ["birthday"],
                            },
                            "transition_to": "get_prescriptions",
                        }
                    ]
                }
            ],
        },
        "get_prescriptions": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "This step is for collecting prescriptions. Ask them what prescriptions they're taking, including the dosage. After recording prescriptions (or confirming none), proceed to allergies.",
                }
            ],
            "functions": [
                {
                    "function_declarations": [
                        {
                            "name": "record_prescriptions",
                            "handler": record_prescriptions,
                            "description": "Record the user's prescriptions. Once confirmed, the next step is to collect allergy information.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "prescriptions": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "medication": {
                                                    "type": "string",
                                                    "description": "The medication's name",
                                                },
                                                "dosage": {
                                                    "type": "string",
                                                    "description": "The prescription's dosage",
                                                },
                                            },
                                            "required": ["medication", "dosage"],
                                        },
                                    }
                                },
                                "required": ["prescriptions"],
                            },
                            "transition_to": "get_allergies",
                        }
                    ]
                }
            ],
        },
        "get_allergies": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Collect allergy information. Ask about any allergies they have. After recording allergies (or confirming none), proceed to medical conditions.",
                }
            ],
            "functions": [
                {
                    "function_declarations": [
                        {
                            "name": "record_allergies",
                            "handler": record_allergies,
                            "description": "Record the user's allergies. Once confirmed, then next step is to collect medical conditions.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "allergies": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "What the user is allergic to",
                                                },
                                            },
                                            "required": ["name"],
                                        },
                                    }
                                },
                                "required": ["allergies"],
                            },
                            "transition_to": "get_conditions",
                        }
                    ]
                }
            ],
        },
        "get_conditions": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Collect medical condition information. Ask about any medical conditions they have. After recording conditions (or confirming none), proceed to visit reasons.",
                }
            ],
            "functions": [
                {
                    "function_declarations": [
                        {
                            "name": "record_conditions",
                            "handler": record_conditions,
                            "description": "Record the user's medical conditions. Once confirmed, the next step is to collect visit reasons.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "conditions": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "The user's medical condition",
                                                },
                                            },
                                            "required": ["name"],
                                        },
                                    }
                                },
                                "required": ["conditions"],
                            },
                            "transition_to": "get_visit_reasons",
                        }
                    ]
                }
            ],
        },
        "get_visit_reasons": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Collect information about the reason for their visit. Ask what brings them to the doctor today. After recording their reasons, proceed to verification.",
                }
            ],
            "functions": [
                {
                    "function_declarations": [
                        {
                            "name": "record_visit_reasons",
                            "handler": record_visit_reasons,
                            "description": "Record the reasons for their visit. Once confirmed, the next step is to verify all information.",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "visit_reasons": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "The user's reason for visiting",
                                                },
                                            },
                                            "required": ["name"],
                                        },
                                    }
                                },
                                "required": ["visit_reasons"],
                            },
                            "transition_to": "verify",
                        }
                    ]
                }
            ],
        },
        "verify": {
            "task_messages": [
                {
                    "role": "system",
                    "content": """Review all collected information with the patient. Follow these steps:
1. Summarize their prescriptions, allergies, conditions, and visit reasons
2. Ask if everything is correct
3. Use the appropriate function based on their response

Be thorough in reviewing all details and wait for explicit confirmation.""",
                }
            ],
            "context_strategy": ContextStrategyConfig(
                strategy=ContextStrategy.APPEND,
                # RESET_WITH_SUMMARY,
                # summary_prompt=(
                #     "Summarize the patient intake conversation, including their birthday, "
                #     "prescriptions, allergies, medical conditions, and reasons for visiting. "
                #     "Focus on the specific medical information provided."
                # ),
            ),
            "functions": [
                {
                    "function_declarations": [
                        {
                            "name": "revise_information",
                            "description": "Return to prescriptions to revise information",
                            "parameters": None,  # Specify None for no parameters
                            "transition_to": "get_prescriptions",
                        },
                        {
                            "name": "confirm_information",
                            "description": "Proceed with confirmed information",
                            "parameters": None,  # Specify None for no parameters
                            "transition_to": "confirm",
                        },
                    ]
                }
            ],
        },
        "confirm": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Once confirmed, thank them, then use the complete_intake function to end the conversation.",
                }
            ],
            "functions": [
                {
                    "function_declarations": [
                        {
                            "name": "complete_intake",
                            "description": "Complete the intake process",
                            "parameters": None,  # Specify None for no parameters
                            "transition_to": "end",
                        }
                    ]
                }
            ],
        },
        "end": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Thank them for their time and end the conversation.",
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}],
        },
    },
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
        voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice - professional, authoritative male voice
        model_id="eleven_monolingual_v1",
        optimize_streaming_latency=2,  # Reduce latency
        stability=0.7,  # Increase stability for more consistent delivery
        similarity_boost=0.7,  # Balanced voice clarity
        style=0.3,  # More businesslike speaking style
        use_speaker_boost=True  # Enhance voice clarity
    )

    # Initialize Google LLM Service
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if not google_api_key:
        # Fallback to a default key or raise an error if preferred
        google_api_key = "AIzaSyCNdv-mYxjvOiSgZta_nGiijQ5IdHDy8iw" # Example fallback
        logger.warning("GOOGLE_API_KEY environment variable not set. Using fallback key.")
        # Alternatively: raise ValueError("GOOGLE_API_KEY environment variable not set.")

    logger.info("Using Google LLM Service")
    llm = GoogleLLMService(
        api_key=google_api_key,
        model="gemini-1.5-flash-latest" # Or configure model via env var if needed
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
