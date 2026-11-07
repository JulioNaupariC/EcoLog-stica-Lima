// ECL-112: analyze the real Vite output without installing a visualizer or
// changing production configuration. The report is never served by the app.
// Usage (from frontend/): node scripts/analyze-static-resources.mjs NEW_REPORT.json
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { mkdir, readFile, readdir, writeFile } from 'node:fs/promises'
import { cpus, totalmem } from 'node:os'
import { dirname, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { gzipSync } from 'node:zlib'
import { build } from 'vite'

const root = fileURLToPath(new URL('../', import.meta.url))
const destination = process.argv[2]
assert(destination?.endsWith('.json'), 'Specify a new JSON report path')
const sha256 = data => createHash('sha256').update(data).digest('hex')
const portable = path => path.replaceAll('\\', '/')
async function filesIn(directory) {
  const entries = await readdir(directory, { withFileTypes: true })
  return (await Promise.all(entries.map(entry => entry.isDirectory()
    ? filesIn(resolve(directory, entry.name)) : [resolve(directory, entry.name)]))).flat()
}
const publicFiles = await Promise.all((await filesIn(resolve(root, 'public'))).map(async file => {
  const data = await readFile(file)
  return { path: portable(relative(root, file)), bytes: data.length, sha256: sha256(data) }
}))
const sourceFiles = await filesIn(resolve(root, 'src'))
const ownRasterFiles = [...sourceFiles, ...publicFiles.map(file => resolve(root, file.path))]
  .filter(file => /\.(png|jpe?g|gif|webp|avif|ico)$/iu.test(file)).map(file => portable(relative(root, file)))
const imports = []
for (const file of sourceFiles.filter(file => /\.(ts|tsx)$/u.test(file) && !file.includes('.test.') && !portable(relative(root, file)).startsWith('src/test/'))) {
  const text = await readFile(file, 'utf8')
  for (const match of text.matchAll(/from ['"]([^.'"][^'"]*)['"]/gu)) imports.push(match[1])
}
const modules = []
const outputs = await build({ root, logLevel: 'warn', build: { write: false }, plugins: [{
  name: 'ecl112-module-inventory',
  generateBundle(_options, bundle) {
    for (const chunk of Object.values(bundle)) {
      if (chunk.type !== 'chunk') continue
      for (const [id, module] of Object.entries(chunk.modules)) {
        if (module.renderedLength > 0) modules.push({
          path: portable(relative(root, id)), chunk: chunk.fileName, renderedBytes: module.renderedLength,
        })
      }
    }
  },
}] })
const emitted = (Array.isArray(outputs) ? outputs : [outputs]).flatMap(output => output.output)
const assets = emitted.map(item => {
  const data = Buffer.from(item.type === 'chunk' ? item.code : item.source)
  return { file: item.fileName, bytes: data.length, gzipBytes: gzipSync(data).length, sha256: sha256(data),
    ...(item.type === 'chunk' ? { entry: item.isEntry, dynamicEntry: item.isDynamicEntry } : {}) }
}).sort((a, b) => b.bytes - a.bytes)
const packages = JSON.parse(await readFile(resolve(root, 'package.json'), 'utf8')).dependencies
const lucideModules = modules.filter(module => module.path.includes('/lucide-react/'))
const fontFiles = assets.filter(asset => /\.woff2$/u.test(asset.file))
const packageModules = new Map()
for (const module of modules) {
  const name = /node_modules\/((?:@[^/]+\/)?[^/]+)/u.exec(module.path)?.[1]
  if (!name) continue
  const summary = packageModules.get(name) ?? { name, modules: 0, renderedBytes: 0 }
  summary.modules += 1
  summary.renderedBytes += module.renderedBytes
  packageModules.set(name, summary)
}
const report = {
  schema: 1, ticket: 'ECL-112', generatedAt: new Date().toISOString(),
  commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: root, encoding: 'utf8' }).trim(),
  modifiedTrackedFiles: execFileSync('git', ['diff', 'HEAD', '--name-only'], { cwd: root, encoding: 'utf8' }).trim().split(/\r?\n/u).filter(Boolean),
  environment: { node: process.version, cpu: cpus()[0]?.model, ramBytes: totalmem() },
  notes: { gzip: 'Independent gzipSync defaults; not measured HTTP transfer',
    modules: 'Vite/Rolldown rendered module lengths before final minification, not additive network bytes',
    raster: 'Own src/public files only. Leaflet map requests external OpenStreetMap PNG tiles.' },
  publicFiles, ownRasterFiles, declaredDependencies: packages,
  importedPackages: [...new Set(imports)].sort(),
  packageModules: [...packageModules.values()].sort((a, b) => b.renderedBytes - a.renderedBytes),
  fonts: { files: fontFiles, bytes: fontFiles.reduce((sum, file) => sum + file.bytes, 0) },
  javascript: { files: assets.filter(asset => asset.file.endsWith('.js')).length,
    bytes: assets.filter(asset => asset.file.endsWith('.js')).reduce((sum, file) => sum + file.bytes, 0) },
  lucide: { modules: lucideModules, renderedBytes: lucideModules.reduce((sum, module) => sum + module.renderedBytes, 0) },
  assets, modules: modules.sort((a, b) => b.renderedBytes - a.renderedBytes),
}
await mkdir(dirname(resolve(destination)), { recursive: true })
await writeFile(destination, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' })
console.log(JSON.stringify({ report: destination, fonts: report.fonts, javascript: report.javascript,
  ownRasterFiles, publicFiles, lucideModules: lucideModules.length }, null, 2))
