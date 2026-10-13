import { useCallback, useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Plus, RefreshCw, Truck } from 'lucide-react'
import { Alert, Badge, Button, Card, DataTable, EmptyState, FormActions, FormSection, PageHeader, Skeleton, StatusBadge } from '../components/ui'
import type { Column } from '../components/ui'
import { createVehicle, listVehicles, VehicleServiceError } from '../services/vehicles'
import type { VehicleCreatePayload, VehicleResponse, VehicleType } from '../services/vehicles'

type VehicleField = keyof VehicleCreatePayload
type FormValues = Record<VehicleField, string>
type FieldErrors = Partial<Record<VehicleField, string>>

const INITIAL_VALUES: FormValues = {
  placa: '',
  tipo: '',
  capacidad_kg: '',
  capacidad_m3: '',
  rendimiento_km_l: '',
  factor_co2_kg_km: '',
  anio_fabricacion: '',
}

const FIELDS: { name: VehicleField; label: string; hint: string }[] = [
  { name: 'placa', label: 'Placa', hint: 'Hasta 10 caracteres; se guarda en mayúsculas. Ej.: ABC-123.' },
  { name: 'tipo', label: 'Tipo', hint: 'Camioneta, furgón o moto.' },
  { name: 'anio_fabricacion', label: 'Año de fabricación', hint: 'Entre 1980 y 2100.' },
  { name: 'capacidad_kg', label: 'Capacidad (kg)', hint: 'Carga útil máxima. Ej.: 1200.' },
  { name: 'capacidad_m3', label: 'Capacidad (m³)', hint: 'Volumen útil. Ej.: 8.50.' },
  { name: 'rendimiento_km_l', label: 'Rendimiento (km/L)', hint: 'Kilómetros por litro. Ej.: 11.500.' },
  { name: 'factor_co2_kg_km', label: 'Factor CO₂ (kg/km)', hint: 'Emisión por kilómetro; 0 si es eléctrico.' },
]

const SECTIONS: { legend: string; description: string; fields: VehicleField[] }[] = [
  { legend: 'Identificación', description: 'Datos con los que se reconoce la unidad.', fields: ['placa', 'tipo', 'anio_fabricacion'] },
  { legend: 'Capacidad', description: 'Límites que usará la planificación de rutas.', fields: ['capacidad_kg', 'capacidad_m3'] },
  { legend: 'Consumo y emisiones', description: 'Base para los indicadores de sostenibilidad.', fields: ['rendimiento_km_l', 'factor_co2_kg_km'] },
]

const TYPE_LABEL: Record<string, string> = { CAMIONETA: 'Camioneta', FURGON: 'Furgón', MOTO: 'Moto' }

const DECIMAL_FIELDS = [
  { name: 'capacidad_kg', places: 2, allowZero: false },
  { name: 'capacidad_m3', places: 2, allowZero: false },
  { name: 'rendimiento_km_l', places: 3, allowZero: false },
  { name: 'factor_co2_kg_km', places: 5, allowZero: true },
] as const

function isVehicleType(value: string): value is VehicleType {
  return value === 'CAMIONETA' || value === 'FURGON' || value === 'MOTO'
}

function decimalError(value: string, places: number, allowZero: boolean): string | undefined {
  if (!value.trim()) return 'Este campo es obligatorio.'
  if (!/^\d+(?:\.\d+)?$/u.test(value)) {
    return 'Usa un número sin signo, con punto decimal; por ejemplo, 1.25.'
  }
  const [whole, fraction = ''] = value.split('.')
  // Count on a copy, preserving the original text and avoiding floating point.
  const integerDigits = whole.replace(/^0+/u, '')
  const fractionalDigits = fraction.replace(/0+$/u, '')
  if (!allowZero && !/[1-9]/u.test(value)) return 'El valor debe ser mayor que cero.'
  if (integerDigits.length > 10 - places || fractionalDigits.length > places) {
    return `Usa como máximo ${10 - places} dígitos enteros y ${places} decimales significativos.`
  }
  return undefined
}

function validate(values: FormValues): { errors: FieldErrors; payload?: VehicleCreatePayload } {
  const errors: FieldErrors = {}
  const plateLength = Array.from(values.placa.trim().toUpperCase()).length
  if (plateLength === 0) errors.placa = 'La placa es obligatoria.'
  else if (plateLength > 10) errors.placa = 'La placa no puede superar 10 caracteres al normalizarse.'
  if (!isVehicleType(values.tipo)) errors.tipo = 'Selecciona un tipo de vehículo válido.'
  for (const { name, places, allowZero } of DECIMAL_FIELDS) {
    const error = decimalError(values[name], places, allowZero)
    if (error) errors[name] = error
  }
  const year = Number(values.anio_fabricacion)
  if (!/^\d{4}$/u.test(values.anio_fabricacion) || year < 1980 || year > 2100) {
    errors.anio_fabricacion = 'Ingresa un año entero entre 1980 y 2100.'
  }
  if (Object.keys(errors).length > 0 || !isVehicleType(values.tipo)) return { errors }
  return { errors, payload: { ...values, tipo: values.tipo, anio_fabricacion: year } }
}

