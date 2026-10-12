const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  for (const f of process.argv.slice(2)) {
    const p = await b.newPage({ viewport: { width: 1340, height: 800 }, deviceScaleFactor: 2 });
    await p.goto('file://' + process.cwd() + '/' + f + '.html');
    await p.waitForTimeout(350);
    await p.screenshot({ path: f + '.png', fullPage: true });
    console.log(f + '.png');
  }
  await b.close();
})();
