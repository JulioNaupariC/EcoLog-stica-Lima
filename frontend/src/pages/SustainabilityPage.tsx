import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { BarChart3, CheckCircle2, Leaf, Route } from 'lucide-react'
import { Alert, Button, Card, DataTable, EmptyState, PageHeader, StatCard } from '../components/ui'
import type { Column } from '../components/ui'
import { operationDateInLima } from '../domain/operationRoutes'
import { InvalidSustainability, METRICS, validPeriod } from '../domain/sustainability'
import type { Period, Sustainability } from '../domain/sustainability'
import { sustainabilityApi, SustainabilityError } from '../services/sustainability'
import type { SustainabilitySource } from '../services/sustainability'
import '../styles/sustainability.css'

const NUMBER = new Intl.NumberFormat('es-PE', { maximumFractionDigits: 2 })
const format = (value: number, unit: string) => `${NUMBER.format(value)} ${unit}`
const dateLabel = (date: string) => date.split('-').reverse().join('/')
type Comparison = { key: string; label: string; unit: string; total: number; baseline: number; saving: number }
const COLUMNS: Column<Comparison>[] = [
  { key: 'label', header: 'Indicador', primary: true, render: row => row.label },
  { key: 'total', header: 'Optimizada', align: 'end', render: row => format(row.total, row.unit) },
  { key: 'baseline', header: 'Secuencial', align: 'end', render: row => format(row.baseline, row.unit) },
  { key: 'saving', header: 'Ahorro', align: 'end', render: row => format(row.saving, row.unit) },
]

function Results({ data }: { data: Sustainability }) {
  if (!data.con_datos) return <EmptyState icon={BarChart3} headingLevel={2} title="Sin datos para este periodo">
    <p>No hay rutas cerradas en el periodo aplicado. No se muestran indicadores ni ahorros sin información.</p>
  </EmptyState>
  // The decoder rejects partial aggregates before this component is rendered.
  const totals = data.metricas!, savings = data.ahorro!
  const rows = METRICS.map(({ key, label, unit }) => ({ key, label, unit, total: totals[key], baseline: totals[key] + savings[key], saving: savings[key] }))
  return <>
    <p className="field-hint">Métricas estimadas de planificación de las rutas cerradas; el cierre no las convierte en telemetría medida.</p>
    <div className="stat-grid">
      <StatCard icon={Route} label="Rutas cerradas" value={NUMBER.format(data.rutas_cerradas)} detail="Rutas incluidas en el periodo" />
      {METRICS.map(({ key, label, unit }) => <StatCard key={key} icon={key === 'co2_kg' ? Leaf : BarChart3} label={label} value={format(totals[key], unit)} />)}
      <StatCard icon={CheckCircle2} label="Cumplimiento de ventanas" value={data.cumplimiento_ventanas_pct === null ? 'No disponible' : format(data.cumplimiento_ventanas_pct, '%')}
        detail="Atendidas dentro de ventana / paradas terminales; no se deduce de la ETA" />
    </div>
    <Card title="Comparación frente a la ruta secuencial" titleId="sustainability-comparison-title">
      <p>Ahorro de distancia: <strong>{savings.pct === null ? 'No calculable (base secuencial cero)' : format(savings.pct, '%')}</strong>.</p>
      <p className="field-hint">Ahorro = secuencial − optimizada, para la misma cobertura. Un valor negativo indica mayor consumo o costo que la referencia. El porcentaje corresponde solo a distancia.</p>
      <DataTable columns={COLUMNS} rows={rows} rowKey={row => row.key} label="Comparación de sostenibilidad"
        caption="Métricas optimizadas, referencia secuencial y ahorro con su unidad para el periodo aplicado" />
    </Card>
    <Card title="Parámetros y equivalente ambiental" titleId="sustainability-parameters-title">
      <h3>Versiones de parámetros utilizadas</h3>
      <ul>{data.parametros_versiones.map(version => <li key={version}><code>{version}</code></li>)}</ul>
      <a href="https://continental-team-il84x39k.atlassian.net/browse/ECL-26">Consultar EN-008: parámetros versionados</a>
      <h3>Equivalente ambiental: No disponible</h3>
      <p>El servicio no publica un equivalente con proyecto registrado, factor vigente, unidad y fuente. No se calcula una compensación ni se afirma un crédito certificado.</p>
    </Card>
  </>
}

