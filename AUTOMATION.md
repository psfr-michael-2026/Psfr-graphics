# PSFR automatic graphics — prepared implementation

Status updated 25 October 2026: deployed. One sample image and caption published to both channels, with Michael supplying screenshots confirming each is visible.
Recurring posting remains OFF. Fresh Claude API generation has not been configured or live-tested.

## Resume here — current checkpoint

This repository is the durable source for automation code, public content instructions, images and delivery receipts. It runs on GitHub's cloud runners; no particular ChatGPT conversation or awake laptop is required for scheduled execution once enabled.

- Facebook: PSFR Health Systems; channel 6adac73f778b240e2f96b17b.
- TikTok: psfrhealthsystems; channel 6adac5fe778b240e2f96a871.
- BUFFER_API_KEY is stored in GitHub Actions secrets. Never request its value in chat.
- Sample headline: "One small step today is still a step."
- Facebook verified by user screenshot: https://www.facebook.com/122128398501469780/posts/122129151057469780
- TikTok verified by user screenshot: https://www.tiktok.com/@psfrhealthsystems/video/7700458258326129952
- Existing sample IDs: Facebook 6add84a2e4be8a4d868ebd25; TikTok 6add84a5bd33ce99c355b36e. Do not recreate or republish these.
- Automatic publishing was confirmed, not notification-only publishing.
- Current renderer produces one 1080x1920 JPEG with a text wordmark. Multi-image posts, video and new layouts require implementation and tests.
- Publishing an existing draft via editPost required explicitly resupplying text, image and service metadata. Facebook requires metadata.facebook.type:post.
- Buffer "sent" is a delivery report; visible platform posts were additionally confirmed by screenshots.
- No paid API generation, new subscriptions or recurring publication has been authorised by this checkpoint.

Next work: agree a public content brief, choose a content bank or separately billed AI API generation, test future content production, agree London morning/evening times, and enable recurring posting only after approval. A prepared content bank can avoid AI API charges but requires replenishment; it is not yet implemented.

Suggested project organisation: retain this conversation for Automation & Publishing; use a separate Content & Design chat in the same PSFR project when useful. In a new chat, provide this repository and ask the assistant to read AUTOMATION.md, brand.txt, config.json and current workflow/state before changes. Claude chat project context is not automatically available to this runner or the API.

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

Completed live: Buffer authentication, exact channel discovery, repository writes, public image fetch, real draft creation, publication to both services, and user visual verification.
Outstanding: fresh AI generation (or a content bank), approved ongoing content brief, final publishing times, and enabling/testing the recurring schedule.

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


## Latest checkpoint — 27 October 2026: three video drafts verified

This supersedes earlier image-only/testing notes for this one authorised test. Recurring posting remains OFF. No publication or scheduling was authorised or performed.

- Saved original morning post: PSFR-2026-10-27-AM, “Train for everyday strength.” Exact saved caption preserved in morning_video_post.json.
- Original 15-second videos with audio transferred without regeneration. Facebook 1440 × 1800; TikTok/YouTube 1080 × 1920. Checksums verified against saved record and immutable hosted bytes at media commit 041f4bf46be3ab488ceafe326515bfa150da5089.
- Draft-only implementation: morning_video_drafts.py; workflow .github/workflows/morning-video-drafts.yml. No schedule; uses existing BUFFER_API_KEY secret without exposing it. State key: 2026-10-27-AM-three-channel-video-draft-test. Pending reservations precede mutations; accepted drafts reused; uncertain attempts require reconciliation.
- Successful run: https://github.com/psfr-michael-2026/Psfr-graphics/actions/runs/40446845396.
- Facebook draft: 6ae020cea6170f32b1774c03.
- TikTok draft: 6ae020d305551cc3591ea201.
- YouTube draft: 6ae020d9e322dad801213466 (vertical TikTok asset reused).
- Each was independently read back from Buffer: correct channel, exact caption, status draft, automatic publishing mode and video/mp4 asset attached. Original files contain AAC soundtrack. This is draft/API verification, not live platform delivery or user playback verification.
- Next action: Michael reviews the existing morning video/music and caption in the three drafts. Await explicit publication instruction; publish these exact draft IDs if authorised. Do not recreate, duplicate or republish the mind post as a test. Both 27 October creatives remain awaiting final approval; fourteen-post bank incomplete. Subscription/editor research remains deferred.


## Music OFF — 27 October 2026 (latest instruction)

Michael requests all PSFR videos WITHOUT MUSIC. This overrides earlier upbeat/112 BPM soundtrack preferences. Do not add any backing music unless explicitly requested later. Applies to the prepared evening post and future videos too; strip audio before use. Original music files are superseded and must not be posted.

The SAME Facebook, TikTok and YouTube morning draft IDs above have been edited to attach silent MP4s. Captions and video pictures are unchanged; no new drafts, publication or scheduling. Zero audio streams and identical compressed video-stream hashes verified; each Buffer draft was read back to verify its new silent video source. Durable per-channel audio_update receipts are in state.json. Silent videos are in generated/ with -silent.mp4 names. Successful run: https://github.com/psfr-michael-2026/Psfr-graphics/actions/runs/40448118007. Recurring posting remains OFF. Await creative approval and explicit publication instruction.


