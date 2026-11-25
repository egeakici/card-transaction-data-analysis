import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const [input, output] = process.argv.slice(2);
const payload = JSON.parse(await fs.readFile(input, 'utf8'));
const workbook = Workbook.create();
for (const item of payload) {
  const sheet = workbook.worksheets.add(item.name);
  sheet.getRange(`A1:A${item.labels.length}`).values = item.labels.map(x => [x]);
}
workbook.recalculate();
const result = await SpreadsheetFile.exportXlsx(workbook);
await result.save(output);
console.log(JSON.stringify({sheets: payload.length, rows: payload.reduce((n,x)=>n+x.labels.length,0)}));
