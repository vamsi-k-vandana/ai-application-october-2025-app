import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { supabase } from './supabaseClient';
import './App.css';

function App() {
  const [backendMessage, setBackendMessage] = useState<string>('');
  const [supabaseData, setSupabaseData] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);

  const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

  useEffect(() => {
    fetchBackendData();
  }, []);

  const fetchBackendData = async () => {
    try {
      // Fetch from FastAPI backend
      const response = await axios.get(`${API_URL}/`);
      setBackendMessage(response.data.message);

      // Fetch from backend endpoint that queries Supabase
      const dataResponse = await axios.get(`${API_URL}/api/data`);
      setSupabaseData(dataResponse.data.data || []);

      setLoading(false);
    } catch (error) {
      console.error('Error fetching data:', error);
      setBackendMessage('Error connecting to backend');
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Hello World App</h1>

        {loading ? (
          <p>Loading...</p>
        ) : (
          <>
            <div style={{ margin: '20px 0' }}>
              <h2>Backend Message:</h2>
              <p>{backendMessage}</p>
            </div>

            <div style={{ margin: '20px 0' }}>
              <h2>Supabase Data:</h2>
              {supabaseData.length > 0 ? (
                <pre>{JSON.stringify(supabaseData, null, 2)}</pre>
              ) : (
                <p>No data from Supabase (make sure to create an 'items' table)</p>
              )}
            </div>

            <button onClick={fetchBackendData}>
              Refresh Data
            </button>
          </>
        )}
      </header>
    </div>
  );
}

export default App;
