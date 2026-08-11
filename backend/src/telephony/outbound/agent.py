import asyncio
import html
import json
import logging
import os
import re
import urllib.request

from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    inference,
    room_io,
    tokenize,
)
from livekit.plugins import google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel


logger = logging.getLogger("bharatmoney-outbound")

load_dotenv(".env.local")

OUTBOUND_TRUNK_ID = os.getenv("LIVEKIT_SIP_OUTBOUND_TRUNK_ID")

CALLEE_IDENTITY = "phone-user"

PMJDY_URL = "https://pmjdy.gov.in/scheme"


SYSTEM_PROMPT = """
You are BharatMoney Voice AI calling a user for the Financial Services
track of VoiceForBharat.

This is an outbound call, so the user did not expect the call.

At the beginning of the call:

1. Clearly say who you are.
2. Clearly explain why you are calling.
3. Tell the user they can end the call at any time.

You are calling to help users understand government financial schemes
and important financial information.

IMPORTANT:
When the user asks about PMJDY, Pradhan Mantri Jan-Dhan Yojana,
Jan Dhan account, PM Jan Dhan, or Jan Dhan benefits:

- ALWAYS use the check_pmjdy_information tool first.
- Use the information returned by the tool.
- Do not say that you cannot provide government scheme information.
- Give a short, simple answer suitable for a phone conversation.
- If the user asks for more details, provide the relevant details
  from the official information returned by the tool.

Keep the conversation short, friendly, respectful, and conversational.

You are an educational assistant.

You are NOT:
- a bank
- a government authority
- a financial advisor
- a loan provider
- a payment service

Never ask for:
- OTP
- UPI PIN
- PIN
- CVV
- password
- full bank account number
- full card number

Never claim to access a bank account.

Never perform banking transactions.

Never guarantee loans, schemes, investments, insurance,
or financial outcomes.

Mirror the caller's language:

English = simple English.
Hindi = natural Hindi.
Hinglish = natural Hinglish.

If the caller wants to end the call, politely say goodbye
and end the call.

If the caller asks for a human, explain that a human callback
can be requested. Do not invent a transfer.

If you reach voicemail or an answering machine, end the call.

Do not use emojis, bullet points, or long explanations
during the phone call.

Keep answers normally to one or two short sentences.
"""


GREETING = (
    "Namaste! Main BharatMoney Voice AI hoon. "
    "Main aapko financial schemes ki important information ke baare mein "
    "remind karne ke liye call kar rahi hoon. "
    "Aap kisi bhi time call end kar sakte hain. "
    "Kya aapke paas ek minute hai?"
)


