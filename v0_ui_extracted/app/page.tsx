'use client'

import { useEffect, useMemo, useState } from 'react'
import { io, type Socket } from 'socket.io-client'
import { Activity, AlertTriangle, AudioLines, CheckCircle2, CircleDot, Radio, RefreshCw, Send, Signal, TowerControl, Waves } from 'lucide-react'

type Role = 'sender' | 'receiver'
type Stage = 'idle' | 'recording' | 'transcribing' | 'sending' | 'awaiting_ack' | 'done' | 'failed'
type Message = { id: string; text: string; language: string; priority: string; packetsTotal: number; packetsLost: number; packetsRetried: number; bytesReceived: number; timestamp: string }
type Summary = { text: string; originalBytes: number; transmittedBytes: number; reductionPct: number; packetsTotal: number; packetsRetried: number; elapsedSeconds: number; delivered: boolean }

const API = process.env.NEXT_PUBLIC_BACKEND_URL?.replace(/\/$/, '') || ''
const languages = [['en', 'English'], ['hi', 'हिन्दी'], ['ta', 'தமிழ்'], ['te', 'తెలుగు']]
const bitrates = [['LOW', '1 kbps'], ['MEDIUM', '4 kbps'], ['HIGH', '8 kbps'], ['EXTREME', '0.5 kbps']]
const stageLabels: Record<Stage, string> = { idle: 'Ready to transmit', recording: 'Recording speech', transcribing: 'Transcribing audio', sending: 'Sending UDP packets', awaiting_ack: 'Waiting for acknowledgement', done: 'Delivered', failed: 'Transmission failed' }

function formatBytes(bytes: number) { return `${bytes >= 1000 ? (bytes / 1000).toFixed(1) : bytes} ${bytes >= 1000 ? 'KB' : 'B'}` }
function Flag({ ok = false }: { ok?: boolean }) { return <span className={`status-dot ${ok ? 'ok' : ''}`} aria-hidden="true" /> }

