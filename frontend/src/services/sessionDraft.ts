/** ECL-83: private, in-memory draft until this tab reloads; never credentials. */
export interface SessionDraft {
  owner: string
  pagina: string
  campos: { campo: string; valor: string }[]
}

export function captureSessionDraft(owner: string, pagina: string): SessionDraft | null {
  const controls = document.querySelectorAll<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>(
    'main form input, main form select, main form textarea',
  )
  const campos = [...controls].filter(control => {
    const sensitive = /password|contrasena|contraseña|token|secret|one-time-code/iu
    return !['password', 'hidden', 'file', 'submit', 'button'].includes(control.type) &&
      !sensitive.test(`${control.id} ${control.name} ${control.autocomplete}`)
  }).map(control => ({
    campo: control.labels?.[0]?.textContent?.trim() || control.name || control.id,
    valor: control instanceof HTMLInputElement && ['checkbox', 'radio'].includes(control.type)
      ? String(control.checked) : control.value,
  })).filter(field => field.campo && field.valor !== '')
  return campos.length ? { owner, pagina, campos } : null
}

export function downloadSessionDraft(draft: SessionDraft): void {
  // The owner is used only for access checks in App; omit it from the file.
  const file = new Blob([JSON.stringify({ pagina: draft.pagina, campos: draft.campos }, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(file)
  const link = document.createElement('a')
  link.href = url
  link.download = 'ecologistica-borrador.json'
  document.body.append(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 0)
}
