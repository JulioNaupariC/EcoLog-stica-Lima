import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <section className="not-found" aria-labelledby="not-found-title">
      <p className="error-code">404</p>
      <h1 id="not-found-title">Página no encontrada</h1>
      <p>La dirección solicitada no existe en esta aplicación.</p>
      <Link className="button-link" to="/">
        Volver al inicio
      </Link>
    </section>
  )
}