export default function Page() {
  const [role, setRole] = useState<Role>('sender')
  const [connected, setConnected] = useState(false)
  const [stage, setStage] = useState<Stage>('idle')
  const [detail, setDetail] = useState('Backend connection is not established')
  const [language, setLanguage] = useState('en')
  const [bitrateMode, setBitrateMode] = useState('MEDIUM')
  const [priority, setPriority] = useState('normal')
  const [receiverIp, setReceiverIp] = useState('192.168.1.100')
  const [summary, setSummary] = useState<Summary | null>(null)
  const [latest, setLatest] = useState<Message | null>(null)
  const [history, setHistory] = useState<Message[]>([])
  const [error, setError] = useState('')
  const [socket, setSocket] = useState<Socket | null>(null)
  const [readyAudioId, setReadyAudioId] = useState<string | null>(null)

  useEffect(() => {
    const s = io(API || undefined, { transports: ['websocket', 'polling'] })
    setSocket(s)
    s.on('connect', () => { setConnected(true); setDetail('Socket.IO link established') })
    s.on('disconnect', () => { setConnected(false); setDetail('Backend disconnected — check Flask service') })
    s.on('sender_progress', (p) => { setStage(p.stage); setDetail(p.detail) })
    s.on('sender_done', (data) => { setSummary(data); setError(''); setStage('done') })
    s.on('sender_error', (e) => { setError(e.message); setStage('failed') })
    s.on('message_received', (message) => { setLatest(message); setReadyAudioId(null); setHistory((items) => [message, ...items.filter((item) => item.id !== message.id)].slice(0, 20)) })
    s.on('audio_ready', (data) => { setReadyAudioId(data.id) })
    fetch(`${API}/api/history`).then((r) => r.ok ? r.json() : []).then(setHistory).catch(() => undefined)
    return () => { s.disconnect() }
  }, [])

  const audioUrl = useMemo(() => (latest && readyAudioId === latest.id) ? `${API}/api/received-audio/${latest.id}` : '', 
[latest, readyAudioId])
  async function changeRole(next: Role) {
    setRole(next); setError('')
    try { const response = await fetch(`${API}/api/role`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ role: next }) }); if (!response.ok) throw new Error((await response.json()).error); setDetail(next === 'receiver' ? 'UDP listener is active on port 5005' : 'Sender controls are armed') } catch (e) { setError(e instanceof Error ? e.message : 'Could not configure backend role') }
  }
  async function sendMessage() {
    setSummary(null); setError(''); setStage('recording')
    try { const response = await fetch(`${API}/api/send`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ language, bitrateMode, priority, receiverIp }) }); if (!response.ok) throw new Error((await response.json()).error) } catch (e) { setError(e instanceof Error ? e.message : 'Could not start sender pipeline'); setStage('failed') }
  }

  return <main className="console-shell">
    <div className="signal-grid" aria-hidden="true" />
    <header className="topbar">
      <div className="brand"><div className="brand-mark"><Radio size={25} /></div><div><p className="eyebrow">LAN VOICE TRANSCEIVER</p><h1>iTantra</h1></div></div>
      <div className="top-meta"><div className="link-state"><Flag ok={connected} /><span>{connected ? 'LINK ONLINE' : 'LINK OFFLINE'}</span></div><span className="port-readout">UDP :5005</span></div>
    </header>
    <section className="role-switch" aria-label="Choose device role"><span className="switch-label">DEVICE ROLE</span><button className={role === 'sender' ? 'active' : ''} onClick={() => changeRole('sender')}><Send size={17} /> SENDER</button><button className={role === 'receiver' ? 'active receiver-active' : ''} onClick={() => changeRole('receiver')}><TowerControl size={17} /> RECEIVER</button></section>
    <div className="connection-line"><Signal size={16} /><span>{detail}</span><span className="line-fill" /><span className="mono">{new Date().toLocaleDateString('en-GB')}</span></div>
    {error && <div className="error-banner" role="alert"><AlertTriangle size={19} /><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error">×</button></div>}
    {role === 'sender' ? <section className="workspace sender-workspace">
      <div className="panel controls-panel"><div className="panel-heading"><div><p className="eyebrow cyan">TRANSMIT CONFIGURATION</p><h2>Prepare message</h2></div><Waves className="heading-icon" /></div>
        <label className="field-label">RECEIVER IP ADDRESS<input value={receiverIp} onChange={(e) => setReceiverIp(e.target.value)} aria-label="Receiver IP address" /></label>
        <div className="field-label">LANGUAGE<span className="option-grid language-grid">{languages.map(([value, label]) => <button key={value} className={language === value ? 'selected' : ''} onClick={() => setLanguage(value)}>{label}</button>)}</span></div>
        <div className="field-label">BITRATE MODE<span className="option-grid">{bitrates.map(([value, label]) => <button key={value} className={bitrateMode === value ? 'selected' : ''} onClick={() => setBitrateMode(value)}><b>{value}</b><small>{label}</small></button>)}</span></div>
        <div className="field-label">DELIVERY PRIORITY<span className="priority-grid"><button className={priority === 'normal' ? 'selected' : ''} onClick={() => setPriority('normal')}>NORMAL<small>3 retries</small></button><button className={`${priority === 'emergency' ? 'emergency selected' : 'emergency'}`} onClick={() => setPriority('emergency')}><AlertTriangle size={15} /> EMERGENCY<small>5 retries</small></button></span></div>
        <button className={`transmit-button ${stage === 'recording' || stage === 'transcribing' || stage === 'sending' || stage === 'awaiting_ack' ? 'busy' : ''}`} disabled={!connected || ['recording', 'transcribing', 'sending', 'awaiting_ack'].includes(stage)} onClick={sendMessage}><CircleDot size={23} />{stage === 'idle' || stage === 'done' || stage === 'failed' ? 'RECORD & TRANSMIT' : stageLabels[stage].toUpperCase()}</button>
      </div>
      <div className="right-stack"><div className="panel pipeline-panel"><div className="panel-heading"><div><p className="eyebrow cyan">LIVE PIPELINE</p><h2>{stageLabels[stage]}</h2></div><Activity className={stage !== 'idle' && stage !== 'done' && stage !== 'failed' ? 'pulse heading-icon' : 'heading-icon'} /></div><div className="pipeline-steps">{(['recording', 'transcribing', 'sending', 'awaiting_ack', 'done'] as Stage[]).map((item, index) => <div className={`pipeline-step ${stage === item ? 'current' : ''} ${(['recording', 'transcribing', 'sending', 'awaiting_ack', 'done'].indexOf(stage) > index) ? 'complete' : ''}`} key={item}><span>{String(index + 1).padStart(2, '0')}</span><b>{stageLabels[item]}</b></div>)}</div><p className="stage-detail">{detail}</p></div>
        {summary && <div className="panel summary-panel"><div className="panel-heading"><div><p className="eyebrow cyan">TRANSMISSION REPORT</p><h2>{summary.delivered ? 'Payload delivered' : 'Delivery uncertain'}</h2></div><CheckCircle2 className="success-icon" /></div><p className="transcript">“{summary.text}”</p><div className="stats-grid"><div><small>REDUCTION</small><strong>{summary.reductionPct}%</strong></div><div><small>PAYLOAD</small><strong>{formatBytes(summary.transmittedBytes)}</strong><em>vs {formatBytes(summary.originalBytes)} text</em></div><div><small>PACKETS</small><strong>{summary.packetsTotal}</strong><em>{summary.packetsRetried} retried</em></div><div><small>ELAPSED</small><strong>{summary.elapsedSeconds}s</strong></div></div></div>}
      </div>
    </section> : <section className="workspace receiver-workspace"><div className="panel live-panel"><div className="receiver-live-head"><div><p className="eyebrow cyan">RECEIVER CHANNEL</p><h2>Listening for packets</h2></div><div className="listening"><span className="radar"><Signal size={25} /></span><b>LIVE</b></div></div>{latest ? <div className="message-card"><div className="message-meta"><span className="tag">{languages.find(([value]) => value === latest.language)?.[1] || latest.language}</span><span className={`tag ${latest.priority === 'emergency' ? 'emergency' : ''}`}>{latest.priority === 'emergency' ? 'EMERGENCY' : 'NORMAL'}</span><time>{latest.timestamp}</time></div><p className="received-text">{latest.text}</p><div className="receive-stats"><span><b>{latest.packetsTotal}</b> packets</span><span><b>{latest.packetsLost}</b> lost</span><span><b>{latest.packetsRetried}</b> retried</span><span><b>{formatBytes(latest.bytesReceived)}</b> received</span></div><audio controls autoPlay src={audioUrl} className="audio-player" aria-label="Synthesized received message" /></div> : <div className="empty-receiver"><AudioLines size={40} /><p>Waiting for the next transmission</p><small>Decoded messages and synthesized audio will appear here instantly.</small></div>}</div><div className="panel history-panel"><div className="panel-heading"><div><p className="eyebrow cyan">CHANNEL LOG</p><h2>Recent transmissions</h2></div><RefreshCw size={18} className="heading-icon" /></div><div className="history-list">{history.length ? history.map((item) => <div className="history-row" key={item.id}><span className="history-time">{item.timestamp}</span><div><b>{item.text}</b><small>{item.language.toUpperCase()} · {item.packetsTotal} packets · {item.priority}</small></div></div>) : <p className="muted">No messages received in this session.</p>}</div></div></section>}
    <footer><span>iTantra // REAL UDP VOICE LINK</span><span>SOCKET.IO {connected ? 'CONNECTED' : 'WAITING'} · {role.toUpperCase()} MODE</span></footer>
  </main>
}
