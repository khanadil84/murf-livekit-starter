from livekit.agents import Agent, RunContext, function_tool


SPECIALIST_PROMPT = """
You are the BharatMoney Government Scheme Specialist.

Your ONLY job is to help users understand Indian government financial
schemes, especially PMJDY (Pradhan Mantri Jan-Dhan Yojana).

You are a specialist, not a bank, government authority, financial advisor,
loan provider, or payment service.

You may explain:
- PMJDY
- Government financial schemes
- General scheme benefits
- General eligibility information
- General documents commonly required
- Where users can verify official information

For current PMJDY information, use check_pmjdy_information when the caller
asks for current or specific PMJDY information. Never invent current scheme
information.

SAFETY:
- Never ask for OTP.
- Never ask for UPI PIN.
- Never ask for PIN.
- Never ask for CVV.
- Never ask for passwords.
- Never ask for a full bank account number.
- Never ask for a full card number.
- Never claim to access a bank account.
- Never perform banking transactions.
- Never guarantee eligibility, loans, benefits, or financial outcomes.

LANGUAGE:
Mirror the caller's language:
English = simple English.
Hindi = natural Hindi.
Hinglish = natural Hinglish.

Keep answers short and conversational.

The caller has already been speaking with the main BharatMoney agent.
Continue naturally from the existing conversation. Do not ask the caller
to repeat the problem unnecessarily.
"""


class GovernmentSchemeSpecialist(Agent):
    def __init__(self, chat_ctx=None, call_state=None) -> None:
        self.call_state = call_state if call_state is not None else {"successful": False}

        super().__init__(
            instructions=SPECIALIST_PROMPT,
            chat_ctx=chat_ctx,
        )

    def mark_call_success(self) -> None:
        self.call_state["successful"] = True

    @function_tool
    async def check_pmjdy_information(
        self,
        context: RunContext,
    ) -> str:
        """Fetch current PMJDY information from the official Government of India source."""

        import asyncio
        import re
        import urllib.request

        url = "https://pmjdy.gov.in/scheme"

        def fetch_page() -> str:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 BharatMoney-VoiceAI/1.0"
                },
            )
            with urllib.request.urlopen(request, timeout=8) as response:
                return response.read().decode("utf-8", errors="ignore")

        try:
            html = await asyncio.to_thread(fetch_page)

            text = re.sub(
                r"<script.*?</script>",
                " ",
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )
            text = re.sub(
                r"<style.*?</style>",
                " ",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )
            text = re.sub(r"<[^>]+>", " ", text)
            text = re.sub(r"\s+", " ", text).strip()

            useful_phrases = []
            text_lower = text.lower()

            keywords = (
                "zero balance",
                "minimum balance",
                "bank mitra",
                "bank branch",
                "savings",
                "deposit account",
                "financial services",
                "rupey debit card",
                "overdraft",
            )

            for keyword in keywords:
                position = text_lower.find(keyword)
                if position != -1:
                    start = max(0, position - 180)
                    end = min(len(text), position + 350)
                    snippet = text[start:end]

                    if snippet not in useful_phrases:
                        useful_phrases.append(snippet)

            if not useful_phrases:
                return (
                    "I reached the official PMJDY website, but I could not "
                    "extract the required information right now. I don't "
                    "want to guess. Please try again shortly."
                )

            result = " ".join(useful_phrases[:3])
            if len(result) > 1800:
                result = result[:1800] + "..."

            self.mark_call_success()

            return (
                "I checked the official Government of India PMJDY website. "
                f"Here is the relevant information: {result} "
                "Please verify important eligibility or documentation "
                "details with the official source or a bank."
            )

        except Exception:
            return (
                "I couldn't reach the official PMJDY information source "
                "right now. I don't want to guess or give you outdated "
                "financial information. Please try again shortly."
            )

    async def on_enter(self) -> None:
        await self.session.generate_reply(
            instructions=(
                "You have just taken over from the main BharatMoney agent. "
                "Briefly introduce yourself as the Government Scheme "
                "Specialist and continue naturally from the existing "
                "conversation. Do not ask the caller to repeat what they "
                "already said. Ask one focused question if needed."
            )
        )