## TikTok music handover test — 27 October 2026
Michael authorised testing ONE existing TikTok post through notification publishing, so he can choose native TikTok music and finish publishing manually. Existing post ID 6ae020d305551cc3591ea201 was switched from automatic to notification mode and sent for immediate manual handover, using the same silent video and caption. Buffer readback: schedulingType notification, notificationStatus notified, status sent. In THIS notification context, sent means the reminder was sent; it is NOT evidence the video was published on TikTok. Do not resend or create another post. Await Michael tapping the Buffer phone notification and completing the handover. Facebook and YouTube remain silent drafts; no other channel changed. Daily posting OFF. Run: https://github.com/psfr-michael-2026/Psfr-graphics/actions/runs/40448837033.

Proposed workflow to test: prepare silent videos/captions, use Buffer Notify Me for TikTok and YouTube so Michael chooses platform music and completes posting. Facebook can stay silent with separately authorised Buffer publishing. This single TikTok handover does not enable a schedule or authorise the remaining posts.


## REJECTED AND REMOVED — shopping-bag post, 27 October 2026
Michael rejected PSFR-2026-10-27-AM (“Train for everyday strength.” shopping-bag creative) as naff/corny and explicitly requested deletion everywhere, including Buffer. Do not reuse, regenerate or recreate it; no replacement requested. Avoid staged smiling stock-style people in fitness clothing carrying shopping bags. Establish a more mature, credible aesthetic from references before another design.

Deleted successfully from Buffer: Facebook 6ae020cea6170f32b1774c03 and YouTube 6ae020d9e322dad801213466 (DeletePostSuccess receipts). TikTok 6ae020d305551cc3591ea201 is a sent NOTIFICATION record, not evidence of social publication; deletePost returned VoidMutationError: Account is not allowed to perform this action on post. It remains unresolved, NOT deleted. Browser fallback reached Buffer email login verification; await Michael approving the emailed sign-in link, then inspect/delete remaining record if UI allows. Do not resend handover or publish. No TikTok externalLink returned at inspection.

The six saved morning-package Library items (two graphics, two silent videos, caption and post JSON) were moved to trash successfully. Active morning videos and morning production/notification runners/workflows removed from current repository tree, with rejection tombstone and deletion receipts retained to prevent duplicates. Repository history has not been rewritten. Local working media removed. Other posts remain untouched; recurring posting OFF. Cleanup run: https://github.com/psfr-michael-2026/Psfr-graphics/actions/runs/40449460821 (failed ONLY because TikTok record deletion rejected; Facebook/YouTube deletion and active asset cleanup succeeded).


## Approved finite week bank — 27 October 2026
Michael approved the fourteen people-free posts for Facebook and TikTok, 28 October–3 November 2026 at 07:00 and 19:00 Europe/London (GMT). Final five tags: #psfrhealthsystems #Fitness #Health #FitnessMotivation #gym. This removes Over40Fitness, retains FitnessMotivation and adds gym. Silent 15-second videos; no YouTube posts.

State key: 2026-10-28-week-01. Twenty posts are independently read back as scheduled: ten Facebook automatic posts and ten TikTok notification handovers, covering 28 October–1 November. Buffer returned LimitReachedError at ten scheduled posts per account. The remaining eight are independently verified DRAFTS for 2–3 November, with exact existing IDs and planned times retained. Successful draft staging run 40479491504. The earlier queue run 40478758198 stopped on the known capacity rejection; it did not create the rejected eleventh Facebook item. The safe draft-staging action retained that rejection receipt before creating its one draft.

Finite capacity-fill runner week_capacity.py edits the SAME remaining draft IDs, never creates new posts in fill mode. Workflow .github/workflows/week-capacity.yml checks at 20:30 UTC on 28, 29 and 30 October; runtime blocks all external calls outside 28–30 October 2026. It retries a known capacity rejection on the next authorised check, stops on uncertain edits, and fails clearly if the last 30 October check remains incomplete. These future edits have NOT yet been live-verified. This is not an indefinite content-generation schedule; original PSFR_AUTOMATION_ENABLED remains OFF. Use the finite runner and receipts for follow-up; do not rerun the original create-and-schedule script to manufacture additional posts.

Facebook will publish automatically; TikTok reminders require Michael to add native music and finish publishing at each notification. Buffer cannot batch-select TikTok library music. Scheduled/draft verification is not proof of future platform delivery. Original rejected shopping-bag notification-record deletion remains a separate unresolved item; no rejected content was reused.


## Instagram included — 27 October 2026
Michael authorised adding PSFR Instagram to all fourteen existing posts. Verified Buffer channel 6ae08d042f1f5ed648e92cc0, @psfrhealthsystems, Instagram business, connected and unpaused. Reused the same approved silent 1080×1920, 15-second videos and exact captions; final tags #psfrhealthsystems #Fitness #Health #FitnessMotivation #gym. Instagram metadata type reel, shouldShareToFeed true, automatic publishing, no added music. Dates remain 28 October–3 November 2026, 07:00 and 19:00 Europe/London.

Confirmed: 10 Instagram Reels read back as scheduled, 4 remaining items read back as drafts. Capacity-fill automation edits these SAME draft IDs at 20:30 UK on 28, 29 and 30 October 2026 as space opens; runtime blocks calls outside that exact window. Future queue filling and live Instagram delivery remain unverified. All fourteen are uploaded; no new creative content generated. Facebook/TikTok existing receipts and schedules preserved. YouTube untouched. Successful run 40498611723. Instagram receipts are under state.json key 2026-10-28-week-01-instagram. Ongoing generation remains OFF; this is the authorised finite week only.
