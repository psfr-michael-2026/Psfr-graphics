# PSFR automatic graphics — prepared implementation

Status: locally tested implementation, not deployed or connected to Michael's accounts.
No live API calls or public posts have been made by this package.

## What this changes

GitHub Actions runs Python on GitHub's computer. The program asks the Claude API
for original evergreen PSFR copy, draws a 1080 × 1920 JPEG, commits the actual
binary image to this public repository, verifies its immutable public URL, then
sends that URL and caption to Michael's existing Buffer channels.

This bypasses both the Claude chat sandbox upload restriction and the GitHub MCP
text-only file tool. There is no daily download, assembly or manual upload.
Michael's laptop is only needed for setup, inspection or changes.
Claude's chat project remains available, but is not automatically consulted by
the API. `brand.txt` supplies the automation's approved public instructions.
Private background files and the P001 introduction are deliberately not included
in this public repository or used for automated posts.

## Prepared files

- `psfr.py`: generation, rendering, hosting, Buffer submission and duplicate protection.
- `.github/workflows/psfr.yml`: manual testing plus a disabled-by-default schedule.
- `brand.txt`: the public content brief.
- `config.json`: repository, model, topics and exact destination IDs.
- `demo.json`: sample copy for a free offline preview.
- `tests/test_pipeline.py`: tests the graphic and external-call failure handling.

The graphic uses PSFR colours and a text wordmark. It does not pretend to contain
the original logo. A cleared original logo can be added after visual approval.

## Account connection and verification order

1. Install these files at the root of `psfr-michael-2026/Psfr-graphics`, preserving
   the `.github/workflows/psfr.yml` directory structure. Keep the existing README
   if desired. ZIP files alone do not install a workflow.
2. Run Actions → PSFR graphics → Run workflow → `demo`. No keys or payment needed.
3. In Buffer Settings → API, create the one personal API key allowed on Free.
   Store it in GitHub repository Settings → Secrets and variables → Actions →
   New repository secret as `BUFFER_API_KEY`. Never put the value in chat/files.
4. Run workflow mode `check`. This only lists connected channels. Set the two
   exact IDs in config.json, e.g.:
   `"channels": [{"id":"ACTUAL_ID","service":"facebook"},{"id":"ACTUAL_ID","service":"tiktok"}]`.
   The check supplies actual service values; match them exactly. Do not guess IDs.
5. Run mode `test-draft` first: it uses the prepared demo text, makes the real image,
   hosts it and submits two Buffer drafts WITHOUT a Claude API key or payment.
   Check these drafts and publish the exact test drafts only when ready. Confirm
   Facebook and TikTok publication before setting up paid generation.
6. Set up Claude Console API billing and an API key. API usage is separate from
   Claude chat subscriptions. No Claude Pro upgrade is required for API use.
   Store that key as repository secret `ANTHROPIC_API_KEY`. Disable automatic
   credit recharge initially. Check the current model remains available.
7. Run mode `draft`. The program generates the graphic, publishes the public
   image in GitHub and creates two Buffer drafts. It does not schedule the drafts.
   Inspect the graphic, caption, selected channels and TikTok photo compatibility.
8. To test social publication, schedule those exact drafts through Buffer once
   Michael is ready. Confirm both posts actually appear, not merely accepted IDs.
9. Configure Buffer's morning/evening queue slots. Only after the live tests pass,
   set Actions repository variable `PSFR_AUTOMATION_ENABLED` to `true`. Scheduled
   runs at 07:17 and 18:17 Europe/London then generate and add one post per channel
   to the next available Buffer slot. These times are placeholders, not optimised
   recommendations. Runs can be delayed; set Buffer slots later than generation.

To stop daily posting, change `PSFR_AUTOMATION_ENABLED` to `false` or disable the
workflow. Scheduled jobs are inactive until that variable is explicitly enabled.
Manual `queue` mode can schedule public posts: do not choose it for a preview.

## Costs

- Standard GitHub Actions runners in public repositories: free execution under
  GitHub's documented policy. This package uses ubuntu-latest, not a paid larger runner.
- Graphics drawn by Python/Pillow: no image-generation subscription.
- Buffer API: included with Free, subject to channel, queue and API limits.
- Claude API: separate prepaid usage; exact cost depends on model and tokens.
  No paid Claude chat subscription or Make/Bannerbear subscription is needed.

No account has been upgraded and no charge has been authorised by this package.

## Tests completed and outstanding

Local tests cover rendering dimensions/size, content validation, draft requests,
durable reservation before a post request, uncertain responses and duplicate skips.
Mocked API results test program behaviour only; they are not live service tests.

Outstanding: actual API authentication, target channel IDs, repository push
permission, public image fetch from GitHub, Buffer draft acceptance, TikTok and
Facebook publication, and the running schedule. Do not label this operational
until those account-specific checks succeed.

Buffer's current API reference includes TikTok photo title metadata. A guide's
supported-platform list omits TikTok. The live draft and publication tests resolve
that documentation discrepancy for Michael's account; do not buy an upgrade
based on the guide or a successful connection alone.

## Failure handling and maintenance

The program saves a pending receipt to GitHub before each Buffer mutation.
On an uncertain response, it stops instead of retrying and risking a duplicate.
Inspect Buffer manually, then reconcile the matching receipt in state.json before
retrying that slot. Accepted receipts are skipped on rerun. Daily slots are based
on the actual London date and morning/evening period. Concurrency serialises runs.
Only this program should write state.json. Repository/branch is fixed to main.

Generation/validation/hosting failures stop before sending anything to Buffer.
The second destination can fail after the first succeeds; receipts record each
independently. Accepted by Buffer is not equivalent to published on the platform.
GitHub emails workflow failures according to the user's notification settings.
Check Buffer's Sent/Error status regularly. Expired channel authorisations, API
credit exhaustion and service changes can need occasional attention.

The automation commits images on successful runs, which creates repository
activity. GitHub may disable schedules after 60 days of repository inactivity.
Generated images are public; secrets must only be stored in GitHub Actions secrets.
The old personal GitHub token is not needed: Actions gets a repository token.

## Local preview

Install Python and dependencies only if testing locally:
`python -m pip install -r requirements.txt`
`python psfr.py demo`
`python -m unittest discover -s tests -v`

The workflow normally runs on GitHub, not the laptop.

## Official sources checked 25 October 2026

- https://docs.github.com/en/billing/concepts/product-billing/github-actions
- https://docs.github.com/en/actions/concepts/security/github_token
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
- https://developers.buffer.com/guides/authentication.html
- https://developers.buffer.com/reference.html
- https://developers.buffer.com/examples/create-image-post.html
- https://developers.buffer.com/examples/get-organizations.html
- https://developers.buffer.com/examples/get-channels.html
- https://support.buffer.com/articles/using-buffers-api-GtIYIQilz5
- https://support.claude.com/en/articles/8977456-how-do-i-pay-for-my-claude-api-usage
- https://platform.claude.com/docs/en/models/haiku-4-5/overview
