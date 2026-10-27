"""The same approved fourteen PSFR posts on the verified Instagram business channel."""
import json,sys,hashlib,urllib.request
from datetime import datetime,timezone
from psfr import ROOT,STATE,buffer,read_json,write_json,persist
from schedule_week import TAGS,FIELDS,verify_post
from week_capacity import verify_draft
CID='6ae08d042f1f5ed648e92cc0'
KEY='2026-10-28-week-01-instagram'
BASE='2026-10-28-week-01'
MODE='automatic'

def query(p,url,draft=False,pid=None):
 action='editPost' if pid else 'createPost'
 identity='id:'+json.dumps(pid) if pid else 'channelId:'+json.dumps(CID)
 approval='' if pid else ',needsApproval:false'
 return ('mutation {'+action+'(input:{'+identity+',text:'+json.dumps(p['caption'])+',dueAt:'+json.dumps(p['dueAt'])+',mode:customScheduled,schedulingType:automatic,saveToDraft:'+str(draft).lower()+approval+',aiAssisted:true,assets:[{video:{url:'+json.dumps(url)+'}}],metadata:{instagram:{type:reel,shouldShareToFeed:true,isAiGenerated:true}}}) {__typename ... on PostActionSuccess {post {id status}} ... on MutationError {message}}}')

def read_back(pid):return buffer('query {post(input:{id:'+json.dumps(pid)+'}) {'+FIELDS+'}}')['post']
def main(action):
 assert action in ['stage','fill']
 now=datetime.now(timezone.utc)
 if action=='fill' and not (datetime(2026,10,28,tzinfo=timezone.utc)<=now<datetime(2026,10,31,tzinfo=timezone.utc)):
  print('Outside exact 2026 bank window; no external calls.');return
 state=read_json(STATE,{})
 source=state[BASE];bank=source['content'];posts=bank['posts']
 assert len(posts)==14 and len({p['id'] for p in posts})==14
 channel=buffer('query {channel(input:{id:'+json.dumps(CID)+'}) {id name service type isDisconnected isLocked isQueuePaused}}')['channel']
 assert channel['name'].lower()=='psfrhealthsystems' and channel['service']=='instagram' and channel['type']=='business'
 assert not any(channel[k] for k in ['isDisconnected','isLocked','isQueuePaused'])
 content={'source_bank':BASE,'posts':posts,'channel_id':CID,'publishing_mode':MODE,'media_commit':source['media_commit'],'authorisation':'Michael requested Instagram inclusion for all fourteen existing posts on 27 October 2026.'}
 record=state.setdefault(KEY,{'content':content,'receipts':{}});assert record['content']==content
 def save():write_json(STATE,state);persist('PSFR: save Instagram approved week receipts')
 urls={}
 for p in posts:
  assert {t for t in p['caption'].split() if t.startswith('#')}==TAGS and p['caption'].count('#')==5
  a=p['assets']['tiktok'];assert a['dimensions']==[1080,1920]
  url='https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/'+content['media_commit']+'/'+a['path'];urls[p['id']]=url
  if action=='stage':
   assert hashlib.sha256((ROOT/a['path']).read_bytes()).hexdigest()==a['sha256']
   with urllib.request.urlopen(url,timeout=60) as response:assert hashlib.sha256(response.read()).hexdigest()==a['sha256']
 save();capacity_full=False
 for p in posts:
  r=record['receipts'].setdefault(p['id'],{});url=urls[p['id']]
  if r.get('verified_scheduled'):continue
  due=datetime.fromisoformat(p['dueAt'].replace('Z','+00:00'));assert due>now,'No late publishing allowed'
  if not r.get('post_id'):
   assert action=='stage','Fill must only edit existing post IDs'
   assert not r.get('status'),'Unresolved creation attempt; reconcile before retry'
   r.update(status='pending',dueAt=p['dueAt'],channel_id=CID,video_url=url,scheduling_type=MODE);save()
   try:response=buffer(query(p,url,draft=capacity_full))['createPost']
   except Exception:
    r['status']='uncertain';save();raise RuntimeError('Uncertain create; no blind retry') from None
   if response.get('__typename')=='LimitReachedError' and not capacity_full:
    r['capacity_rejection']=response;r['status']='pending-draft';save();capacity_full=True
    try:response=buffer(query(p,url,draft=True))['createPost']
    except Exception:
     r['status']='uncertain-draft';save();raise RuntimeError('Uncertain draft; no blind retry') from None
   pid=response.get('post',{}).get('id')
   if not pid:r.update(status='rejected',error=response);save();raise RuntimeError('Instagram rejected item: '+json.dumps(response))
   r.update(status='accepted',post_id=pid);save()
  result=read_back(r['post_id'])
  if result['status']=='scheduled':
   verify_post(result,CID,MODE,p,url);r.update(last_status=result,verified_scheduled=True,verified_draft=False);save();print('VERIFIED SCHEDULED',p['id'],r['post_id'],flush=True);continue
  verify_draft(result,CID,MODE,p,url);r.update(last_status=result,verified_draft=True,verified_scheduled=False);save()
  if action=='stage':print('VERIFIED DRAFT',p['id'],r['post_id'],flush=True);continue
  assert r.get('schedule_attempt',{}).get('status') not in ['pending','uncertain'],'Unresolved schedule edit'
  r['schedule_attempt']={'status':'pending','attempted_at':now.isoformat()};save()
  try:response=buffer(query(p,url,pid=r['post_id']))['editPost']
  except Exception:
   r['schedule_attempt']['status']='uncertain';save();raise RuntimeError('Uncertain scheduling edit; reconcile first') from None
  if response.get('__typename')=='LimitReachedError':
   r['schedule_attempt'].update(status='deferred-capacity',result=response);save();continue
  if not response.get('post',{}).get('id'):
   r['schedule_attempt'].update(status='rejected',result=response);save();raise RuntimeError('Schedule edit rejected')
  r['schedule_attempt']['status']='accepted';save()
  result=read_back(r['post_id']);verify_post(result,CID,MODE,p,url);r.update(last_status=result,verified_scheduled=True,verified_draft=False);save();print('SCHEDULED SAME ID',p['id'],r['post_id'],flush=True)
 scheduled=sum(x.get('verified_scheduled',False) for x in record['receipts'].values());drafts=sum(x.get('verified_draft',False) and not x.get('verified_scheduled',False) for x in record['receipts'].values())
 record['verification']={'scheduled_posts':scheduled,'verified_drafts':drafts,'live_delivery_verified':False,'finite_bank_only':True}
 record['capacity_fill']={'window':'2026-10-28 through 2026-10-30','time':'20:30 Europe/London','existing_ids_only':True,'enabled':scheduled<14}
 save();assert scheduled+drafts==14
 if action=='fill' and now.date().isoformat()=='2026-10-30' and scheduled<14:raise RuntimeError('Final queue fill incomplete; inspect exact draft IDs')
 print('COMPLETE:',scheduled,'scheduled Instagram Reels;',drafts,'verified drafts. Live delivery not yet verified.')
if __name__=='__main__':main(sys.argv[1])
