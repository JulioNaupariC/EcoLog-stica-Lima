set -eu
npm run typecheck
npm run lint
node --check /validation/verify-incidents-offline.mjs
npm run test:coverage -- --maxWorkers=1 --reporter=default --reporter=junit --outputFile.junit=/evidence/frontend-tests.xml
npm run build
