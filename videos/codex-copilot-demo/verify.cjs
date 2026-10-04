// Owner: video media. Verify actual frames, deterministic seeks and preview controls.
const {chromium}=require('playwright');
const {pathToFileURL}=require('url');
const path=require('path'),fs=require('fs'),os=require('os');
(async()=>{
 const out=fs.mkdtempSync(path.join(os.tmpdir(),'copilot-video-qa-'));
 const browser=await chromium.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1920,height:1080}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  await page.addInitScript(()=>{window.__recording=true;window.__seekRender=true;});
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
  await page.waitForFunction(()=>window.__ready);
  const times=[0,2,6,10.5,15.5,21,23.99];
  const expected=['intro','intro','allowance','delegation','verification','outro','outro'];
  for(let i=0;i<times.length;i++){
   await page.evaluate(t=>window.__seek(t),times[i]);
   const current=await page.evaluate(()=>[...document.querySelectorAll('.scene')].filter(e=>getComputedStyle(e).visibility==='visible').map(e=>e.id));
   if(current.length!==1||current[0]!==expected[i])throw Error('Wrong scene at '+times[i]+': '+current);
   const overflow=await page.evaluate(()=>[...document.querySelectorAll('.scene')].filter(e=>getComputedStyle(e).visibility==='visible').flatMap(s=>[...s.querySelectorAll('.main-copy,.detail')]).filter(e=>e.getBoundingClientRect().right>1920||e.getBoundingClientRect().bottom>830).map(e=>e.className));
   if(overflow.length)throw Error('Canvas overflow: '+overflow);
   await page.screenshot({path:path.join(out,'frame-'+i+'.png')});
  }
  await page.evaluate(()=>window.__seek(6));const before=await page.screenshot();
  await page.evaluate(()=>{window.__seek(21);window.__seek(6);});const after=await page.screenshot();
  if(!before.equals(after))throw Error('Non-deterministic seek');
  const preview=await browser.newPage({viewport:{width:1440,height:900}});
  preview.on('pageerror',e=>errors.push(e.message));
  await preview.goto(pathToFileURL(path.join(__dirname,'index.html')).href);await preview.waitForFunction(()=>window.__ready);
  await preview.click('#restart');await preview.waitForTimeout(250);await preview.click('#play');
  if(await preview.locator('#play').textContent()!=='Play')throw Error('Pause failed');
  await preview.click('#sound');if(await preview.locator('#sound').textContent()!=='Sound on')throw Error('Sound control failed');
  await preview.locator('#scrub').fill('15.5');await preview.locator('#scrub').dispatchEvent('input');
  if(!((await preview.locator('#time').textContent()).startsWith('15.5')))throw Error('Scrub failed');
  await preview.setViewportSize({width:375,height:667});
  await preview.waitForFunction(()=>document.querySelector('#stage').getBoundingClientRect().width<376);
  const bounds=await preview.locator('#stage').boundingBox();if(bounds.width>376||bounds.height>668)throw Error('Fit failed');
  if(errors.length)throw Error(errors.join('\n'));
  console.log(JSON.stringify({ok:true,frames:times,deterministic:true,controls:true,responsive:true,consoleErrors:0,qaDir:out}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
