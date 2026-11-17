---
name: agentrobo-studio
description: Criação de mininovelas com roteiro, personagens, cenas coerentes, orçamento e montagem em 720p, usando Google Flow com Omni Flash 1.2 ou Veo 3.1 Lite.
display_name: Estúdio de Mininovelas
summary: Dirija uma série e seus episódios sem perder a continuidade nem desperdiçar créditos.
version: 0.1.0
enabled_by_default: true
always: true
tier: recommended
os:
  - windows
---

## Agentrobo Studio: workflow

When the user asks for mininovelas, clips, episodes or Google Flow, use tools starting with studio_ (tool_search if not shown). Respond in Brazilian Portuguese. Use the Gemini/OpenAI LLM already configured in Monaw for actual story, screenplay, dialogue and prompt-writing. The Studio engine holds the authoritative state; it is not a second language model.

**Hard output requirements:** Every generated or imported clip must be native 720p: 1280x720 (16:9) or 720x1280 (9:16). Allowed models are precisely veo-3.1-lite and omni-flash-1.2; never silently switch to Fast, Quality, older models, 360p or automatic upscale. Use one generation per request, not multiple variations.

**Recommended economical model:** Veo 3.1 Lite 8s at 720p for most shots (10 Flow credits for non-Ultra); Omni Flash 1.2 only when its prompt, character control or duration justifies a higher cost (3 credits per second at 720p for <= 10s non-subscribers). The actual cost shown in Flow is authoritative. If different from Studio estimate, DO NOT submit and tell the user. No paid credit purchase, upgrades or extra generations without prior user approval.

### Stage A: planning (no credits spent)
1. Ask only for essential creative direction if missing; otherwise create a good default: fiction series, 1-3 main characters, <=2 locations, short first episode. Select 16:9 by default; 9:16 if the user requests short-form mobile.
2. studio_create_project(title, premise, genre, aspect, daily_limit, episode_limit). Save the project ID.
3. Generate story bible with IDs CHAR01 etc (name, appearance, wardrobe, voice), fixed locations SET01 and season arc. Call studio_story_bible with JSON strings. Preserve established character identities, appearance, voice, relationships and chronology.
4. Break episode into scenes of 8s whenever possible. Call studio_plan_episode with JSON string of scene objects:
   {"summary":"...","dialogue":"...","camera":"...","characters":["CHAR01"],"location_id":"SET01","continuity":"...","model":"veo-3.1-lite","seconds":8,"feature":"text_to_video"}
   Only supported feature values: text_to_video, frames_to_video, ingredients_to_video. For Veo references, use 8s. One plan per episode.
5. Get studio_next_scene, present budget/progress succinctly. Do not waste credits on a long unclear script.

### Stage B: supervised Flow automation (a real browser, not an undocumented API)
1. Call studio_prepare_scene for exactly one scene. The returned prompt includes all voice/appearance/wardrobe continuity. Use this only when project/episode budgets permit.
2. Use the Monaw Chrome extension tools: mcp__chrome-devtools__list_pages, new_page/navigate_page, take_snapshot, inspect_element, fill/type/click, and fresh read-only observation. Open https://flow.google.com/. Do not automate browser login, CAPTCHA, 2FA or account protection.
3. Observe the live interface. Select the exact model, 720p, duration, aspect, one output, and compatible text/frames/ingredients mode. **Do not guess selectors or click coordinates from memory.** If the interface changes, re-observe. If the model or 720p option is not shown, stop.
4. Read the actual remaining credits and cost per generation. If it is more than estimated, exceeds the daily or episode budget, or user has not authorized this generation, stop and request approval in Monaw. A generic OS approval notice for low-risk actions is NOT permission to consume credits. Never bypass Monaw's existing approval checks. Do not use private Google endpoints or undocumented APIs.
5. Only when explicit prior user authorization covers this exact generation may you click the official Generate control. Once clicked, treat the outcome as uncertain until a fresh observation independently confirms a completed clip or the user has reconciled it. studio_record_generation records the user-observed UI model/720p/cost/status evidence; it does not actually submit or authorize browser actions.
6. If Chrome disconnects or times out, **do not click Generate again**. Reconnect read-only, inspect Flow project and credits, then reconcile one specific scene. studio_reconcile_no_charge is only appropriate when an observation proves that no generation and no charge occurred. Otherwise leave it uncertain for human review. Do not mark uncertain outcomes as safe by assumption.
7. Download through the visible supported Flow UI. Import only the actual file via studio_import_clip. This uses ffprobe to require true native 720p; no misleading local upscale. If download path or asset cannot be located, ask user to point to the downloaded file.
8. Check clip visually against story bible (face, clothes, language, audio, setting, continuity). studio_review_clip(approve=True/False) only after inspecting. A rejected clip must not be regenerated without budget and approval.
9. Repeat one scene at a time, preserving progress. Call studio_project_status to show completion and credits already committed.

### Stage C: assembling and delivering
- Call studio_assemble_episode only after ALL scenes are approved. Requires FFmpeg and ffprobe installed and on PATH. The engine normalizes fps/audio and joins scenes into a 720p MP4 using local CPU; 8 GB machines may be slow.
- Check the resulting MP4, pace, and sound; do not claim cinema-quality continuity or perfect speech automatically.
- Notify completion via Monaw's local notifications; no extra call to Google.
- A successful episode is a reproducible project folder under Monaw's workspace. Never upload it to the public GitHub repository.

### Safeguards
- Every scene has a stable ID and state. Do not overwrite files or erase a history/ledger.
- No unattended credit purchases or spending decisions. Avoid duplicate generation after unknown outcomes.
- Respect browser policy, website terms and the user's permission gates. If the Flow interface cannot reliably be controlled, produce the story bible, scene prompts and budget anyway, and hand the user the prepared prompt rather than pretending clips were produced.
- Do not confuse AI-generated episode planning with rendered files; report the actual stage of each scene.
