// Offline browser smoke: no real LINE or Google identity and no external writes.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:390,height:844}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const origin='https://life.example';
 let commits=0;
 await page.route('**/*', async route=>{
  const u=new URL(route.request().url());
  if(u.hostname==='static.line-scdn.net')return route.fulfill({contentType:'text/javascript',body:'window.liff={init:async()=>{},isLoggedIn:()=>true,getIDToken:()=>"mock-token"};'});
  if(u.pathname.startsWith('/line/')){const file=path.join(__dirname,'../web',u.pathname);return route.fulfill({contentType:u.pathname.endsWith('.js')?'text/javascript':u.pathname.endsWith('.css')?'text/css':'text/html',body:fs.readFileSync(file)});}
  let data;
  if(u.pathname==='/api/v1/line/config')data={origin,liff_id:'123-test'};
  else if(u.pathname==='/api/v1/line/session')data={linked:true,name:'測試使用者'};
  else if(u.pathname==='/api/v1/inbox/interpret')data={candidates:[{target:'note',fields:{title:'水電師傅',body:'下週再來看'},ambiguities:[]}]};
  else if(u.pathname==='/api/v1/inbox/commit'){commits++;data={status:'COMPLETE',results:[{status:'CREATED',entity_id:'n1'}]};}
  else if(u.pathname==='/api/v1/line/search')data={items:[{id:'n1',title:'水電師傅',detail:'<script>evil()</script>',kind:u.searchParams.get('kind')}],has_more:false};
  else if(u.pathname==='/api/v1/shopping-lists')data=[{id:'list1',name:'日常採買',items:[{id:'i1',name:'牛奶',is_done:false}]}];
  else if(u.pathname.startsWith('/api/v1/shopping-items/'))data={id:'i1',is_done:true};
  else if(u.pathname==='/api/v1/integrations/google/calendar/events')data={events:[{summary:'看牙醫',start:{dateTime:'2026-10-29T15:00:00+08:00'}}]};
  else if(u.pathname==='/api/v1/free-events/curated')data={items:[{identity_key:'a'.repeat(64),title:'週末活動',summary:'待確認活動',original_url:'https://example.test',verification_status:'pending_review',fee_kind:'unknown'}],has_more:false};
  else if(u.pathname.endsWith('/actions/save')){assert.equal(route.request().method(),'PUT');data={active:true};}
  else if(u.pathname==='/api/v1/line/drafts')data={items:[]};
  else return route.fulfill({status:404,contentType:'application/json',body:'{"detail":"Unexpected mock route"}'});
  return route.fulfill({contentType:'application/json',body:JSON.stringify(data)});
 });
 await page.goto(origin+'/line/index.html');
 await page.getByLabel('內容',{exact:true}).fill('下週水電再來看');
 await page.getByRole('button',{name:'解析並檢查'}).click();
 await page.getByRole('button',{name:'確認新增',exact:true}).click();
 await page.getByText('已新增；再次點選不會重複建立。').waitFor();assert.equal(commits,1);
 await page.locator('[data-page=search]').click();
 await page.getByText('<script>evil()</script>',{exact:true}).waitFor();
 await page.locator('[data-page=shopping]').click();
 await page.getByLabel('牛奶').check();
 await page.locator('[data-page=calendar]').click();await page.getByText('看牙醫',{exact:true}).waitFor();
 await page.locator('[data-page=activities]').click();await page.getByRole('button',{name:'收藏',exact:true}).click();
 await page.getByText('已收藏。',{exact:true}).waitFor();
 assert.equal(errors.length,0,errors.join('\n'));
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
 await browser.close();console.log('PASS: capture confirmation, escaped search, shopping checkbox, calendar, activity save, mobile width');
})().catch(e=>{console.error(e);process.exit(1);});
