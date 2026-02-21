"""
ElevenLabs Voice Reporter — speaks critical findings aloud.
Triggers when overall Braintrust score > 0.6 (real vulnerability found).
"""
from elevenlabs.client import ElevenLabs
from elevenlabs import play
from config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID
from observability.datadog_tracer import trace_step

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


@trace_step("reporter", "voice-report")
async def voice_report(attack_plan: dict, scores: dict, iteration: int):
    overall = scores.get("overall", 0)
    if overall < 0.4:
        print("[Reporter] Score too low — no voice report triggered.")
        return

    severity = attack_plan.get("severity_prediction", "unknown").upper()
    vector = attack_plan.get("attack_vector", "unknown").replace("_", " ")
    endpoint = attack_plan.get("target_endpoint", "/")

    script = f"""
    PenAgent alert. Iteration {iteration} complete.
    {'Critical finding detected.' if overall > 0.7 else 'Potential vulnerability found.'}
    Attack vector: {vector}.
    Target endpoint: {endpoint}.
    Severity: {severity}.
    Braintrust overall score: {overall:.0%}.
    Recommend immediate review.
    """

    audio = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=script.strip(),
        model_id="eleven_turbo_v2"
    )
    play(audio)
    print(f"[Reporter] Voice report delivered. Score: {overall:.0%}")
