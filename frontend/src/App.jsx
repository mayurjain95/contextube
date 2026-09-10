import { useState } from 'react'
import './App.css'

const API_BASE = '/api'

function App() {
  // 'input' | 'indexing' | 'chat'
  const [stage, setStage] = useState('input')
  const [url, setUrl] = useState('')
  const [videoId, setVideoId] = useState(null)
  const [error, setError] = useState(null)

  const [messages, setMessages] = useState([]) // {role: 'user'|'agent', text, wasCovered}
  const [question, setQuestion] = useState('')
  const [asking, setAsking] = useState(false)

  async function handleIndex(e) {
    e.preventDefault()
    setError(null)
    setStage('indexing')

    try {
      const res = await fetch(`${API_BASE}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Indexing failed (${res.status})`)
      }

      const data = await res.json()
      setVideoId(data.video_id)
      setStage('chat')
    } catch (err) {
      setError(err.message)
      setStage('input')
    }
  }

  async function handleAsk(e) {
    e.preventDefault()
    if (!question.trim() || asking) return

    const userQuestion = question
    setMessages((prev) => [...prev, { role: 'user', text: userQuestion }])
    setQuestion('')
    setAsking(true)

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ video_id: videoId, question: userQuestion }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error(body.detail || `Question failed (${res.status})`)
      }

      const data = await res.json()
      setMessages((prev) => [
        ...prev,
        { role: 'agent', text: data.answer, wasCovered: data.was_covered },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'agent', text: `Error: ${err.message}`, wasCovered: false },
      ])
    } finally {
      setAsking(false)
    }
  }

  function handleReset() {
    setStage('input')
    setUrl('')
    setVideoId(null)
    setMessages([])
    setError(null)
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <span>ContexTube</span>
        </div>
        <span className="live-pill"><span /> LOCAL INTELLIGENCE</span>
      </header>

      {stage === 'input' && (
        <main className="landing">
          <div className="eyebrow"><span className="eyebrow-line" /> VIDEO INTELLIGENCE <span className="eyebrow-line" /></div>
          <h1>Turn any video into<br /><em>a conversation.</em></h1>
          <p className="lede">Drop in a YouTube link. Ask sharper questions.<br />Get answers grounded in what was actually said.</p>
          <form className="url-form" onSubmit={handleIndex}>
            <div className="input-shell">
              <span className="input-icon">URL</span>
              <input type="text" placeholder="Paste a YouTube URL to begin" value={url} onChange={(e) => setUrl(e.target.value)} required />
            </div>
            <button type="submit">Analyze video <span className="arrow">&#8594;</span></button>
            {error && <p className="error">{error}</p>}
          </form>
          <div className="feature-row">
            <span><b>01</b> TRANSCRIPT SEARCH</span>
            <span><b>02</b> GROUNDED ANSWERS</span>
            <span><b>03</b> LOCAL &amp; PRIVATE</span>
          </div>
        </main>
      )}

      {stage === 'indexing' && (
        <main className="loading-state">
          <div className="pulse-ring"><span>Q</span></div>
          <div className="eyebrow"><span className="eyebrow-line" /> BUILDING YOUR INDEX</div>
          <h1>Listening closely.</h1>
          <p className="hint">Fetching the transcript and mapping the ideas inside.<br />Longer videos may take a little more time.</p>
          <div className="progress-track"><span /></div>
          <p className="loading-meta">TRANSCRIBE <i /> EMBED <i /> READY</p>
        </main>
      )}

      {stage === 'chat' && (
        <main className="chat">
          <div className="chat-header">
            <div><span className="section-label">ACTIVE VIDEO</span><strong>{videoId}</strong></div>
            <button className="link-button" onClick={handleReset}>
              + New video
            </button>
          </div>

          <div className="messages">
            {messages.length === 0 && (
              <div className="empty-chat"><span className="empty-mark">+</span><h2>Your video, decoded.</h2><p>Ask for a summary, a detail, or the argument behind an idea.</p></div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`message ${m.role}`}>
                <span className="role-label">
                  {m.role === 'user' ? 'You' : 'Agent'}
                </span>
                <p className={m.role === 'agent' && m.wasCovered === false ? 'not-covered' : ''}>
                  {m.text}
                </p>
              </div>
            ))}
            {asking && <p className="hint thinking"><span /> Thinking through the transcript...</p>}
          </div>

          <form className="question-form" onSubmit={handleAsk}>
            <input
              type="text"
              placeholder="Ask a question about the video"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={asking}
            />
            <button type="submit" disabled={asking} aria-label="Ask question"><span>&#8593;</span></button>
          </form>
        </main>
      )}
    </div>
  )
}

export default App
