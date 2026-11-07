import { captureSessionDraft, downloadSessionDraft } from './sessionDraft'

afterEach(() => { document.body.innerHTML = ''; vi.restoreAllMocks(); vi.unstubAllGlobals() })

it('captura campos útiles sin contraseñas, ocultos, archivos ni secretos revelados', () => {
  document.body.innerHTML = `<main><form>
    <label for="plate">Placa</label><input id="plate" value="DEMO-001">
    <input name="password" type="password" value="synthetic-secret">
    <input name="revealed-password" value="synthetic-secret">
    <input name="secret" type="hidden" value="synthetic-hidden">
    <input name="file" type="file"><input name="empty" value="">
    <input name="active" type="checkbox" checked><textarea name="note">Prueba</textarea>
    <select name="type"><option value="MOTO" selected>Moto</option></select>
    </form></main>`
  const draft = captureSessionDraft('owner-a', '/vehiculos')!
  expect(draft.campos).toEqual([{ campo: 'Placa', valor: 'DEMO-001' }, { campo: 'active', valor: 'true' },
    { campo: 'note', valor: 'Prueba' }, { campo: 'type', valor: 'MOTO' }])
  expect(JSON.stringify(draft)).not.toContain('synthetic-secret')
  expect(sessionStorage.length).toBe(0)
  expect(localStorage.length).toBe(0)
})

it('sin formulario compatible no inventa un borrador', () => {
  expect(captureSessionDraft('owner-a', '/')).toBeNull()
})

it('solo descarga por acción explícita, omite el propietario y libera la URL', () => {
  vi.useFakeTimers()
  const create = vi.fn().mockReturnValue('blob:synthetic')
  const revoke = vi.fn()
  vi.stubGlobal('URL', class extends URL { static createObjectURL = create; static revokeObjectURL = revoke })
  const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
  downloadSessionDraft({ owner: 'owner-a', pagina: '/vehiculos', campos: [{ campo: 'Placa', valor: 'DEMO-001' }] })
  expect(click).toHaveBeenCalledOnce()
  expect(create).toHaveBeenCalledWith(expect.any(Blob))
  vi.runAllTimers()
  expect(revoke).toHaveBeenCalledWith('blob:synthetic')
  vi.useRealTimers()
})
