import { useEffect, useRef, useState } from 'react'
import * as L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { mapPositions, routeTime } from '../domain/operationRoutes'
import type { OperationRoute, RouteAlert } from '../domain/operationRoutes'

export function OperationRouteMap({ route, alerts, selectedStopId }: { route: OperationRoute; alerts: RouteAlert[]; selectedStopId?: string }) {
  const container = useRef<HTMLDivElement>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    if (!container.current) return
    let map: L.Map | undefined
    let observer: ResizeObserver | undefined
    try {
      map = L.map(container.current, { scrollWheelZoom: false, attributionControl: false, zoomControl: false })
      L.control.zoom({ position: 'topright', zoomInTitle: 'Acercar mapa', zoomOutTitle: 'Alejar mapa' }).addTo(map)
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19, updateWhenIdle: true, keepBuffer: 1,
      }).on('tileerror', () => setError('No se pudieron cargar las teselas. El trazado y la lista de paradas siguen disponibles.')).addTo(map)
      const positions = mapPositions(route)
      L.polyline(positions, { color: '#036b59', weight: 5 }).addTo(map)
      map.fitBounds(L.latLngBounds(positions), { padding: [28, 28], maxZoom: 15 })
      for (const stop of route.paradas) {
        const content = document.createElement('p')
        content.textContent = `Parada ${stop.secuencia}. Pedido ${stop.pedido_id}. ` +
          `ETA estimada: ${routeTime(stop.eta)} (Lima). Ventana: ${routeTime(stop.ventana_inicio)} a ${routeTime(stop.ventana_fin)}. ` +
          `Estado: ${stop.estado}. ` + alerts.filter(a => a.paradaId === stop.parada_id || !a.paradaId)
            .map(a => `${a.bloqueo ? 'Bloqueo configurado' : 'Riesgo informativo'}, ${a.tipo}: ${a.texto}. Severidad ${a.severidad}. Fuente ${a.fuente}, ${routeTime(a.hora)}. Alcance: ${a.alcance}.`).join(' ')
        const marker = L.marker([stop.latitud, stop.longitud], {
          title: `Parada ${stop.secuencia}`, alt: `Parada ${stop.secuencia}`,
          keyboard: false, interactive: false,
          icon: L.divIcon({ className: 'route-stop-pin', html: String(stop.secuencia), iconSize: [36, 36], iconAnchor: [18, 18] }),
        }).addTo(map).bindPopup(content)
        if (stop.parada_id === selectedStopId) marker.openPopup()
      }
      if (selectedStopId) {
        container.current.focus({ preventScroll: true })
        container.current.scrollIntoView({ block: 'center' })
      }
      if (typeof ResizeObserver !== 'undefined') {
        const current = map
        observer = new ResizeObserver(() => current.invalidateSize())
        observer.observe(container.current)
      }
    } catch {
      void Promise.resolve().then(() => setError('El mapa no está disponible. Consulta la lista de paradas.'))
    }
    return () => { observer?.disconnect(); map?.remove() }
  }, [route, alerts, selectedStopId])
  return <div className="operation-map-panel">
    <p id="route-map-help" className="field-hint">Mapa interactivo: usa las flechas para desplazarte y +/− para acercar o alejar. Los números siguen el orden de la lista. Usa «Ver parada en mapa» en la lista para consultar su detalle.</p>
    {error ? <p role="status" className="route-map-warning">{error}</p> : null}
    <div ref={container} className="operation-route-map" role="region" aria-label={`Mapa de ruta ${route.vehiculo.placa}`} aria-describedby="route-map-help" />
    <p className="map-attribution">© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap contributors</a> · <a href="https://leafletjs.com/">Leaflet</a></p>
  </div>
}
