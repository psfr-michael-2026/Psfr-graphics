"""Remove sound from the existing three drafts; never create or publish a post."""
import hashlib
import json
import subprocess
import urllib.request
from psfr import ROOT, STATE, buffer, read_json, write_json, persist, git
from morning_video_drafts import KEY, TARGETS, read_back

def probe(path):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]))

def video_hash(path):
    return subprocess.check_output(['ffmpeg','-v','error','-i',str(path),'-map','0:v:0','-c:v','copy','-f','hash','-'],text=True).strip()

def main():
    state = read_json(STATE,{})
    record = state[KEY]
    post = read_json(ROOT / 'morning_video_post.json')
    generated = ROOT / 'generated'
    generated.mkdir(exist_ok=True)
    manifest = {}
    for platform, dimensions in [('Facebook',[1440,1800]),('TikTok',[1080,1920])]:
        source = ROOT / ('PSFR-2026-10-27-AM-' + platform + '-music.mp4')
        target = generated / ('PSFR-2026-10-27-AM-' + platform + '-silent.mp4')
        if not target.exists():
            subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-map','0:v:0','-c:v','copy','-an','-movflags','+faststart',str(target)],check=True)
        info = probe(target)
        assert all(s['codec_type'] != 'audio' for s in info['streams'])
        video = next(s for s in info['streams'] if s['codec_type'] == 'video')
        assert [video['width'],video['height']] == dimensions
        assert abs(float(info['format']['duration']) - 15) < .1
        assert video_hash(source) == video_hash(target), 'Video stream changed'
        manifest[platform] = {'path':str(target.relative_to(ROOT)),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'dimensions':dimensions,'audio_streams':0}
    record['content']['audio_policy'] = 'silent-no-music'
    record['content']['silent_assets'] = manifest
    write_json(STATE,state)
    persist('PSFR: store silent morning videos')
    commit = git('rev-parse','HEAD')
    def save():
        write_json(STATE,state)
        persist('PSFR: save music removal receipts')
    for cid, service, platform, metadata in TARGETS:
        receipt = record['receipts'][cid]
        pid = receipt['post_id']
        current = read_back(pid)
        assert current['status'].lower() == 'draft', 'Refusing to change a non-draft post'
        assert current['channelId'] == cid
        url = 'https://raw.githubusercontent.com/psfr-michael-2026/Psfr-graphics/' + commit + '/' + manifest[platform]['path']
        if receipt.get('audio_update',{}).get('status') == 'verified':
            assert current['assets'][0]['source'] == receipt['video_url']
            print(service + ': already verified silent draft')
            continue
        with urllib.request.urlopen(url,timeout=60) as response:
            assert hashlib.sha256(response.read()).hexdigest() == manifest[platform]['sha256']
        receipt['audio_update'] = {'status':'pending','target_url':url}
        save()
        query = ('mutation { editPost(input: {id: ' + json.dumps(pid) + ', text: ' + json.dumps(current['text']) +
                 ', saveToDraft: true, schedulingType: automatic, aiAssisted: true, assets: [{video: {url: ' +
                 json.dumps(url) + '}}], metadata: {' + metadata +
                 '}}) { __typename ... on PostActionSuccess { post { id status } } ... on MutationError { message } } }')
        try:
            result = buffer(query)['editPost']
        except Exception:
            receipt['audio_update']['status'] = 'uncertain'
            save()
            raise RuntimeError('Uncertain edit response; reconcile existing draft before retry.') from None
        if result.get('post',{}).get('id') != pid:
            receipt['audio_update'].update(status='rejected',error=result.get('message',result.get('__typename')))
            save()
            raise RuntimeError('Draft edit rejected: ' + str(receipt['audio_update']['error']))
        verified = read_back(pid)
        receipt['last_status'] = verified
        save()
        assert verified['status'].lower() == 'draft'
        assert verified['text'] == current['text']
        assert verified['channelId'] == cid
        assert len(verified['assets']) == 1
        assert verified['assets'][0]['source'] == url
        assert verified['assets'][0]['mimeType'] == 'video/mp4'
        receipt['video_url'] = url
        receipt['audio_update'].update(status='verified',audio_streams=0)
        save()
        print(json.dumps({'service':service,'post_id':pid,'status':'draft','audio_streams':0}))
    post['soundtrack'] = None
    post['audio_policy'] = 'silent-no-music'
    for platform in manifest:
        post['platforms'][platform]['video'] = manifest[platform]['path']
        post['platforms'][platform]['video_sha256'] = manifest[platform]['sha256']
    write_json(ROOT / 'morning_video_post.json',post)
    git('add','morning_video_post.json')
    persist('PSFR: record silent video production policy')
    print('All three existing drafts now use silent videos. Nothing published or scheduled.')

if __name__ == '__main__':
    main()
