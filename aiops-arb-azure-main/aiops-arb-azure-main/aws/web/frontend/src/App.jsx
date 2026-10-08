import React, { useState, useEffect, useRef, createContext, useContext } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeRaw from 'rehype-raw'
import mermaid from 'mermaid'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ComposedChart, Area, ReferenceLine
} from 'recharts'

mermaid.initialize({ startOnLoad: false, theme: 'dark', maxTextSize: 100000, securityLevel: 'loose' })

// ── i18n ──────────────────────────────────────────────────────────────────────
const T = {
  ko: {
    dashboard: 'ARB 대시보드', run: 'ARB 점검', history: '히스토리',
    reports: '리포트', cost: '비용',
    overallStatus: '전체 점검 현황', failTrend: '프로젝트별 FAIL 추이',
    selectProject: '-- 프로젝트 선택 --', noData: '데이터 없음', noHistory: '점검 이력이 없습니다',
    startInspection: '점검 시작', inspecting: '점검 중...', serviceName: '서비스명',
    accountId: '계정 ID', region: '리전', autoRegion: '전체 리전 자동 탐지',
    scopeLabel: '점검 범위', scopeAll: '전체 (인프라 + DB)', scopeDatabase: 'DB만 점검',
    scopeDatabaseDesc: 'Aurora / RDS / DynamoDB / ElastiCache만 점검합니다.',
    enginesLabel: '점검할 DB 엔진 선택', enginesAll: '전체 선택', enginesNone: '전체 해제',
    realtime: '실시간 로그', statusCol: '상태', resultCol: '점검 결과',
    startTime: '시작', endTime: '완료', logBtn: '로그', reportBtn: '리포트',
    reportTitle: '리포트 조회', download: '⬇ 다운로드', selectReport: '좌측에서 리포트를 선택하세요',
    costTitle: '비용 현황', projectCol: '과제명', countCol: '점검 횟수', lastDate: '최근 점검일',
    monthlyCost: '월별 AWS 비용', totalCost: '월 합계', projectStatus: '과제별 점검 현황',
    month: '월', costCol: '비용', confirmed: '확정', estimated: '추정값',
    recentLabel: '최근', monthTotal: '월 합계', inspectionCount: '점검 수',
    costUnit: '비용 ($)', threeMonthTotal: '12개월 합계',
    locale: 'ko', guide: '운영 가이드', help: '도움말',
  },
  en: {
    dashboard: 'ARB Dashboard', run: 'ARB Inspection', history: 'History',
    reports: 'Reports', cost: 'Cost',
    overallStatus: 'Overall Inspection Status', failTrend: 'FAIL Trend by Project',
    selectProject: '-- Select Project --', noData: 'No Data', noHistory: 'No inspection history',
    startInspection: 'Start Inspection', inspecting: 'Inspecting...', serviceName: 'Service Name',
    accountId: 'Account ID', region: 'Region', autoRegion: 'Auto-detect all regions',
    scopeLabel: 'Scope', scopeAll: 'Full (Infra + DB)', scopeDatabase: 'Database Only',
    scopeDatabaseDesc: 'Inspects Aurora / RDS / DynamoDB / ElastiCache only.',
    enginesLabel: 'Select DB Engines', enginesAll: 'Select All', enginesNone: 'Deselect All',
    realtime: 'Realtime Log', statusCol: 'Status', resultCol: 'Result',
    startTime: 'Started', endTime: 'Finished', logBtn: 'Log', reportBtn: 'Report',
    reportTitle: 'Reports', download: '⬇ Download', selectReport: 'Select a report on the left',
    costTitle: 'Cost Overview', projectCol: 'Project', countCol: 'Inspections', lastDate: 'Last Inspection',
    monthlyCost: 'Monthly AWS Cost', totalCost: 'Monthly Total', projectStatus: 'Inspections by Project',
    month: 'Month', costCol: 'Cost', confirmed: 'Final', estimated: 'Estimated',
    recentLabel: 'Latest', monthTotal: 'Monthly Total', inspectionCount: 'Inspections',
    costUnit: 'Cost ($)', threeMonthTotal: '12-Month Total',
    locale: 'en-US', guide: 'Ops Guide', help: 'Help',
  }
}
const LangContext = createContext('ko')
const useLang = () => { const lang = useContext(LangContext); return (key) => T[lang][key] || key }


function MermaidBlock({ code }) {
  const ref = useRef(null)
  useEffect(() => {
    if (!ref.current) return
    const id = 'mermaid-' + Math.random().toString(36).slice(2)
    mermaid.render(id, code).then(({ svg }) => {
      if (ref.current) ref.current.innerHTML = svg
    }).catch(() => {
      if (ref.current) ref.current.textContent = code
    })
  }, [code])
  return <div ref={ref} style={{ background: '#1a1d27', padding: '12px', borderRadius: '6px', overflowX: 'auto' }} />
}

const API = ''

const REGIONS = [
  'ap-northeast-2', 'ap-northeast-1', 'ap-southeast-1', 'ap-southeast-2',
  'us-east-1', 'us-east-2', 'us-west-1', 'us-west-2',
  'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-central-1',
  'ca-central-1', 'ap-south-1',
]

function StatusBadge({ status }) {
  return <span className={`badge badge-${status}`}>{status}</span>
}

