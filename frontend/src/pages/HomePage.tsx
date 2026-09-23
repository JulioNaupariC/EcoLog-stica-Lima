export function HomePage() {
  return (
    <section className="hero" aria-labelledby="home-title">
      <p className="eyebrow">Frontend operativo</p>
      <h1 id="home-title">Rutas sostenibles para Lima</h1>
      <p className="lead">
        EcoLogística Lima cuenta con una base React y TypeScript lista para
        incorporar sus próximos incrementos funcionales.
      </p>
      <div className="status" role="status">
        <span className="status-marker" aria-hidden="true" />
        Aplicación iniciada correctamente
      </div>
    </section>
  )
}
