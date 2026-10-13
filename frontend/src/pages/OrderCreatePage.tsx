import { FormEvent, useRef, useState } from 'react'
import { ClientCombobox } from '../components/ClientCombobox'
import { ClientPreferencesProposal } from '../components/ClientPreferencesProposal'
import { FormField as Field } from '../components/FormField'
import { CheckCircle2, Send } from 'lucide-react'
import { Alert, Button, FormActions, FormSection, PageHeader } from '../components/ui'
import type { ClientOption } from '../services/clients'
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
    errors.cliente_id = 'Selecciona un cliente de la lista.'
  } else if (!UUID_PATTERN.test(clienteId)) {
    errors.cliente_id = 'Selecciona un cliente válido de la lista.'
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
  const [client, setClient] = useState<ClientOption | null>(null)
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

  const describedBy = (field: FormField) => [errors[field] ? `${field}-error` : null, `${field}-hint`].filter(Boolean).join(' ')
  // Inline validation: re-check a field with content when the user leaves it.
  const validateField = (field: FormField) => {
    if (field === 'cliente_id' || !values[field as keyof OrderFormValues]) return
    const fieldError = validate(values).errors[field]
    setErrors((current) => ({ ...current, [field]: fieldError }))
  }
  const fieldProps = (field: FormField) => ({
    'aria-invalid': Boolean(errors[field]),
    'aria-describedby': describedBy(field),
    onBlur: () => validateField(field),
  })

  return (
    <section className="order-page" aria-labelledby="order-title">
      <PageHeader titleId="order-title" title="Registrar pedido" eyebrow="Gestión de pedidos"
        breadcrumbs={[{ label: 'Inicio', to: '/' }, { label: 'Registrar pedido' }]}
        description="Busca un cliente existente por su nombre y completa los datos necesarios para la planificación." />

      {globalError ? <Alert tone="danger">{globalError}</Alert> : null}
      {status === 'success' && createdOrder ? (
        <Alert tone="success" role="status" title="Pedido registrado.">
          <span className="alert-line">ID: {createdOrder.pedido_id}</span>
          <span className="alert-line">Estado: {createdOrder.estado}</span>
        </Alert>
      ) : null}

      <form className="form-stack order-form" onSubmit={(event) => { void handleSubmit(event) }} noValidate>
        <FormSection legend="Cliente" description="El pedido se asocia a un cliente registrado.">
          <ClientCombobox
            id="cliente_id"
            label="Cliente"
            hint="Escribe parte del nombre o pega el identificador del cliente."
            required
            error={errors.cliente_id}
            selected={client}
            onSelect={(option) => {
              setClient(option)
              updateValue('cliente_id', option?.cliente_id ?? '')
            }}
          />
          {client ? (
            <ClientPreferencesProposal
              key={client.cliente_id}
              clientId={client.cliente_id}
              orderReference={values.referencia}
              onUseReference={(reference) => updateValue('referencia', reference)}
            />
          ) : null}
        </FormSection>

        <FormSection legend="Lugar de entrega" description="Indica coordenadas completas o un punto de referencia verificable (RN-006).">
          <Field id="direccion" label="Dirección" error={errors.direccion} hint="Calle, número y distrito.">
            <input id="direccion" name="direccion" type="text" maxLength={255} required value={values.direccion} onChange={(event) => updateValue('direccion', event.target.value)} {...fieldProps('direccion')} />
          </Field>
          <Field id="referencia" label="Punto de referencia" error={errors.referencia} hint="Ayuda al conductor a ubicar la entrega.">
            <input id="referencia" name="referencia" type="text" maxLength={255} value={values.referencia} onChange={(event) => updateValue('referencia', event.target.value)} {...fieldProps('referencia')} />
          </Field>
          <div className="form-grid">
            <Field id="latitud" label="Latitud" error={errors.latitud} hint="Entre -90 y 90. Ej.: -12.0464.">
              <input id="latitud" name="latitud" type="number" min="-90" max="90" step="any" value={values.latitud} onChange={(event) => updateValue('latitud', event.target.value)} {...fieldProps('latitud')} />
            </Field>
            <Field id="longitud" label="Longitud" error={errors.longitud} hint="Entre -180 y 180. Ej.: -77.0428.">
              <input id="longitud" name="longitud" type="number" min="-180" max="180" step="any" value={values.longitud} onChange={(event) => updateValue('longitud', event.target.value)} {...fieldProps('longitud')} />
            </Field>
          </div>
        </FormSection>

        <FormSection legend="Ventana de entrega" description="Horario en el que el cliente puede recibir el pedido.">
          <div className="form-grid">
            <Field id="ventana_inicio" label="Inicio de ventana" error={errors.ventana_inicio} hint="Fecha y hora de Lima.">
              <input id="ventana_inicio" name="ventana_inicio" type="datetime-local" required value={values.ventana_inicio} onChange={(event) => updateValue('ventana_inicio', event.target.value)} {...fieldProps('ventana_inicio')} />
            </Field>
            <Field id="ventana_fin" label="Fin de ventana" error={errors.ventana_fin} hint="Debe ser posterior al inicio.">
              <input id="ventana_fin" name="ventana_fin" type="datetime-local" required value={values.ventana_fin} onChange={(event) => updateValue('ventana_fin', event.target.value)} {...fieldProps('ventana_fin')} />
            </Field>
          </div>
        </FormSection>

        <FormSection legend="Carga" description="Datos que usará la planificación para asignar capacidad.">
          <div className="form-grid">
            <Field id="peso_kg" label="Peso (kg)" error={errors.peso_kg} hint="Hasta 2 decimales. Ej.: 12.50.">
              <input id="peso_kg" name="peso_kg" type="text" inputMode="decimal" required value={values.peso_kg} onChange={(event) => updateValue('peso_kg', event.target.value)} {...fieldProps('peso_kg')} />
            </Field>
            <Field id="volumen_m3" label="Volumen (m³)" error={errors.volumen_m3} hint="Hasta 3 decimales. Ej.: 0.080.">
              <input id="volumen_m3" name="volumen_m3" type="text" inputMode="decimal" required value={values.volumen_m3} onChange={(event) => updateValue('volumen_m3', event.target.value)} {...fieldProps('volumen_m3')} />
            </Field>
            <Field id="tipo_producto" label="Tipo de producto" error={errors.tipo_producto} hint="Hasta 20 caracteres. Ej.: Perecible.">
              <input id="tipo_producto" name="tipo_producto" type="text" maxLength={20} required value={values.tipo_producto} onChange={(event) => updateValue('tipo_producto', event.target.value)} {...fieldProps('tipo_producto')} />
            </Field>
            <Field id="prioridad" label="Prioridad" hint="Express y perecible penalizan más la tardanza (RN-007).">
              <select id="prioridad" name="prioridad" value={values.prioridad} aria-describedby="prioridad-hint" onChange={(event) => updateValue('prioridad', event.target.value)}>
                <option value="EXPRESS">Express</option>
                <option value="ESTANDAR">Estándar</option>
                <option value="ECONOMICO">Económico</option>
              </select>
            </Field>
          </div>
        </FormSection>

        <FormActions>
          <Button type="submit" icon={status === 'success' ? CheckCircle2 : Send} disabled={status === 'submitting'}>
            {status === 'submitting' ? 'Registrando…' : 'Registrar pedido'}
          </Button>
        </FormActions>
      </form>
    </section>
  )
}