type View = { status: 'loading' } | { status: 'error'; message: string } | { status: 'ready'; data: Sustainability }
export function SustainabilityPage({ onSessionExpired, source = sustainabilityApi }: {
  onSessionExpired: () => void; source?: SustainabilitySource
}) {
  const [initial] = useState<Period>(() => { const today = operationDateInLima(); return { desde: `${today.slice(0, 7)}-01`, hasta: today } })
  const [period, setPeriod] = useState(initial)
  const [view, setView] = useState<View>({ status: 'loading' })
  const [validation, setValidation] = useState('')
  const sequence = useRef(0), controller = useRef<AbortController | null>(null), start = useRef<HTMLInputElement>(null)
  const load = useCallback(async (requested: Period) => {
    const current = ++sequence.current
    controller.current?.abort()
    const pending = new AbortController(); controller.current = pending
    setView({ status: 'loading' }); setValidation('')
    try {
      const data = await source.load(requested, pending.signal)
      if (current !== sequence.current || pending.signal.aborted) return
      setView({ status: 'ready', data })
    } catch (error) {
      if (current !== sequence.current || pending.signal.aborted) return
      if (error instanceof SustainabilityError && error.kind === 'unauthorized') onSessionExpired()
      const message = error instanceof SustainabilityError || error instanceof InvalidSustainability
        ? error.message : 'No se pudieron cargar los indicadores. Intenta de nuevo.'
      setView({ status: 'error', message })
    }
  }, [source, onSessionExpired])
  useEffect(() => {
    let active = true
    const current = sequence
    void Promise.resolve().then(() => { if (active) void load(initial) })
    return () => { active = false; current.current++; controller.current?.abort() }
  }, [load, initial])
  function submit(event: FormEvent) {
    event.preventDefault()
    if (!validPeriod(period)) {
      sequence.current++; controller.current?.abort()
      const message = 'Indica fechas válidas: Desde debe ser anterior o igual a Hasta.'
      setValidation(message); setView({ status: 'error', message }); start.current?.focus(); return
    }
    void load({ ...period })
  }
  const data = view.status === 'ready' ? view.data : null
  return <section className="sustainability-page" aria-labelledby="sustainability-title">
    <PageHeader titleId="sustainability-title" title="Operación y sostenibilidad" eyebrow="Indicadores"
      description="Consulta las rutas cerradas de un periodo y compáralas con la referencia secuencial. Fechas inclusivas de Lima (UTC−5)."
      breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Sostenibilidad' }]} />
    <form className="card sustainability-filters" aria-label="Periodo de sostenibilidad" onSubmit={submit} noValidate>
      <div className="form-field"><label htmlFor="sustainability-from">Desde</label>
        <input ref={start} id="sustainability-from" name="desde" type="date" required value={period.desde}
          aria-invalid={Boolean(validation)} aria-describedby={validation ? 'sustainability-validation' : undefined}
          onChange={event => setPeriod(current => ({ ...current, desde: event.target.value }))} /></div>
      <div className="form-field"><label htmlFor="sustainability-to">Hasta</label>
        <input id="sustainability-to" name="hasta" type="date" required value={period.hasta}
          aria-invalid={Boolean(validation)} aria-describedby={validation ? 'sustainability-validation' : undefined}
          onChange={event => setPeriod(current => ({ ...current, hasta: event.target.value }))} /></div>
      <Button type="submit">Consultar periodo</Button>
      {validation ? <p id="sustainability-validation" className="field-error">{validation}</p> : null}
    </form>
    {view.status === 'loading' ? <p role="status">Consultando indicadores del periodo…</p> : null}
    {view.status === 'error' ? <Alert tone="danger" title="No se pudo consultar el periodo">{view.message}</Alert> : null}
    {data ? <>
      <p role="status">Periodo aplicado: <strong>{dateLabel(data.periodo.desde)} — {dateLabel(data.periodo.hasta)}</strong> · Lima, ambos días incluidos.</p>
      {data.simulado ? <Alert tone="warning" title="Datos de prueba">El servicio devuelve datos de demostración. Estas cifras no acreditan resultados operativos ni ambientales reales.</Alert> : null}
      <Results data={data} />
    </> : null}
  </section>
}
