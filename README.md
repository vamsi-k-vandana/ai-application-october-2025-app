# Hello World App - React + FastAPI + Supabase

A full-stack application boilerplate with React frontend, FastAPI backend, Supabase database, and Render deployment configuration.

## Project Structure

```
base-app/
├── backend/
│   ├── main.py              # FastAPI application
│   ├── requirements.txt     # Python dependencies
│   └── .env.example        # Environment variables template
├── frontend/
│   ├── src/
│   │   ├── App.tsx         # Main React component
│   │   └── supabaseClient.ts  # Supabase client config
│   ├── package.json
│   └── .env.example        # Environment variables template
├── render.yaml             # Render deployment config
└── README.md
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- A Supabase account and project
- A Render account (for deployment)

## Local Development Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd base-app
```

### 2. Set up Supabase

1. Go to [supabase.com](https://supabase.com) and create a new project
2. Create a table called `items` in your Supabase database:
   ```sql
   CREATE TABLE items (
     id SERIAL PRIMARY KEY,
     name TEXT,
     created_at TIMESTAMP DEFAULT NOW()
   );
   ```
3. Insert some test data:
   ```sql
   INSERT INTO items (name) VALUES ('Test Item 1'), ('Test Item 2');
   ```
4. Get your Supabase URL and anon key from Project Settings > API

### 3. Backend Setup

```bash
# Create and activate virtual environment
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env and add your Supabase credentials

# Run the backend
uvicorn main:app --reload --port 8000
```

The backend will be available at http://localhost:8000

### 4. Frontend Setup

```bash
# In a new terminal
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env
# Edit .env and add your Supabase credentials and API URL

# Run the frontend
npm start
```

The frontend will be available at http://localhost:3000

## Environment Variables

### Backend (.env)
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key
```

### Frontend (.env)
```
REACT_APP_API_URL=http://localhost:8000
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=your-supabase-anon-key
```

## Deployment to Render

### Option 1: Using render.yaml (Blueprint)

1. Push your code to GitHub
2. Go to [Render Dashboard](https://dashboard.render.com)
3. Click "New" > "Blueprint"
4. Connect your GitHub repository
5. Render will detect the `render.yaml` file and create both services
6. Add environment variables in the Render dashboard for each service

### Option 2: Manual Deployment

#### Backend Service
1. Go to Render Dashboard
2. Click "New" > "Web Service"
3. Connect your repository
4. Configure:
   - Name: `fastapi-backend`
   - Runtime: `Python 3`
   - Build Command: `pip install -r backend/requirements.txt`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY`

#### Frontend Service
1. Click "New" > "Static Site"
2. Connect your repository
3. Configure:
   - Name: `react-frontend`
   - Build Command: `cd frontend && npm install && npm run build`
   - Publish Directory: `frontend/build`
4. Add environment variables:
   - `REACT_APP_API_URL` (your backend URL)
   - `REACT_APP_SUPABASE_URL`
   - `REACT_APP_SUPABASE_ANON_KEY`

### Post-Deployment

After deployment, update the frontend's `REACT_APP_API_URL` to point to your deployed backend URL.

## API Endpoints

- `GET /` - Hello world message
- `GET /api/health` - Health check
- `GET /api/data` - Fetch data from Supabase

## Features

- React TypeScript frontend with Axios for API calls
- FastAPI backend with CORS support
- Supabase integration for database
- Ready for Render deployment
- Environment-based configuration

## Next Steps

- Add authentication with Supabase Auth
- Implement CRUD operations
- Add proper error handling
- Set up proper CORS origins for production
- Add tests
- Configure CI/CD

## License

MIT
