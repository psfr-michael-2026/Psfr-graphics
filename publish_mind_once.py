"""Publish approved W01-D02-AM once per channel; no recurring schedule."""
import hashlib
import json
import subprocess
import time
from pathlib import Path
from psfr import buffer, discover_channels, persist, write_json, STATE

ROOT = Path(__file__).resolve().parent
KEY = '2026-10-26-W01-D02-AM-approved'
TARGETS = {'6adac73f778b240e2f96b17b': 'facebook', '6adac5fe778b240e2f96a871': 'tiktok'}

def query_for(channel_id, service, post, image_url):
    metadata = 'facebook: {type: post}' if service == 'facebook' else 'tiktok: {title: '+json.dumps(post['headline'])+'}'
    return ('mutation { createPost(input: {channelId: '+json.dumps(channel_id)+
            ', text: '+json.dumps(post['caption'])+', assets: [{image: {url: '+json.dumps(image_url)+'}}]'+
            ', metadata: {'+metadata+'}, schedulingType: automatic, mode: shareNow, saveToDraft: false, needsApproval: false, aiAssisted: true})'+
            ' { __typename ... on PostActionSuccess { post { id status } } ... on MutationError { message } } }')

def main():
    post = json.loads((ROOT/'approved/move-for-your-mind/post.json').read_text())
    from PIL import Image
    for service, asset in post['assets'].items():
        image = ROOT / asset['path']
        if hashlib.sha256(image.read_bytes()).hexdigest() != asset['sha256']:
            raise RuntimeError('Approved image hash mismatch; stopped.')
        with Image.open(image) as im:
            if list(im.size) != asset['dimensions']:
                raise RuntimeError('Approved image dimensions mismatch; stopped.')
    if post['caption'].count('#') != 5 or '#psfrhealthsystems' not in post['caption']:
        raise RuntimeError('Approved hashtag check failed.')
    live = {c['id']: c for c in discover_channels()}
    for channel_id, service in TARGETS.items():
        if channel_id not in live or live[channel_id]['service'].lower() != service:
            raise RuntimeError('Confirmed channel mismatch; stopped.')
    state = json.loads(STATE.read_text())
    record = state.setdefault(KEY, {'content':post, 'receipts':{}})
    if record['content'] != post:
        raise RuntimeError('Existing approval record differs; stopped.')
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    urls = {}
    import urllib.request
    for service, asset in post['assets'].items():
        url = 'https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/'+commit+'/'+asset['path']
        with urllib.request.urlopen(url, timeout=30) as response:
            if hashlib.sha256(response.read()).hexdigest() != asset['sha256']:
                raise RuntimeError('Public approved image mismatch; stopped.')
        urls[service] = url
    def save(message):
        write_json(STATE,state)
        persist(message)
    for channel_id, service in TARGETS.items():
        url = urls[service]
        receipt = record['receipts'].setdefault(channel_id,{})
        if receipt.get('status') == 'accepted':
            continue
        if receipt.get('status'):
            raise RuntimeError('Previous attempt requires reconciliation; no duplicate created.')
        receipt.update(status='pending', image_url=url)
        save('PSFR: reserve approved mind post publication '+service)
        try:
            result = buffer(query_for(channel_id,service,post,url))['createPost']
        except Exception:
            receipt['status']='uncertain'
            save('PSFR: record uncertain mind post response '+service)
            raise RuntimeError('Uncertain Buffer response. Do not retry publication blindly.') from None
        if not result.get('post',{}).get('id'):
            receipt.update(status='rejected',result=result)
            save('PSFR: record rejected mind post response '+service)
            raise RuntimeError('Buffer rejected approved publication; see durable receipt.')
        receipt.update(status='accepted',post_id=result['post']['id'])
        save('PSFR: save approved mind post post ID '+service)
        print('ACCEPTED',service,json.dumps(result),flush=True)
    for attempt in range(24):
        done=True
        for channel_id, service in TARGETS.items():
            receipt=record['receipts'][channel_id]
            pid=receipt['post_id']
            fields='id status channelId sentAt externalLink error { message supportUrl }'
            result=buffer('query { post(input: {id: '+json.dumps(pid)+'}) { '+fields+' } }')['post']
            if result['channelId'] != channel_id:
                raise RuntimeError('Status channel mismatch.')
            receipt['last_status']=result
            print('STATUS',service,json.dumps(result),flush=True)
            if result['status'].lower() not in ('sent','error','failed'):
                done=False
        save('PSFR: save approved mind post delivery status')
        if done:
            break
        time.sleep(10)
    if not all(r.get('last_status',{}).get('status','').lower()=='sent' for r in record['receipts'].values()):
        raise RuntimeError('Not all channels confirmed sent; inspect saved receipts before further action.')

if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Stopped: publication incomplete; inspect durable receipts. No blind retry.', flush=True)
        raise SystemExit(1)
