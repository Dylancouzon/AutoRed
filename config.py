import os
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_LOCATION = os.getenv("GCP_LOCATION", "us-central1")
MODEL_ID = os.getenv("MODEL_ID", "gemini-2.5-pro")  # swap to gemini-3 when live

BRAINTRUST_API_KEY = os.getenv("BRAINTRUST_API_KEY")
BRAINTRUST_PROJECT = os.getenv("BRAINTRUST_PROJECT", "penagent-evals")

DD_API_KEY = os.getenv("DD_API_KEY")
DD_APP_KEY = os.getenv("DD_APP_KEY")
DD_SITE = os.getenv("DD_SITE", "datadoghq.com")
DD_SERVICE = os.getenv("DD_SERVICE", "penagent")
DD_ENV = os.getenv("DD_ENV", "hackathon")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")

TARGET_URL = os.getenv("TARGET_URL", "http://localhost:8080")
TARGET_NAME = os.getenv("TARGET_NAME", "DVWA")

MAX_LOOP_ITERATIONS = 3
