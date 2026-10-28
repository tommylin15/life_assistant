'use strict';
let code='';
const $=id=>document.getElementById(id);
async function api(path,body){const r=await fetch('/api/v1/line/'+path,{method:body===undefined?'GET':'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:(d.error?.message||`請先登入或確認功能已開放（${r.status}）`));return d;}
async function run(fn){try{$('status').textContent='處理中…';await fn();}catch(e){$('status').textContent=e.message;}}
$('start').onclick=()=>run(async()=>{const d=await api('link/start',{});code=d.code;$('code').textContent=d.message;$('challenge').hidden=false;$('confirm').disabled=true;$('suffix').textContent='';$('status').textContent='請傳送綁定碼，再回本頁核對。';});
$('copy').onclick=()=>run(async()=>{await navigator.clipboard.writeText('綁定 '+code);$('status').textContent='已複製。';});
$('check').onclick=()=>run(async()=>{const d=await api('link/check',{code});$('suffix').textContent=d.ready?'請確認 LINE 回覆尾碼為：'+d.line_suffix:'尚未收到，請確認已傳給正確官方帳號。';$('confirm').disabled=!d.ready;$('status').textContent='檢查完成。';});
$('confirm').onclick=()=>run(async()=>{await api('link/confirm',{code});code='';$('challenge').hidden=true;$('status').textContent='綁定完成！回 LINE 開啟「我的 Life」。';});
$('unlink').onclick=()=>{if(confirm('解除後，LINE 舊登入將立即失效。Life 原有資料會保留。確定解除？'))run(async()=>{await api('link/unlink',{});$('status').textContent='已解除綁定。';});};
run(async()=>{const r=await fetch('/auth/me',{credentials:'same-origin'});if(!r.ok)throw Error('請先登入 Life，再重新開啟本頁。');const d=await r.json();$('identity').textContent=`目前 Life 帳號：${d.email}`;await api('link/status');$('login').hidden=true;$('status').textContent='請確認這是你要連結的 Life 帳號。';});
