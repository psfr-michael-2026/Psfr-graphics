"""PSFR scheduled graphics. Defaults to offline preview; no embedded credentials."""
import argparse
import datetime as dt
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
from urllib.parse import quote
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'state.json'


def read_json(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    tmp.replace(path)


def request_json(url, payload, headers):
    # Never retry a mutation: a timeout can occur after the service accepted it.
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={'Content-Type': 'application/json', **headers})
    with urllib.request.urlopen(req, timeout=90) as response:
        return json.load(response)


def buffer(query):
    key = os.environ.get('BUFFER_API_KEY')
    if not key:
        raise RuntimeError('BUFFER_API_KEY is missing from repository secrets.')
    data = request_json('https://api.buffer.com', {'query': query},
                        {'Authorization': 'Bearer ' + key})
    if data.get('errors'):
        raise RuntimeError('Buffer rejected the request. Check the API schema and account permissions.')
    return data['data']


def discover_channels():
    orgs = buffer('query { account { organizations { id name } } }')['account']['organizations']
    result = []
    for org in orgs:
        query = 'query { channels(input: {organizationId: ' + json.dumps(org['id']) + \
                '}) { id name displayName service isQueuePaused } }'
        result.extend(buffer(query)['channels'])
    return result


def validate_post(post):
    limits = {'headline': 85, 'takeaway': 150, 'caption': 900}
    for field, limit in limits.items():
        value = post.get(field)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError('Invalid content field: ' + field)
        if any(ord(c) < 32 and c not in '\n\t' for c in value):
            raise ValueError('Unsupported control character in content.')
    if post['caption'].count('#') > 5:
        raise ValueError('Caption exceeds five hashtags.')
    return {k: post[k].strip() for k in limits}


def generate(config, state, slot):
    key = os.environ.get('ANTHROPIC_API_KEY')
    if not key:
        raise RuntimeError('ANTHROPIC_API_KEY is missing. Demo does not need a key.')
    recent = [r['content']['headline'] for r in list(state.values())[-40:] if r.get('content')]
    topic = config['topics'][int(hashlib.sha256(slot.encode()).hexdigest(), 16) % len(config['topics'])]
    payload = {'model': config['model'], 'max_tokens': 600,
               'system': (ROOT / 'brand.txt').read_text(),
               'messages': [{'role': 'user', 'content': json.dumps({'topic': topic, 'avoid': recent})}]}
    result = request_json('https://api.anthropic.com/v1/messages', payload,
                          {'x-api-key': key, 'anthropic-version': '2023-06-01'})
    if result.get('stop_reason') != 'end_turn':
        raise ValueError('Content generation did not finish normally.')
    text = ''.join(block.get('text', '') for block in result['content'] if block['type'] == 'text')
    post = validate_post(json.loads(text))
    if post['headline'].casefold() in [x.casefold() for x in recent]:
        raise ValueError('Generated headline repeats a recent post; stopped.')
    return post


def font(size, bold=False):
    name = 'DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'
    candidates = [ROOT / 'assets' / name, Path('/usr/share/fonts/truetype/dejavu') / name]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    raise RuntimeError('DejaVu fonts are missing; install fonts-dejavu-core.')


def wrap(draw, text, face, width):
    words = text.split()
    lines = []
    current = ''
    for word in words:
        candidate = (current + ' ' + word).strip()
        if draw.textlength(candidate, font=face) <= width:
            current = candidate
        else:
            if not current or draw.textlength(word, font=face) > width:
                raise ValueError('A word is too wide for the graphic.')
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render(post, path):
    image = Image.new('RGB', (1080, 1920), '#101114')
    draw = ImageDraw.Draw(image)
    draw.rectangle((80, 170, 190, 180), fill='#E81020')
    draw.text((80, 220), 'PSFR', font=font(110, True), fill='white')
    draw.text((85, 350), 'HEALTH SYSTEMS', font=font(31), fill='#c9cbd1')
    for size in range(90, 47, -2):
        face = font(size, True)
        lines = wrap(draw, post['headline'], face, 910)
        if len(lines) * (size + 16) <= 650:
            break
    else:
        raise ValueError('Headline cannot fit safely.')
    y = 560
    for line in lines:
        draw.text((80, y), line, font=face, fill='white')
        y += size + 16
    y += 85
    detail_face = font(39)
    details = wrap(draw, post['takeaway'], detail_face, 900)
    if y + len(details) * 57 > 1530:
        raise ValueError('Takeaway cannot fit safely.')
    for line in details:
        draw.text((85, y), line, font=detail_face, fill='#c9cbd1')
        y += 57
    colours = ['#E81020', '#F07020', '#70D030', '#0868F0']
    labels = ['POWER', 'STRENGTH', 'FUEL', 'RECOVERY']
    for i, (colour, label) in enumerate(zip(colours, labels)):
        x = 80 + i * 230
        draw.rectangle((x, 1635, x + 210, 1645), fill=colour)
        draw.text((x, 1678), label, font=font(23, True), fill='white')
    draw.text((85, 1790), 'psfrhealthsystems.co.uk', font=font(32), fill='#c9cbd1')
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, quality=94, optimize=True)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def persist(message):
    git('add', 'state.json', 'generated')
    if git('diff', '--cached', '--name-only'):
        git('commit', '-m', message)
        git('push', 'origin', 'HEAD:main')


