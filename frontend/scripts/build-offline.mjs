import { readdir, readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { resolve } from 'node:path'
const root = resolve('dist')
const files = ['index.html', ...(await readdir(resolve(root, 'assets'))).filter(name => /\.(js|css)$/u.test(name)).map(name => `assets/${name}`)]
const hash = createHash('sha256')
for (const file of files) hash.update(await readFile(resolve(root, file)))
const version = hash.digest('hex')
await writeFile(resolve(root, 'offline-shell.json'), JSON.stringify({ version, files }))
const worker = await readFile(resolve(root, 'sw.js'), 'utf8')
await writeFile(resolve(root, 'sw.js'), worker.replace('__SHELL_VERSION__', version))
