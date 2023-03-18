import os
from dotenv import load_dotenv

load_dotenv()

# TODO find a way to sync these variables with the ones in:
# `infrastructure/src/utils/constants.ts`
PASCAL_CASE_PREFIX = 'AskPaper'
CAMEL_CASE_PREFIX = 'askPaper'
SNAKE_CASE_PREFIX = 'ask_paper'
KEBAB_CASE_PREFIX = 'ask-paper'

DB_FUNCTION_INVOCATIONS = F'{SNAKE_CASE_PREFIX}_function_invocations'
DB_EMAILS_SENT = f'{SNAKE_CASE_PREFIX}_emails_sent'
DB_JSON_PAPERS = f'{SNAKE_CASE_PREFIX}_json_papers'
DB_FEEDBACK = f'{SNAKE_CASE_PREFIX}_feedback'
DB_GUEST_USERS = f'{SNAKE_CASE_PREFIX}_guest_users'

ASK_PAPER_BANNER_IMG = "https://hippoai-sandbox.s3.eu-central-1.amazonaws.com/askpaperbanner.png"

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
LATEST_COMMIT_ID = os.getenv("LATEST_COMMIT_ID", 'local')
ENVIRONMENT = os.getenv("ENVIRONMENT", 'dev')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', f'{KEBAB_CASE_PREFIX}-papers-{ENVIRONMENT}')
FILESYSTEM_BASE = os.getenv('FILESYSTEM_BASE', '.')
EMAIL_SENDER = 'alex@hippoai.dev'
MAX_CONTEXTS = 7
LLM_MAX_TOKENS = 4000