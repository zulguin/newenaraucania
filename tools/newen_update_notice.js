/* Newen: comprobación de versiones Android/PC en el cliente web empaquetado. */
(function(){
'use strict';
const current=document.currentScript?.dataset.version;
const platform=window.Capacitor?.getPlatform?.()==='android'?'android':/Android/i.test(navigator.userAgent)?'android':/Electron/i.test(navigator.userAgent)?'windows':null;
if(!current||!platform)return;
const base='https://github.com/zulguin/newenaraucania/releases/download/';
const version=s=>/^v?\d+\.\d+\.\d+$/.test(s||'')?s.replace(/^v/,'').split('.').map(Number):null;
function newer(a,b){a=version(a);b=version(b);if(!a||!b)return false;for(let i=0;i<3;i++){if(a[i]!==b[i])return a[i]>b[i]}return false}
let busy=false,seen='';
async function check(){
 if(busy)return;busy=true;
 try{
 const response=await fetch('https://api.github.com/repos/zulguin/newenaraucania/releases?per_page=30',{headers:{Accept:'application/vnd.github+json'},cache:'no-store'});
 if(!response.ok)return;
 const releases=await response.json();
 const available=releases.filter(r=>!r.draft&&newer(r.tag_name,current)).sort((a,b)=>newer(a.tag_name,b.tag_name)?-1:newer(b.tag_name,a.tag_name)?1:0);
 for(const r of available){
 const v=r.tag_name.replace(/^v/,''),name=platform==='android'?'Newen-Araucania-'+v+'-beta-debug.apk':'Newen-Araucania-'+v+'-Setup.exe';
 const asset=r.assets?.find(a=>a.state==='uploaded'&&a.name===name&&a.browser_download_url===base+r.tag_name+'/'+name);
 if(!asset)continue;
 if(seen===r.tag_name)return;
 seen=r.tag_name;
 const panel=document.createElement('aside');panel.id='newen-update-notice';document.getElementById(panel.id)?.remove();
 panel.style.cssText='position:fixed;z-index:2147483000;bottom:max(12px,env(safe-area-inset-bottom));left:50%;transform:translateX(-50%);width:min(440px,calc(100vw - 24px));box-sizing:border-box;padding:14px;background:#171d24;color:#f5e2bb;border:2px solid #b58b4f;border-radius:10px;box-shadow:0 8px 30px #0009;font:14px/1.45 system-ui;text-align:left';
 const title=document.createElement('strong');title.textContent='Nueva versión '+v+' disponible';
 const msg=document.createElement('p');msg.textContent='Tienes '+current+'. Exporta tu partida antes de actualizar. '+(platform==='android'?'Android pedirá confirmar la instalación del APK.':'Cierra el juego antes de ejecutar el instalador.');msg.style.margin='8px 0';
 const open=document.createElement('a');open.href=asset.browser_download_url;open.target='_blank';open.rel='noopener noreferrer';open.textContent='Descargar actualización';open.style.cssText='display:inline-block;padding:8px 12px;border-radius:5px;background:#bf9b61;color:#181412;font-weight:bold;text-decoration:none;margin-right:8px';
 open.addEventListener('click',e=>{const browser=window.Capacitor?.Plugins?.Browser;if(browser?.open){e.preventDefault();browser.open({url:asset.browser_download_url}).catch(()=>{window.location.href=asset.browser_download_url})}});
 const close=document.createElement('button');close.type='button';close.textContent='Más tarde';close.style.cssText='padding:8px 12px;background:#27313b;color:#fff;border:1px solid #8c7858;border-radius:5px';close.onclick=()=>panel.remove();
 panel.append(title,msg,open,close);document.body.append(panel);return;
 }
 }catch(e){console.debug('Newen: comprobación de actualización no disponible',e)}finally{busy=false}
}
setTimeout(check,12000);setInterval(()=>{if(!document.hidden)check()},60*60*1000);
})();
