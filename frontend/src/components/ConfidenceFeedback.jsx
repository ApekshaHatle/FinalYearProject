function ConfidenceFeedback({ confidence, feedbackRecordId, token, initialVote }) {
  const [vote, setVote] = useState(initialVote ?? null)
  const [submitted, setSubmitted] = useState(initialVote != null)
  const [loading, setLoading] = useState(false)
  const [learningData, setLearningData] = useState(null)  // NEW: stores what was learned

  useEffect(() => {
    if (initialVote != null) { setVote(initialVote); setSubmitted(true) }
  }, [initialVote])

  if (!confidence) return null

  const levels = {
    high:   { color: '#16a34a', bg: 'rgba(22,163,74,0.1)',  dot: '#22c55e', text: 'High confidence' },
    medium: { color: '#b45309', bg: 'rgba(245,158,11,0.1)', dot: '#f59e0b', text: 'Medium confidence' },
    low:    { color: '#b91c1c', bg: 'rgba(239,68,68,0.1)',  dot: '#ef4444', text: 'Low confidence' },
  }
  const cfg = levels[confidence.label] ?? { color: '#888', bg: 'rgba(128,128,128,0.1)', dot: '#aaa', text: 'No data' }
  const pct = confidence.score != null ? Math.round(confidence.score * 100) : null

  async function submit(v) {
    if (submitted || loading || !feedbackRecordId) return
    setLoading(true)
    setVote(v)
    try {
      const res = await fetch('http://localhost:8000/api/chat/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ record_id: feedbackRecordId, vote: v })
      })
      const data = await res.json()
      setSubmitted(true)
      // NEW: store what the backend learned to show in UI
      setLearningData(data)
    } catch (e) {
      console.error('Feedback error:', e)
      setSubmitted(true)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={cfStyles.row}>
      {/* Confidence pill */}
      <span style={{ ...cfStyles.pill, color: cfg.color, background: cfg.bg, border: `1px solid ${cfg.color}28` }}>
        <span style={{ ...cfStyles.dot, background: cfg.dot, boxShadow: `0 0 0 3px ${cfg.dot}22` }} />
        {cfg.text}
        {pct != null && (
          <span style={{ ...cfStyles.pct, color: cfg.color, background: `${cfg.color}14` }}>
            {pct}%
          </span>
        )}
      </span>

      <span style={cfStyles.divider} />

      {!submitted ? (
        <span style={cfStyles.fbRow}>
          <span style={cfStyles.fbLabel}>Helpful?</span>
          <button onClick={() => submit(1)} disabled={loading} title="Yes, helpful"
            style={{ ...cfStyles.thumbBtn, ...(vote === 1 ? cfStyles.thumbUpActive : {}) }}>
            <ThumbsUp size={13} strokeWidth={2} />
          </button>
          <button onClick={() => submit(-1)} disabled={loading} title="No, not helpful"
            style={{ ...cfStyles.thumbBtn, ...(vote === -1 ? cfStyles.thumbDownActive : {}) }}>
            <ThumbsDown size={13} strokeWidth={2} />
          </button>
        </span>
      ) : (
        // NEW: Show a richer "what was learned" message
        <LearningIndicator vote={vote} learningData={learningData} />
      )}
    </div>
  )
}

// NEW component — shows what the system learned after feedback
function LearningIndicator({ vote, learningData }) {
  const [expanded, setExpanded] = useState(false)

  const isPositive = vote === 1
  const color = isPositive ? '#16a34a' : '#b45309'
  const bg    = isPositive ? 'rgba(22,163,74,0.08)' : 'rgba(180,83,9,0.08)'
  const border= isPositive ? 'rgba(22,163,74,0.25)' : 'rgba(180,83,9,0.25)'

  // Parse what keywords were updated from the response
  const keywordsUpdated = learningData?.keywords_updated || []
  const newWeight       = learningData?.updated_confidence

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <button
        onClick={() => setExpanded(e => !e)}
        style={{
          display: 'inline-flex', alignItems: 'center', gap: '6px',
          background: bg, border: `1px solid ${border}`,
          borderRadius: '999px', padding: '3px 10px 3px 8px',
          cursor: 'pointer', fontSize: '11px', fontWeight: 500, color,
        }}
      >
        {isPositive
          ? <><ThumbsUp size={11} strokeWidth={2} /> System learned · {expanded ? 'hide' : 'details'}</>
          : <><ThumbsDown size={11} strokeWidth={2} /> Noted · {expanded ? 'hide' : 'details'}</>}
        <ChevronDown size={10} style={{ transform: expanded ? 'rotate(180deg)' : 'none', transition: 'transform .2s' }} />
      </button>

      {expanded && (
        <div style={{
          background: 'var(--color-background-secondary)',
          border: '1px solid var(--color-border-tertiary)',
          borderRadius: '8px', padding: '8px 12px', fontSize: '11px',
          color: 'var(--color-text-secondary)', lineHeight: 1.6,
        }}>
          {isPositive ? (
            <>
              <span style={{ color: '#16a34a', fontWeight: 500 }}>EMA weights updated (+1 signal)</span><br />
              {keywordsUpdated.length > 0
                ? <>Keywords reinforced: <span style={{ fontFamily: 'monospace', color: 'var(--color-text-primary)' }}>{keywordsUpdated.join(', ')}</span><br /></>
                : null}
              Next similar queries will receive a <span style={{ color: '#16a34a', fontWeight: 500 }}>higher confidence</span> score.
              {newWeight != null && <> New trust weight: <span style={{ fontFamily: 'monospace' }}>{newWeight.toFixed(3)}</span></>}
            </>
          ) : (
            <>
              <span style={{ color: '#b45309', fontWeight: 500 }}>EMA weights updated (−1 signal)</span><br />
              {keywordsUpdated.length > 0
                ? <>Keywords flagged: <span style={{ fontFamily: 'monospace', color: 'var(--color-text-primary)' }}>{keywordsUpdated.join(', ')}</span><br /></>
                : null}
              Next similar queries will show a <span style={{ color: '#b45309', fontWeight: 500 }}>lower confidence</span> score as a warning.
            </>
          )}
        </div>
      )}
    </div>
  )
}