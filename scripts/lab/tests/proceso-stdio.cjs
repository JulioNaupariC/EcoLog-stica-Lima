// Only a dedicated synthetic marker, never dump the process environment.
console.log(process.env.ECL68_STDIO_TEST === 'synthetic-marker' ? 'env-ok' : 'env-missing');
console.error('stderr-ok');
process.stdin.on('end', () => { console.log('stdin-eof'); process.exit(7); });
process.stdin.resume();
