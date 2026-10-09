import { FormEvent, useRef, useState } from 'react'
import { FormField as Field } from '../components/FormField'
import {
  createOrder,
  datetimeLocalToIso,
  OrderCreatePayload,
  OrderCreateResponse,
  OrderServiceError,
  Priority,
} from '../services/orders'

type FormField = keyof OrderCreatePayload
type FieldErrors = Partial<Record<FormField, string>>
type SubmitStatus = 'idle' | 'submitting' | 'success' | 'error'

interface OrderFormValues {
  cliente_id: string
  direccion: string
  referencia: string
  latitud: string
  longitud: string
  peso_kg: string
  volumen_m3: string
  ventana_inicio: string
  ventana_fin: string
  prioridad: Priority
  tipo_producto: string
}

const INITIAL_VALUES: OrderFormValues = {
  cliente_id: '',
  direccion: '',
  referencia: '',
  latitud: '',
  longitud: '',
  peso_kg: '',
  volumen_m3: '',
  ventana_inicio: '',
  ventana_fin: '',
  prioridad: 'ESTANDAR',
  tipo_producto: '',
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/iu

function decimalError(value: string, decimalPlaces: number, label: string): string | undefined {
  if (!value.trim()) {
    return `${label} es obligatorio.`
  }
  const pattern = new RegExp(`^\\d+(?:\\.\\d{1,${decimalPlaces}})?$`, 'u')
  if (!pattern.test(value) || Number(value) <= 0 || !Number.isFinite(Number(value))) {
    return `${label} debe ser mayor que cero y tener como máximo ${decimalPlaces} decimales.`
  }
  return undefined
}

function coordinateError(value: string, minimum: number, maximum: number, label: string): string | undefined {
  if (!value) {
    return undefined
  }
  const number = Number(value)
  if (!Number.isFinite(number) || number < minimum || number > maximum) {
    return `${label} debe estar entre ${minimum} y ${maximum}.`
  }
  return undefined
}

function validate(values: OrderFormValues): {
  errors: FieldErrors
  payload?: OrderCreatePayload
} {
  const errors: FieldErrors = {}
  const clienteId = values.cliente_id.trim()
  const direccion = values.direccion.trim()
  const referencia = values.referencia.trim()
  const tipoProducto = values.tipo_producto.trim()

  if (!clienteId) {
    errors.cliente_id = 'El ID del cliente es obligatorio.'
  } else if (!UUID_PATTERN.test(clienteId)) {
    errors.cliente_id = 'Ingresa un UUID de cliente válido.'
  }
  if (!direccion) {
    errors.direccion = 'La dirección es obligatoria.'
  } else if (direccion.length > 255) {
    errors.direccion = 'La dirección no puede superar 255 caracteres.'
  }
  if (referencia.length > 255) {
    errors.referencia = 'La referencia no puede superar 255 caracteres.'
  }

  const hasLatitude = values.latitud !== ''
  const hasLongitude = values.longitud !== ''
  if (hasLatitude !== hasLongitude) {
    const message = 'Latitud y longitud deben ingresarse juntas.'
    errors.latitud = message
    errors.longitud = message
  } else {
    const latitudeError = coordinateError(values.latitud, -90, 90, 'La latitud')
    const longitudeError = coordinateError(values.longitud, -180, 180, 'La longitud')
    if (latitudeError) errors.latitud = latitudeError
    if (longitudeError) errors.longitud = longitudeError
  }
  if (!hasLatitude && !hasLongitude && !referencia) {
    errors.referencia = 'Ingresa coordenadas completas o un punto de referencia.'
  }

  const weightError = decimalError(values.peso_kg, 2, 'El peso')
  const volumeError = decimalError(values.volumen_m3, 3, 'El volumen')
  if (weightError) errors.peso_kg = weightError
  if (volumeError) errors.volumen_m3 = volumeError

  const startIso = datetimeLocalToIso(values.ventana_inicio)
  const endIso = datetimeLocalToIso(values.ventana_fin)
  if (!startIso) errors.ventana_inicio = 'Ingresa una fecha y hora inicial válida.'
  if (!endIso) errors.ventana_fin = 'Ingresa una fecha y hora final válida.'
  if (startIso && endIso && new Date(endIso).getTime() <= new Date(startIso).getTime()) {
    errors.ventana_fin = 'La hora final debe ser posterior a la hora inicial.'
  }

  if (!tipoProducto) {
    errors.tipo_producto = 'El tipo de producto es obligatorio.'
  } else if (tipoProducto.length > 20) {
    errors.tipo_producto = 'El tipo de producto no puede superar 20 caracteres.'
  }

  if (Object.keys(errors).length > 0 || !startIso || !endIso) {
    return { errors }
  }

  return {
    errors,
    payload: {
      cliente_id: clienteId,
      direccion,
      referencia: referencia || null,
      latitud: hasLatitude ? Number(values.latitud) : null,
      longitud: hasLongitude ? Number(values.longitud) : null,
      peso_kg: values.peso_kg,
      volumen_m3: values.volumen_m3,
      ventana_inicio: startIso,
      ventana_fin: endIso,
      prioridad: values.prioridad,
      tipo_producto: tipoProducto,
    },
  }
}

export function OrderCreatePage() {
  const [values, setValues] = useState<OrderFormValues>(INITIAL_VALUES)
  const [errors, setErrors] = useState<FieldErrors>({})
  const [status, setStatus] = useState<SubmitStatus>('idle')
  const [globalError, setGlobalError] = useState('')
  const [createdOrder, setCreatedOrder] = useState<OrderCreateResponse | null>(null)
  const submittingRef = useRef(false)

  function updateValue(field: keyof OrderFormValues, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
    setErrors((current) => ({ ...current, [field]: undefined }))
    if (status !== 'submitting') {
      setStatus('idle')
      setGlobalError('')
      setCreatedOrder(null)
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (submittingRef.current) return

    const result = validate(values)
    setErrors(result.errors)
    setCreatedOrder(null)
    if (!result.payload) {
      setStatus('error')
      setGlobalError('Revisa los campos indicados antes de registrar el pedido.')
      return
    }

    submittingRef.current = true
    setStatus('submitting')
    setGlobalError('')
    try {
      const order = await createOrder(result.payload)
      setCreatedOrder(order)
      setStatus('success')
    } catch (error) {
      if (error instanceof OrderServiceError) {
        const backendErrors: FieldErrors = {}
        const generalIssues: string[] = []
        for (const issue of error.issues) {
          if (issue.field) {
            backendErrors[issue.field] = issue.message
          } else {
            generalIssues.push(issue.message)
          }
        }
        setErrors((current) => ({ ...current, ...backendErrors }))
        setGlobalError(
          generalIssues.length > 0
            ? `${error.message} ${generalIssues.join(' ')}`
            : error.message,
        )
      } else {
        setGlobalError('No se pudo registrar el pedido.')
      }
      setStatus('error')
    } finally {
      submittingRef.current = false
    }
  }

  const describedBy = (field: FormField) => errors[field] ? `${field}-error` : undefined

  return (
    <section className="order-page" aria-labelledby="order-title">
      <p className="eyebrow">Gestión de pedidos</p>
      <h1 id="order-title">Registrar pedido</h1>
      <p className="form-intro">
        Ingresa el UUID de un cliente existente y los datos necesarios para la planificación.
      </p>

      {globalError ? <div className="form-alert error-alert" role="alert">{globalError}</div> : null}
      {status === 'success' && createdOrder ? (
        <div className="form-alert success-alert" role="status">
          <strong>Pedido registrado.</strong>
          <span>ID: {createdOrder.pedido_id}</span>
          <span>Estado: {createdOrder.estado}</span>
        </div>
      ) : null}

      <form className="order-form" onSubmit={(event) => { void handleSubmit(event) }} noValidate>
        <Field id="cliente_id" label="ID del cliente (UUID)" error={errors.cliente_id}>
          <input id="cliente_id" name="cliente_id" type="text" autoComplete="off" required value={values.cliente_id} onChange={(event) => updateValue('cliente_id', event.target.value)} aria-invalid={Boolean(errors.cliente_id)} aria-describedby={describedBy('cliente_id')} />
        </Field>

        <Field id="direccion" label="Dirección" error={errors.direccion}>
          <input id="direccion" name="direccion" type="text" maxLength={255} required value={values.direccion} onChange={(event) => updateValue('direccion', event.target.value)} aria-invalid={Boolean(errors.direccion)} aria-describedby={describedBy('direccion')} />
        </Field>

        <Field id="referencia" label="Punto de referencia" error={errors.referencia}>
          <input id="referencia" name="referencia" type="text" maxLength={255} value={values.referencia} onChange={(event) => updateValue('referencia', event.target.value)} aria-invalid={Boolean(errors.referencia)} aria-describedby={describedBy('referencia')} />
        </Field>

        <div className="form-grid">
          <Field id="latitud" label="Latitud" error={errors.latitud}>
            <input id="latitud" name="latitud" type="number" min="-90" max="90" step="any" value={values.latitud} onChange={(event) => updateValue('latitud', event.target.value)} aria-invalid={Boolean(errors.latitud)} aria-describedby={describedBy('latitud')} />
          </Field>
          <Field id="longitud" label="Longitud" error={errors.longitud}>
            <input id="longitud" name="longitud" type="number" min="-180" max="180" step="any" value={values.longitud} onChange={(event) => updateValue('longitud', event.target.value)} aria-invalid={Boolean(errors.longitud)} aria-describedby={describedBy('longitud')} />
          </Field>
          <Field id="peso_kg" label="Peso (kg)" error={errors.peso_kg}>
            <input id="peso_kg" name="peso_kg" type="text" inputMode="decimal" required value={values.peso_kg} onChange={(event) => updateValue('peso_kg', event.target.value)} aria-invalid={Boolean(errors.peso_kg)} aria-describedby={describedBy('peso_kg')} />
          </Field>
          <Field id="volumen_m3" label="Volumen (m³)" error={errors.volumen_m3}>
            <input id="volumen_m3" name="volumen_m3" type="text" inputMode="decimal" required value={values.volumen_m3} onChange={(event) => updateValue('volumen_m3', event.target.value)} aria-invalid={Boolean(errors.volumen_m3)} aria-describedby={describedBy('volumen_m3')} />
          </Field>
          <Field id="ventana_inicio" label="Inicio de ventana" error={errors.ventana_inicio}>
            <input id="ventana_inicio" name="ventana_inicio" type="datetime-local" required value={values.ventana_inicio} onChange={(event) => updateValue('ventana_inicio', event.target.value)} aria-invalid={Boolean(errors.ventana_inicio)} aria-describedby={describedBy('ventana_inicio')} />
          </Field>
          <Field id="ventana_fin" label="Fin de ventana" error={errors.ventana_fin}>
            <input id="ventana_fin" name="ventana_fin" type="datetime-local" required value={values.ventana_fin} onChange={(event) => updateValue('ventana_fin', event.target.value)} aria-invalid={Boolean(errors.ventana_fin)} aria-describedby={describedBy('ventana_fin')} />
          </Field>
        </div>

        <Field id="prioridad" label="Prioridad">
          <select id="prioridad" name="prioridad" value={values.prioridad} onChange={(event) => updateValue('prioridad', event.target.value)}>
            <option value="EXPRESS">Express</option>
            <option value="ESTANDAR">Estándar</option>
            <option value="ECONOMICO">Económico</option>
          </select>
        </Field>

        <Field id="tipo_producto" label="Tipo de producto" error={errors.tipo_producto}>
          <input id="tipo_producto" name="tipo_producto" type="text" maxLength={20} required value={values.tipo_producto} onChange={(event) => updateValue('tipo_producto', event.target.value)} aria-invalid={Boolean(errors.tipo_producto)} aria-describedby={describedBy('tipo_producto')} />
        </Field>

        <button className="submit-button" type="submit" disabled={status === 'submitting'}>
          {status === 'submitting' ? 'Registrando…' : 'Registrar pedido'}
        </button>
      </form>
    </section>
  )
}
