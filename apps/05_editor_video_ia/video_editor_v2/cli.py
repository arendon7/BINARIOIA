from __future__ import annotations
import argparse, json, shlex
from pathlib import Path
from .models import ProjectSpec
from .pipeline import VideoEditPipeline
from .transcriber import FasterWhisperTranscriber, FasterWhisperConfig
from .validator import validate_project
from .ffmpeg_compiler import compile_ffmpeg
from .proxy import compile_proxy_ffmpeg

def main():
    ap=argparse.ArgumentParser(description='Binario IA · Editor Video IA v2 RC3')
    ap.add_argument('project')
    ap.add_argument('--plan',default=None)
    ap.add_argument('--preview',default=None)
    ap.add_argument('--subtitle-dir',default=None)
    ap.add_argument('--render',default=None)
    ap.add_argument('--proxy',default=None)
    ap.add_argument('--check-files',action='store_true')
    ap.add_argument('--auto-transcribe',action='store_true')
    ap.add_argument('--whisper-model',default='small')
    ap.add_argument('--burn-subtitles',action='store_true')
    args=ap.parse_args()
    project=ProjectSpec.from_json(args.project)
    if args.burn_subtitles: project.edit.burn_subtitles=True
    errors=validate_project(project,check_files=args.check_files)
    if errors:
        print('PROYECTO INVÁLIDO')
        for e in errors: print('-',e)
        return 2
    tp=None
    if args.auto_transcribe: tp=FasterWhisperTranscriber(FasterWhisperConfig(model_size=args.whisper_model))
    result=VideoEditPipeline(transcript_provider=tp).analyze(project,preview_path=args.preview,subtitle_dir=args.subtitle_dir)
    plan=result.plan
    print(json.dumps({'plan':plan.to_dict(),'qc':result.qc},indent=2,ensure_ascii=False))
    if args.plan: Path(args.plan).write_text(json.dumps(plan.to_dict(),indent=2,ensure_ascii=False),encoding='utf-8')
    subtitle_for_render=result.ass_path if project.edit.burn_subtitles else None
    if args.render:
        print('\nFFMPEG FINAL:'); print(shlex.join(compile_ffmpeg(project,plan,args.render,subtitle_path=subtitle_for_render)))
    if args.proxy:
        print('\nFFMPEG PROXY:'); print(shlex.join(compile_proxy_ffmpeg(project,plan,args.proxy,subtitle_path=subtitle_for_render)))
    if result.preview_path: print('\nPREVIEW:',result.preview_path)
    if result.srt_path: print('SRT:',result.srt_path)
    if result.ass_path: print('ASS:',result.ass_path)
    return 0

if __name__=='__main__': raise SystemExit(main())
