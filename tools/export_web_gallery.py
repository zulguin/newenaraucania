"""Export lightweight website previews from the published game ZIP, not game code."""
import io, json, os, re, sys, zipfile
from pathlib import Path
from PIL import Image, ImageDraw
z=zipfile.ZipFile(sys.argv[1])
root=Path(sys.argv[2]); root.mkdir(parents=True,exist_ok=True)
version=sys.argv[3]
paths={Path(n).name:n for n in z.namelist() if '/assets/' in '/'+n and not n.endswith('/')}
manifest={"version":version,"heroes":{},"bosses":{},"mounts":{}}
def sheet(name):
    return Image.open(io.BytesIO(z.read(paths[name]))).convert("RGBA")
def frames(name,c,r,seq):
    im=sheet(name); w,h=im.size
    return [im.crop((round((i%c)*w/c),round((i//c)*h/r),round((i%c+1)*w/c),round((i//c+1)*h/r))) for i in seq]
def normalize(items,size=224):
    # Use one shared scale across all frames, preserving relative character scale and animation.
    mx=max(max(i.size) for i in items)
    out=[]
    for im in items:
        w,h=im.size; k=(size-8)/mx
        im=im.resize((max(1,round(w*k)),max(1,round(h*k))),Image.Resampling.LANCZOS)
        canvas=Image.new("RGBA",(size,size)); canvas.alpha_composite(im,((size-im.width)//2,size-im.height-4))
        out.append(canvas)
    return out
def emit(key,items,duration=145):
    items=normalize(items); dest=key+".webp"
    items[0].save(root/dest,save_all=True,append_images=items[1:],duration=duration,loop=0,quality=75,method=4)
    return dest
def add(group,key,name,c,r,seqs):
    if name not in paths: return
    result={}
    for action,seq in seqs.items():
        result[action]=emit(group+"-"+key+"-"+action,frames(name,c,r,seq),260 if action=="idle" else 145)
    manifest[group][key]=result
seq16={"idle":[0,1,2,3],"walk":[4,5,6,7],"attack":[8,9,10,11],"skill":[8,9,10,11],"ultimate":[12,13,14,15]}
seq32={"idle":[0,1,2,3],"walk":[4,5,6,7],"attack":[8,9,10,11,12,13,14,15],"skill":[20,21,22,23],"ultimate":[24,25,26,27]}
# Specialized hero renderers take precedence over legacy sheets.
for key,filename,c,r,seq in [
("mh","newen312_mapuche.png",4,4,{"idle":[0],"walk":[1,2,3,2],"attack":[4,5,6,7],"skill":[8,9,10,11],"ultimate":[12,13,14,15]}),
("mf","newen288_hero_mf_32.webp",4,8,seq32),
("kh","newen291_hero_kh_32.webp",4,8,seq32),("kf","newen291_hero_kf_32.webp",4,8,seq32),
("sh","newen307_atacameno.png",4,4,seq16),("sf","newen307_atacamena.png",4,4,seq16),
("nh","newen288_hero_nh_32.webp",4,8,seq32),("nf","newen309_selknam_f.png",4,4,seq16),
("bh","newen308_cacu_brujo.png",4,4,seq16),("bf","newen308_cacu_bruja.png",4,4,seq16),
("ch","newen313_chono_h.png",4,4,{"idle":[0,1],"walk":[4,5,4,5],"attack":[6,7,8],"skill":[9,10,11],"ultimate":[12,13,14,15]}),
("cf","newen313_chono_f.png",4,4,{"idle":[0,1],"walk":[4,5,4,5],"attack":[6,7,8],"skill":[9,10,11],"ultimate":[12,13,14,15]})]:
    add("heroes",key,filename,c,r,seq)
# Special boss transformations use separate source sheets.
for key,stem in [("caicai","caicai"),("tenten","tenten")]:
    if "newen279_"+stem+"_human_16.webp" in paths:
        add("bosses",key,"newen279_"+stem+"_human_16.webp",4,4,{"idle":[0,1,2,3],"walk":[4,5,6,7],"attack":[8,9,10,11],"skill":[12,13,14,15]})
        if "newen279_"+stem+"_serpent_16.webp" in paths:
            a=frames("newen279_"+stem+"_human_16.webp",4,4,[0,1,2])+frames("newen279_"+stem+"_serpent_16.webp",4,4,[0,1,2,3,8,9,10,11])
            manifest["bosses"][key]["transform"]=emit("bosses-"+key+"-transform",a,180)
            for action,seq in {"serpent_idle":[0,1,2,3],"serpent_walk":[4,5,6,7],"serpent_attack":[8,9,10,11],"serpent_skill":[12,13,14,15]}.items():
                manifest["bosses"][key][action]=emit("bosses-"+key+"-"+action,frames("newen279_"+stem+"_serpent_16.webp",4,4,seq))
for key in ["millalobo","maite","kuyen","rabbit"]:
    add("bosses",key,"newen314_"+key+".webp",4,4,{"idle":[0,1,2,3],"attack":[4,5,6,7],"ultimate":[12,13,14,15]})
if "millalobo" in manifest["bosses"] and "newen314_beast.webp" in paths:
    a=frames("newen314_millalobo.webp",4,4,[0,1,2,3])+frames("newen314_beast.webp",4,4,[0,1,2,3,8,9,10,11])
    manifest["bosses"]["millalobo"]["transform"]=emit("bosses-millalobo-transform",a,180)
for key,filename,c,r in [("k","newen296_mount_k_24.webp",6,4),("s","newen296_mount_s_24.webp",6,4),("n","newen296_mount_n_24.webp",6,4),("b","newen296_mount_b_24.webp",6,4),("kong","newen296_mount_kong_24.webp",6,4),("m","newen297_mount_m_24.webp",6,4),("carm","newen297_mount_carm_24.webp",6,4),("quetz","newen300_mount_quetz_24.webp",6,4),("camahueto","newen314_camahueto.webp",4,4),("cipactli","newen303_cipactli_mount.webp",4,4)]:
    count=c*r
    add("mounts",key,filename,c,r,{"idle":list(range(min(c,count))),"walk":list(range(c,min(2*c,count))),"skill":list(range(2*c,count))})
# Chono canoe is drawn procedurally by the original game, not stored as an atlas.
if "newen313_chono_h.png" in paths:
    out=[]
    import math
    for i in range(6):
        im=Image.new("RGBA",(320,320));d=ImageDraw.Draw(im); dy=round(math.sin(i*math.tau/6)*4)
        rider=frames("newen313_chono_h.png",4,4,[0,1,2,3,0,1][i:i+1])[0]
        rider.thumbnail((205,205));im.alpha_composite(rider,((320-rider.width)//2,235-rider.height+dy))
        d.ellipse((22,233+dy,298,260+dy),fill="#43bfe5",outline="#9df5ff",width=3)
        d.polygon([(28,211+dy),(80,232+dy),(160,239+dy),(240,232+dy),(292,211+dy),(274,252+dy),(220,266+dy),(100,266+dy),(46,252+dy)],fill="#754425",outline="#ce9a59",width=4)
        out.append(im)
    manifest["mounts"]["c"]={"idle":emit("mounts-c-idle",out,170)}
if "newen253_selection_forest.webp" in paths:
    im=sheet("newen253_selection_forest.webp"); im.thumbnail((1100,620)); im.convert("RGB").save(root/"forest.webp",quality=83);manifest["forest"]="forest.webp"
# Extra bosses, only when corresponding original atlases exist.
for key in ["llorona","machi_oscura","puma","trauco","mapin","caleu","pihuy","carm","chupa","quetz","silbon","anchi","cadejo","patasola","kong"]:
    fname="newen315_boss_"+key+"_48.webp"
    if fname in paths:
        add("bosses",key,fname,8,6,{"idle":[0,1,2,3,4,5]})
# Pincoya: only the approved red-haired, green-dress atlas used by the game.
add("bosses","pincoya","newen280_boss_pincoya_16.webp",4,4,{"idle":[0,1,2,3],"walk":[4,5,6,7],"attack":[8,9,10,11],"skill":[12,13,14,15]})
# Chalo has original individual portraits, not an animation atlas.
if all(n in paths for n in ["newen244_chalo_main.png","newen244_chalo_split.png","newen244_bag_camping.png"]):
    main,split,bag=[sheet(n) for n in ["newen244_chalo_main.png","newen244_chalo_split.png","newen244_bag_camping.png"]]
    import math
    def portrait_motion(im,attack=False):
        im=normalize([im],224)[0]
        out=[]
        for i in range(8):
            u=i/7
            dx=round(8*math.sin(math.pi*u)) if attack else 0
            dy=round(2*math.sin(2*math.pi*u))
            canvas=Image.new("RGBA",(240,240))
            canvas.alpha_composite(im,(8+dx,8+dy))
            out.append(canvas)
        return out
    main_frames=portrait_motion(main)
    child=normalize([split],144)[0]
    duo=Image.new("RGBA",(320,224))
    duo.alpha_composite(child,(12,76))
    duo.alpha_composite(child,(164,76))
    original=normalize([main],216)[0]
    before=Image.new("RGBA",(320,224)); before.alpha_composite(original,(52,4))
    manifest["bosses"]["chalo"]={"idle":emit("bosses-chalo-idle",main_frames),"attack":emit("bosses-chalo-attack",portrait_motion(main,True)), "transform":emit("bosses-chalo-transform",[before]*5+[duo]*6,150),"split":emit("bosses-chalo-split",portrait_motion(split)),"reward":emit("bosses-chalo-reward",[bag])}
(root/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False),encoding="utf-8")
print("Generated",sum(map(len,[manifest["heroes"],manifest["bosses"],manifest["mounts"]])),"entries from",version)