function serviceMessage(error: unknown): string {
  return error instanceof VehicleServiceError ? error.message : 'No se pudo completar la operación.'
}

function VehicleForm({ onCreated }: { onCreated: (vehicle: VehicleResponse) => void }) {
  const [values, setValues] = useState<FormValues>(INITIAL_VALUES)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [globalError, setGlobalError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const submittingRef = useRef(false)
  const mountedRef = useRef(false)
  const formRef = useRef<HTMLFormElement>(null)
  const errorRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    if (!globalError || submitting) return
    const firstInvalid = FIELDS.find(({ name }) => errors[name])
    const control = firstInvalid && formRef.current?.elements.namedItem(firstInvalid.name)
    if (control instanceof HTMLElement) control.focus()
    else errorRef.current?.focus()
  }, [errors, globalError, submitting])

  function updateValue(field: VehicleField, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
    setGlobalError('')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submittingRef.current) return
    const result = validate(values)
    setErrors(result.errors)
    if (!result.payload) {
      setGlobalError('Revisa los campos indicados antes de registrar el vehículo.')
      return
    }

    submittingRef.current = true
    setSubmitting(true)
    setGlobalError('')
    try {
      const vehicle = await createVehicle(result.payload)
      if (!mountedRef.current) return
      setValues(INITIAL_VALUES)
      setErrors({})
      onCreated(vehicle)
    } catch (error) {
      if (!mountedRef.current) return
      const nextErrors: FieldErrors = {}
      if (error instanceof VehicleServiceError) {
        for (const issue of error.issues) nextErrors[issue.field] = issue.message
        if (error.kind === 'conflict') nextErrors.placa = error.message
      }
      setErrors(nextErrors)
      setGlobalError(serviceMessage(error))
    } finally {
      submittingRef.current = false
      if (mountedRef.current) setSubmitting(false)
    }
  }

  function renderField(name: VehicleField) {
    const field = FIELDS.find(item => item.name === name)!
    const id = `vehicle-${name}`
    const describedBy = [errors[name] ? `${id}-error` : null, `${id}-hint`].filter(Boolean).join(' ')
    const inputProps = {
      id,
      name,
      required: true,
      disabled: submitting,
      value: values[name],
      'aria-invalid': Boolean(errors[name]),
      'aria-describedby': describedBy,
    }
    return (
      <div className="form-field" key={name}>
        <label htmlFor={id}>{field.label}</label>
        {name === 'tipo' ? (
          <select {...inputProps} onChange={(event) => updateValue(name, event.target.value)}>
            <option value="">Selecciona un tipo</option>
            <option value="CAMIONETA">Camioneta</option>
            <option value="FURGON">Furgón</option>
            <option value="MOTO">Moto</option>
          </select>
        ) : (
          <input
            {...inputProps}
            type="text"
            inputMode={name === 'placa' ? 'text' : name === 'anio_fabricacion' ? 'numeric' : 'decimal'}
            onChange={(event) => updateValue(name, event.target.value)}
          />
        )}
        {errors[name] ? <p className="field-error" id={`${id}-error`}>{errors[name]}</p> : null}
        <p className="field-hint" id={`${id}-hint`}>{field.hint}</p>
      </div>
    )
  }

  return (
    <Card title="Registrar vehículo" titleId="vehicle-form-title" className="vehicle-registration">
      <p id="vehicle-format-help" className="card-description">
        Todos los campos son obligatorios. Usa punto decimal, sin separadores de miles ni exponentes.
      </p>
      {globalError ? (
        <Alert tone="danger" ref={errorRef} tabIndex={-1}>{globalError}</Alert>
      ) : null}
      {submitting ? <p className="field-hint" role="status">Registrando vehículo…</p> : null}
      <form
        className="form-stack"
        aria-labelledby="vehicle-form-title"
        aria-describedby="vehicle-format-help"
        aria-busy={submitting}
        noValidate
        ref={formRef}
        onSubmit={(event) => { void handleSubmit(event) }}
      >
        {SECTIONS.map(section => (
          <FormSection key={section.legend} legend={section.legend} description={section.description}>
            <div className="form-grid">{section.fields.map(renderField)}</div>
          </FormSection>
        ))}
        <FormActions>
          <Button type="submit" icon={Plus} disabled={submitting}>
            {submitting ? 'Registrando…' : 'Registrar vehículo'}
          </Button>
        </FormActions>
      </form>
    </Card>
  )
}

function stateBadge(estado: string) {
  if (estado === 'ACTIVO' || estado === 'INACTIVO') return <StatusBadge status={estado} />
  // Unknown states are shown verbatim (as text) rather than guessed.
  return <Badge tone="neutral" icon={null}>{estado}</Badge>
}

