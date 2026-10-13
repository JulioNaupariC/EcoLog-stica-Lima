import { MapPinOff } from 'lucide-react'
import { EmptyState, LinkButton } from '../components/ui'

export function NotFoundPage() {
  return <EmptyState icon={MapPinOff} title="Página no encontrada" headingLevel={1} titleId="not-found-title"
    action={<LinkButton to="/" variant="secondary">Volver al inicio</LinkButton>}>
    <p>Error 404. La dirección solicitada no existe en esta aplicación.</p>
  </EmptyState>
}
