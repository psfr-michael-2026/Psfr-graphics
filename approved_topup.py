"""Stage explicitly approved packages and fill Buffer spaces with the same IDs."""
import hashlib,json,subprocess,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from psfr import ROOT,STATE,buffer,discover_channels,read_json,write_json,persist
from schedule_week import FIELDS,TAGS,verify_post
from week_capacity import verify_draft

KEY='approved-rolling-posts-v1'
MANIFEST=ROOT/'approved/rolling/manifest.json'
TARGETS=[('6adac73f778b240e2f96b17b','facebook','automatic'),
         ('6adac5fe778b240e2f96a871','tiktok','notification'),
         ('6ae08d042f1f5ed648e92cc0','instagram','automatic')]

def stamp(value):return datetime.fromisoformat(value.replace('Z','+00:00'))
def read_post(pid):return buffer('query {post(input:{id:'+json.dumps(pid)+'}) {'+FIELDS+'}}')['post']
def request(p,cid,service,mode,url,pid=None,draft=True):
    action='editPost' if pid else 'createPost'
    identity='id:'+json.dumps(pid) if pid else 'channelId:'+json.dumps(cid)
    approval='' if pid else ',needsApproval:false'
    metadata={'facebook':'facebook:{type:post}',
              'tiktok':'tiktok:{isAiGenerated:true}',
              'instagram':'instagram:{type:reel,shouldShareToFeed:true,isAiGenerated:true}'}[service]
    return ('mutation {'+action+'(input:{'+identity+',text:'+json.dumps(p['caption'])+
            ',dueAt:'+json.dumps(p['dueAt'])+',mode:customScheduled,schedulingType:'+mode+
            ',saveToDraft:'+str(draft).lower()+approval+',aiAssisted:true,assets:[{video:{url:'+json.dumps(url)+
            '}}],metadata:{'+metadata+'}}){__typename ... on PostActionSuccess {post{id status}} ... on MutationError{message}}}')

