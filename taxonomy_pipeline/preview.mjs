import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile } from '@oai/artifact-tool';

const [root, output] = process.argv.slice(2);
const manifests = [];
for (const name of await fs.readdir(path.join(root, '_taxonomy_analysis/manifests'))) {
  const m=JSON.parse(await fs.readFile(path.join(root,'_taxonomy_analysis/manifests',name),'utf8'));
  if (m.format==='xlsx') manifests.push(m);
}
await fs.mkdir(output,{recursive:true});
const results=[];
for (const m of manifests) {
  const data=await fs.readFile(path.join(root,m.source_file));
  const workbook=await SpreadsheetFile.importXlsx(data.buffer.slice(data.byteOffset,data.byteOffset+data.byteLength));
  for (let i=0;i<m.sheets.length;i++) {
    const item=m.sheets[i];
    const sheet=workbook.worksheets.getItem(item.name);
    const start=item.header_record;
    const col=item.source_columns;
    const labelRange=sheet.getRangeByIndexes(start-1,col,Math.min(6,item.source_rows-start+1),1);
    const values=labelRange.values;
    if (values[0][0]!=='taxonomy_label') throw new Error(`Missing label header ${m.source_file}/${item.name}`);
    const column=n=>{let s='';while(n){let r=(n-1)%26;s=String.fromCharCode(65+r)+s;n=Math.floor((n-1)/26);}return s;};
    const range=`${column(Math.max(1,col-1))}${start}:${column(col+1)}${start+5}`;
    const blob=await workbook.render({sheetIndex:i,range,scale:1.5,format:'png'});
    const name=`${m.file_id}_${i+1}.png`;
    await fs.writeFile(path.join(output,name),new Uint8Array(await blob.arrayBuffer()));
    results.push({file:m.source_file,sheet:item.name,render:name,label_values:values});
  }
}
await fs.writeFile(path.join(output,'preview_checks.json'),JSON.stringify(results,null,2));
console.log(JSON.stringify({workbooks:manifests.length,sheets:results.length}));
