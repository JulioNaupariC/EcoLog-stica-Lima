// Verifica contraste WCAG 2.1 AA de las combinaciones de tokens usadas en la UI.
// Uso: node scripts/check-contrast.mjs   (sale con 1 si alguna combinación no cumple)
import { readFile } from 'node:fs/promises'

const css = await readFile(new URL('../src/styles/tokens.css', import.meta.url), 'utf8')

function block(selectorStart) {
  const start = css.indexOf(selectorStart)
  const open = css.indexOf('{', start)
  let depth = 0
  for (let i = open; i < css.length; i += 1) {
    if (css[i] === '{') depth += 1
    if (css[i] === '}' && --depth === 0) return css.slice(open + 1, i)
  }
  throw new Error('Bloque no encontrado: ' + selectorStart)
}

function tokens(text) {
  const map = {}
  for (const [, name, value] of text.matchAll(/--([\w-]+):\s*([^;]+);/gu)) map[name] = value.trim()
  return map
}

const light = tokens(block(':root {'))
const dark = { ...light, ...tokens(block(':root[data-theme="dark"]')) }

function resolveColor(theme, name) {
  let value = theme['color-' + name]
  for (let guard = 0; value?.startsWith('var(') && guard < 5; guard += 1) value = theme[value.slice(6, -1)]
  if (!/^#[0-9a-f]{6}$/iu.test(value ?? '')) throw new Error(`--color-${name} no es un color hexadecimal: ${value}`)
  return value
}

function luminance(hex) {
  const channels = [1, 3, 5].map(index => parseInt(hex.slice(index, index + 2), 16) / 255)
    .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
}

function ratio(a, b) {
  const [high, low] = [luminance(a), luminance(b)].sort((x, y) => y - x)
  return (high + 0.05) / (low + 0.05)
}

// [primer plano, fondo, mínimo, uso]
const PAIRS = [
  ['text', 'bg', 4.5, 'Texto principal sobre el fondo'],
  ['text', 'surface', 4.5, 'Texto principal sobre tarjetas'],
  ['text', 'surface-muted', 4.5, 'Texto sobre cabeceras de tabla'],
  ['text-muted', 'bg', 4.5, 'Texto secundario sobre el fondo'],
  ['text-muted', 'surface', 4.5, 'Ayudas y metadatos en tarjetas'],
  ['text-muted', 'surface-muted', 4.5, 'Cabeceras de tabla y campos deshabilitados'],
  ['primary-contrast', 'primary', 4.5, 'Texto de botón primario'],
  ['primary-contrast', 'primary-hover', 4.5, 'Botón primario en hover'],
  ['link', 'surface', 4.5, 'Enlaces y navegación activa'],
  ['link', 'bg', 4.5, 'Migas de pan y enlaces de página'],
  ['link', 'surface-muted', 4.5, 'Enlaces en filas resaltadas'],
  ['link', 'brand-50', 4.5, 'Enlace/etiqueta sobre siguiente parada'],
  ['text', 'brand-50', 4.5, 'Texto de la siguiente parada'],
  ['text-muted', 'brand-50', 4.5, 'Metadatos de la siguiente parada'],
  ['success-fg', 'success-bg', 4.5, 'Badge/alerta de éxito'],
  ['warning-fg', 'warning-bg', 4.5, 'Badge/alerta de advertencia'],
  ['danger-fg', 'danger-bg', 4.5, 'Badge/alerta de error'],
  ['danger-fg', 'surface', 4.5, 'Mensaje de error bajo un campo'],
  ['info-fg', 'info-bg', 4.5, 'Badge/alerta informativa'],
  ['neutral-fg', 'neutral-bg', 4.5, 'Badge neutral («Inactivo», «Próximamente»)'],
  ['sustain-fg', 'sustain-bg', 4.5, 'Indicador de sostenibilidad'],
  ['primary-contrast', 'primary', 4.5, 'Número de parada'],
  ['focus', 'surface', 3, 'Contorno de foco (elemento de interfaz)'],
  ['focus', 'bg', 3, 'Contorno de foco sobre el fondo'],
  ['focus', 'surface-muted', 3, 'Foco sobre tablas y detalles resaltados'],
  ['border-strong', 'surface', 3, 'Borde de campos de formulario'],
  ['border-strong', 'bg', 3, 'Borde de acciones secundarias sobre la página'],
  ['primary', 'surface', 3, 'Borde destacado de la siguiente parada'],
]

let failures = 0
const results = []
const json = process.argv.includes('--json')
for (const [theme, name] of [[light, 'claro'], [dark, 'oscuro']]) {
  if (!json) console.log(`\nTema ${name}`)
  for (const [fg, bg, min, use] of PAIRS) {
    const value = ratio(resolveColor(theme, fg), resolveColor(theme, bg))
    const ok = value >= min
    if (!ok) failures += 1
    results.push({ theme: name, foreground: fg, background: bg, ratio: value, minimum: min, use, passed: ok })
    if (!json) console.log(`${ok ? 'OK ' : 'FAIL'} ${value.toFixed(2).padStart(5)}:1 (mín. ${min}) --color-${fg} / --color-${bg} · ${use}`)
  }
}
// Panel de marca del login: texto inverso sobre verde profundo (claro) y texto sobre verde oscuro (oscuro).
const authLight = ratio(resolveColor(light, 'text-inverse'), resolveColor(light, 'brand-900'))
const authDark = ratio(resolveColor(dark, 'text'), resolveColor(dark, 'brand-50'))
for (const [value, label] of [[authLight, 'claro'], [authDark, 'oscuro']]) {
  const ok = value >= 4.5
  if (!ok) failures += 1
  results.push({ theme: label, use: 'Panel de marca del login', ratio: value, minimum: 4.5, passed: ok })
  if (!json) console.log(`${ok ? 'OK ' : 'FAIL'} ${value.toFixed(2).padStart(5)}:1 (mín. 4.5) panel de marca del login, tema ${label}`)
}
if (json) console.log(JSON.stringify({ scope: 'Token contrast pairs only; not a full WCAG conformance claim', results, failures }, null, 2))
else console.log(failures ? `\n${failures} combinaciones no cumplen AA.` : '\nLas combinaciones revisadas cumplen los mínimos de contraste AA.')
process.exitCode = failures ? 1 : 0
