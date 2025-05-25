import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@localhost/medi_scribe')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY') 