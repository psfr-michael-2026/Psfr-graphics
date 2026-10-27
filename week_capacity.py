"""Finite approved bank: store remaining drafts, then fill capacity using the SAME IDs."""
import json,sys,hashlib,urllib.request,os
from datetime import datetime,timezone
from pathlib import Path
from psfr import ROOT,STATE,buffer,read_json,write_json,persist
from schedule_week import TARGETS,FIELDS,query_for,verify_post,TAGS
KEY='2026-10-28-week-01'

def read_back(pid):return buffer('query {post(input:{id:'+json.dumps(pid)+'}) {'+FIELDS+'}}')['post']
def verify_draft(x,cid,mode,p,url):
 assert x['status']=='draft' and x['channelId']==cid and x['text']==p['caption'] and x['schedulingType']==mode
 assert any(a.get('source')==url and a.get('mimeType','').startswith('video/') for a in x['assets'])
def edit_query(pid,service,mode,p,url):
 q=query_for('unused',service,mode,p,url)
 q=q.replace('createPost(input: {channelId:"unused",','editPost(input: {id:'+json.dumps(pid)+',').replace(',needsApproval:false','')
 return q

def main(action):
 now=datetime.now(timezone.utc)
 if action=='fill' and not (datetime(2026,10,28,tzinfo=timezone.utc)<=now<datetime(2026,10,31,tzinfo=timezone.utc)):
  print('Outside authorised 2026 capacity-fill window; no external calls.');return
 state=read_json(STATE,{});record=state[KEY];bank=record['content']
 assert len(bank['posts'])==14
 def save():write_json(STATE,state);persist('PSFR: save finite week capacity receipts')
 for p in bank['posts']:
  assert {t for t in p['caption'].split() if t.startswith('#')}==TAGS
  for cid,service,mode in TARGETS:
   key=p['id']+':'+service;r=record['receipts'].setdefault(key,{})
   if r.get('verified_scheduled'):continue
   url='https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/'+record['media_commit']+'/'+p['assets'][service]['path']
   if action=='stage' and not r.get('post_id'):
    if r.get('status') and not (r['status']=='rejected' and r.get('error',{}).get('__typename')=='LimitReachedError'):
     raise RuntimeError('Unresolved prior create; no retry: '+key)
    assert datetime.fromisoformat(p['dueAt'].replace('Z','+00:00'))>now
    a=p['assets'][service];assert hashlib.sha256((ROOT/a['path']).read_bytes()).hexdigest()==a['sha256']
    with urllib.request.urlopen(url,timeout=60) as res:assert hashlib.sha256(res.read()).hexdigest()==a['sha256']
    if r.get('error'):r['capacity_rejection']=r.pop('error')
    r.update(status='pending-draft',channel_id=cid,scheduling_type=mode,dueAt=p['dueAt'],video_url=url);save()
    try:result=buffer(query_for(cid,service,mode,p,url).replace('saveToDraft:false','saveToDraft:true'))['createPost']
    except Exception:
     r['status']='uncertain-draft';save();raise RuntimeError('Uncertain draft creation; reconcile before retry: '+key) from None
    pid=result.get('post',{}).get('id')
    if not pid:r.update(status='rejected-draft',error=result);save();raise RuntimeError('Draft rejected: '+json.dumps(result))
    r.update(status='accepted',post_id=pid);save()
   assert r.get('post_id'),'No existing draft; fill may never create a new post'
   result=read_back(r['post_id'])
   if result['status']=='scheduled':
    verify_post(result,cid,mode,p,url);r.update(last_status=result,verified_scheduled=True,verified_draft=False);save();continue
   verify_draft(result,cid,mode,p,url)
   r.update(last_status=result,verified_draft=True);save()
   if action=='stage':print('DRAFT',key,r['post_id'],flush=True);continue
   if r.get('scheduling_attempt',{}).get('status') in ['pending','uncertain']:raise RuntimeError('Unresolved prior edit; no retry')
   assert datetime.fromisoformat(p['dueAt'].replace('Z','+00:00'))>now,'Never publish a missed slot late'
   r['scheduling_attempt']={'status':'pending','attempted_at':now.isoformat()};save()
   try:response=buffer(edit_query(r['post_id'],service,mode,p,url))['editPost']
   except Exception:
    r['scheduling_attempt']['status']='uncertain';save();raise RuntimeError('Uncertain edit; reconcile before retry') from None
   if not response.get('post',{}).get('id'):
    if response.get('__typename')=='LimitReachedError':
     r['scheduling_attempt'].update(status='deferred-capacity',result=response);save();continue
    r['scheduling_attempt'].update(status='rejected',result=response);save();raise RuntimeError('Scheduling edit rejected: '+json.dumps(response))
   r['scheduling_attempt']['status']='accepted';save()
   result=read_back(r['post_id']);verify_post(result,cid,mode,p,url)
   r.update(last_status=result,verified_scheduled=True,verified_draft=False);save();print('SCHEDULED SAME ID',key,r['post_id'],flush=True)
 scheduled=sum(x.get('verified_scheduled',False) for x in record['receipts'].values());drafts=sum(x.get('verified_draft',False) and not x.get('verified_scheduled',False) for x in record['receipts'].values())
 record['verification']={'scheduled_posts':scheduled,'verified_drafts':drafts,'live_delivery_verified':False,'finite_bank_only':True}
 record['capacity_fill']={'window':'2026-10-28 through 2026-10-30','time':'20:30 Europe/London','existing_ids_only':True,'no_new_content':True,'enabled':scheduled<28}
 save();assert scheduled+drafts==28
 if action=='fill' and now.date().isoformat()=='2026-10-30' and scheduled<28:
  raise RuntimeError('Final authorised capacity-fill attempt incomplete: inspect remaining draft IDs; no late publishing.')
 print('VERIFIED',scheduled,'scheduled;',drafts,'drafts; exact finite bank, no live delivery claim.')
if __name__=='__main__':main(sys.argv[1])
