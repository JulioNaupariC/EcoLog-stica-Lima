import {readFile,readdir,writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
const results={compression:'Independent node:zlib.gzipSync defaults; see Vite logs separately',unit:'bytes'};
for(const [label,directory] of [['antes',process.argv[2]],['despues',process.argv[3]]]) {
  const base=resolve(directory);
  const html=await readFile(resolve(base,'index.html'),'utf8');
  const initial=[...html.matchAll(/(?:src|href)="(\/assets\/[^\"]+\.js)"/g)].map(match=>match[1]);
  const files=[];
  for(const name of initial) {
    const data=await readFile(resolve(base,name.slice(1)));
    files.push({file:name,bytes:data.length,gzip_bytes:gzipSync(data).length,sha256:createHash('sha256').update(data).digest('hex')});
  }
  let allJsBytes=0;
  for(const file of await readdir(resolve(base,'assets'))) {
    if(file.endsWith('.js')) allJsBytes+=(await readFile(resolve(base,'assets',file))).length;
  }
  results[label]={initial_js:files,initial_bytes:files.reduce((s,f)=>s+f.bytes,0),initial_gzip_bytes:files.reduce((s,f)=>s+f.gzip_bytes,0),all_js_bytes:allJsBytes};
}
results.initial_reduction_percent=(1-results.despues.initial_bytes/results.antes.initial_bytes)*100;
results.gzip_reduction_percent=(1-results.despues.initial_gzip_bytes/results.antes.initial_gzip_bytes)*100;
await writeFile(process.argv[4],JSON.stringify(results,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify(results,null,2));
