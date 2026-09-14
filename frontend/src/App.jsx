import React, { useState, useEffect } from 'react'
import { supabase } from '../lib/supabaseClient'
import '../styles/App.css'

export default function App() {
  const [user, setUser] = useState(null)
  const [markets, setMarkets] = useState([])
  const [weather, setWeather] = useState(null)
  const [predictions, setPredictions] = useState(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    checkUser()
  }, [])

  const checkUser = async () => {
    const { data: { user } } = await supabase.auth.getUser()
    setUser(user)
  }

  const handleLogin = async (phone, password) => {
    setLoading(true)
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        phone,
        password
      })
      if (error) throw error
      setUser(data.user)
    } catch (error) {
      alert('Login failed: ' + error.message)
    } finally {
      setLoading(false)
    }
  }

  const fetchMarkets = async () => {
    setLoading(true)
    try {
      const response = await fetch('http://localhost:8000/api/markets')
      const data = await response.json()
      setMarkets(data)
    } catch (error) {
      console.error('Error fetching markets:', error)
      setMarkets([{ status: 'UNAVAILABLE_DATA' }])
    } finally {
      setLoading(false)
    }
  }

  const fetchWeather = async (lat, lon) => {
    setLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/weather/current?latitude=${lat}&longitude=${lon}`)
      const data = await response.json()
      setWeather(data)
    } catch (error) {
      console.error('Error fetching weather:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchPredictions = async (commodity) => {
    setLoading(true)
    try {
      const response = await fetch(`http://localhost:8000/api/ai/predict-price?commodity=${commodity}`)
      const data = await response.json()
      setPredictions(data)
    } catch (error) {
      console.error('Error fetching predictions:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app-container">
      <header>
        <h1>🌾 EasyAgri - Live Agricultural Data</h1>
        <p>Real-time market prices, weather, and AI predictions</p>
      </header>

      <main>
        {!user ? (
          <div className="auth-section">
            <h2>Login with Supabase Auth</h2>
            <p>No demo credentials - Enter your real phone and password</p>
            <LoginForm onLogin={handleLogin} loading={loading} />
          </div>
        ) : (
          <div className="dashboard">
            <div className="user-info">
              <p>👤 Logged in as: {user.phone}</p>
              <button onClick={() => supabase.auth.signOut()}>Logout</button>
            </div>

            <div className="data-section">
              <h2>📊 Live Market Data</h2>
              <p className="info">Real government data from data.gov.in / AGMARKNET</p>
              <button onClick={fetchMarkets} disabled={loading}>
                {loading ? 'Loading...' : 'Fetch Live Markets'}
              </button>
              {markets.length > 0 && (
                <div className="data-display">
                  {markets[0].status === 'UNAVAILABLE_DATA' ? (
                    <p className="unavailable">UNAVAILABLE_DATA - Configure DATA_GOV_IN_API_KEY</p>
                  ) : (
                    <table>
                      <thead>
                        <tr>
                          <th>Commodity</th>
                          <th>Market</th>
                          <th>Price (₹)</th>
                          <th>Source</th>
                        </tr>
                      </thead>
                      <tbody>
                        {markets.map((market, idx) => (
                          <tr key={idx}>
                            <td>{market.commodity}</td>
                            <td>{market.market}</td>
                            <td>₹{market.price}</td>
                            <td>{market.source}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>

            <div className="data-section">
              <h2>🌤️ Live Weather</h2>
              <p className="info">Real-time data from Open-Meteo API</p>
              <div className="weather-controls">
                <input type="number" id="latitude" placeholder="Latitude" />
                <input type="number" id="longitude" placeholder="Longitude" />
                <button onClick={() => {
                  const lat = document.getElementById('latitude').value
                  const lon = document.getElementById('longitude').value
                  fetchWeather(lat, lon)
                }} disabled={loading}>
                  Get Weather
                </button>
              </div>
              {weather && (
                <div className="data-display">
                  {weather.status === 'UNAVAILABLE_DATA' ? (
                    <p className="unavailable">UNAVAILABLE_DATA</p>
                  ) : (
                    <div className="weather-info">
                      <p><strong>Temperature:</strong> {weather.temperature}°C</p>
                      <p><strong>Humidity:</strong> {weather.humidity}%</p>
                      <p><strong>Wind Speed:</strong> {weather.wind_speed} km/h</p>
                      <p><strong>Condition:</strong> {weather.condition}</p>
                      <p className="source">Source: {weather.source}</p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="data-section">
              <h2>🤖 AI Price Predictions</h2>
              <p className="info">Based on real historical market data (min. 7 observations required)</p>
              <div className="prediction-controls">
                <input type="text" id="commodity" placeholder="Commodity name (e.g., wheat)" />
                <button onClick={() => {
                  const commodity = document.getElementById('commodity').value
                  fetchPredictions(commodity)
                }} disabled={loading}>
                  Predict Price
                </button>
              </div>
              {predictions && (
                <div className="data-display">
                  {predictions.status === 'UNAVAILABLE_DATA' ? (
                    <p className="unavailable">UNAVAILABLE_DATA - Insufficient historical data</p>
                  ) : (
                    <div className="prediction-info">
                      <p><strong>Commodity:</strong> {predictions.commodity}</p>
                      <p><strong>Predicted Price:</strong> ₹{predictions.predicted_price}</p>
                      <p><strong>Confidence:</strong> {(predictions.confidence * 100).toFixed(2)}%</p>
                      <p><strong>Based on:</strong> {predictions.based_on_observations} observations</p>
                      <p><strong>Model:</strong> {predictions.model}</p>
                      <p className="source">Status: {predictions.status}</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      <footer>
        <p>📍 Data sources: Real data only | No demo records | Government APIs + Supabase</p>
        <p>Backend: <a href="http://localhost:8000">http://localhost:8000</a></p>
      </footer>
    </div>
  )
}

function LoginForm({ onLogin, loading }) {
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    onLogin(phone, password)
  }

  return (
    <form onSubmit={handleSubmit} className="login-form">
      <input
        type="tel"
        placeholder="Phone number"
        value={phone}
        onChange={(e) => setPhone(e.target.value)}
        required
      />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit" disabled={loading}>
        {loading ? 'Logging in...' : 'Login'}
      </button>
    </form>
  )
}
