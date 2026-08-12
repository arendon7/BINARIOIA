from __future__ import annotations
from pathlib import Path
from .models import ProjectSpec, TimelinePlan
from .assets import overlay_xy_asset
from .subtitles import ffmpeg_subtitle_filter
from .audio_enhancement import build_audio_enhancement
from .runtime_tools import resolve_ffmpeg

def _path(path: str) -> str: return str(Path(path))

def _asset_video_chain(asset, input_label: str, output_label: str, canvas_w: int, duration: float) -> str:
    dur=max(.05,float(duration)); opacity=max(0.0,min(1.0,float(getattr(asset,"opacity",1.0)))); width_norm=getattr(asset,"width_norm",None)
    scale=f"scale={max(8,int(canvas_w*max(.03,min(.95,float(width_norm)))))}:-1" if width_norm is not None else f"scale=iw*{max(.03,min(4.0,float(getattr(asset,'scale',.2)))):.4f}:-1"
    parts=[f"[{input_label}:v]trim=duration={dur:.3f}","setpts=PTS-STARTPTS","format=rgba",scale]
    rot=max(-180.0,min(180.0,float(getattr(asset,"rotation_deg",0.0) or 0.0)))
    if abs(rot)>0.01: parts.append(f"rotate={rot:.4f}*PI/180:c=none:ow=rotw(iw):oh=roth(ih)")
    parts.append(f"colorchannelmixer=aa={opacity:.3f}")
    ain=str(getattr(asset,"animation_in","fade") or "none"); aout=str(getattr(asset,"animation_out","fade") or "none"); din=min(dur/2,max(0.0,float(getattr(asset,"animation_in_duration",.25) or 0.0))); dout=min(dur/2,max(0.0,float(getattr(asset,"animation_out_duration",.25) or 0.0)))
    if ain=="fade" and din>.001: parts.append(f"fade=t=in:st=0:d={din:.3f}:alpha=1")
    if aout=="fade" and dout>.001: parts.append(f"fade=t=out:st={max(0.0,dur-dout):.3f}:d={dout:.3f}:alpha=1")
    parts.append(f"setpts=PTS-STARTPTS+{float(getattr(asset,'start',0.0)):.3f}/TB[{output_label}]"); return ",".join(parts)

def _asset_overlay_xy(asset, start: float, duration: float) -> tuple[str,str]:
    xnorm=max(0.0,min(1.0,float(getattr(asset,"x_norm",.5) if getattr(asset,"x_norm",None) is not None else .5))); ynorm=max(0.0,min(1.0,float(getattr(asset,"y_norm",.1) if getattr(asset,"y_norm",None) is not None else .1))); tx=f"(W-w)*{xnorm:.6f}"; ty=f"(H-h)*{ynorm:.6f}"; anim=str(getattr(asset,"animation_in","fade") or "none"); d=max(.001,min(float(duration)/2,float(getattr(asset,"animation_in_duration",.25) or .25))); st=float(start)
    if anim=="slide_left": return f"if(lt(t,{st+d:.3f}),-w+(({tx})+w)*(t-{st:.3f})/{d:.3f},{tx})",ty
    if anim=="slide_right": return f"if(lt(t,{st+d:.3f}),W+(({tx})-W)*(t-{st:.3f})/{d:.3f},{tx})",ty
    if anim=="slide_up": return tx,f"if(lt(t,{st+d:.3f}),H+(({ty})-H)*(t-{st:.3f})/{d:.3f},{ty})"
    if anim=="slide_down": return tx,f"if(lt(t,{st+d:.3f}),-h+(({ty})+h)*(t-{st:.3f})/{d:.3f},{ty})"
    return tx,ty

def _audio_chain(project: ProjectSpec, plan: TimelinePlan, label: str = "acat") -> str:
    decision = build_audio_enhancement(project, plan); return f"[{label}]" + ",".join(decision.filters) + "[voicebase]"

