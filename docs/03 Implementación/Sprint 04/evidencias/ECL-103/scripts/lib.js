const BASE='http://127.0.0.1:4173', API='http://127.0.0.1:8000';
async function login(p, email, pw) {
  await p.goto(BASE+'/login');
  await p.getByLabel(/correo/i).fill(email);
  await p.getByLabel(/contraseña/i).first().fill(pw);
  await p.getByRole('button', {name: /iniciar sesión/i}).click();
  await p.waitForURL(BASE+'/', {timeout: 15000});
}
module.exports = { BASE, API, login };
