# Medi-Scribe

An AI-powered medical scribe web application that automatically generates SOAP notes from patient-provider conversations.

## Features

- Audio recording and upload
- Real-time transcription
- AI-powered SOAP note generation
- Note editing and management

## Tech Stack

- Backend: Python/Flask
- Frontend: Next.js with TypeScript
- Database: MySQL
- Containerization: Docker

## Setup Instructions

### Prerequisites

- Python 3.8+
- Node.js 16+
- MySQL 8.0+
- Docker and Docker Compose

### Development Setup

1. Clone the repository
2. Set up the backend:

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Set up the frontend:

   ```bash
   cd frontend
   npm install
   ```

4. Start the development servers:

   ```bash
   # Backend
   cd backend
   flask run

   # Frontend
   cd frontend
   npm run dev
   ```

## Project Structure

```
medi-scribe/
├── backend/           # Flask backend
│   ├── app/          # Application code
│   ├── tests/        # Backend tests
│   └── requirements.txt
├── frontend/         # Next.js frontend
│   ├── src/         # Source code
│   └── package.json
└── docker-compose.yml
```

## License

MIT
