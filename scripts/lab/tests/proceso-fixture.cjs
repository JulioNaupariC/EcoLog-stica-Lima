// Isolated process: no network, database, filesystem or environment output.
const mode = process.argv[2];
console.log(`fixture-start mode=${mode}`);
if (mode === 'Normal') {
  setTimeout(() => { console.log('fixture-normal-exit code=0'); process.exit(0); }, 8000);
} else {
  setInterval(() => {}, 1000);
}
