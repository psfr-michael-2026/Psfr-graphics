"""One TikTok notification handover, never automatic social publication."""
import json
import time
from psfr import ROOT, STATE, buffer, read_json, write_json, persist
from morning_video_drafts import KEY

CID = '6adac5fe778b240e2f96a871'
PID = '6ae020d305551cc3591ea201'

def get_post():
    return buffer('query { post(input: {id: "'+PID+'"}) { id channelId status text schedulingType notificationStatus assets { source mimeType } } }')['post']

def edit(post,send):
    q = ('mutation { editPost(input: {id: "'+PID+'", text: '+json.dumps(post['text'])+
         ', schedulingType: notification, saveToDraft: '+('false, mode: shareNow' if send else 'true')+
         ', assets: [{video: {url: '+json.dumps(post['assets'][0]['source'])+
         '}}], metadata: {tiktok: {isAiGenerated: true}}}) { __typename ... on PostActionSuccess { post { id status } } ... on MutationError { message } } }')
    assert 'schedulingType: automatic' not in q
    return buffer(q)['editPost']

def main():
    state=read_json(STATE,{})
    record=state[KEY]
    receipt=record['receipts'][CID]
    assert receipt['post_id']==PID
    result=receipt.setdefault('notification_handover',{})
    def save():
        write_json(STATE,state)
        persist('PSFR: TikTok notification handover receipt')
    current=get_post()
    channel=buffer('query { channel(input: {id: "'+CID+'"}) { id service hasActiveMemberDevice isDisconnected } }')['channel']
    print(json.dumps({'channel':channel,'post_id':PID,'status':current['status'],'schedulingType':current['schedulingType'],'notificationStatus':current.get('notificationStatus')}))
    if result.get('status')=='notified':
        print('Notification already reported; not sending another.')
        return
    if result.get('status') in ('pending','uncertain','accepted'):
        result['last_status']=current
        save()
        print('Previous attempt needs reconciliation; no duplicate notification sent.')
        return
    assert current['channelId']==CID
    assert current['status'].lower()=='draft', 'Existing post is not a draft; stopped'
    assert receipt['audio_update']['status']=='verified'
    assert current['assets'][0]['source']==receipt['video_url']
    assert '-silent.mp4' in current['assets'][0]['source']
    assert not channel['isDisconnected']
    if not channel['hasActiveMemberDevice']:
        result.update(status='blocked_no_mobile_device',last_status=current)
        save()
        print('BLOCKED: No active Buffer mobile device. Open/sign into Buffer app and enable notifications; no post changed.')
        return
    result['status']='pending'
    save()
    try:
        updated=edit(current,False)
        assert updated.get('post',{}).get('id')==PID, updated.get('message','Draft mode update rejected')
        checked=get_post()
        assert checked['status'].lower()=='draft' and checked['schedulingType']=='notification'
        sent=edit(checked,True)
    except Exception:
        result['status']='uncertain'
        save()
        raise RuntimeError('Handover response uncertain; inspect existing post before retry.') from None
    if not sent.get('post',{}).get('id'):
        result.update(status='rejected',error=sent.get('message',sent.get('__typename')))
        save()
        raise RuntimeError('Notification request rejected: '+str(result['error']))
    result.update(status='accepted',response=sent)
    save()
    for attempt in range(5):
        current=get_post()
        assert current['schedulingType']=='notification'
        result['last_status']=current
        receipt['last_status']=current
        if current.get('notificationStatus')=='notified':
            result['status']='notified'
        save()
        if result['status']=='notified':
            break
        time.sleep(2)
    print(json.dumps({'post_id':PID,'handover_status':result['status'],'post_status':current['status'],'notificationStatus':current.get('notificationStatus'),'schedulingType':current['schedulingType']}))
    print('This is a manual TikTok handover; social publication must be completed in TikTok by Michael.')

if __name__=='__main__':
    main()
