// Run one spec per process beside the authoring-only bundled @oai/artifact-tool.
import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const specPath=process.argv[2];
if (!specPath) throw new Error('Usage: node author_long_workbooks.mjs <one-suite-spec.json>');
const [spec]=JSON.parse(await fs.readFile(specPath,'utf8'));
const previews=path.join(path.dirname(path.dirname(specPath)),'previews',spec.suite);
await fs.mkdir(previews,{recursive:true});
const wb=Workbook.create();
for(const source of spec.sheets) {
  const sh=wb.worksheets.add(source.name);
  const width=Math.max(...source.rows.map(r=>r.length));
  const last=source.rows.length;
  let dateCount=0;
  const rows=source.rows.map(row=>Array.from({length:width},(_,i)=> {
      const v=row[i]??null;
      if(typeof v==='string' && /^\d{4}-\d{2}-\d{2}(?: \d{2}:\d{2}:\d{2})?$/.test(v)) {
        dateCount++;
        // Native Excel dates are day serials. Writing the serial explicitly
        // avoids local-midnight coercion of a JS Date in the authoring engine.
        const iso=v.length===10 ? v+'T00:00:00Z' : v.replace(' ','T')+'Z';
        return (Date.parse(iso)-Date.UTC(1899,11,30))/86400000;
      }
      return v;
  }));
  sh.getRange('A1').write(rows);
  console.log(`Wrote ${source.name}: ${last} rows`);
  const used=sh.getUsedRange();
  used.format.font={name:'Arial',size:10,color:'#243247'};
  used.format.rowHeight=22;
  used.format.columnWidth=22;
  used.format.verticalAlignment='center';
  for(const [col,width] of Object.entries(source.widths))
    sh.getRange(`${col}1:${col}${last}`).format.columnWidth=width;
  for(const merged of source.merges) sh.mergeCells(merged);
  for(const address of source.headers) {
    const h=sh.getRange(address);
    h.format.fill='#E8EEF7';
    h.format.font={name:'Arial',size:10,bold:true,color:'#243247'};
    h.format.wrapText=true;
    h.format.rowHeight=40;
    h.format.horizontalAlignment='center';
  }
  for(const [range,format] of Object.entries(source.formats)) sh.getRange(range).setNumberFormat(format);
  sh.freezePanes.freezeRows(Number(source.headers[0].match(/(\d+)$/)[1]));
  sh.showGridLines=false;
  console.log(`Populated ${source.name}: ${last} rows, ${width} columns, ${dateCount} date cells`);
}
wb.recalculate();
const inspected=await wb.inspect({kind:'sheet',include:'id,name',maxChars:3000});
await fs.writeFile(path.join(previews,'sheets.ndjson'),inspected.ndjson);
for(const source of spec.sheets) {
  for(const [i,range] of source.previews.entries()) {
    const image=await wb.render({sheetName:source.name,range,scale:1,format:'png'});
    await fs.writeFile(path.join(previews,`${source.name}-${i}.png`),new Uint8Array(await image.arrayBuffer()));
  }
}
const output=await SpreadsheetFile.exportXlsx(wb);
await output.save(spec.file);
try { await fs.rename(spec.file+'.inspect.ndjson',path.join(previews,'export.ndjson')); }
catch(err) { if(err.code!=='ENOENT') throw err; }
console.log(`Exported ${spec.suite}; RSS ${(process.memoryUsage().rss/1048576).toFixed(1)} MiB`);
// All exports and diagnostic writes have been awaited; end this one-file CLI.
process.exit(0);
