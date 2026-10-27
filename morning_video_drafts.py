"""One authorised draft per channel. No scheduling or publication path."""
import hashlib
import json
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from psfr import ROOT, STATE, buffer, discover_channels, read_json, write_json, persist

KEY = '2026-10-27-AM-three-channel-video-draft-test'
MEDIA_COMMIT = '041f4bf46be3ab488ceafe326515bfa150da5089'
TARGETS = [
    ('6adac73f778b240e2f96b17b', 'facebook', 'Facebook', 'facebook: {type: post}'),
    ('6adac5fe778b240e2f96a871', 'tiktok', 'TikTok', 'tiktok: {isAiGenerated: true}'),
    ('6adfc03d2f1f5ed648df2866', 'youtube', 'TikTok', 'youtube: {title: "Train for everyday strength.", categoryId: "17", madeForKids: false, isAiGenerated: true}'),
]

def verify_media(path, expected):
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected['video_sha256'], 'Video checksum mismatch'
    probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)]))
    video = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    assert [video['width'], video['height']] == expected['dimensions']
    assert any(s['codec_type'] == 'audio' for s in probe['streams']), 'Missing soundtrack'
    assert abs(float(probe['format']['duration']) - 15) < .1
    url = 'https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/' + MEDIA_COMMIT + '/' + path.name
    with urllib.request.urlopen(url, timeout=60) as response:
        assert hashlib.sha256(response.read()).hexdigest() == expected['video_sha256'], 'Hosted bytes differ'
    return url

def query_for(cid, caption, url, metadata):
    return ('mutation { createPost(input: {channelId: ' + json.dumps(cid) + ', text: ' + json.dumps(caption) +
            ', schedulingType: automatic, mode: addToQueue, saveToDraft: true, needsApproval: false, aiAssisted: true, '+
            'assets: [{video: {url: ' + json.dumps(url) + '}}], metadata: {' + metadata +
            '}}) { __typename ... on PostActionSuccess { post { id status } } ... on MutationError { message } } }')

def read_back(pid):
    return buffer('query { post(input: {id: ' + json.dumps(pid) + '}) { id status channelId text schedulingType assets { mimeType source } } }')['post']

def main():
    post = read_json(ROOT / 'morning_video_post.json')
    caption = post['caption']
    assert caption.count('#') == 5
    channels = {c['id']: c for c in discover_channels()}
    urls = {}
    for cid, service, platform, metadata in TARGETS:
        assert channels[cid]['service'].lower() == service
        expected = post['platforms'][platform]
        urls[cid] = verify_media(ROOT / expected['video'], expected)
    state = read_json(STATE, {})
    record = state.setdefault(KEY, {'content': {'id': post['id'], 'headline': post['headline'], 'caption': caption, 'authorised_action': 'draft-only', 'media_commit': MEDIA_COMMIT}, 'receipts': {}})
    def save():
        write_json(STATE, state)
        persist('PSFR: morning video draft receipts')
    for cid, service, platform, metadata in TARGETS:
        receipt = record['receipts'].setdefault(cid, {})
        if receipt.get('status') not in (None, 'accepted'):
            raise RuntimeError('Previous attempt needs reconciliation: ' + cid)
        if not receipt.get('post_id'):
            receipt.update(status='pending', video_url=urls[cid], service=service)
            save()
            try:
                result = buffer(query_for(cid, caption, urls[cid], metadata))['createPost']
            except Exception:
                receipt['status'] = 'uncertain'
                save()
                raise RuntimeError('Uncertain create response. Inspect Buffer; do not retry blindly.') from None
            pid = result.get('post', {}).get('id')
            if not pid:
                receipt.update(status='rejected', error=result.get('message', result.get('__typename')))
                save()
                raise RuntimeError('Draft rejected: ' + str(receipt['error']))
            receipt.update(status='accepted', post_id=pid)
            save()
        verified = read_back(receipt['post_id'])
        receipt['last_status'] = verified
        save()
        assert verified['status'].lower() == 'draft'
        assert verified['channelId'] == cid
        assert verified['text'] == caption
        assert verified['schedulingType'] == 'automatic'
        assert any(a.get('mimeType', '').startswith('video/') for a in verified['assets'])
        receipt['verified_draft'] = True
        save()
        print(json.dumps({'service': service, 'post_id': receipt['post_id'], 'status': verified['status'], 'video_attached': True}))
    print('Verified three drafts. Nothing scheduled or published. Live platform delivery remains untested.')

if __name__ == '__main__':
    main()