def compile_ffmpeg(project: ProjectSpec, plan: TimelinePlan, output_path: str, *, subtitle_path: str | None = None, lower_third_path: str | None = None, proxy: bool = False) -> list[str]:
    if not plan.cuts: raise ValueError("No hay cortes para renderizar")
    sources = {s.id: s for s in project.sources if s.enabled}; audio_sources = {a.id: a for a in project.audio_sources if a.enabled and a.kind == "dialogue"}; used=[]
    for c in plan.cuts:
        if c.source_id not in used: used.append(c.source_id)
    used_external_audio=[]
    for c in plan.cuts:
        aid=getattr(c,"audio_source_id",None)
        if aid and aid in audio_sources and aid not in used_external_audio: used_external_audio.append(aid)
    bg=[a for a in plan.assets if a.enabled and a.kind=="background"]; matte=[a for a in plan.assets if a.enabled and a.kind=="subject_matte"]; behind=sorted([a for a in plan.assets if a.enabled and a.placement=="behind_subject" and a.kind in ("logo","image","lower_third")],key=lambda a:a.z_index); fg=sorted([a for a in plan.assets if a.enabled and a.placement=="foreground" and a.kind in ("logo","image","lower_third")],key=lambda a:a.z_index); broll=sorted([a for a in plan.assets if a.enabled and (a.kind=="broll" or a.placement=="broll")],key=lambda a:(a.start,a.z_index)); music=[a for a in plan.assets if a.enabled and a.kind=="music"]
    cmd=[resolve_ffmpeg(),"-y"]; idx={}; n=0
    for sid in used: idx[("source",sid)]=n; n+=1; cmd += ["-i",_path(sources[sid].path)]
    for aid in used_external_audio: idx[("dialogue_audio",aid)]=n; n+=1; cmd += ["-i",_path(audio_sources[aid].path)]
    for a in bg[:1]+behind+fg: idx[("asset",a.id)]=n; n+=1; cmd += ["-loop","1","-framerate",str(project.output.fps),"-i",_path(a.path)]
    for a in broll+matte[:1]: idx[("asset",a.id)]=n; n+=1; cmd += ["-i",_path(a.path)]
    for a in music[:1]:
        idx[("asset",a.id)]=n; n+=1
        if a.loop: cmd += ["-stream_loop","-1"]
        cmd += ["-i",_path(a.path)]
    if proxy: w,h=project.output.proxy_width,project.output.proxy_height; fps=min(project.output.fps,24)
    else: w,h,fps=project.output.width,project.output.height,project.output.fps
    f=[]; vl=[]; al=[]
    for i,c in enumerate(plan.cuts):
        si=idx[("source",c.source_id)]; v=f"v{i}"; a=f"a{i}"
        if project.edit.auto_reframe:
            fx=max(0.0,min(1.0,float(getattr(c,"focus_x_norm",0.5)))); fy=max(0.0,min(1.0,float(getattr(c,"focus_y_norm",0.5)))); f.append(f"[{si}:v]trim=start={c.source_start:.3f}:end={c.source_end:.3f},setpts=PTS-STARTPTS,fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}:x='max(0,min(iw-ow,iw*{fx:.6f}-ow/2))':y='max(0,min(ih-oh,ih*{fy:.6f}-oh/2))'[{v}]")
        else: f.append(f"[{si}:v]trim=start={c.source_start:.3f}:end={c.source_end:.3f},setpts=PTS-STARTPTS,fps={fps},scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:black[{v}]")
        fade=min(max(0.0,float(getattr(project.edit,"audio_join_fade_ms",12.0))/1000.0),max(0.0,c.duration/5.0)); selected_audio_id=getattr(c,"audio_source_id",None)
        if selected_audio_id and selected_audio_id in audio_sources and c.audio_source_start is not None and c.audio_source_end is not None:
            ai=idx[("dialogue_audio",selected_audio_id)]; chain=f"[{ai}:a]atrim=start={float(c.audio_source_start):.6f}:end={float(c.audio_source_end):.6f},asetpts=PTS-STARTPTS"; tempo=max(0.5,min(2.0,float(getattr(c,"audio_tempo",1.0) or 1.0)))
            if abs(tempo-1.0)>1e-7: chain += f",atempo={tempo:.9f}"
            if fade>.001: chain += f",afade=t=in:st=0:d={fade:.4f},afade=t=out:st={max(0.0,c.duration-fade):.4f}:d={fade:.4f}"
            f.append(chain+f"[{a}]")
        else:
            chain=f"[{si}:a]atrim=start={c.source_start:.3f}:end={c.source_end:.3f},asetpts=PTS-STARTPTS"
            if fade>.001: chain += f",afade=t=in:st=0:d={fade:.4f},afade=t=out:st={max(0.0,c.duration-fade):.4f}:d={fade:.4f}"
            f.append(chain+f"[{a}]")
        vl.append(f"[{v}]"); al.append(f"[{a}]")
    f.append("".join(x for pair in zip(vl,al) for x in pair)+f"concat=n={len(plan.cuts)}:v=1:a=1[vcat][acat]"); current="vcat"
    if bg:
        bi=idx[("asset",bg[0].id)]; f.append(f"[{bi}:v]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},trim=duration={plan.actual_duration:.3f},setpts=PTS-STARTPTS[basebg]"); base="basebg"
    elif behind:
        f.append(f"[vcat]split=2[vmain][vblur];[vblur]scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},boxblur=18:2[basebg]"); current="vmain"; base="basebg"
    else: base=current
    back=base
    for j,a in enumerate(behind):
        ai=idx[("asset",a.id)]; end=a.end if a.end is not None else plan.actual_duration; lab=f"bh{j}"; out=f"bho{j}"; dur=max(.05,end-a.start); f.append(_asset_video_chain(a,str(ai),lab,w,dur)); x,y=_asset_overlay_xy(a,a.start,dur); f.append(f"[{back}][{lab}]overlay=x='{x}':y='{y}':enable='between(t,{a.start:.3f},{end:.3f})':eof_action=pass[{out}]"); back=out
    if matte:
        mi=idx[("asset",matte[0].id)]; f.append(f"[{current}]format=rgba[subjectrgb];[{mi}:v]scale={w}:{h},format=gray,setpts=PTS-STARTPTS[mask];[subjectrgb][mask]alphamerge[subject]"); f.append(f"[{back}][subject]overlay=0:0:shortest=1[withsubject]"); current="withsubject"
    elif behind or bg:
        f.append(f"[{current}]scale=iw*0.94:ih*0.94[mainfit]"); f.append(f"[{back}][mainfit]overlay=(W-w)/2:(H-h)/2:shortest=1[withbg]"); current="withbg"
    for j,a in enumerate(broll):
        ai=idx[("asset",a.id)]; end=a.end if a.end is not None else min(plan.actual_duration,a.start+(a.max_duration or 4)); dur=max(.05,end-a.start); lab=f"br{j}"; out=f"bro{j}"; f.append(f"[{ai}:v]trim=start=0:end={dur:.3f},setpts=PTS-STARTPTS+{a.start:.3f}/TB,fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}[{lab}]"); f.append(f"[{current}][{lab}]overlay=0:0:enable='between(t,{a.start:.3f},{end:.3f})':eof_action=pass[{out}]"); current=out
    for j,a in enumerate(fg):
        ai=idx[("asset",a.id)]; end=a.end if a.end is not None else plan.actual_duration; lab=f"fg{j}"; out=f"fgo{j}"; dur=max(.05,end-a.start); f.append(_asset_video_chain(a,str(ai),lab,w,dur)); x,y=_asset_overlay_xy(a,a.start,dur); f.append(f"[{current}][{lab}]overlay=x='{x}':y='{y}':enable='between(t,{a.start:.3f},{end:.3f})':eof_action=pass[{out}]"); current=out
    if lower_third_path and project.edit.auto_lower_thirds: f.append(f"[{current}]{ffmpeg_subtitle_filter(lower_third_path)}[lowered]"); current="lowered"
    if subtitle_path and project.edit.burn_subtitles: f.append(f"[{current}]{ffmpeg_subtitle_filter(subtitle_path)}[subbed]"); current="subbed"
    f.append(f"[{current}]format=yuv420p[vout]"); f.append(_audio_chain(project,plan,"acat")); audio_label="voicebase"
    if music:
        m=music[0]; mi=idx[("asset",m.id)]; f.append(f"[{mi}:a]atrim=duration={plan.actual_duration:.3f},asetpts=PTS-STARTPTS,volume={m.volume_db:.1f}dB[musicbase]")
        if project.edit.music_ducking:
            f.append("[voicebase]asplit=2[voice_mix][voice_side]"); f.append(f"[musicbase][voice_side]sidechaincompress=threshold={project.edit.music_duck_threshold:.4f}:ratio={project.edit.music_duck_ratio:.2f}:attack=20:release=400[ducked]"); f.append("[voice_mix][ducked]amix=inputs=2:duration=first:normalize=0[aout]")
        else: f.append("[voicebase][musicbase]amix=inputs=2:duration=first:normalize=0[aout]")
        audio_label="aout"
    crf=project.output.proxy_crf if proxy else project.output.crf; preset="veryfast" if proxy else project.output.preset
    cmd += ["-filter_complex",";".join(f),"-map","[vout]","-map",f"[{audio_label}]","-c:v",project.output.video_codec,"-preset",preset,"-crf",str(crf),"-c:a",project.output.audio_codec,"-movflags","+faststart","-t",f"{plan.actual_duration:.3f}",_path(output_path)]; return cmd
