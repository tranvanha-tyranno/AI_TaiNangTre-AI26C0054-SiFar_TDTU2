// Authoring-only dependency: run a copy beside the bundled node_modules junction.
import fs from 'node:fs/promises';
import path from 'node:path';
import { SpreadsheetFile, Workbook } from '@oai/artifact-tool';

const specPath = process.argv[2];
if (!specPath) throw new Error('Usage: node author_public_transfer_workbooks.mjs <workbooks.json> [suite]');
const specs = JSON.parse(await fs.readFile(specPath, 'utf8'));
const previewDir = path.join(path.dirname(specPath), 'previews');
await fs.mkdir(previewDir, { recursive: true });
for (const spec of specs.filter(s => !process.argv[3] || s.suite === process.argv[3])) {
  const wb = Workbook.create();
  for (const source of spec.sheets) {
    const sheet = wb.worksheets.add(source.name);
    const width = Math.max(...source.rows.map(r => r.length));
    const rows = source.rows.map(row => Array.from({ length: width }, (_, c) => {
      const v = row[c] ?? null;
      return typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v) ? new Date(v + 'T00:00:00Z') : v;
    }));
    sheet.getRange(source.start).write(rows);
    const used = sheet.getUsedRange();
    used.format.font = { name: 'Arial', size: 10, color: '#243247' };
    used.format.columnWidth = 22;
    used.format.rowHeight = 24;
    used.format.verticalAlignment = 'center';
    for (const [col, width] of Object.entries(source.widths))
      sheet.getRange(`${col}1:${col}${rows.length}`).format.columnWidth = width;
    for (const merge of source.merges) sheet.mergeCells(merge);
    for (const address of source.headers) {
      const header = sheet.getRange(address);
      header.format.fill = '#E8EEF7';
      header.format.font = { name: 'Arial', size: 10, bold: true, color: '#243247' };
      header.format.wrapText = true;
      header.format.rowHeight = 42;
      header.format.horizontalAlignment = 'center';
    }
    for (const [address, format] of Object.entries(source.formats))
      sheet.getRange(address).setNumberFormat(format);
    const firstHeader = source.headers[0];
    const depth = Number(firstHeader.match(/(\d+)$/)[1]);
    sheet.freezePanes.freezeRows(depth);
    sheet.showGridLines = false;
  }
  wb.recalculate();
  const inspection = await wb.inspect({ kind: 'sheet', include: 'id,name', maxChars: 2500 });
  await fs.writeFile(path.join(previewDir, `${spec.suite}-inspect.ndjson`), inspection.ndjson);
  const errors = await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!|#SPILL!|#CALC!', options:{useRegex:true,maxResults:20},summary:'Formula error scan'});
  await fs.writeFile(path.join(previewDir, `${spec.suite}-errors.ndjson`), errors.ndjson);
  for (const source of spec.sheets) {
    for (const [i, range] of source.previews.entries()) {
      const blob = await wb.render({ sheetName: source.name, range, scale: 1, format: 'png' });
      await fs.writeFile(path.join(previewDir, `${spec.suite}-${source.name}-${i}.png`), new Uint8Array(await blob.arrayBuffer()));
    }
  }
  const file = await SpreadsheetFile.exportXlsx(wb);
  await file.save(spec.file);
  try { await fs.rename(spec.file + '.inspect.ndjson', path.join(previewDir, `${spec.suite}-export.ndjson`)); }
  catch (err) { if (err.code !== 'ENOENT') throw err; }
  console.log(`Exported ${spec.suite}: ${spec.sheets.length} sheets`);
}
