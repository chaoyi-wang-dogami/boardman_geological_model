// Run with Playwright available through NODE_PATH or an installed node module.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const html=path.resolve(process.argv[2]);const out=path.resolve(process.argv[3]);
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1500,height:1000},offline:true});
 const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const results={offline:true};
 try {
  await page.goto('file://'+html,{waitUntil:'load'});
  assert.match(await page.locator('#visible-count').innerText(),/^332 of 332/);
  assert.equal(await page.locator('.leaflet-control-scale').count(),1);
  const expected={numeric:{numeric_complete:246,missing_depth:19,missing_elevation:1,inconsistent:66},ground:{recorded_linked_site:36,calculated_only:295,missing:1}};
  for(const [view,categories] of Object.entries(expected)){
   await page.selectOption('#view',view);
   for(const [category,n] of Object.entries(categories)){
    await page.selectOption('#category',category);assert.match(await page.locator('#visible-count').innerText(),new RegExp('^'+n+' of 332'));
   }
  }
  await page.locator('#reset').click();
  for(const [id,strat,lith] of [['MORR_0001751',10,0],['MORR_0052638',17,80],['UMAT_0005858',5,7],['MORR_0000561',5,0]]){
   await page.fill('#search',id);assert.match(await page.locator('#visible-count').innerText(),/^1 of 332/);
   await page.locator('#well-list button').click();
   const detail=await page.locator('#details').innerText();
   assert.ok(detail.includes(`Stratigraphy (${strat} intervals)`));assert.ok(detail.includes(`Lithology (${lith} intervals)`));
   assert.equal(await page.evaluate(()=>window.boardmanMap.selectedWell),id);
  }
  await page.fill('#search','MORR_0000592');await page.locator('#well-list button').click();
  await page.locator('[data-well="MORR_0000596"]').click();
  assert.equal(await page.locator('#scope').inputValue(),'archive');
  assert.match(await page.locator('#details').innerText(),/Archived duplicate/);
  await page.locator('[data-well="MORR_0000592"]').click();
  assert.equal(await page.locator('#scope').inputValue(),'working');
  await page.locator('#reset').click();await page.selectOption('#scope','archive');
  assert.match(await page.locator('#visible-count').innerText(),/^7070 of 7070/);
  await page.selectOption('#scope','all');assert.match(await page.locator('#visible-count').innerText(),/^7402 of 7402/);
  await page.fill('#search','NO_SUCH_WELL');assert.match(await page.locator('#visible-count').innerText(),/^0 of 7402/);
  await page.locator('#reset').click();await page.fill('#search','MORR_0001751');await page.locator('#well-list button').click();
  await page.screenshot({path:path.join(path.dirname(html),'database_map_preview.png'),fullPage:true});
  await page.locator('#reset').click();await page.selectOption('#background','usgs');
  await page.waitForFunction(()=>document.getElementById('tile-status').textContent.includes('unavailable'),{timeout:15000});
  assert.match(await page.locator('#visible-count').innerText(),/^332 of 332/);
  await page.selectOption('#background','none');
  assert.deepEqual(errors,[]);
  Object.assign(results,{passed:true,category_counts:expected,working_wells:332,archived_wells:7070,all_wells:7402,full_interval_details:true,duplicate_navigation:true,search_and_reset:true,tile_failure_handled:true,scale_present:true,page_errors:errors});
  fs.writeFileSync(out,JSON.stringify(results,null,2)+'\n');console.log('Browser checks passed: offline controls, intervals, findings, archive links, counts, tile failure.');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
