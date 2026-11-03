"""Publish only Michael's exact approved weights post now, once per channel."""
import json,hashlib,urllib.request,subprocess
from datetime import datetime,timezone
from psfr import buffer,read_json,write_json,STATE,persist
IG_COMMIT=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
KEY='PSFR-20261103-HEAVY-OR-REPS-PUBLISH-NOW'
CAPTION="HEAVIER WEIGHTS OR MORE REPS AS YOU GET OLDER?\n\nBoth have a place.\n\nHeavier weights with fewer reps generally produce greater gains in maximal strength. Lighter weights with more reps can also build muscle—but those sets still need enough effort.\n\nWhat about your joints?\n\nThere isn’t one rep range that protects everyone’s joints. Choose exercises and weights you can control, build gradually and adjust if a movement causes joint pain. Simply doing more repetitions doesn’t automatically make an exercise kinder to your joints.\n\nA practical starting point is a weight you can lift for 8–12 controlled reps, finishing while you could still manage another couple with good technique. It’s a starting point, rather than a rule for every exercise.\n\nGetting older doesn’t mean you have to stop getting stronger.\n\nSave this for your next session. Which feels better for you: heavier sets or more reps? Tell us in the comments.\n\nwww.psfrhealthsystems.co.uk\n\n#psfrhealthsystems #Fitness #Health #FitnessMotivation #gym"
COMMIT="65cf6fc5e3464906982305a542d205cf963effcc"
TARGETS=[('6adac73f778b240e2f96b17b','facebook','automatic','Facebook','7c6d2218c1dae19475c07493cd261dd6f731132c9c203051192205d6b9ede9d8'),
('6adac5fe778b240e2f96a871','tiktok','notification','Vertical','6ab5ee1693455aa1d7b4aeeba43d93abfad38f9a2282d9c8cc954b61273ac720'),
('6ae08d042f1f5ed648e92cc0','instagram','automatic','Vertical','6ab5ee1693455aa1d7b4aeeba43d93abfad38f9a2282d9c8cc954b61273ac720')]
def main():
 assert datetime.now(timezone.utc).date().isoformat()=='2026-11-03','One-day authorisation expired'
 state=read_json(STATE,{})
 rec=state.setdefault(KEY,{'caption':CAPTION,'approval_reference':'Michael: Good. Now get that in. Followed by: We need a post to go out now. (3 November 2026)','receipts':{}})
 assert rec['caption']==CAPTION
 def save():write_json(STATE,state);persist('PSFR: save approved immediate weights-post receipt')
 for cid,service,mode,layout,sha in TARGETS:
  url='https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/'+COMMIT+'/approved/rolling/PSFR-20261103-HEAVY-OR-REPS-'+layout+'.mp4'
  if service=='instagram':
   url='https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/'+IG_COMMIT+'/approved/rolling/PSFR-20261103-HEAVY-OR-REPS-Vertical-25fps.mp4'
   sha='6c88ebe370eeaf4118f7f792dcc2594cb56410ddbc63b49902085265b8b8ba4e'
  with urllib.request.urlopen(url,timeout=60) as res:assert hashlib.sha256(res.read()).hexdigest()==sha
  flags=buffer('query {channel(input:{id:'+json.dumps(cid)+'}) {isDisconnected isLocked isQueuePaused hasActiveMemberDevice}}')['channel']
  assert not any(flags[k] for k in ['isDisconnected','isLocked','isQueuePaused'])
  if mode=='notification':assert flags['hasActiveMemberDevice']
  r=rec['receipts'].setdefault(service,{})
  if service=='instagram' and r.get('status')=='rejected' and not r.get('post_id'):
   assert r.get('response',{}).get('__typename')=='InvalidInputError'
   assert 'frame rate' in r.get('response',{}).get('message','')
   previous=dict(r);r.clear();r['previous_rejection']=previous;save()
  if not r.get('post_id'):
   assert not r.get('status'),'Uncertain previous create; reconcile before retry'
   r.update(status='pending',channel_id=cid,video_url=url,scheduling_type=mode);save()
   metadata={'facebook':'facebook:{type:post}','tiktok':'tiktok:{isAiGenerated:true}','instagram':'instagram:{type:reel,shouldShareToFeed:true,isAiGenerated:true}'}[service]
   query='mutation {createPost(input:{channelId:'+json.dumps(cid)+',text:'+json.dumps(CAPTION)+',schedulingType:'+mode+',mode:shareNow,saveToDraft:false,needsApproval:false,aiAssisted:true,assets:[{video:{url:'+json.dumps(url)+'}}],metadata:{'+metadata+'}}){__typename ... on PostActionSuccess {post{id status}} ... on MutationError{message}}}'
   try:result=buffer(query)['createPost']
   except Exception:
    r['status']='uncertain';save();raise RuntimeError('Uncertain Buffer response; do not retry blindly') from None
   if not result.get('post',{}).get('id'):
    r.update(status='rejected',response=result);save();raise RuntimeError('Buffer rejected immediate post')
   r.update(status='accepted',post_id=result['post']['id']);save()
  post=buffer('query {post(input:{id:'+json.dumps(r['post_id'])+'}) {id channelId text status schedulingType notificationStatus externalLink assets{mimeType source}}}')['post']
  assert post['channelId']==cid and post['text']==CAPTION and post['schedulingType']==mode
  assert any(a['source']==url for a in post['assets'])
  r['last_status']=post;save()
  print('IMMEDIATE_POST_STATUS',service,json.dumps({k:post.get(k) for k in ['id','status','notificationStatus','externalLink']}),flush=True)
if __name__=='__main__':main()