def fetch_pmjdy_page() -> str:
    """
    Fetch the official PMJDY scheme page.

    This uses Python's standard library so no additional package
    is required.
    """

    request = urllib.request.Request(
        PMJDY_URL,
        headers={
            "User-Agent": "BharatMoney-VoiceAI/1.0",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=10,
    ) as response:

        raw_html = response.read().decode(
            "utf-8",
            errors="ignore",
        )

    # Remove scripts and styles.
    text = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        raw_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Remove HTML tags.
    text = re.sub(
        r"<[^>]+>",
        " ",
        text,
    )

    # Decode HTML entities.
    text = html.unescape(text)

    # Normalize whitespace.
    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    # Keep the response reasonably small for the LLM.
    return text[:12000]


class OutboundAgent(Agent):

    def __init__(self, ctx: JobContext) -> None:

        super().__init__(
            instructions=SYSTEM_PROMPT,
        )

        self.ctx = ctx

    @function_tool
    async def check_pmjdy_information(
        self,
        context: RunContext,
    ) -> str:
        """
        Fetch current PMJDY information from the official
        Government of India PMJDY website.
        """

        logger.info(
            "Fetching official PMJDY information",
            extra={
                "user_id": CALLEE_IDENTITY,
                "source": PMJDY_URL,
                "room": self.ctx.room.name,
            },
        )

        try:

            page_text = await asyncio.to_thread(
                fetch_pmjdy_page
            )

            if not page_text:

                logger.warning(
                    "Official PMJDY page returned empty content"
                )

                return (
                    "The official PMJDY website did not return "
                    "information right now. Please try again."
                )

            logger.info(
                "Official PMJDY information fetched successfully",
                extra={
                    "room": self.ctx.room.name,
                },
            )

            return (
                "Official PMJDY information from the Government "
                "of India website:\n\n"
                + page_text
            )

        except Exception as exc:

            logger.exception(
                "Failed to fetch official PMJDY information"
            )

            return (
                "I could not access the official PMJDY website "
                "right now. Please try again later."
            )

    @function_tool
    async def end_call(
        self,
        context: RunContext,
    ) -> str:
        """End the outbound call when the caller wants to finish."""

        await context.session.generate_reply(
            instructions=(
                "Say a very short and polite goodbye. "
                "Tell the caller they can contact BharatMoney again anytime."
            )
        )

        logger.info(
            "Ending BharatMoney outbound call",
            extra={
                "room": self.ctx.room.name,
            },
        )

        try:

            await self.ctx.api.room.delete_room(
                api.DeleteRoomRequest(
                    room=self.ctx.room.name
                )
            )

        except Exception:

            logger.exception(
                "Failed to delete room"
            )

        return "Call ended."

    @function_tool
    async def detected_answering_machine(
        self,
        context: RunContext,
    ) -> str:
        """End the call if voicemail or an answering machine answers."""

        logger.info(
            "Answering machine detected",
            extra={
                "room": self.ctx.room.name,
            },
        )

        try:

            await self.ctx.api.room.delete_room(
                api.DeleteRoomRequest(
                    room=self.ctx.room.name
                )
            )

        except Exception:

            logger.exception(
                "Failed to delete room"
            )

        return "Call ended."


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


def phone_number_from_metadata(
    ctx: JobContext,
) -> str | None:

    """Read the destination SIP address from dial.py metadata."""

    metadata = ctx.job.metadata

    if not metadata:
        return None

    try:

        data = json.loads(metadata)

        return data.get("phone_number")

    except json.JSONDecodeError:

        return metadata.strip() or None


@server.rtc_session(agent_name="outbound-agent")
async def outbound_agent(
    ctx: JobContext,
):

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    phone_number = phone_number_from_metadata(ctx)

    if not phone_number:

        logger.error(
            "No destination SIP address supplied"
        )

        ctx.shutdown()

        return

    if not OUTBOUND_TRUNK_ID:

        logger.error(
            "LIVEKIT_SIP_OUTBOUND_TRUNK_ID is not set"
        )

        ctx.shutdown()

        return

    logger.info(
        "BharatMoney outbound session starting",
        extra={
            "room": ctx.room.name,
            "destination": phone_number,
        },
    )

    await ctx.connect()

    session = AgentSession(

        # LiveKit Inference + Deepgram STT.
        stt=inference.STT(
            model="deepgram/nova-3-general",
            language="multi",
        ),

        # Gemini.
        llm=google.LLM(
            model="gemini-2.5-flash",
        ),

        # Murf TTS.
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(
                min_sentence_len=1
            ),
            text_pacing=True,
            min_buffer_size=1,
            max_buffer_delay_in_ms=0,
            streaming=True,
        ),

        turn_detection=MultilingualModel(),

        vad=ctx.proc.userdata["vad"],

        preemptive_generation=True,

        min_endpointing_delay=0.3,

        max_endpointing_delay=1.5,

        allow_interruptions=True,
    )

    # Start the AI session while the phone is ringing.
    session_started = asyncio.create_task(
        session.start(
            agent=OutboundAgent(ctx),
            room=ctx.room,
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=lambda params: (
                        noise_cancellation.BVCTelephony()
                        if params.participant.kind
                        == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                        else noise_cancellation.BVC()
                    ),
                ),
            ),
        )
    )

    logger.info(
        "Calling Linphone destination",
        extra={
            "destination": phone_number,
            "room": ctx.room.name,
        },
    )

    try:

        await ctx.api.sip.create_sip_participant(
            api.CreateSIPParticipantRequest(
                room_name=ctx.room.name,
                sip_trunk_id=OUTBOUND_TRUNK_ID,
                sip_call_to=phone_number,
                participant_identity=CALLEE_IDENTITY,
                participant_name="BharatMoney User",
                wait_until_answered=True,
            )
        )

    except api.TwirpError as e:

        logger.error(
            "Outbound call failed",
            extra={
                "destination": phone_number,
                "error": e.message,
                "sip_status": e.metadata.get("sip_status"),
            },
        )

        session_started.cancel()

        ctx.shutdown()

        return

    except Exception:

        logger.exception(
            "Unexpected outbound call error"
        )

        session_started.cancel()

        ctx.shutdown()

        return

    await session_started

    logger.info(
        "BharatMoney outbound call answered successfully",
        extra={
            "room": ctx.room.name,
            "destination": phone_number,
        },
    )

    # Speak immediately after the user answers.
    await session.say(
        GREETING,
        allow_interruptions=True,
    )


if __name__ == "__main__":
    cli.run_app(server)