const VEHICLE_COLUMNS: Column<VehicleResponse>[] = [
  { key: 'placa', header: 'Placa', primary: true, render: vehicle => <strong>{vehicle.placa}</strong> },
  { key: 'tipo', header: 'Tipo', render: vehicle => TYPE_LABEL[vehicle.tipo] ?? vehicle.tipo },
  { key: 'kg', header: 'Capacidad (kg)', align: 'end', render: vehicle => vehicle.capacidad_kg },
  { key: 'm3', header: 'Capacidad (m³)', align: 'end', render: vehicle => vehicle.capacidad_m3 },
  { key: 'rend', header: 'Rendimiento (km/L)', align: 'end', render: vehicle => vehicle.rendimiento_km_l },
  { key: 'co2', header: 'Factor (kg CO₂/km)', align: 'end', render: vehicle => vehicle.factor_co2_kg_km },
  { key: 'anio', header: 'Año', align: 'end', render: vehicle => vehicle.anio_fabricacion },
  { key: 'estado', header: 'Estado', render: vehicle => stateBadge(vehicle.estado) },
]

function VehicleTable({ vehicles }: { vehicles: VehicleResponse[] }) {
  return <DataTable columns={VEHICLE_COLUMNS} rows={vehicles} rowKey={vehicle => vehicle.vehiculo_id}
    caption="Vehículos registrados, incluidos activos e inactivos"
    label="Tabla de vehículos, desplazamiento horizontal" />
}

interface ListState {
  status: 'loading' | 'ready' | 'error'
  vehicles: VehicleResponse[]
  error: string
}

export function VehiclesPage({ canCreate }: { canCreate: boolean }) {
  const [list, setList] = useState<ListState>({ status: 'loading', vehicles: [], error: '' })
  const [createdVehicle, setCreatedVehicle] = useState<VehicleResponse | null>(null)
  const latestRequest = useRef(0)
  const listErrorRef = useRef<HTMLDivElement>(null)

  const loadList = useCallback((afterCreate = false) => {
    const requestId = ++latestRequest.current
    void listVehicles().then(
      (vehicles) => {
        if (requestId !== latestRequest.current) return
        setList({ status: 'ready', vehicles, error: '' })
      },
      (error: unknown) => {
        if (requestId !== latestRequest.current) return
        const message = serviceMessage(error)
        setList((current) => ({
          ...current,
          status: 'error',
          error: afterCreate ? `Vehículo registrado. No se pudo actualizar el listado. ${message}` : message,
        }))
      },
    )
  }, [])

  useEffect(() => {
    loadList()
    // Invalidates earlier GETs, including StrictMode's first mount and unmount.
    return () => { latestRequest.current += 1 }
  }, [loadList])

  useEffect(() => {
    if (list.status === 'error') listErrorRef.current?.focus()
  }, [list])

  function refreshList(afterCreate = false) {
    setList((current) => ({ ...current, status: 'loading', error: '' }))
    loadList(afterCreate)
  }

  function handleCreated(vehicle: VehicleResponse) {
    setCreatedVehicle(vehicle)
    refreshList(true)
  }

  const active = list.vehicles.filter(vehicle => vehicle.estado === 'ACTIVO').length
  return (
    <section className="vehicles-page" aria-labelledby="vehicles-title">
      <PageHeader titleId="vehicles-title" title="Vehículos" eyebrow="Gestión de flota"
        breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Vehículos' }]}
        description="Unidades disponibles para la planificación, con su capacidad y factor de emisión." />
      {createdVehicle ? (
        <Alert tone="success" role="status">Vehículo registrado: {createdVehicle.placa}.</Alert>
      ) : null}
      {list.status === 'loading' ? <p className="visually-hidden" role="status">Cargando vehículos…</p> : null}
      <Card as="div" title="Listado de vehículos" titleId="vehicle-list-title" className="vehicle-list"
        description={list.vehicles.length ? `${list.vehicles.length} registrados · ${active} activos` : undefined}
        actions={<Button variant="secondary" size="sm" icon={RefreshCw} disabled={list.status === 'loading'} onClick={() => refreshList()}>
          Actualizar listado
        </Button>}>
        <div aria-busy={list.status === 'loading'} className="card-body" role="region" aria-label="Listado de vehículos">
          {list.status === 'loading' && list.vehicles.length === 0 ? <Skeleton lines={4} /> : null}
          {list.status === 'error' ? (
            <Alert tone="danger" ref={listErrorRef} tabIndex={-1}>
              {list.error}
              {list.vehicles.length > 0 ? <span> El listado mostrado puede estar desactualizado.</span> : null}
            </Alert>
          ) : null}
          {list.status === 'ready' && list.vehicles.length === 0 ? (
            <EmptyState icon={Truck} title="Sin vehículos" headingLevel={3}>
              <p role="status">No hay vehículos registrados.</p>
            </EmptyState>
          ) : null}
          {list.vehicles.length > 0 ? <VehicleTable vehicles={list.vehicles} /> : null}
        </div>
      </Card>
      {canCreate ? <VehicleForm onCreated={handleCreated} /> : null}
    </section>
  )
}
