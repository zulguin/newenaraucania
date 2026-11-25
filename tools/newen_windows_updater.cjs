/* Actualización Windows de Newen, incluido el canal de betas de GitHub. */
const {app,dialog,shell}=require('electron');
const fs=require('node:fs'),path=require('node:path'),{pathToFileURL}=require('node:url');
const manifest=require('./newen-original-main.json');
const original=path.resolve(__dirname,manifest.main);
const base='https://github.com/zulguin/newenaraucania/releases/download/';
const version=s=>/^v?\d+\.\d+\.\d+$/.test(s||'')?s.replace(/^v/,'').split('.').map(Number):null;
function newer(a,b){a=version(a);b=version(b);if(!a||!b)return false;for(let i=0;i<3;i++){if(a[i]!==b[i])return a[i]>b[i]}return false}
let busy=false,offered='';
async function check(){
 if(busy||!app.isPackaged||process.platform!=='win32')return;busy=true;
 try{
 const response=await fetch('https://api.github.com/repos/zulguin/newenaraucania/releases?per_page=30',{headers:{Accept:'application/vnd.github+json','User-Agent':'Newen-Araucania'},signal:AbortSignal.timeout(15000)});
 if(!response.ok)return;
 const releases=await response.json();
 const r=releases.filter(r=>!r.draft&&newer(r.tag_name,app.getVersion())).sort((a,b)=>newer(a.tag_name,b.tag_name)?-1:newer(b.tag_name,a.tag_name)?1:0).find(r=>r.assets?.some(a=>a.state==='uploaded'&&a.name==='Newen-Araucania-'+r.tag_name.replace(/^v/,'')+'-Setup.exe'));
 if(!r||offered===r.tag_name)return;
 const name='Newen-Araucania-'+r.tag_name.replace(/^v/,'')+'-Setup.exe',asset=r.assets.find(a=>a.name===name);
 const feed=base+r.tag_name+'/';
 if(asset.browser_download_url!==feed+name)return;
 offered=r.tag_name;
 const choice=await dialog.showMessageBox({type:'info',title:'Newen Araucanía',message:'Nueva versión '+r.tag_name+' disponible',detail:'Guarda y exporta tu partida antes de actualizar. La descarga se puede realizar mientras juegas.',buttons:['Descargar actualización','Más tarde'],defaultId:0,cancelId:1});
 if(choice.response!==0)return;
 if(!r.assets.some(a=>a.name==='latest.yml'&&a.state==='uploaded')){await shell.openExternal(asset.browser_download_url);return}
 try{
 const {NsisUpdater}=require('electron-updater');
 const updater=new NsisUpdater({provider:'generic',url:feed,channel:'latest'});
 updater.autoDownload=false;updater.autoInstallOnAppQuit=false;updater.allowPrerelease=true;updater.allowDowngrade=false;
 updater.on('error',e=>console.warn('Newen updater:',e.message));
 const result=await updater.checkForUpdates();
 if(!result?.isUpdateAvailable||result.updateInfo?.version!==r.tag_name.replace(/^v/,''))throw Error('Metadatos de actualización no coinciden');
 await updater.downloadUpdate();
 const install=await dialog.showMessageBox({type:'info',title:'Newen Araucanía',message:'Actualización descargada',detail:'Guarda tu partida antes de reiniciar. ¿Instalar ahora?',buttons:['Instalar y reiniciar','Más tarde'],defaultId:1,cancelId:1});
 if(install.response===0)updater.quitAndInstall(false,true);
 }catch(e){console.warn('Newen: descarga automática no disponible:',e.message);const fallback=await dialog.showMessageBox({type:'warning',message:'No se pudo completar la descarga automática',detail:'Puedes descargar el instalador oficial desde GitHub.',buttons:['Abrir descarga','Cancelar'],cancelId:1});if(fallback.response===0)await shell.openExternal(asset.browser_download_url)}
 }catch(e){console.warn('Newen: consulta de versiones:',e.message)}finally{busy=false}
}
// Conserva el punto de entrada original. No altera el directorio de partidas.
(async()=>{
 try{require(original)}catch(e){if(e.code!=='ERR_REQUIRE_ESM')throw e;await import(pathToFileURL(original).href)}
 await app.whenReady();
 setTimeout(check,15000);
 const timer=setInterval(check,60*60*1000);timer.unref?.();
})().catch(e=>{console.error('Newen: error iniciando el programa original',e);app.quit()});
