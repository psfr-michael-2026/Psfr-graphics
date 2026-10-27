"""Schedule only Michael's approved fourteen-post bank. No generation or recurrence."""
import hashlib,json,subprocess,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from psfr import ROOT,STATE,buffer,discover_channels,read_json,write_json,persist
TARGETS=[('6adac73f778b240e2f96b17b','facebook','automatic'),('6adac5fe778b240e2f96a871','tiktok','notification')]
TAGS={'#psfrhealthsystems','#Fitness','#Health','#FitnessMotivation','#gym'}
FIELDS='id status channelId text dueAt schedulingType assets { mimeType source }'

def query_for(cid,service,mode,p,url):
 metadata='facebook: {type: post}' if service=='facebook' else 'tiktok: {isAiGenerated: true}'
 return ('mutation { createPost(input: {channelId:'+json.dumps(cid)+',text:'+json.dumps(p['caption'])+',dueAt:'+json.dumps(p['dueAt'])+',schedulingType:'+mode+',mode:customScheduled,saveToDraft:false,needsApproval:false,aiAssisted:true,assets:[{video:{url:'+json.dumps(url)+'}}],metadata:{'+metadata+'}}) { __typename ... on PostActionSuccess {post {id status}} ... on MutationError {message} } }')

def validate_bank(bank,now):
 assert bank['bank']=='2026-10-28-week-01'
 assert len(bank['posts'])==14
 assert len({p['id'] for p in bank['posts']})==14
 for p in bank['posts']:
  tags={w for w in p['caption'].split() if w.startswith('#')}
  assert tags==TAGS and p['caption'].count('#')==5
  dt=datetime.fromisoformat(p['dueAt'].replace('Z','+00:00'))
  assert dt>now,'No past-dated publishing is allowed'
  assert dt.hour==(7 if p['id'].endswith('AM') else 19)
  assert dt.minute==0
  assert 'shopping' not in p['headline'].lower()

def verify_post(result,cid,mode,p,url):
 assert result['channelId']==cid
 assert result['text']==p['caption']
 assert result['schedulingType']==mode
 assert result['status'].lower() in ['scheduled','buffer']
 actual=datetime.fromisoformat(result['dueAt'].replace('Z','+00:00'))
 expected=datetime.fromisoformat(p['dueAt'].replace('Z','+00:00'))
 assert actual==expected
 assert any(a.get('source')==url and a.get('mimeType','').startswith('video/') for a in result['assets'])

def main():
 bank=read_json(ROOT/'approved/week-01/week.json');validate_bank(bank,datetime.now(timezone.utc))
 channels={c['id']:c for c in discover_channels()}
 for cid,service,mode in TARGETS:
  assert channels[cid]['service'].lower()==service
  c=buffer('query {channel(input:{id:'+json.dumps(cid)+'}) {id hasActiveMemberDevice isDisconnected isLocked isQueuePaused}}')['channel']
  assert not c['isDisconnected'] and not c['isLocked'] and not c['isQueuePaused']
  if mode=='notification':assert c['hasActiveMemberDevice'],'TikTok needs an active phone for music handover'
 state=read_json(STATE,{})
 record=state.setdefault(bank['bank'],{'content':bank,'media_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'receipts':{}})
 assert record['content']==bank,'Existing approved content differs; stopped'
 urls={}
 # Verify every local and immutable hosted video before any Buffer write.
 for p in bank['posts']:
  for cid,service,mode in TARGETS:
   a=p['assets'][service];f=ROOT/a['path'];assert hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256']
   probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(f)]))
   assert len(probe['streams'])==1 and probe['streams'][0]['codec_type']=='video'
   assert [probe['streams'][0]['width'],probe['streams'][0]['height']]==a['dimensions']
   assert abs(float(probe['format']['duration'])-15)<.1
   url='https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/'+record['media_commit']+'/'+a['path']
   with urllib.request.urlopen(url,timeout=60) as res:assert hashlib.sha256(res.read()).hexdigest()==a['sha256']
   urls[(p['id'],cid)]=url
 def save():
  write_json(STATE,state);persist('PSFR: save approved week scheduling receipts')
 save()
 for p in bank['posts']:
  for cid,service,mode in TARGETS:
   key=p['id']+':'+service;r=record['receipts'].setdefault(key,{})
   if r.get('status') not in (None,'accepted'):raise RuntimeError('Previous attempt needs reconciliation: '+key)
   url=urls[(p['id'],cid)]
   if not r.get('post_id'):
    r.update(status='pending',channel_id=cid,scheduling_type=mode,dueAt=p['dueAt'],video_url=url);save()
    try:result=buffer(query_for(cid,service,mode,p,url))['createPost']
    except Exception:
     r['status']='uncertain';save();raise RuntimeError('Uncertain response; inspect before retry: '+key) from None
    pid=result.get('post',{}).get('id')
    if not pid:
     r.update(status='rejected',error=result);save();raise RuntimeError('Buffer rejected '+key+': '+json.dumps(result))
    r.update(status='accepted',post_id=pid);save()
   result=buffer('query {post(input:{id:'+json.dumps(r['post_id'])+'}) {'+FIELDS+'}}')['post']
   r['last_status']=result;save();verify_post(result,cid,mode,p,url)
   r['verified_scheduled']=True;save()
   print('VERIFIED',key,r['post_id'],result['status'],result['dueAt'],mode,flush=True)
 record['verification']={'scheduled_posts':28,'live_delivery_verified':False,'finite_bank_only':True};save()
 print('COMPLETE: 14 Facebook automatic posts and 14 TikTok notification handovers scheduled; live delivery is not yet verified.')
if __name__=='__main__':main()
