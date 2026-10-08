import type { DemoItinerary } from '../domain/driverItinerary'
export const DEMO_ITINERARY: DemoItinerary = {
  id: 'DEMO-04',
  stops: [
    { id: 'uno', sequence: 1, order: 'DEMO-101', client: 'Almacén de salida', address: 'Av. Argentina 1250, Lima', window: '09:10 · Entrega registrada', load: '2 bultos · 12 kg', reception: 'Equipo de recepción (ficticio)', instructions: ['Entrega de demostración completada.'], state: 'ENTREGADO' },
    { id: 'dos', sequence: 2, order: 'DEMO-102', client: 'Mercado Central', address: 'Jr. Ucayali 320, Cercado de Lima', window: '09:45–10:00 · Hora estimada 09:50', load: '4 bultos · 28 kg', reception: 'Equipo de recepción (ficticio). Ingreso por puerta lateral.', instructions: ['Verifica la ventana de atención.', 'Usa la puerta lateral de recepción.', 'Ten a mano el código DEMO-102.'], state: 'EN_RUTA' },
    { id: 'tres', sequence: 3, order: 'DEMO-103', client: 'Punto de distribución', address: 'Av. Colonial 540, Lima', window: '10:30–10:45', load: '6 bultos · 36 kg', reception: 'Recepción de demostración', instructions: ['Confirma la recepción con el destinatario ficticio.'], state: 'PENDIENTE' },
    { id: 'cuatro', sequence: 4, order: 'DEMO-104', client: 'Centro de acopio', address: 'Av. Venezuela 850, Lima', window: '11:15–11:30 · +15 min previstos', load: '3 bultos · 18 kg', reception: 'Recepción de demostración', instructions: ['Revisa el horario antes de salir.'], state: 'DEMORADO' },
  ],
  alerts: [{ id: 'demora-demo', title: 'Atención · Vía con demora', description: 'Av. Abancay: +15 min previstos.', instruction: 'Revisa el horario antes de salir.', stopIds: ['dos', 'cuatro'] }],
}
