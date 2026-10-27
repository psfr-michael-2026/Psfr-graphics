"""Delete only the rejected shopping-bag post from Buffer and active assets."""
import json
import os
from pathlib import Path
from psfr import ROOT, STATE, buffer, read_json, write_json, persist, git
KEY='2026-10-27-AM-three-channel-video-draft-test'
TARGETS={
 '6adac73f778b240e2f96b17b':'6ae020cea6170f32b1774c03',
 '6adac5fe778b240e2f96a871':'6ae020d305551cc3591ea201',
 '6adfc03d2f1f5ed648df2866':'6ae020d9e322dad801213466'}
def main():
 state=read_json(STATE,{})
 record=state[KEY]
 record['content']['status']='rejected-do-not-reuse'
 record['content']['authorised_action']='delete'
 record['content']['rejection_reason']='Michael rejected the shopping-bag aesthetic as corny and requested complete removal.'
 def save():
  write_json(STATE,state)
  persist('PSFR: rejected shopping post deletion receipts')
 save()
 failed=[]
 for cid,pid in TARGETS.items():
  receipt=record['receipts'][cid]
  assert receipt['post_id']==pid
  deletion=receipt.setdefault('deletion',{})
  if deletion.get('status')=='deleted':
   continue
  if deletion.get('status') in ('pending','uncertain'):
   failed.append(pid+': reconcile earlier deletion before retry')
   continue
  current=buffer('query { post(input: {id: '+json.dumps(pid)+'}) { id channelId status schedulingType notificationStatus externalLink } }')['post']
  assert current['channelId']==cid
  deletion.update(status='pending',previous_status=current)
  save()
  try:
   result=buffer('mutation { deletePost(input: {id: '+json.dumps(pid)+'}) { __typename ... on DeletePostSuccess { id } ... on MutationError { message } } }')['deletePost']
  except Exception:
   deletion['status']='uncertain'
   save()
   failed.append(pid+': deletion response uncertain')
   continue
  if result.get('id')==pid and result.get('__typename')=='DeletePostSuccess':
   deletion.update(status='deleted',response=result)
   receipt['status']='deleted'
   receipt['verified_draft']=False
   receipt['last_status']={'id':pid,'channelId':cid,'status':'deleted'}
   print(json.dumps({'post_id':pid,'channel_id':cid,'status':'deleted'}))
  else:
   deletion.update(status='rejected',response=result)
   failed.append(pid+': '+str(result.get('message',result.get('__typename'))))
  save()
 # Remove active video assets and retired scripts so they cannot recreate the rejected post.
 paths=[
 'PSFR-2026-10-27-AM-Facebook-music.mp4','PSFR-2026-10-27-AM-TikTok-music.mp4',
 'generated/PSFR-2026-10-27-AM-Facebook-silent.mp4','generated/PSFR-2026-10-27-AM-TikTok-silent.mp4',
 'morning_video_post.json','morning_video_drafts.py','mute_morning_drafts.py','tiktok_notification_handover.py',
 '.github/workflows/morning-video-drafts.yml','.github/workflows/mute-morning-drafts.yml','.github/workflows/tiktok-notification-handover.yml']
 for relative in paths:
  path=ROOT/relative
  if path.exists():
   path.unlink()
   git('add','-u','--',relative)
 record['content']['active_assets_removed']=True
 save()
 if failed:
  raise RuntimeError('Some Buffer deletions need attention: '+'; '.join(failed))
 print('All three rejected Buffer post records deleted. Active media and recreating runners removed. Other posts untouched.')
if __name__=='__main__':
 main()
