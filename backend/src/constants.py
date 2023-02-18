import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_KEY = os.environ["OPENAI_KEY"]
LATEST_COMMIT_ID = os.getenv("LATEST_COMMIT_ID", 'local')
ENVIRONMENT = os.getenv("ENVIRONMENT", 'local')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME', None)
FILESYSTEM_BASE = os.getenv('FILESYSTEM_BASE', '.')