def main(action):
    assert action in ['stage','fill']
    manifest=read_json(MANIFEST);now=datetime.now(timezone.utc)
    # Only exact packages Michael has approved may enter the upload manifest.
    # Drafting content or running this workflow does not itself grant approval.
    posts=sorted(manifest['posts'],key=lambda p:p['dueAt'])
    assert manifest.get('hosting_approved') is True
    assert len({p['id'] for p in posts})==len(posts)
    for p in posts:
        assert p['approved'] is True and p.get('approved_on')
        assert {x for x in p['caption'].split() if x.startswith('#')}==TAGS and p['caption'].count('#')==5
        local_due=stamp(p['dueAt']).astimezone(ZoneInfo('Europe/London'))
        assert local_due.hour in [7,19] and local_due.minute==0 and local_due.second==0
        assert stamp(p['dueAt'])>=datetime(2026,11,4,tzinfo=timezone.utc)
    state=read_json(STATE,{})
    record=state.setdefault(KEY,{'posts':{},'receipts':{}})
    pending=[p for p in posts if any(not record['receipts'].get(p['id']+':'+service,{}).get('verified_scheduled') for _,service,_ in TARGETS)]
    if not pending:
        print('All approved packages already queued; no Buffer calls.');return
    # A known missed slot is never moved or published late automatically.
    assert all(stamp(p['dueAt'])>now for p in pending),'An approved slot has passed; human reconciliation required.'
    def save():write_json(STATE,state);persist('PSFR: save approved rolling queue receipts')
    channels={c['id']:c for c in discover_channels()}
    for cid,service,mode in TARGETS:
        assert channels[cid]['service'].lower()==service
        c=buffer('query {channel(input:{id:'+json.dumps(cid)+'}) {id isDisconnected isLocked isQueuePaused hasActiveMemberDevice}}')['channel']
        assert not any(c[k] for k in ['isDisconnected','isLocked','isQueuePaused'])
        if mode=='notification':assert c['hasActiveMemberDevice']
    urls={}
    for p in pending:
        existing=record['posts'].get(p['id'])
        if existing:assert existing['content']==p,'Approved content changed; stop'
        else:
            assert action=='stage','Fill may not add a package'
            assert p.get('approval_reference'),'New packages need a recorded explicit approval reference'
            # Check all saved bank and rolling entries for a conflicting reserved slot.
            for other_key,other in state.items():
                if other_key==KEY:continue
                for receipt in other.get('receipts',{}).values():
                    if receipt.get('dueAt'):
                        assert stamp(receipt['dueAt'])!=stamp(p['dueAt']),'Existing bank slot conflict'
            for other_id,other in record['posts'].items():
                assert stamp(other['content']['dueAt'])!=stamp(p['dueAt']),'Rolling slot conflict'
            record['posts'][p['id']]={'content':p,'media_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()}
        for cid,service,mode in TARGETS:
            asset=p['assets']['facebook' if service=='facebook' else 'vertical']
            path=ROOT/asset['path'];assert path.is_relative_to(ROOT/'approved/rolling')
            assert hashlib.sha256(path.read_bytes()).hexdigest()==asset['sha256']
            assert asset['dimensions']==([1440,1800] if service=='facebook' else [1080,1920])
            probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))
            assert len(probe['streams'])==1 and probe['streams'][0]['codec_type']=='video'
            assert [probe['streams'][0]['width'],probe['streams'][0]['height']]==asset['dimensions']
            assert abs(float(probe['format']['duration'])-15)<.05
            url='https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/'+record['posts'][p['id']]['media_commit']+'/'+asset['path']
            with urllib.request.urlopen(url,timeout=60) as response:assert hashlib.sha256(response.read()).hexdigest()==asset['sha256']
            urls[p['id'],cid]=url
    save()
    # First stage every approved item, before any attempt to consume queue capacity.
    for p in pending:
        for cid,service,mode in TARGETS:
            key=p['id']+':'+service;r=record['receipts'].setdefault(key,{})
            url=urls[p['id'],cid]
            if not r.get('post_id'):
                assert action=='stage' and not r.get('status'),'Unresolved create; no blind retry'
                r.update(status='pending',channel_id=cid,dueAt=p['dueAt'],video_url=url,scheduling_type=mode);save()
                try:result=buffer(request(p,cid,service,mode,url))['createPost']
                except Exception:
                    r['status']='uncertain';save();raise RuntimeError('Uncertain creation; reconcile first') from None
                pid=result.get('post',{}).get('id')
                if not pid:
                    r.update(status='rejected',response=result);save();raise RuntimeError('Buffer rejected draft; inspect receipts')
                r.update(status='accepted',post_id=pid);save()
            result=read_post(r['post_id'])
            if result['status']=='scheduled':
                verify_post(result,cid,mode,p,url);r.update(last_status=result,verified_scheduled=True,verified_draft=False)
            else:
                verify_draft(result,cid,mode,p,url)
                assert stamp(result['dueAt'])==stamp(p['dueAt'])
                r.update(last_status=result,verified_draft=True,verified_scheduled=False)
            save()
    full=set()
    for p in pending:
        for cid,service,mode in TARGETS:
            r=record['receipts'][p['id']+':'+service]
            if r.get('verified_scheduled') or cid in full:continue
            assert r.get('schedule_attempt',{}).get('status') not in ['pending','uncertain'],'Unresolved edit; reconcile first'
            r['schedule_attempt']={'status':'pending','at':now.isoformat()};save()
            try:result=buffer(request(p,cid,service,mode,urls[p['id'],cid],pid=r['post_id'],draft=False))['editPost']
            except Exception:
                r['schedule_attempt']['status']='uncertain';save();raise RuntimeError('Uncertain schedule edit; reconcile first') from None
            if result.get('__typename')=='LimitReachedError':
                r['schedule_attempt'].update(status='deferred-capacity',response=result);save();full.add(cid);continue
            if not result.get('post',{}).get('id'):
                r['schedule_attempt'].update(status='rejected',response=result);save();raise RuntimeError('Schedule edit rejected')
            r['schedule_attempt']['status']='accepted';save()
            result=read_post(r['post_id']);verify_post(result,cid,mode,p,urls[p['id'],cid])
            r.update(last_status=result,verified_scheduled=True,verified_draft=False);save()
    totals={}
    for _,service,_ in TARGETS:
        recs=[v for k,v in record['receipts'].items() if k.endswith(':'+service)]
        totals[service]={'scheduled':sum(bool(r.get('verified_scheduled')) for r in recs),'drafts':sum(bool(r.get('verified_draft')) for r in recs)}
    record['verification']={'checked_at':now.isoformat(),'counts':totals,'live_delivery_verified':False};save()
    print('APPROVED_TOPUP_COUNTS',json.dumps(totals),flush=True)

if __name__=='__main__':main(sys.argv[1])