// ── Dashboard Page ────────────────────────────────────────────────────────────
function DashboardPage() {
  const t = useLang()
  const [projects, setProjects] = useState([])
  const [selected, setSelected] = useState('')
  const [trend, setTrend] = useState([])
  const [monthly, setMonthly] = useState([])
  const now = new Date()
  const [viewMonth, setViewMonth] = useState(`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}`)

  useEffect(() => {
    fetch(`${API}/api/dashboard/projects`).then(r => r.json()).then(p => {
      setProjects(p)
      if (p.length > 0) setSelected(p[0].account_id)
    })
  }, [])

  useEffect(() => {
    fetch(`${API}/api/dashboard/monthly?month=${viewMonth}`).then(r => r.json()).then(setMonthly)
  }, [viewMonth])

  useEffect(() => {
    if (!selected) return
    fetch(`${API}/api/dashboard/trend?account_id=${encodeURIComponent(selected)}`).then(r => r.json()).then(setTrend)
  }, [selected])

  const latest = trend[trend.length - 1]

  // 월 선택 옵션 생성 (최근 6개월)
  const monthOptions = []
  for (let i = 0; i < 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const m = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`
    monthOptions.push(m)
  }

  // 툴팁 커스텀
  const MonthlyTooltip = ({ active, payload, label }) => {
    if (!active || !payload?.length) return null
    const d = payload[0]?.payload
    return (
      <div style={{ background: '#1a1d27', border: '1px solid #2d3148', borderRadius: 6, padding: '8px 12px', fontSize: 12 }}>
        <div style={{ color: '#94a3b8', marginBottom: 4 }}>{label}</div>
        <div style={{ color: '#7c6af7' }}>{t('inspectionCount')}: {d?.count || 0}</div>
        {d?.cost > 0 && <div style={{ color: '#4ade80', marginTop: 2 }}>Cost: ${d.cost.toFixed(2)}</div>}
        {d?.projects?.length > 0 && (
          <div style={{ color: '#64748b', marginTop: 4 }}>{d.projects.join(', ')}</div>
        )}
      </div>
    )
  }

  return (
    <div>
      <div className="page-title">{t('dashboard')}</div>

      {/* 전체 점검 현황 */}
      <div style={{ marginBottom: 16 }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
            <h2 style={{ margin: 0 }}>{t('overallStatus')}</h2>
            <select value={viewMonth} onChange={e => setViewMonth(e.target.value)}
              style={{ background: '#0f1117', border: '1px solid #2d3148', borderRadius: 6, padding: '5px 10px', color: '#e2e8f0', fontSize: 13 }}>
              {monthOptions.map(m => <option key={m}>{m}</option>)}
            </select>
            <span style={{ fontSize: 12, color: '#64748b' }}>
              {t('monthTotal')}: <span style={{ color: '#4ade80', fontWeight: 600 }}>
                ${monthly.reduce((s, d) => s + (d.cost || 0), 0).toFixed(2)}
              </span>
            </span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <ComposedChart data={monthly} margin={{ top: 4, right: 50, left: 0, bottom: 4 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
              <XAxis dataKey="day" tickFormatter={d => d.slice(8)} tick={{ fontSize: 10, fill: '#64748b' }} />
              <YAxis yAxisId="left" allowDecimals={false} tick={{ fontSize: 11, fill: '#64748b' }} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11, fill: '#4ade80' }}
                tickFormatter={v => `$${v}`} />
              <Tooltip content={<MonthlyTooltip />} />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Bar yAxisId="left" dataKey="count" fill="#7c6af7" name={t('inspectionCount')} radius={[3, 3, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="cost" stroke="#4ade80"
                strokeWidth={2} dot={{ r: 3, fill: '#4ade80' }} name={t('costUnit')} connectNulls />
              {(() => {
                // 점검 0건인 날들의 평균 → 고정 비용 기준선
                const zeroDays = monthly.filter(d => d.count === 0 && d.cost > 0)
                if (zeroDays.length === 0) return null
                const baseline = zeroDays.reduce((s, d) => s + d.cost, 0) / zeroDays.length
                return (
                  <ReferenceLine yAxisId="right" y={baseline} stroke="#fb923c" strokeDasharray="6 3" strokeWidth={1.5}
                    label={{ value: `고정 ~$${baseline.toFixed(1)}`, position: 'insideRight', fill: '#fb923c', fontSize: 10 }} />
                )
              })()}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 프로젝트별 FAIL 추이 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 16 }}>
          <h2 style={{ margin: 0 }}>{t('failTrend')}</h2>
          <select value={selected} onChange={e => setSelected(e.target.value)}
            style={{ background: '#0f1117', border: '1px solid #2d3148', borderRadius: 6, padding: '6px 12px', color: '#e2e8f0', fontSize: 14 }}>
            <option value="">{t('selectProject')}</option>
            {projects.map(p => <option key={p.account_id} value={p.account_id}>{p.service_name}</option>)}
          </select>
        </div>

        {!selected ? (
          <div className="empty">{t('selectProject')}</div>
        ) : trend.length === 0 ? (
          <div className="empty">{t('noData')}</div>
        ) : (
          <>
            {latest && (
              <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
                {[
                  { label: 'PASS', value: latest.pass, color: '#4ade80' },
                  { label: 'FAIL', value: latest.fail, color: '#f87171' },
                  { label: 'Critical FAIL', value: latest.critical, color: '#fb923c' },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ flex: 1, textAlign: 'center', background: '#0f1117', borderRadius: 8, padding: '16px 12px' }}>
                    <div style={{ fontSize: 28, fontWeight: 700, color }}>{value}</div>
                    <div style={{ fontSize: 12, color: '#64748b', marginTop: 4 }}>{label}</div>
                    <div style={{ fontSize: 11, color: '#475569', marginTop: 2 }}>{t('recentLabel')} ({latest.label})</div>
                  </div>
                ))}
              </div>
            )}
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                <XAxis dataKey="label" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} />
                <Tooltip contentStyle={{ background: '#1a1d27', border: '1px solid #2d3148', fontSize: 12 }}
                  formatter={(v, name) => [v, name]}
                  labelFormatter={l => `${t('recentLabel')}: ${l}`} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="pass" stroke="#4ade80" strokeWidth={2} dot={{ r: 4 }} name="PASS" />
                <Line type="monotone" dataKey="fail" stroke="#f87171" strokeWidth={2} dot={{ r: 4 }} name="FAIL" />
                <Line type="monotone" dataKey="critical" stroke="#fb923c" strokeWidth={2} dot={{ r: 4 }} name="Critical" />
              </LineChart>
            </ResponsiveContainer>
          </>
        )}
      </div>
    </div>
  )
}


// ── DB Pre-Survey Panel ──────────────────────────────────────────────────────
function DBPreSurveyPanel({ accountId }) {
  const lang = useContext(LangContext)
  const isEn = lang === 'en'
  const [info, setInfo] = useState({})
  const [selectedEngine, setSelectedEngine] = useState(null)
  const [uploadedFiles, setUploadedFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState('')
  const fileRef = useRef(null)
  // 수동 설문 상태
  const [manualSchema, setManualSchema] = useState({})
  const [manualAnswers, setManualAnswers] = useState({})
  const [manualSavedAt, setManualSavedAt] = useState({})
  const [manualSaving, setManualSaving] = useState(false)
  const [openManualSec, setOpenManualSec] = useState(null)

  useEffect(() => {
    fetch(`${API}/api/db-presurvey/info`).then(r => r.json()).then(setInfo)
    fetch(`${API}/api/db-manual-survey/schema`).then(r => r.json()).then(setManualSchema)
  }, [])

  useEffect(() => {
    if (!accountId || accountId.length !== 12) return
    fetch(`${API}/api/db-presurvey/files/${accountId}`).then(r => r.json()).then(setUploadedFiles)
  }, [accountId, uploadMsg])

  // 엔진 선택 시 수동 설문 저장값 로드
  useEffect(() => {
    if (!selectedEngine || !accountId || accountId.length !== 12) return
    fetch(`${API}/api/db-manual-survey/${accountId}/${selectedEngine}`)
      .then(r => r.json())
      .then(d => {
        setManualAnswers(prev => ({ ...prev, [selectedEngine]: d.data || {} }))
        setManualSavedAt(prev => ({ ...prev, [selectedEngine]: d.submitted_at }))
        // 첫 번째 섹션 자동 열기
        const schema = manualSchema[selectedEngine]
        if (schema && schema.sections.length > 0 && !openManualSec) {
          setOpenManualSec(schema.sections[0].key)
        }
      })
  }, [selectedEngine, accountId])

  const setManualField = (engine, key, val) => {
    setManualAnswers(prev => ({ ...prev, [engine]: { ...(prev[engine] || {}), [key]: val } }))
  }

  const saveManualSurvey = async (engine) => {
    setManualSaving(true)
    const res = await fetch(`${API}/api/db-manual-survey/${accountId}/${engine}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(manualAnswers[engine] || {}),
    })
    const data = await res.json()
    setManualSavedAt(prev => ({ ...prev, [engine]: data.submitted_at }))
    setManualSaving(false)
  }

  const downloadScript = async (engine) => {
    const res = await fetch(`${API}/api/db-presurvey/script/${engine}`)
    const data = await res.json()
    const blob = new Blob([data.content], { type: 'text/plain' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = data.filename; a.click()
  }

  const downloadSample = async (engine) => {
    const res = await fetch(`${API}/api/db-presurvey/sample/${engine}`)
    const data = await res.json()
    const blob = new Blob([data.content], { type: 'text/markdown' })
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
    a.download = data.filename; a.click()
  }

  const uploadFile = async (engine, file) => {
    setUploading(true); setUploadMsg('')
    const form = new FormData(); form.append('file', file)
    const res = await fetch(`${API}/api/db-presurvey/upload/${accountId}/${engine}`, { method: 'POST', body: form })
    const data = await res.json()
    setUploadMsg(data.status === 'uploaded' ? `✅ 업로드 완료: ${data.path}` : '❌ 업로드 실패')
    setUploading(false)
  }

  return (
    <div style={{ background: '#0a0c14', border: '1px solid #2d3148', borderRadius: 10, padding: 16, marginTop: 12 }}>
      <div style={{ fontSize: 14, fontWeight: 700, color: '#60a5fa', marginBottom: 8 }}>🗄️ {isEn ? 'DB Pre-Survey' : 'DB 사전 서베이'}</div>
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 12 }}>
        {isEn
          ? 'DB internal info (accounts/permissions/schema/indexes) is collected by running a script on the DB Bastion host. Upload the result file here to include it in the ARB inspection.'
          : 'DB 내부 정보(계정/권한/스키마/인덱스 등)는 DB Bastion 호스트에서 스크립트를 실행하여 수집합니다.\n결과 파일을 여기에 업로드하면 ARB 점검 시 자동으로 반영됩니다.'
        }
      </div>

      {/* 엔진 선택 */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 12 }}>
        {Object.entries(info).map(([key, eng]) => (
          <button key={key} onClick={() => setSelectedEngine(selectedEngine === key ? null : key)}
            className={`btn btn-sm ${selectedEngine === key ? 'btn-primary' : 'btn-outline'}`}>
            {eng.label}
          </button>
        ))}
      </div>

      {/* 선택된 엔진 상세 */}
      {selectedEngine && info[selectedEngine] && (() => {
        const eng = info[selectedEngine]
        return (
          <div style={{ background: '#1a1d27', borderRadius: 8, padding: 14, border: '1px solid #2d3148' }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: '#e2e8f0', marginBottom: 8 }}>{eng.label} {isEn ? 'Pre-Survey' : '사전 서베이'}</div>
            <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 10 }}>{isEn ? (eng.description_en || eng.description) : eng.description}</p>

            {/* 수동 설문 폼 (위쪽) */}
            {manualSchema[selectedEngine] && (
              <div style={{ marginBottom: 14, borderBottom: '1px solid #2d3148', paddingBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                  <div>
                    <span style={{ fontSize: 12, fontWeight: 700, color: '#a78bfa' }}>
                      📋 {isEn ? 'Manual Survey' : '수동 설문'}
                    </span>
                    {manualSavedAt[selectedEngine] && (
                      <span style={{ fontSize: 10, color: '#4ade80', marginLeft: 8 }}>
                        ✅ {isEn ? `Saved (${manualSavedAt[selectedEngine].slice(0,16)})` : `저장됨 (${manualSavedAt[selectedEngine].slice(0,16)})`}
                      </span>
                    )}
                  </div>
                  {accountId.length === 12 && (
                    <button className="btn btn-primary btn-sm" onClick={() => saveManualSurvey(selectedEngine)} disabled={manualSaving}>
                      {manualSaving ? <span className="spinner" /> : (isEn ? '💾 Save' : '💾 저장')}
                    </button>
                  )}
                </div>
                <div style={{ fontSize: 11, color: '#64748b', marginBottom: 10 }}>
                  {isEn
                    ? 'Answer questions that cannot be automatically collected by the script.'
                    : '스크립트로 자동 수집할 수 없는 항목을 직접 입력해주세요.'}
                </div>
                {manualSchema[selectedEngine].sections.map(sec => (
                  <div key={sec.key} style={{ marginBottom: 6 }}>
                    <div onClick={() => setOpenManualSec(openManualSec === sec.key ? null : sec.key)}
                      style={{ padding: '7px 10px', background: '#0f1117', borderRadius: 6, cursor: 'pointer',
                        display: 'flex', justifyContent: 'space-between', border: '1px solid #2d3148' }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: openManualSec === sec.key ? '#a78bfa' : '#94a3b8' }}>
                        {isEn ? (sec.label_en || sec.label) : sec.label}
                      </span>
                      <span style={{ color: '#475569' }}>{openManualSec === sec.key ? '▾' : '▸'}</span>
                    </div>
                    {openManualSec === sec.key && (
                      <div style={{ padding: '10px 12px', background: '#0f1117', borderRadius: '0 0 6px 6px',
                        borderLeft: '1px solid #2d3148', borderRight: '1px solid #2d3148', borderBottom: '1px solid #2d3148' }}>
                        {sec.fields.map(f => {
                          const curVal = (manualAnswers[selectedEngine] || {})[f.key]
                          return (
                            <div key={f.key} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                              <label style={{ fontSize: 11, color: '#94a3b8', flex: 1, minWidth: 0 }}>
                                {isEn ? (f.label_en || f.label) : f.label}
                              </label>
                              {f.type === 'bool' && (
                                <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                                  {['true', 'false'].map(v => (
                                    <button key={v} onClick={() => setManualField(selectedEngine, f.key, v === 'true')}
                                      style={{ padding: '3px 10px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600,
                                        background: curVal === (v === 'true') ? (v === 'true' ? '#14532d' : '#450a0a') : '#2d3148',
                                        color: curVal === (v === 'true') ? (v === 'true' ? '#4ade80' : '#f87171') : '#64748b' }}>
                                      {v === 'true' ? 'Y' : 'N'}
                                    </button>
                                  ))}
                                </div>
                              )}
                              {f.type === 'select' && (
                                <select value={curVal || ''} onChange={e => setManualField(selectedEngine, f.key, e.target.value)}
                                  style={{ background: '#0a0c14', border: '1px solid #2d3148', borderRadius: 4, padding: '3px 8px',
                                    color: '#e2e8f0', fontSize: 11, flexShrink: 0 }}>
                                  <option value="">{isEn ? 'Select' : '선택'}</option>
                                  {f.options.map(o => <option key={o}>{o}</option>)}
                                </select>
                              )}
                            </div>
                          )
                        })}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* 스크립트 실행 안내 (아래쪽) */}
            {(eng.has_script || eng.guide_en?.length > 0) && (
              <div style={{ background: '#0f1117', borderRadius: 6, padding: 12, marginBottom: 10 }}>
                <div style={{ fontSize: 11, color: '#7c6af7', fontWeight: 600, marginBottom: 6 }}>{isEn ? '📋 Script Guide' : '📋 스크립트 실행 안내'}</div>
                {isEn
                  ? (eng.guide_en || []).map((line, i) => (
                      <div key={i} style={{ fontSize: 11, color: '#64748b', lineHeight: 1.6 }}>{line}</div>
                    ))
                  : eng.header_lines.filter(l => l.trim()).map((line, i) => (
                      <div key={i} style={{ fontSize: 11, color: '#64748b', lineHeight: 1.6 }}>{line}</div>
                    ))
                }
              </div>
            )}

            {/* 단계별 안내 */}
            <div style={{ background: '#0f1117', borderRadius: 6, padding: 12, marginBottom: 10 }}>
              <div style={{ fontSize: 11, color: '#4ade80', fontWeight: 600, marginBottom: 8 }}>{isEn ? '🚀 Steps' : '🚀 실행 순서'}</div>
              {[
                { n: '1', ko: 'DB Bastion 호스트에 SSH 접속 (mysql client가 설치된 서버)', en: 'SSH into DB Bastion host (server with mysql client installed)' },
                { n: '2', ko: eng.has_script ? '아래 스크립트 다운로드 버튼으로 스크립트를 받아 Bastion에 업로드' : '아래 샘플 파일 형식에 맞게 수동으로 작성',
                          en: eng.has_script ? 'Download the script below and upload to Bastion' : 'Manually write the file following the sample format below' },
                { n: '3', ko: eng.has_script ? 'chmod +x aurora-mysql-survey.sh && ./aurora-mysql-survey.sh' : '샘플 형식을 참고하여 .md 파일 작성',
                          en: eng.has_script ? 'chmod +x aurora-mysql-survey.sh && ./aurora-mysql-survey.sh' : 'Write .md file following sample format', color: '#a78bfa' },
                { n: '4', ko: '생성된 .md 파일을 다운로드하여 아래 업로드', en: 'Download the generated .md file and upload below' },
              ].map(({ n, ko, en, color }) => (
                <div key={n} style={{ display: 'flex', gap: 8, marginBottom: 6, alignItems: 'flex-start' }}>
                  <span style={{ background: '#7c6af7', color: '#fff', width: 18, height: 18, borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 700, flexShrink: 0 }}>{n}</span>
                  <span style={{ fontSize: 11, color: color || '#e2e8f0', lineHeight: 1.5 }}>{isEn ? en : ko}</span>
                </div>
              ))}
            </div>

            {/* 버튼 */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
              {eng.has_script && (
                <button className="btn btn-outline btn-sm" onClick={() => downloadScript(selectedEngine)}
                  style={{ borderColor: '#4ade80', color: '#4ade80' }}>
                  {isEn ? '⬇ Download Script (.sh)' : '⬇ 스크립트 다운로드 (.sh)'}
                </button>
              )}
              {eng.has_sample && (
                <button className="btn btn-outline btn-sm" onClick={() => downloadSample(selectedEngine)}
                  style={{ borderColor: '#60a5fa', color: '#60a5fa' }}>
                  {isEn ? '📄 View Sample (.md)' : '📄 샘플 파일 보기 (.md)'}
                </button>
              )}
              {accountId.length === 12 && (
                <>
                  <button className="btn btn-primary btn-sm" onClick={() => fileRef.current?.click()} disabled={uploading}>
                    {uploading ? <span className="spinner" /> : (isEn ? '⬆ Upload Result File' : '⬆ 결과 파일 업로드')}
                  </button>
                  <input ref={fileRef} type="file" accept=".md,.txt" style={{ display: 'none' }}
                    onChange={e => { if (e.target.files[0]) uploadFile(selectedEngine, e.target.files[0]); e.target.value = '' }} />
                </>
              )}
            </div>
            {uploadMsg && <div style={{ fontSize: 11, color: uploadMsg.startsWith('✅') ? '#4ade80' : '#f87171', marginBottom: 8 }}>{uploadMsg}</div>}
          </div>
        )
      })()}

      {/* 업로드된 파일 목록 */}
      {uploadedFiles.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>📁 {isEn ? 'Uploaded Files' : '업로드된 파일'}</div>
          {uploadedFiles.map(f => (
            <div key={f.name} style={{ fontSize: 11, color: '#94a3b8', padding: '3px 0',
              display: 'flex', justifyContent: 'space-between' }}>
              <span>📄 {f.name}</span>
              <span style={{ color: '#475569' }}>{f.uploaded_at.slice(0, 16)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}


// ── Survey Panel ──────────────────────────────────────────────────────────────
function SurveyPanel({ accountId, onClose }) {
  const lang = useContext(LangContext)
  const isEn = lang === 'en'
  const [schema, setSchema] = useState({})
  const [answers, setAnswers] = useState({})
  const [savedAt, setSavedAt] = useState(null)
  const [saving, setSaving] = useState(false)
  const [openSec, setOpenSec] = useState(null)

  useEffect(() => {
    if (!accountId) return
    // 스키마 + 기존 서베이 병렬 로드
    Promise.all([
      fetch(`${API}/api/survey/schema`).then(r => r.json()),
      fetch(`${API}/api/survey/${accountId}`).then(r => r.json()),
    ]).then(([sc, sv]) => {
      setSchema(sc)
      setAnswers(sv.data || {})
      setSavedAt(sv.submitted_at)
      if (Object.keys(sc).length > 0) setOpenSec(Object.keys(sc)[0])
    })
  }, [accountId])

  const set = (key, val) => setAnswers(prev => ({ ...prev, [key]: val }))

  const save = async () => {
    setSaving(true)
    const res = await fetch(`${API}/api/survey/${accountId}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(answers),
    })
    const data = await res.json()
    setSavedAt(data.submitted_at)
    setSaving(false)
  }

  return (
    <div style={{ background: '#0a0c14', border: '1px solid #2d3148', borderRadius: 10, padding: 16, marginTop: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <span style={{ fontSize: 14, fontWeight: 700, color: '#a78bfa' }}>📋 {isEn ? 'Pre-Survey' : '사전 서베이'}</span>
          <span style={{ fontSize: 11, color: '#475569', marginLeft: 8 }}>{isEn ? 'Account' : '계정'}: {accountId}</span>
          {savedAt && <span style={{ fontSize: 10, color: '#4ade80', marginLeft: 8 }}>✅ {isEn ? `Saved (${savedAt.slice(0,16)})` : `저장됨 (${savedAt.slice(0,16)})`}</span>}
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <button className="btn btn-primary btn-sm" onClick={save} disabled={saving}>
            {saving ? <span className="spinner" /> : (isEn ? '💾 Save' : '💾 저장')}
          </button>
          <button className="btn btn-outline btn-sm" onClick={onClose}>✕</button>
        </div>
      </div>
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 10 }}>
        {isEn
          ? 'Enter items that are difficult for the Agent to judge automatically. Once saved, they will be automatically applied during inspection.'
          : 'Agent가 자동 판단하기 어려운 항목을 사전에 입력합니다. 저장 후 점검 시 자동 반영됩니다.'
        }
      </div>
      {Object.entries(schema).map(([secKey, sec]) => (
        <div key={secKey} style={{ marginBottom: 6 }}>
          <div onClick={() => setOpenSec(openSec === secKey ? null : secKey)}
            style={{ padding: '7px 10px', background: '#1a1d27', borderRadius: 6, cursor: 'pointer',
              display: 'flex', justifyContent: 'space-between', border: '1px solid #2d3148' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: openSec === secKey ? '#a78bfa' : '#94a3b8' }}>{isEn ? (sec.label_en || sec.label) : sec.label}</span>
            <span style={{ color: '#475569' }}>{openSec === secKey ? '▾' : '▸'}</span>
          </div>
          {openSec === secKey && (
            <div style={{ padding: '10px 12px', background: '#1a1d27', borderRadius: '0 0 6px 6px',
              borderLeft: '1px solid #2d3148', borderRight: '1px solid #2d3148', borderBottom: '1px solid #2d3148' }}>
              {sec.fields.map(f => (
                <div key={f.key} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                  <label style={{ fontSize: 12, color: '#94a3b8', flex: 1, minWidth: 0 }}>{isEn ? (f.label_en || f.label) : f.label}</label>
                  {f.type === 'bool' && (
                    <div style={{ display: 'flex', gap: 4, flexShrink: 0 }}>
                      {['true', 'false'].map(v => (
                        <button key={v} onClick={() => set(f.key, v === 'true')}
                          style={{ padding: '3px 10px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 11, fontWeight: 600,
                            background: answers[f.key] === (v === 'true') ? (v === 'true' ? '#14532d' : '#450a0a') : '#2d3148',
                            color: answers[f.key] === (v === 'true') ? (v === 'true' ? '#4ade80' : '#f87171') : '#64748b' }}>
                          {v === 'true' ? 'Y' : 'N'}
                        </button>
                      ))}
                    </div>
                  )}
                  {f.type === 'select' && (
                    <select value={answers[f.key] || ''} onChange={e => set(f.key, e.target.value)}
                      style={{ background: '#0f1117', border: '1px solid #2d3148', borderRadius: 4, padding: '3px 8px',
                        color: '#e2e8f0', fontSize: 11, flexShrink: 0 }}>
                      <option value="">{isEn ? 'Select' : '선택'}</option>
                      {f.options.map(o => <option key={o}>{o}</option>)}
                    </select>
                  )}
                  {f.type === 'text' && (
                    <input value={answers[f.key] || ''} onChange={e => set(f.key, e.target.value)}
                      style={{ background: '#0f1117', border: '1px solid #2d3148', borderRadius: 4, padding: '3px 8px',
                        color: '#e2e8f0', fontSize: 11, width: 160, flexShrink: 0 }} />
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}


// DB 엔진 목록
const DB_ENGINES = [
  { id: 'aurora-mysql',    label: 'Aurora MySQL' },
  { id: 'aurora-postgres', label: 'Aurora PostgreSQL' },
  { id: 'rds-mysql',       label: 'RDS MySQL' },
  { id: 'rds-postgres',    label: 'RDS PostgreSQL' },
  { id: 'dynamodb',        label: 'DynamoDB' },
  { id: 'elasticache',     label: 'ElastiCache' },
]

function RunPage({ runState, setRunState }) {
  const t = useLang()
  const lang = useContext(LangContext)
  const isEn = lang === 'en'
  const [form, setForm] = useState({ service_name: '', account_id: '', region: 'ap-northeast-2', auto_region: false, scope: 'all' })
  const [selectedRegions, setSelectedRegions] = useState([])  // 멀티 리전
  const [multiMode, setMultiMode] = useState(false)
  const [selectedEngines, setSelectedEngines] = useState(DB_ENGINES.map(e => e.id))  // 기본 전체 선택
  const [showSurvey, setShowSurvey] = useState(false)
  const [showDBSurvey, setShowDBSurvey] = useState(false)
  const [surveyInfo, setSurveyInfo] = useState(null)
  const { logs, job, running, jobId } = runState
  const setLogs = (v) => setRunState(s => ({ ...s, logs: typeof v === 'function' ? v(s.logs) : v }))
  const setJob = (v) => setRunState(s => ({ ...s, job: v }))
  const setRunning = (v) => setRunState(s => ({ ...s, running: v }))
  const setJobId = (v) => setRunState(s => ({ ...s, jobId: v }))
  const logRef = useRef(null)

  // 계정 ID 입력 시 서베이 상태 조회
  useEffect(() => {
    if (!form.account_id || form.account_id.length !== 12) { setSurveyInfo(null); return }
    fetch(`${API}/api/survey/${form.account_id}`).then(r => r.json()).then(d => {
      setSurveyInfo(d.submitted_at ? d : null)
    }).catch(() => setSurveyInfo(null))
  }, [form.account_id])

  const toggleRegion = (r) => setSelectedRegions(prev =>
    prev.includes(r) ? prev.filter(x => x !== r) : [...prev, r])

  const submit = async () => {
    if (!form.service_name || !form.account_id) return
    if (form.scope === 'database' && selectedEngines.length === 0) return
    setRunning(true); setLogs([]); setJob(null)
    const engines = form.scope === 'database' ? selectedEngines : []
    let payload
    if (form.auto_region) {
      payload = { service_name: form.service_name, account_id: form.account_id, region: 'auto', scope: form.scope, engines }
    } else if (multiMode && selectedRegions.length > 0) {
      payload = { service_name: form.service_name, account_id: form.account_id, region: selectedRegions[0], regions: selectedRegions, scope: form.scope, engines }
    } else {
      payload = { service_name: form.service_name, account_id: form.account_id, region: form.region, scope: form.scope, engines }
    }
    const res = await fetch(`${API}/api/arb/run`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
    const data = await res.json()
    const firstJobId = data.job_id
    const allJobIds = data.job_ids || [firstJobId]
    setJobId(firstJobId)

    if (allJobIds.length > 1) {
      setLogs([`🌐 ${allJobIds.length}개 리전 순차 점검 시작: ${selectedRegions.join(', ')}\n`])
    }

    const es = new EventSource(`${API}/api/arb/stream/${firstJobId}`)
    es.onmessage = (e) => {
      const d = JSON.parse(e.data)
      if (d.line !== undefined) setLogs(prev => [...prev, d.line])
      if (d.status) {
        setRunning(false); es.close(); fetchJob(firstJobId)
        const msg = d.status === 'done'
          ? allJobIds.length > 1
            ? `\n✅ 1번째 리전 완료. 나머지 ${allJobIds.length - 1}개 리전은 백그라운드에서 순차 실행됩니다.\n`
            : '\n✅ 점검이 완료되었습니다. 히스토리/리포트 탭에서 결과를 확인하세요.\n'
          : '\n❌ 점검 중 오류가 발생했습니다.\n'
        setLogs(prev => [...prev, msg])
      }
    }
    es.onerror = () => { setRunning(false); es.close() }
  }

  const fetchJob = async (id) => {
    const res = await fetch(`${API}/api/arb/jobs/${id}`)
    setJob(await res.json())
  }

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  return (
    <div>
      <div className="page-title">{t('run')}</div>
      <div className="card">
        {/* 점검 범위 선택 */}
        <div className="form-group" style={{ marginBottom: 16 }}>
          <label>{t('scopeLabel')}</label>
          <div style={{ display: 'flex', gap: 8, marginTop: 6 }}>
            <button
              className={`btn btn-sm ${form.scope === 'all' ? 'btn-primary' : 'btn-outline'}`}
              onClick={() => setForm(f => ({ ...f, scope: 'all' }))}>
              🔍 {t('scopeAll')}
            </button>
            <button
              className={`btn btn-sm ${form.scope === 'database' ? 'btn-primary' : 'btn-outline'}`}
              style={form.scope === 'database' ? { background: '#0ea5e9', borderColor: '#0ea5e9' } : {}}
              onClick={() => { setForm(f => ({ ...f, scope: 'database' })); setSelectedEngines(DB_ENGINES.map(e => e.id)) }}>
              🗄️ {t('scopeDatabase')}
            </button>
          </div>
          {form.scope === 'database' && (
            <div style={{ marginTop: 10, padding: '10px 12px', background: '#0f1117', border: '1px solid #1e3a5f', borderRadius: 8 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                <span style={{ fontSize: 12, color: '#38bdf8' }}>🗄️ {t('enginesLabel')}</span>
                <button className="btn btn-outline btn-sm" style={{ fontSize: 10 }}
                  onClick={() => setSelectedEngines(
                    selectedEngines.length === DB_ENGINES.length ? [] : DB_ENGINES.map(e => e.id)
                  )}>
                  {selectedEngines.length === DB_ENGINES.length ? t('enginesNone') : t('enginesAll')}
                </button>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 16px' }}>
                {DB_ENGINES.map(e => (
                  <label key={e.id} style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 13,
                    color: selectedEngines.includes(e.id) ? '#7dd3fc' : '#475569' }}>
                    <input type="checkbox"
                      checked={selectedEngines.includes(e.id)}
                      onChange={() => setSelectedEngines(prev =>
                        prev.includes(e.id) ? prev.filter(x => x !== e.id) : [...prev, e.id]
                      )} />
                    {e.label}
                  </label>
                ))}
              </div>
              {selectedEngines.length === 0 && (
                <div style={{ marginTop: 6, fontSize: 11, color: '#f87171' }}>⚠️ {isEn ? 'Select at least 1 engine.' : '최소 1개 이상 선택하세요.'}</div>
              )}
              <div style={{ marginTop: 8, fontSize: 11, color: '#38bdf8' }}>💡 {t('scopeDatabaseDesc')}</div>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
          <h2 style={{ margin: 0 }}>{t('serviceName')}</h2>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            {form.account_id.length !== 12 && (
              <span style={{ fontSize: 11, color: '#475569' }}>
                {isEn ? '⚠ Enter Account ID to enable pre-survey' : '⚠ 사전 서베이를 진행하려면 Account ID를 입력하세요'}
              </span>
            )}
            <button
              className="btn btn-outline btn-sm"
              disabled={form.account_id.length !== 12}
              style={{
                borderColor: form.account_id.length === 12 ? (surveyInfo ? '#4ade80' : '#7c6af7') : '#2d3148',
                color: form.account_id.length === 12 ? (surveyInfo ? '#4ade80' : '#7c6af7') : '#475569',
                cursor: form.account_id.length !== 12 ? 'not-allowed' : 'pointer',
                opacity: form.account_id.length !== 12 ? 0.5 : 1,
              }}
              onClick={() => form.account_id.length === 12 && setShowSurvey(v => !v)}>
              📋 {isEn ? `Pre-Survey${surveyInfo ? ' ✅' : ''}` : `사전 서베이${surveyInfo ? ' ✅' : ''}`}
            </button>
            <button
              className="btn btn-outline btn-sm"
              disabled={form.account_id.length !== 12}
              style={{
                borderColor: form.account_id.length === 12 ? '#60a5fa' : '#2d3148',
                color: form.account_id.length === 12 ? '#60a5fa' : '#475569',
                cursor: form.account_id.length !== 12 ? 'not-allowed' : 'pointer',
                opacity: form.account_id.length !== 12 ? 0.5 : 1,
              }}
              onClick={() => form.account_id.length === 12 && setShowDBSurvey(v => !v)}>
              🗄️ {isEn ? 'DB Pre-Survey' : 'DB 사전 서베이'}
            </button>
          </div>
        </div>
        {showSurvey && form.account_id.length === 12 && (
          <SurveyPanel accountId={form.account_id}
            onClose={() => { setShowSurvey(false); fetch(`${API}/api/survey/${form.account_id}`).then(r=>r.json()).then(d=>setSurveyInfo(d.submitted_at?d:null)) }} />
        )}
        {showDBSurvey && form.account_id.length === 12 && (
          <DBPreSurveyPanel accountId={form.account_id} />
        )}
        <div className="form-row">
          <div className="form-group">
            <label>{t('serviceName')}</label>
            <input placeholder="예: spay.global.dev" value={form.service_name}
              onChange={e => setForm(f => ({ ...f, service_name: e.target.value }))} />
          </div>
          <div className="form-group">
            <label>{t('accountId')}</label>
            <input placeholder="예: 764668829134" value={form.account_id}
              onChange={e => setForm(f => ({ ...f, account_id: e.target.value }))} />
          </div>
          <div className="form-group" style={{ maxWidth: 240 }}>
            <label>{t('region')}</label>
            {/* 단일/멀티 토글 */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 6 }}>
              <button className={`btn btn-sm ${!multiMode && !form.auto_region ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => { setMultiMode(false); setForm(f => ({ ...f, auto_region: false })) }}>단일</button>
              <button className={`btn btn-sm ${multiMode ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => { setMultiMode(true); setForm(f => ({ ...f, auto_region: false })) }}>멀티</button>
              <button className={`btn btn-sm ${form.auto_region ? 'btn-primary' : 'btn-outline'}`}
                onClick={() => { setForm(f => ({ ...f, auto_region: !f.auto_region })); setMultiMode(false) }}>자동</button>
            </div>
            {!multiMode && !form.auto_region && (
              <select value={form.region} onChange={e => setForm(f => ({ ...f, region: e.target.value }))}>
                {REGIONS.map(r => <option key={r}>{r}</option>)}
              </select>
            )}
            {multiMode && (
              <div style={{ maxHeight: 160, overflowY: 'auto', border: '1px solid #2d3148', borderRadius: 6, padding: 8, background: '#0f1117' }}>
                <div style={{ marginBottom: 4 }}>
                  <button className="btn btn-outline btn-sm" style={{ fontSize: 10 }}
                    onClick={() => setSelectedRegions(selectedRegions.length === REGIONS.length ? [] : [...REGIONS])}>
                    {selectedRegions.length === REGIONS.length ? '전체 해제' : '전체 선택'}
                  </button>
                </div>
                {REGIONS.map(r => (
                  <label key={r} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0', cursor: 'pointer', fontSize: 12, color: selectedRegions.includes(r) ? '#a78bfa' : '#94a3b8' }}>
                    <input type="checkbox" checked={selectedRegions.includes(r)} onChange={() => toggleRegion(r)} />
                    {r}
                  </label>
                ))}
              </div>
            )}
            {form.auto_region && <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>⚠️ 전체 리전 자동 탐지</div>}
            {multiMode && selectedRegions.length > 0 && (
              <div style={{ fontSize: 11, color: '#7c6af7', marginTop: 4 }}>선택: {selectedRegions.length}개 리전</div>
            )}
          </div>
          <button className="btn btn-primary" onClick={submit}
            disabled={running || !form.service_name || !form.account_id || (multiMode && selectedRegions.length === 0)}>
            {running ? <><span className="spinner" />{t('inspecting')}</> : t('startInspection')}
          </button>
        </div>
        {form.auto_region && (
          <div style={{ marginTop: 10, fontSize: 12, color: '#64748b' }}>
            ⚠️ 전체 리전 탐지: EC2/RDS가 존재하는 리전을 자동으로 찾아 점검합니다. 시간이 더 소요될 수 있습니다.
          </div>
        )}
      </div>

      {(logs.length > 0 || running) && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h2>{t('realtime')}</h2>
            {job && <StatusBadge status={job.status} />}
          </div>
          <div className="log-box" ref={logRef}>
            {logs.map((l, i) => <span key={i} className="log-line">{l}</span>)}
            {running && <span className="log-line" style={{ color: '#7c6af7' }}>▌</span>}
          </div>
        </div>
      )}
    </div>
  )
}

// ── History Page ──────────────────────────────────────────────────────────────
function HistoryPage({ onViewReport }) {
  const t = useLang()
  const [jobs, setJobs] = useState([])
  const [summaries, setSummaries] = useState({})
  const [logJob, setLogJob] = useState(null)
  const [logText, setLogText] = useState('')

  useEffect(() => {
    const load = async () => {
      const data = await fetch(`${API}/api/arb/jobs`).then(r => r.json())
      setJobs(data)
      // done 상태 job의 summary 병렬 로드
      const doneJobs = data.filter(j => j.status === 'done')
      const results = await Promise.all(
        doneJobs.map(j => fetch(`${API}/api/arb/jobs/${j.job_id}/summary`).then(r => r.json()).then(s => [j.job_id, s]))
      )
      setSummaries(Object.fromEntries(results))
    }
    load()
    const t = setInterval(load, 5000)
    return () => clearInterval(t)
  }, [])

  const viewLog = async (j) => {
    setLogJob(j)
    setLogText('⏳ 로딩 중...')
    try {
      const res = await fetch(`${API}/api/arb/jobs/${j.job_id}/log`)
      const data = await res.json()
      const log = data.log || '(로그 없음)'
      // 너무 긴 로그는 마지막 50000자만 표시
      setLogText(log.length > 50000 ? '...(앞 내용 생략)...\n' + log.slice(-50000) : log)
    } catch (e) {
      setLogText(`로그 로딩 실패: ${e.message}`)
    }
  }

  return (
    <div>
      <div className="page-title">{t('history')}</div>
      <div className="card">
        {jobs.length === 0 ? <div className="empty">{t('noHistory')}</div> : (
          <table className="table">
            <thead>
              <tr>
                <th>{t('serviceName')}</th><th>{t('accountId')}</th><th>{t('region')}</th>
                <th>{t('statusCol')}</th><th>{t('resultCol')}</th><th>{t('startTime')}</th><th>{t('endTime')}</th><th></th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(j => {
                const s = summaries[j.job_id]
                return (
                  <tr key={j.job_id}>
                    <td>{j.service_name}</td>
                    <td style={{ fontFamily: 'monospace', fontSize: 12 }}>{j.account_id}</td>
                    <td>{j.region}</td>
                    <td><StatusBadge status={j.status} /></td>
                    <td>
                      {s && (s.pass !== undefined) ? (
                        <span style={{ fontSize: 12 }}>
                          <span style={{ color: '#4ade80' }}>✅{s.pass}</span>
                          {' / '}
                          <span style={{ color: '#f87171' }}>❌{s.fail}</span>
                          {' / '}
                          <span style={{ color: '#94a3b8' }}>N/A {s.critical !== undefined ? `(C:${s.critical})` : ''}</span>
                        </span>
                      ) : <span style={{ fontSize: 12, color: '#475569' }}>-</span>}
                    </td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>{j.started_at ? new Date(j.started_at).toLocaleString(t('locale')) : '-'}</td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>{j.finished_at ? new Date(j.finished_at).toLocaleString(t('locale')) : '-'}</td>
                    <td style={{ display: 'flex', gap: 6 }}>
                      <button className="btn btn-outline btn-sm" onClick={() => viewLog(j)}>{t('logBtn')}</button>
                      {j.status === 'done' && (
                        <button className="btn btn-primary btn-sm" onClick={() => onViewReport(j)}>{t('reportBtn')}</button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
      {logJob && (
        <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.7)',
          zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}
          onClick={(e) => e.target === e.currentTarget && setLogJob(null)}>
          <div className="card" style={{ width: '80vw', maxWidth: 900, maxHeight: '80vh', display: 'flex', flexDirection: 'column', padding: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 16px', borderBottom: '1px solid #2d3148' }}>
              <h2 style={{ fontSize: 14 }}>{logJob.service_name} ({logJob.region}) 실행 로그</h2>
              <button className="btn btn-outline btn-sm" onClick={() => setLogJob(null)}>✕ 닫기</button>
            </div>
            <div className="log-box" style={{ flex: 1, margin: 12, maxHeight: 'calc(80vh - 60px)', overflowY: 'auto' }}>{logText}</div>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Reports Page ──────────────────────────────────────────────────────────────
function ReportsPage({ job, onGuide }) {
  const lang = useContext(LangContext)
  const t = useLang()
  const [failItems, setFailItems] = useState([])
  const [summaryGuide, setSummaryGuide] = useState([])  // summary.md 카테고리별 가이드
  const [showGuidePanel, setShowGuidePanel] = useState(false)
  const [guideCategory, setGuideCategory] = useState(null)  // 선택된 카테고리
  const [tree, setTree] = useState([])
  const [openService, setOpenService] = useState(null)
  const [openDate, setOpenDate] = useState(null)
  const [selected, setSelected] = useState(null)
  const [content, setContent] = useState('')

  useEffect(() => {
    const classify = (files) => {
      const summary = files.find(f => f.name === 'summary.md') || null
      const infra = files.filter(f => ['architecture.md','devops.md','operation.md','service-stability.md','system-stability.md','diagram.md','improvement-plan.md'].includes(f.name))
      const database = files.filter(f => !['summary.md','architecture.md','devops.md','operation.md','service-stability.md','system-stability.md','diagram.md','improvement-plan.md'].includes(f.name))
      return { summary, infra, database }
    }
    if (job) {
      fetch(`${API}/api/arb/jobs/${job.job_id}/reports`).then(r => r.json()).then(files => {
        if (files.length > 0) {
          const date = files[0].path.split('/')[2] || job.finished_at?.slice(0, 10) || ''
          const { summary, infra, database } = classify(files)
          setTree([{ service: job.service_name, dates: [{ date, summary, infra, database }] }])
          setOpenService(job.service_name)
          setOpenDate(date)
        }
      })
    } else {
      fetch(`${API}/api/arb/reports/tree`).then(r => r.json()).then(data => {
        setTree(data)
        if (data.length > 0) {
          const firstService = data[0]
          setOpenService(firstService.service)
          if (firstService.dates.length > 0) {
            const firstDate = firstService.dates[0]
            setOpenDate(firstDate.date)
            // 최근 summary.md 자동 로드
            if (firstDate.summary) {
              loadReport(firstDate.summary, lang)
            }
          }
        }
      })
    }
    setSelected(null); setContent('')
  }, [job])

  const loadReport = async (r, targetLang = lang) => {
    setSelected(r)
    setContent('⏳ Translating...')
    setFailItems([])
    setSummaryGuide([])
    setShowGuidePanel(false)
    setGuideCategory(null)
    const res = await fetch(`${API}/api/arb/reports/content?path=${encodeURIComponent(r.path)}&lang=${targetLang}`)
    const data = await res.json()
    setContent(data.content)
    // summary.md이면 카테고리별 가이드 로드
    if (r.name === 'summary.md') {
      fetch(`${API}/api/guide/summary-fails?path=${encodeURIComponent(r.path)}`)
        .then(res => res.json()).then(setSummaryGuide).catch(() => {})
    }
    // 기타 리포트 FAIL 항목
    fetch(`${API}/api/guide/report-fails?path=${encodeURIComponent(r.path)}`)
      .then(res => res.json()).then(setFailItems).catch(() => {})
  }

  // 언어 변경 시 현재 열린 리포트 재번역
  useEffect(() => {
    if (selected) loadReport(selected, lang)
  }, [lang])

  const download = () => {
    const blob = new Blob([content], { type: 'text/markdown' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = selected.name
    a.click()
  }

  const currentFiles = tree
    .find(s => s.service === openService)
    ?.dates.find(d => d.date === openDate)
    ?.files || []

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <div className="page-title" style={{ margin: 0 }}>{t('reportTitle')}</div>
        {job && (
          <span style={{ fontSize: 13, color: '#7c6af7', background: '#1e1a3a', padding: '3px 10px', borderRadius: 4 }}>
            {job.service_name} · {job.region} · {new Date(job.finished_at).toLocaleString(t('locale'))}
          </span>
        )}
      </div>
      <div className="split-with-chat">
        <div className="split-main">
        <div className="split-left">
          <div className="card" style={{ padding: '12px' }}>
            {/* 프로젝트 목록 */}
            {tree.map(s => (
              <div key={s.service}>
                <div onClick={() => { setOpenService(openService === s.service ? null : s.service); setOpenDate(null) }}
                  style={{ padding: '8px 10px', cursor: 'pointer', borderRadius: 6, display: 'flex', justifyContent: 'space-between',
                    background: openService === s.service ? '#252840' : 'transparent', color: '#e2e8f0', fontSize: 14, fontWeight: 600 }}>
                  <span>📁 {s.service}</span>
                  <span style={{ color: '#64748b' }}>{openService === s.service ? '▾' : '▸'}</span>
                </div>
                {openService === s.service && s.dates.map(d => {
                  const fileCount = (d.summary ? 1 : 0) + (d.infra?.length || 0) + (d.database?.length || 0)
                  return (
                  <div key={d.date}>
                    <div onClick={() => setOpenDate(openDate === d.date ? null : d.date)}
                      style={{ padding: '6px 10px 6px 24px', cursor: 'pointer', borderRadius: 6, display: 'flex', justifyContent: 'space-between',
                        background: openDate === d.date ? '#1e2235' : 'transparent', color: '#94a3b8', fontSize: 13 }}>
                      <span>📅 {d.date}</span>
                      <span style={{ color: '#475569' }}>{fileCount}개</span>
                    </div>
                    {openDate === d.date && (
                      <div style={{ paddingLeft: 8 }}>
                        {/* Summary - 최상단 강조 */}
                        {d.summary && (
                          <div onClick={() => loadReport(d.summary)}
                            style={{ padding: '6px 10px', cursor: 'pointer', borderRadius: 6, margin: '4px 0',
                              background: selected?.path === d.summary.path ? '#2a1f5e' : '#1e1a3a',
                              border: `1px solid ${selected?.path === d.summary.path ? '#7c6af7' : '#3d3660'}`,
                              display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span style={{ fontSize: 14 }}>📊</span>
                            <span style={{ fontSize: 12, fontWeight: 700, color: selected?.path === d.summary.path ? '#a78bfa' : '#c4b5fd' }}>
                              summary.md
                            </span>
                          </div>
                        )}
                        {/* Infra 그룹 */}
                        {d.infra?.length > 0 && (
                          <div style={{ margin: '6px 0 2px' }}>
                            <div style={{ fontSize: 10, color: '#475569', padding: '2px 6px', fontWeight: 700, letterSpacing: '0.05em' }}>🏗️ INFRA</div>
                            {d.infra.map(f => (
                              <div key={f.path} onClick={() => loadReport(f)}
                                style={{ padding: '4px 8px 4px 20px', cursor: 'pointer', borderRadius: 4, fontSize: 12,
                                  color: selected?.path === f.path ? '#7c6af7' : '#64748b',
                                  background: selected?.path === f.path ? '#1e1a3a' : 'transparent' }}>
                                {f.name}
                              </div>
                            ))}
                          </div>
                        )}
                        {/* Database 그룹 */}
                        {d.database?.length > 0 && (
                          <div style={{ margin: '6px 0 2px' }}>
                            <div style={{ fontSize: 10, color: '#475569', padding: '2px 6px', fontWeight: 700, letterSpacing: '0.05em' }}>🗄️ DATABASE</div>
                            {d.database.map(f => (
                              <div key={f.path} onClick={() => loadReport(f)}
                                style={{ padding: '4px 8px 4px 20px', cursor: 'pointer', borderRadius: 4, fontSize: 12,
                                  color: selected?.path === f.path ? '#7c6af7' : '#64748b',
                                  background: selected?.path === f.path ? '#1e1a3a' : 'transparent' }}>
                                {f.name}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  )
                })}
              </div>
            ))}
            {tree.length === 0 && <div className="empty">리포트 없음</div>}
          </div>
        </div>
        <div className="split-right">
          {selected ? (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: selected.name === 'summary.md' && summaryGuide.length > 0 ? 8 : 16 }}>
                <div style={{ fontSize: 14, color: '#94a3b8' }}>{selected.path}</div>
                <div style={{ display: 'flex', gap: 8 }}>
                  {failItems.length > 0 && selected.name !== 'summary.md' && (
                    <button className="btn btn-outline btn-sm"
                      style={{ borderColor: '#7c6af7', color: '#7c6af7' }}
                      onClick={() => setShowGuidePanel(v => !v)}>
                      📖 가이드 ({failItems.length})
                    </button>
                  )}
                  <button className="btn btn-outline btn-sm" onClick={download}>{t('download')}</button>
                </div>
              </div>

              {/* summary.md 카테고리별 [가이드] 버튼 */}
              {selected.name === 'summary.md' && summaryGuide.length > 0 && (() => {
                const CAT_EN = {
                  '아키텍처': 'Architecture', 'DevOps': 'DevOps', '운영': 'Operations',
                  '서비스 안정성': 'Service Stability', '시스템 안정성': 'System Stability',
                  'RDS PostgreSQL': 'RDS PostgreSQL', 'RDS MySQL': 'RDS MySQL',
                  'Aurora MySQL': 'Aurora MySQL', 'Aurora PostgreSQL': 'Aurora PostgreSQL', 'DynamoDB': 'DynamoDB',
                }
                return (
                <div style={{ background: '#0a0c14', borderRadius: 8, padding: 10, marginBottom: 14, border: '1px solid #2d3148' }}>
                  <div style={{ fontSize: 12, color: '#7c6af7', fontWeight: 600, marginBottom: 8 }}>
                    📖 {lang === 'en' ? 'Operations Guide by Category' : '카테고리별 운영 가이드'}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {summaryGuide.map(cat => {
                      const label = lang === 'en' ? (CAT_EN[cat.category] || cat.category) : cat.category
                      return (
                        <button key={cat.category}
                          onClick={() => setGuideCategory(guideCategory?.category === cat.category ? null : cat)}
                          style={{ padding: '5px 12px', borderRadius: 5, border: `1px solid ${guideCategory?.category === cat.category ? '#7c6af7' : '#2d3148'}`,
                            background: guideCategory?.category === cat.category ? '#1e1a3a' : 'transparent',
                            color: guideCategory?.category === cat.category ? '#a78bfa' : '#94a3b8',
                            cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
                          ❌ {label}
                        </button>
                      )
                    })}
                  </div>
                  {guideCategory && (
                    <div style={{ marginTop: 10, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {guideCategory.docs.map(doc => (
                        <div key={doc.file} onClick={() => onGuide(doc.check_id)}
                          style={{ padding: '4px 10px', borderRadius: 4, background: '#1a1d27', border: '1px solid #2d3148',
                            cursor: 'pointer', fontSize: 11, color: '#7c6af7', display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span style={{ color: '#475569', fontFamily: 'monospace', fontSize: 10 }}>{doc.check_id}</span>
                          <span style={{ color: '#94a3b8' }}>{doc.title.slice(0, 30)}{doc.title.length > 30 ? '…' : ''}</span>
                          <span style={{ color: '#4ade80' }}>→</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
                )
              })()}

              {/* 기타 리포트 FAIL 가이드 패널 */}
              {showGuidePanel && failItems.length > 0 && selected.name !== 'summary.md' && (
                <div style={{ background: '#0f1117', borderRadius: 8, padding: 12, marginBottom: 16, border: '1px solid #2d3148' }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#7c6af7', marginBottom: 8 }}>📖 FAIL 항목 Knowledge 가이드</div>
                  {failItems.map(item => (
                    <div key={item.check_id} style={{ marginBottom: 8, padding: '8px 10px', background: '#1a1d27', borderRadius: 6,
                      display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <span style={{ fontSize: 12, fontWeight: 700, color: '#f87171', marginRight: 8 }}>{item.check_id}</span>
                        <span style={{ fontSize: 12, color: '#94a3b8' }}>{item.description.slice(0, 60)}</span>
                      </div>
                      {item.guide_count > 0 && (
                        <button className="btn btn-primary btn-sm" onClick={() => onGuide(item.check_id)}>
                          가이드 {item.guide_count}건 →
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
              <div className="markdown-body">
                {(() => {
                  // summary.md 전용: 테이블 행의 카테고리-FAIL 클릭 처리
                  const CAT_TO_GUIDE = {
                    '아키텍처': ['ARCH-011','ARCH-010','ARCH-014','ARCH-015','ARCH-019','ARCH-022','ARCH-023','ARCH-026','ARCH-027','ARCH-028','ARCH-029','ARCH-031'],
                    'architecture': ['ARCH-011','ARCH-010','ARCH-014','ARCH-015','ARCH-019','ARCH-026','ARCH-027','ARCH-028','ARCH-029'],
                    'devops': ['DEV-001','DEV-005','DEV-011','DEV-012'],
                    '운영': ['OPS-002','OPS-006','OPS-007','OPS-011','OPS-012','OPS-013'],
                    'operation': ['OPS-002','OPS-006','OPS-007','OPS-011'],
                    '서비스 안정성': ['SYS-001','SYS-002','SYS-003','SYS-004'],
                    'service-stability': ['SYS-001','SYS-002','SYS-003','SYS-004'],
                    '시스템 안정성': ['SYS-003','SYS-004'],
                    'system-stability': ['SYS-003','SYS-004'],
                    'rds postgresql': ['RDS-HA-001','RDS-SEC-002','COM-BR-001','COM-BR-002','COM-NI-001','COM-AC-001'],
                    'rds mysql': ['RDS-HA-001','COM-BR-001','COM-BR-002'],
                    'aurora mysql': ['AUR-MY-003','AUR-MY-006','AUR-MON-003','COM-BR-001'],
                    'elasticache': ['COM-BR-001','COM-MON-001'],
                    'dynamodb': ['DDB-SEC-002','DDB-SEC-004'],
                  }
                  const handleFailClick = (rowText) => {
                    const lower = rowText.toLowerCase()
                    for (const [key, checks] of Object.entries(CAT_TO_GUIDE)) {
                      if (lower.includes(key)) {
                        // 첫 번째 check_id로 가이드 탭 이동
                        onGuide(checks[0])
                        return
                      }
                    }
                  }
                  return (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      rehypePlugins={[rehypeRaw]}
                      components={{
                        code({ inline, className, children }) {
                          const lang2 = (className || '').replace('language-', '')
                          if (!inline && lang2 === 'mermaid') return <MermaidBlock code={String(children).trim()} />
                          return inline ? <code className={className}>{children}</code> : <pre><code className={className}>{children}</code></pre>
                        },
                        tr({ children, ...props }) {
                          // 행 전체 텍스트 추출
                          const rowText = children?.map ? children.map(c => {
                            if (!c?.props?.children) return ''
                            const txt = c.props.children
                            return Array.isArray(txt) ? txt.join('') : String(txt)
                          }).join(' ') : ''
                          const hasFail = rowText.includes('❌') && rowText.includes('FAIL')
                          if (hasFail && selected?.name === 'summary.md') {
                            return (
                              <tr {...props} style={{ cursor: 'pointer' }}
                                onClick={() => handleFailClick(rowText)}
                                title="클릭하여 운영 가이드 보기">
                                {children}
                              </tr>
                            )
                          }
                          return <tr {...props}>{children}</tr>
                        },
                        td({ children, ...props }) {
                          const text = String(children)
                          if (text.includes('❌') && text.includes('FAIL') && selected?.name === 'summary.md') {
                            return (
                              <td {...props}>
                                <span style={{ color: '#f87171', fontWeight: 700 }}>
                                  {children} <span style={{ fontSize: 10, color: '#7c6af7', borderBottom: '1px dashed #7c6af7' }}>가이드↗</span>
                                </span>
                              </td>
                            )
                          }
                          return <td {...props}>{children}</td>
                        }
                      }}
                    >{content}</ReactMarkdown>
                  )
                })()}
              </div>
            </div>
          ) : <div className="empty" style={{ marginTop: 60 }}>{t('selectReport')}</div>}
        </div>
        </div>{/* split-main */}
        <ChatPanel reportPath={selected?.path} offsetTop={120} />
      </div>
    </div>
  )
}
function ChatPanel({ reportPath, offsetTop = 100 }) {
  const lang = useContext(LangContext)
  const isKo = lang === 'ko'
  const initMsg = isKo
    ? '안녕하세요! ARB 점검 결과와 운영 가이드에 대해 질문해주세요.\n\n💡 예시:\n- "ARCH-011 FAIL 원인과 개선 방법은?"\n- "백업 정책 가이드 알려줘"\n- "Multi-AZ 구성 방법은?"'
    : 'Hello! Ask me anything about ARB inspection results and the operations guide.\n\n💡 Examples:\n- "What is the cause and fix for ARCH-011 FAIL?"\n- "Show me the backup policy guide"\n- "How to configure Multi-AZ?"'
  const [messages, setMessages] = useState([{ role: 'assistant', content: initMsg }])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [panelWidth, setPanelWidth] = useState(null)
  const bottomRef = useRef(null)
  const panelRef = useRef(null)

  const startResize = (e) => {
    e.preventDefault()
    const startX = e.clientX
    const startW = panelRef.current?.offsetWidth || 300
    const onMove = (ev) => {
      const delta = startX - ev.clientX  // 왼쪽 드래그 = 넓어짐
      setPanelWidth(Math.max(180, Math.min(700, startW + delta)))
    }
    const onUp = () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
  }

  // 언어 변경 시 초기 메시지 갱신
  useEffect(() => {
    setMessages(prev => {
      const rest = prev.filter((_, i) => i !== 0)
      return [{ role: 'assistant', content: initMsg }, ...rest]
    })
  }, [lang])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const send = async () => {
    const q = input.trim()
    if (!q || streaming) return
    setInput('')
    const newMessages = [...messages, { role: 'user', content: q }]
    setMessages(newMessages)
    setStreaming(true)

    const history = newMessages.slice(1, -1).map(m => ({ role: m.role, content: m.content }))
    let answer = ''
    setMessages(prev => [...prev, { role: 'assistant', content: '' }])

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q, report_path: reportPath || null, history, lang }),
      })
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        const lines = buf.split('\n')
        buf = lines.pop()
        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const data = JSON.parse(line.slice(5).trim())
          if (data.text) {
            answer += data.text
            setMessages(prev => [...prev.slice(0, -1), { role: 'assistant', content: answer }])
          }
          if (data.done || data.error) break
        }
      }
    } catch (e) {
      setMessages(prev => [...prev.slice(0, -1), { role: 'assistant', content: `오류: ${e.message}` }])
    }
    setStreaming(false)
  }

  return (
    <div style={{ display: 'flex', flexShrink: 0 }}>
      {/* 리사이저 — 드래그하여 채팅 패널 너비 조절 */}
      <div
        onMouseDown={startResize}
        style={{ width: 6, cursor: 'col-resize', background: '#2d3148', flexShrink: 0, borderRadius: 3, transition: 'background 0.15s' }}
        onMouseEnter={e => e.currentTarget.style.background = '#7c6af7'}
        onMouseLeave={e => e.currentTarget.style.background = '#2d3148'}
        title="드래그하여 크기 조절"
      />
      <div ref={panelRef} className="card chat-panel"
        style={{ padding: 0, height: `calc(100vh - ${offsetTop}px)`, width: panelWidth ? `${panelWidth}px` : undefined }}>
      <div style={{ padding: '10px 14px', borderBottom: '1px solid #2d3148', fontSize: 13, fontWeight: 600, color: '#7c6af7' }}>
        💬 ARB 질의응답
        <div style={{ fontSize: 10, color: '#475569', fontWeight: 400, marginTop: 2 }}>운영가이드 + 점검 리포트 기반 답변</div>
      </div>
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? 'chat-msg-user' : 'chat-msg-assistant'}>
            {m.role === 'user'
              ? <span style={{ whiteSpace: 'pre-wrap' }}>{m.content}</span>
              : <div className="markdown-body" style={{ fontSize: 12 }}>
                  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                    {m.content}
                  </ReactMarkdown>
                </div>
            }
            {m.role === 'assistant' && streaming && i === messages.length - 1 && (
              <span style={{ color: '#7c6af7' }}>▌</span>
            )}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="chat-input-row">
        <textarea rows={2} placeholder="질문을 입력하세요 (Enter: 전송, Shift+Enter: 줄바꿈)"
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
          disabled={streaming} />
        <button className="btn btn-primary btn-sm" onClick={send} disabled={streaming || !input.trim()}
          style={{ alignSelf: 'flex-end' }}>
          {streaming ? <span className="spinner" /> : '전송'}
        </button>
      </div>
      </div>
    </div>
  )
}

// ── Guide Page ────────────────────────────────────────────────────────────────
function GuidePage({ initialCheckId }) {
  const lang = useContext(LangContext)
  const [checkId, setCheckId] = useState(initialCheckId || '')
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [arbTree, setArbTree] = useState([])
  const [openCat, setOpenCat] = useState(null)
  const [selectedDoc, setSelectedDoc] = useState(null)
  const [docContent, setDocContent] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetch(`${API}/api/guide/arb-tree?lang=${lang}`).then(r => r.json()).then(data => {
      setArbTree(data)
      if (data.length > 0) setOpenCat(data[0].category)
    })
    if (initialCheckId) searchByCheckId(initialCheckId)
  }, [initialCheckId, lang])

  // 언어 변경 시 열린 문서 재번역
  useEffect(() => {
    if (selectedDoc) loadDoc(selectedDoc)
  }, [lang])

  const searchByCheckId = async (cid) => {
    if (!cid) return
    setLoading(true); setSelectedDoc(null)
    const res = await fetch(`${API}/api/guide/check/${cid.trim()}`)
    const data = await res.json()
    setResults(data.docs || [])
    setLoading(false)
  }

  const searchByKeyword = async () => {
    if (!query.trim()) { setResults(null); return }
    setLoading(true); setSelectedDoc(null)
    const res = await fetch(`${API}/api/guide/search?q=${encodeURIComponent(query.trim())}`)
    setResults(await res.json())
    setLoading(false)
  }

  const loadDoc = async (doc) => {
    setSelectedDoc(doc)
    setDocContent('⏳ Loading...')
    const res = await fetch(`${API}/api/guide/doc?file=${encodeURIComponent(doc.file)}&lang=${lang}`)
    const data = await res.json()
    setDocContent(data.content)
  }

  const arbTreePanel = (
    <div className="card" style={{ padding: '10px 8px', maxHeight: 620, overflowY: 'auto' }}>
      {arbTree.map(cat => (
        <div key={cat.category} style={{ marginBottom: 2 }}>
          {/* 카테고리 헤더 */}
          <div onClick={() => setOpenCat(openCat === cat.category ? null : cat.category)}
            style={{ padding: '7px 10px', cursor: 'pointer', borderRadius: 6, display: 'flex',
              justifyContent: 'space-between', alignItems: 'center',
              background: openCat === cat.category ? '#252840' : 'transparent' }}>
            <span style={{ fontSize: 13, fontWeight: 600, color: openCat === cat.category ? '#a78bfa' : '#94a3b8' }}>
              {cat.icon} {cat.category}
            </span>
            <span style={{ fontSize: 11, color: '#475569' }}>{openCat === cat.category ? '▾' : '▸'}</span>
          </div>
          {/* Check ID 항목들 */}
          {openCat === cat.category && (
            <div style={{ paddingLeft: 8, marginTop: 2 }}>
              {cat.children.map(item => (
                <div key={item.id}
                  onClick={() => { setCheckId(item.id); searchByCheckId(item.id) }}
                  style={{ padding: '5px 10px', cursor: 'pointer', borderRadius: 4, marginBottom: 1,
                    background: checkId === item.id && results !== null ? '#1e1a3a' : 'transparent',
                    borderLeft: checkId === item.id && results !== null ? '2px solid #7c6af7' : '2px solid transparent',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontSize: 10, color: '#7c6af7', fontFamily: 'monospace', marginRight: 6 }}>{item.id}</span>
                    <span style={{ fontSize: 12, color: '#cbd5e1' }}>{item.label}</span>
                  </div>
                  {item.doc_count > 0 && (
                    <span style={{ fontSize: 10, color: '#4ade80', background: '#14532d', padding: '1px 5px', borderRadius: 3 }}>
                      {item.doc_count}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )

  const searchResultPanel = (
    <div className="card" style={{ padding: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <h2 style={{ fontSize: 13, margin: 0 }}>
          {checkId ? `${checkId} 관련 문서` : '검색 결과'} ({results?.length || 0}건)
        </h2>
        <button className="btn btn-outline btn-sm" onClick={() => { setResults(null); setCheckId(''); setQuery('') }}>목차로</button>
      </div>
      {!results?.length
        ? <div className="empty">관련 문서 없음</div>
        : results.map(r => (
          <div key={r.file} onClick={() => loadDoc(r)}
            style={{ padding: '7px 10px', cursor: 'pointer', borderRadius: 6, marginBottom: 3,
              background: selectedDoc?.file === r.file ? '#1e1a3a' : 'transparent',
              borderLeft: selectedDoc?.file === r.file ? '3px solid #7c6af7' : '3px solid transparent' }}>
            <div style={{ fontSize: 12, color: '#e2e8f0', fontWeight: 600 }}>{r.title}</div>
            {r.breadcrumb?.length > 0 && (
              <div style={{ fontSize: 10, color: '#475569', marginTop: 2 }}>{r.breadcrumb.slice(-2).join(' > ')}</div>
            )}
            {r.score > 0 && <span style={{ fontSize: 10, color: '#7c6af7' }}>{'★'.repeat(Math.min(r.score, 5))}</span>}
          </div>
        ))}
    </div>
  )

  return (
    <div style={{ display: 'flex', gap: 16 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
      <div className="page-title">운영 가이드</div>
      <div style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
        내부 Knowledge 데이터(645개 문서) 기반 — 외부 자료 미사용
      </div>
      {/* 검색바 */}
      <div className="card" style={{ marginBottom: 12, padding: '10px 14px' }}>
        <div style={{ display: 'flex', gap: 8 }}>
          <input placeholder="키워드 검색 (공백으로 AND 조합, 예: multi-az 백업)" value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && searchByKeyword()}
            style={{ background: '#0f1117', border: '1px solid #2d3148', borderRadius: 6, padding: '7px 12px', color: '#e2e8f0', fontSize: 13, flex: 1 }} />
          <button className="btn btn-primary btn-sm" onClick={searchByKeyword}>검색</button>
          {results !== null && <button className="btn btn-outline btn-sm" onClick={() => { setResults(null); setQuery(''); setCheckId('') }}>초기화</button>}
        </div>
        {loading && <div style={{ color: '#7c6af7', fontSize: 12, marginTop: 6 }}><span className="spinner" />검색 중...</div>}
      </div>

      <div className="split">
        <div className="split-left">
          {results !== null ? searchResultPanel : arbTreePanel}
        </div>
        <div className="split-right">
          {selectedDoc ? (
            <div className="card">
              <div style={{ fontSize: 13, color: '#94a3b8', marginBottom: 12, fontWeight: 600 }}>{selectedDoc.title}</div>
              <div className="markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}
                  components={{ code({ inline, className, children }) {
                    const lang2 = (className || '').replace('language-', '')
                    if (!inline && lang2 === 'mermaid') return <MermaidBlock code={String(children).trim()} />
                    return inline ? <code className={className}>{children}</code> : <pre><code className={className}>{children}</code></pre>
                  }}}>
                  {docContent}
                </ReactMarkdown>
              </div>
            </div>
          ) : <div className="empty" style={{ marginTop: 60 }}>좌측에서 항목을 선택하면 관련 문서가 표시됩니다</div>}
        </div>
      </div>
      </div>{/* flex inner */}
      <div style={{ paddingTop: 90 }}>
        <ChatPanel reportPath={null} offsetTop={210} />
      </div>
    </div>
  )
}

// ── Cost Page

// ── Cost Page ─────────────────────────────────────────────────────────────────
function CostPage() {
  const t = useLang()
  const [data, setData] = useState({ projects: [], monthly_cost: [] })

  useEffect(() => {
    fetch(`${API}/api/dashboard/cost?months=12`).then(r => r.json()).then(setData)
  }, [])

  const totalCost = data.monthly_cost.reduce((s, m) => s + m.cost, 0)

  return (
    <div>
      <div className="page-title">{t('costTitle')}</div>

      {/* 과제별 점검 현황 테이블 */}
      <div className="card" style={{ marginBottom: 16 }}>
        <h2 style={{ marginBottom: 16 }}>{t('projectStatus')}</h2>
        {data.projects.length === 0 ? <div className="empty">{t('noData')}</div> : (
          <table className="table">
            <thead>
              <tr>
                <th>{t('projectCol')}</th>
                <th style={{ textAlign: 'center' }}>{t('countCol')}</th>
                <th>{t('lastDate')}</th>
              </tr>
            </thead>
            <tbody>
              {data.projects.map(p => (
                <tr key={p.project}>
                  <td style={{ fontWeight: 600, color: '#a78bfa' }}>{p.project}</td>
                  <td style={{ textAlign: 'center', fontWeight: 700, color: '#7c6af7', fontSize: 16 }}>{p.count}</td>
                  <td style={{ fontSize: 12, color: '#64748b' }}>{p.last_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 월별 비용 그래프 */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2>{t('monthlyCost')}</h2>
          <span style={{ fontSize: 14, color: '#64748b' }}>
            {t('threeMonthTotal')}: <span style={{ color: '#4ade80', fontWeight: 700 }}>${totalCost.toFixed(2)}</span>
          </span>
        </div>
        {data.monthly_cost.length === 0 ? <div className="empty">{t('noData')}</div> : (
          <>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={data.monthly_cost} margin={{ top: 4, right: 16, left: 0, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#2d3148" />
                <XAxis dataKey="month" tick={{ fontSize: 12, fill: '#64748b' }} />
                <YAxis tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={v => `$${v}`} />
                <Tooltip contentStyle={{ background: '#1a1d27', border: '1px solid #2d3148', fontSize: 12 }}
                  formatter={(v) => [`$${v.toFixed(2)}`, t('costCol')]} />
                <Bar dataKey="cost" radius={[4, 4, 0, 0]}
                  fill="#4ade80" name={`AWS ${t('costCol')}`} />
              </BarChart>
            </ResponsiveContainer>
            <table className="table" style={{ marginTop: 16 }}>
              <thead>
                <tr><th>{t('month')}</th><th style={{ textAlign: 'right' }}>AWS {t('costCol')}</th><th></th></tr>
              </thead>
              <tbody>
                {data.monthly_cost.map(m => (
                  <tr key={m.month}>
                    <td style={{ fontWeight: 600 }}>{m.month}</td>
                    <td style={{ textAlign: 'right', color: '#4ade80', fontWeight: 700 }}>${m.cost.toFixed(2)}</td>
                    <td style={{ fontSize: 12, color: '#64748b' }}>{m.estimated ? t('estimated') : t('confirmed')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  )
}

// ── App ───────────────────────────────────────────────────────────────────────
const ArbLogo = () => (
  <svg width="56" height="56" viewBox="0 0 56 56" fill="none" xmlns="http://www.w3.org/2000/svg">
    <rect width="56" height="56" rx="12" fill="#1e1a3a"/>
    <polygon points="28,8 48,44 8,44" fill="none" stroke="#7c6af7" strokeWidth="3" strokeLinejoin="round"/>
    <line x1="28" y1="8" x2="28" y2="44" stroke="#7c6af7" strokeWidth="1.5" strokeDasharray="3,3"/>
    <line x1="8" y1="44" x2="48" y2="44" stroke="#7c6af7" strokeWidth="1.5" strokeDasharray="3,3"/>
    <circle cx="28" cy="8" r="3" fill="#a78bfa"/>
    <circle cx="8" cy="44" r="3" fill="#a78bfa"/>
    <circle cx="48" cy="44" r="3" fill="#a78bfa"/>
    <text x="28" y="38" textAnchor="middle" fill="#e2e8f0" fontSize="11" fontWeight="bold" fontFamily="sans-serif">ARB</text>
  </svg>
)

// ── Help Page ─────────────────────────────────────────────────────────────────
function HelpPage() {
  const ts = Date.now()
  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <iframe
        src={`/docs/arbaiops_manual_guide.html?v=${ts}`}
        style={{ flex: 1, border: 'none', background: '#fff' }}
        title="ARB AI-Ops User Manual"
      />
    </div>
  )
}

export default function App() {
  const [page, setPage] = useState('dashboard')
  const [reportJob, setReportJob] = useState(null)
  const [runState, setRunState] = useState({ logs: [], job: null, running: false, jobId: null })
  const [lang, setLang] = useState('ko')
  const [guideCheckId, setGuideCheckId] = useState(null)

  const goReport = (job) => { setReportJob(job); setPage('reports') }
  const goGuide = (checkId) => { setGuideCheckId(checkId); setPage('guide') }

  const nav = [
    { id: 'dashboard', icon: '📊', labelKey: 'dashboard' },
    { id: 'run', icon: '🔍', labelKey: 'run' },
    { id: 'history', icon: '📋', labelKey: 'history' },
    { id: 'reports', icon: '📄', labelKey: 'reports' },
    { id: 'guide', icon: '📖', labelKey: 'guide' },
    { id: 'cost', icon: '💰', labelKey: 'cost' },
    { id: 'help', icon: '❓', labelKey: 'help' },
  ]

  return (
    <LangContext.Provider value={lang}>
      <div className="layout">
        <aside className="sidebar">
          <div className="sidebar-logo">
            <h1>ARB</h1>
            <span>Architecture Review Board AI-Powered</span>
          </div>
          <nav>
            {nav.map(n => (
              <div key={n.id} className={`nav-item ${page === n.id ? 'active' : ''}`}
                onClick={() => { setPage(n.id); if (n.id === 'reports') setReportJob(null); if (n.id === 'guide') setGuideCheckId(null) }}>
                <span className="nav-icon">{n.icon}</span>
                {T[lang][n.labelKey]}
              </div>
            ))}
          </nav>
          {/* 언어 선택 */}
          <div style={{ padding: '12px 16px', borderTop: '1px solid #2d3148' }}>
            <div style={{ display: 'flex', gap: 8, justifyContent: 'center' }}>
              {['ko', 'en'].map(l => (
                <button key={l} onClick={() => setLang(l)}
                  style={{ padding: '4px 12px', borderRadius: 4, border: 'none', cursor: 'pointer', fontSize: 12, fontWeight: 600,
                    background: lang === l ? '#7c6af7' : '#2d3148', color: lang === l ? '#fff' : '#94a3b8' }}>
                  {l === 'ko' ? '한국어' : 'English'}
                </button>
              ))}
            </div>
          </div>
          {/* 로고 */}
          <div style={{ padding: '16px 16px 20px', textAlign: 'center' }}>
            <ArbLogo />
            <div style={{ fontSize: 11, color: '#64748b', marginTop: 8, lineHeight: 1.4 }}>Cloud Operation Group 2026</div>
          </div>
        </aside>
        <main className="main">
          {page === 'dashboard' && <DashboardPage />}
          <div style={{ display: page === 'run' ? 'block' : 'none' }}>
            <RunPage runState={runState} setRunState={setRunState} />
          </div>
          {page === 'history' && <HistoryPage onViewReport={goReport} />}
          {page === 'reports' && <ReportsPage job={reportJob} onGuide={goGuide} />}
          {page === 'guide' && <GuidePage initialCheckId={guideCheckId} />}
          {page === 'cost' && <CostPage />}
          {page === 'help' && <HelpPage />}
        </main>
      </div>
    </LangContext.Provider>
  )
}
