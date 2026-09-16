"""Portable local helpers. No network, no bundled media, no payment handling."""
import argparse,json,math,re,shutil,subprocess,sys
from pathlib import Path

def plan(a):
 video=Path(a.video).resolve();out=Path(a.output).resolve()
 if out.exists():raise ValueError('Output already exists; choose a new revision filename')
 if not video.is_file():raise ValueError('Video does not exist')
 if not math.isfinite(a.duration) or a.duration<=0:raise ValueError('Duration must be positive')
 roles={'voice_only':['voice'],'music_fx':['music','effects'],'full':['voice','music','effects'],'silent':[]}[a.mode]
 args=[a.ffmpeg,'-n','-v','error','-i',str(video)];labels=[]
 for role in roles:
  v=getattr(a,role)
  if not v:
   if role=='effects':continue
   raise ValueError(f'Missing independent {role} source')
  p=Path(v).resolve()
  if not p.is_file():raise ValueError(f'Missing file: {p}')
  if p==out:raise ValueError('Output must differ from input')
  args+=['-i',str(p)];labels.append(f'[{len(labels)+1}:a:0]')
 args+=['-map','0:v:0','-c:v','copy']
 if labels:
  graph=''.join(labels)+f'amix=inputs={len(labels)}:duration=longest:normalize=0,alimiter=limit=0.89:level=false:latency=true,apad[a]'
  args+=['-filter_complex',graph,'-map','[a]','-c:a','aac','-b:a','320k','-ar','48000','-ac','2']
 else:args+=['-an']
 return args+['-t',str(a.duration),'-movflags','+faststart',str(out)]

def check_srt(path):
 t=Path(path).read_text('utf-8-sig');matches=re.findall(r'(\d{2,}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2,}):(\d{2}):(\d{2}),(\d{3})',t)
 if not matches:raise ValueError('No SRT timestamps found')
 last=0;errors=[]
 for i,m in enumerate(matches,1):
  nums=list(map(int,m));a,b=[v[0]*3600+v[1]*60+v[2]+v[3]/1000 for v in (nums[:4],nums[4:])]
  if any(nums[k]>59 for k in [1,2,5,6]):errors.append(f'{i}: invalid minute/second')
  if b<=a or a<last:errors.append(f'{i}: overlap or non-positive duration')
  last=b
 if errors:raise ValueError('; '.join(errors))
 return {'captions':len(matches),'last_end':last,'timing':'pass','semantic_alignment':'not_checked'}

def main():
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='cmd',required=True)
 sub.add_parser('doctor');q=sub.add_parser('init');q.add_argument('directory')
 q=sub.add_parser('check-srt');q.add_argument('file')
 q=sub.add_parser('export-audio');q.add_argument('--video',required=True);q.add_argument('--output',required=True)
 q.add_argument('--mode',required=True,choices=['voice_only','music_fx','full','silent']);q.add_argument('--duration',type=float,required=True)
 for x in ['voice','music','effects']:q.add_argument('--'+x)
 q.add_argument('--ffmpeg',default='ffmpeg');q.add_argument('--execute',action='store_true',help='Without this flag, show command only')
 a=p.parse_args()
 if a.cmd=='doctor':print(json.dumps({'python':sys.version.split()[0],'ffmpeg':shutil.which('ffmpeg'),'ffprobe':shutil.which('ffprobe')},ensure_ascii=False))
 elif a.cmd=='init':
  root=Path(a.directory);root.mkdir(parents=True,exist_ok=True);cfg=root/'project.json'
  if cfg.exists():raise ValueError('Project already initialized')
  for d in ['inputs','sources','design','renders','delivery']:(root/d).mkdir(exist_ok=True)
  cfg.write_text(json.dumps({'title':'新宣传片','fps':25,'width':3840,'height':2160,'audio':{'mode':None,'voice':None,'music':None,'effects':None},'chapter_title':{'outline':0,'shadow':0,'persistent':True},'scenes':[]},ensure_ascii=False,indent=2),'utf8')
  print(cfg)
 elif a.cmd=='check-srt':print(json.dumps(check_srt(a.file),ensure_ascii=False))
 else:
  cmd=plan(a)
  if a.execute:subprocess.run(cmd,check=True)
  else:print(json.dumps(cmd,ensure_ascii=False,indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,FileNotFoundError,subprocess.CalledProcessError) as e:sys.exit(str(e))