def verify_image(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=20) as response:
                content = response.read(8_000_001)
            img = Image.open(io.BytesIO(content))
            img.verify()
            if len(content) > 8_000_000 or img.size != (1080, 1920):
                raise ValueError('Public graphic has incorrect dimensions or size.')
            return
        except Exception:
            if attempt == 3:
                raise RuntimeError('Public image verification failed; no Buffer post was created.') from None
            time.sleep(3)


def create_query(channel, post, url, mode):
    # JSON string quoting also safely quotes GraphQL string literals.
    metadata = ''
    if channel['service'].lower() == 'tiktok':
        metadata = ', metadata: {tiktok: {title: ' + json.dumps(post['headline']) + '}}'
    return ('mutation { createPost(input: {channelId: ' + json.dumps(channel['id']) +
            ', text: ' + json.dumps(post['caption']) + ', schedulingType: automatic, mode: addToQueue' +
            ', needsApproval: false, aiAssisted: true, saveToDraft: ' + ('true' if mode in ('draft', 'test-draft') else 'false') +
            ', assets: [{image: {url: ' + json.dumps(url) + '}}]' + metadata +
            '}) { ... on PostActionSuccess { post { id } } ... on MutationError { message } } }')


def deliver(channel, post, url, mode, receipt, save):
    status = receipt.get('status')
    if status == 'accepted':
        return
    if status in ('pending', 'uncertain', 'rejected'):
        raise RuntimeError('A previous attempt needs reconciliation in Buffer; refusing to duplicate it.')
    # Commit a reservation BEFORE making the external mutation. A lost response cannot cause a blind retry.
    receipt.update(status='pending')
    save()
    try:
        result = buffer(create_query(channel, post, url, mode))['createPost']
    except Exception:
        receipt['status'] = 'uncertain'
        save()
        raise RuntimeError('Buffer response was uncertain. Check Buffer before another attempt.') from None
    if not result.get('post', {}).get('id'):
        receipt['status'] = 'rejected'
        save()
        raise RuntimeError('Buffer did not accept this post. Check the channel and media requirements.')
    receipt.update(status='accepted', post_id=result['post']['id'])
    save()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['demo', 'check', 'test-draft', 'draft', 'queue'], default='demo', nargs='?')
    args = parser.parse_args()
    config = read_json(ROOT / 'config.json')
    if args.mode == 'demo':
        post = validate_post(read_json(ROOT / 'demo.json'))
        render(post, ROOT / 'preview.jpg')
        print('Offline preview created. No accounts contacted; nothing published.')
        return
    channels = discover_channels()
    print(json.dumps({'channels': channels}, indent=2))
    if args.mode == 'check':
        return
    targets = config['channels']
    if not targets:
        raise RuntimeError('No target channels configured. Run check and choose the two exact channel IDs.')
    live = {channel['id']: channel for channel in channels}
    for target in targets:
        channel = live.get(target['id'])
        if not channel or channel['service'].lower() != target['service'].lower():
            raise RuntimeError('Configured channel missing or service mismatch; stopped.')
        if channel.get('isQueuePaused') and args.mode == 'queue':
            raise RuntimeError('A target channel queue is paused; stopped.')
    now = dt.datetime.now(ZoneInfo('Europe/London'))
    slot = now.strftime('%Y-%m-%d') + ('-am' if now.hour < 12 else '-pm')
    state = read_json(STATE, {})
    key = slot + '-' + args.mode
    record = state.setdefault(key, {'receipts': {}})
    if not record.get('content'):
        record['content'] = (validate_post(read_json(ROOT / 'demo.json')) if args.mode == 'test-draft'
                             else generate(config, state, slot))
    post = record['content']
    relative = 'generated/' + key + '.jpg'
    render(post, ROOT / relative)
    def save():
        write_json(STATE, state)
        persist('PSFR: ' + key)
    save()
    commit = git('rev-parse', 'HEAD')
    image_url = ('https://raw.githubusercontent.com/' + config['repository'] + '/' + commit + '/' + quote(relative))
    verify_image(image_url)
    for target in targets:
        receipt = record['receipts'].setdefault(target['id'], {})
        deliver(live[target['id']], post, image_url, args.mode, receipt, save)
    print('Buffer accepted the ' + args.mode + ' requests. Acceptance is not proof of social publication.')


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        # Do not print raw HTTP bodies, request headers or API keys into public logs.
        print('Stopped: ' + str(error) if isinstance(error, (ValueError, RuntimeError)) else
              'Stopped: request or local operation failed. Credentials were not printed.', file=sys.stderr)
        sys.exit(1)
