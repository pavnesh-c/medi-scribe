# Medi-Scribe

A real-time medical conversation transcription and SOAP note generation application. This tool helps healthcare providers by automatically transcribing patient conversations and generating structured SOAP notes.

## Features

- **Live Audio Recording**: Record medical conversations in real-time with support for MP3 format
- **Real-time Transcription**: Powered by Deepgram's Nova-2 model for accurate speech-to-text conversion
- **Speaker Diarization**: Automatically identifies and labels different speakers in the conversation
- **SOAP Note Generation**: Converts transcribed conversations into structured SOAP (Subjective, Objective, Assessment, Plan) notes
- **File Upload**: Support for uploading pre-recorded audio files

## Tech Stack

### Frontend

- Next.js 14
- React
- Web Audio API for audio recording

### Backend

- Python
- FastAPI
- Deepgram API for transcription
- OpenAI API for SOAP note generation
- SQLAlchemy for database management

## Prerequisites

- Python 3.8+
- Node.js 18+
- FFmpeg (for audio processing)
- Deepgram API key
- OpenAI API key

## Environment Variables

### Backend (.env)

```
DEEPGRAM_API_KEY=your_deepgram_api_key
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=your_database_url
UPLOAD_DIR=uploads
```

## Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/medi-scribe.git
cd medi-scribe
```

2. Set up the backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Set up the frontend:

```bash
cd frontend
npm install
```

4. Create necessary directories:

```bash
mkdir -p backend/uploads
```

## Running the Application

1. Start the backend server:

```bash
cd backend
uvicorn app.main:app --reload
```

2. Start the frontend development server:

```bash
cd frontend
npm run dev
```

3. Access the application at `http://localhost:3000`

## Project Structure

```
medi-scribe/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── services/
│   │   └── utils/
│   ├── uploads/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   ├── components/
│   │   └── constants/
│   └── package.json
└── README.md
```
