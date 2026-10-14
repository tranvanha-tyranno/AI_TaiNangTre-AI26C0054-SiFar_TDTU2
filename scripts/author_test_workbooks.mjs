// Run from a working directory with the bundled @oai/artifact-tool dependency.
import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const specPath = process.argv[2];
if (!specPath) throw new Error('Usage: node author_test_workbooks.mjs <workbooks.json>');
const specs = JSON.parse(await fs.readFile(specPath, 'utf8'));
const previewDir = path.join(path.dirname(specPath), 'previews');
await fs.mkdir(previewDir, { recursive: true });
function column(n) {
  let out = '';
  while(n) { n--; out = String.fromCharCode(65+n%26)+out; n = Math.floor(n/26); }
  return out;
}
for (const spec of specs) {
  const wb = Workbook.create();
  for (const source of spec.sheets) {
    const sheet = wb.worksheets.add(source.name);
    const rows = source.rows.map(row => row.map(value =>
      typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(value+'T00:00:00Z') : value));
    const width = Math.max(...rows.map(row => row.length));
    const padded = rows.map(row => [...row, ...Array(width-row.length).fill(null)]);
    sheet.getRange(source.start).write(padded);
    const used = sheet.getUsedRange();
    used.format.font = { name:'Arial', size:10, color:'#243247' };
    used.format.rowHeight = 23;
    used.format.columnWidth = 19;
    used.format.verticalAlignment = 'center';
    sheet.getRange(`A1:A${rows.length}`).format.columnWidth = 25;
    const headerDepth = spec.suite.startsWith('06') ? 2 : spec.suite.startsWith('08') ? 3 : 1;
    const header = sheet.getRange(`A1:${column(width)}${headerDepth}`);
    header.format.fill = '#E8EEF7';
    header.format.font = { name:'Arial', size:10, bold:true, color:'#243247' };
    header.format.wrapText = true;
    header.format.rowHeight = 30;
    header.format.horizontalAlignment = 'center';
    for (const merge of source.merges) sheet.mergeCells(merge);
    for (const [range, format] of Object.entries(source.formats)) sheet.getRange(range).setNumberFormat(format);
    if(source.name === 'Records') {
      sheet.getRange(`B1:B${rows.length}`).format.columnWidth = 32;
      sheet.getRange(`F1:F${rows.length}`).format.columnWidth = 38;
    }
    if(source.name === 'People') {
      sheet.getRange(`C1:C${rows.length}`).format.columnWidth = 25;
      sheet.getRange(`H1:H${rows.length}`).format.columnWidth = 25;
    }
    if(source.name === 'Indicators') {
      sheet.getRange('A13:I13').merge();
      sheet.getRange('A13').format.font = { name:'Arial', size:10, italic:true, color:'#64748B' };
    }
    sheet.showGridLines = false;
    sheet.freezePanes.freezeRows(headerDepth);
  }
  wb.recalculate();
  const inspection = await wb.inspect({kind:'sheet', include:'id,name', maxChars:1500});
  await fs.writeFile(path.join(previewDir, spec.suite+'-inspect.ndjson'), inspection.ndjson);
  for (const source of spec.sheets) {
    const endColumn = source.name === 'Big' ? 'D' : column(Math.max(...source.rows.map(row => row.length)));
    const preview = await wb.render({sheetName:source.name,range:`A1:${endColumn}${Math.min(source.rows.length,13)}`,scale:1,format:'png'});
    await fs.writeFile(path.join(previewDir, spec.suite+'-'+source.name+'.png'),new Uint8Array(await preview.arrayBuffer()));
    if(source.name === 'Big') {
      const wide = await wb.render({sheetName:source.name,range:'AI1:AI8',scale:1,format:'png'});
      await fs.writeFile(path.join(previewDir,spec.suite+'-wide.png'),new Uint8Array(await wide.arrayBuffer()));
    }
  }
  const file = await SpreadsheetFile.exportXlsx(wb);
  await file.save(spec.file);
  // Export diagnostics belong with previews, not the dataset inputs.
  const diagnostic = spec.file+'.inspect.ndjson';
  try { await fs.rename(diagnostic,path.join(previewDir,spec.suite+'-export.ndjson')); }
  catch (error) { if (error.code !== 'ENOENT') throw error; }
  console.log('Exported '+spec.suite);
}
