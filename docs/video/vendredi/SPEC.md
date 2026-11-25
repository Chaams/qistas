# SPEC — "Vendredi 17:58" (Qistas explainer)

GOAL:    the viewer understands that Qistas weighs every PR of an Arabic chatbot and blocks it when it leaks data, invents or answers in the wrong dialect; they remember "the bot only ships if it holds the balance".
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps
TIME:    the voice is the clock; ~55-62 s (7 voiced lines, 0.4 s gap). Calm BGM ~90 BPM under the voice, ducked to -18 dB.
LOOK:    blue-tinted paper #f3f4f7 with 1.5% fibre noise; ink #18203a for every word and line; brass #86590f is the only accent: the balance, the pans, the payoff word. Red #b8382c only on the leak and on ❌; green #1d7a4a only on ✅.
         Display: Space Grotesk 700, titles 96 px, tracking -2%. Body: IBM Plex Sans 500, 40 px. Arabic: IBM Plex Sans Arabic 600, 56 px in chat bubbles. Mono (PR comment, IBAN): IBM Plex Mono 500, 32 px.
         Medium: printed product UI on paper: flat surfaces, a 0 8 24 rgba(24,32,58,.12) shadow on the phone and the PR card only. No gradients, no glow.
OBJECTS: a phone (rounded 64 px body, ink bezel, a WhatsApp-like chat) with the Gulf customer's message and the bot's reply; a GitHub-like PR card (title, diff of system_prompt.txt, the qistas-report comment); a brass balance (post, beam, two pans with chains) labelled "baseline" and "PR"; test-case cards (YAML lines); four weights labelled dialect / fidélité / PII / injection.
MOTION:  enter = power3.out 18 f; move = power2.inOut 24 f; exit = power2.in 12 f; the beam tilt = back.out(1.4) 27 f; staggers 4 f. One hero move per shot.
SHOTS:   (seconds follow the voice lines L1..L7)
  S1 L1 hook: phone fills 70% height, clock «الجمعة 17:58»; customer bubble types in; bot reply lands; the IBAN SA03 8000 0000 6080 1016 7519 gets a red circle drawn around it. Sound: message pop, then a low thud on the circle. Hand-off: the circled IBAN slides left and becomes a line in the PR diff.
  S2 L2 the cause: PR card «Update system_prompt.txt», diff with two red removed lines (dialect rule, PII rule); a grey "tests ✓ passed" badge that is wrong, struck through when the voice says "n'ont rien vu". Hand-off: the PR card shrinks onto the right pan of the balance.
  S3 L3 reveal: the balance draws in (post, beam, pans), title «Qistas» + «القسطاس» in brass. Balance level.
  S4 L4 cases: the customer bubble becomes a YAML test-case card (id, turns, expected_dialect: gulf); three more cards stack behind (arabizi, PII, multi-turn). Hand-off: cards fly onto the PR pan as weights.
  S5 L5 judge: four weights land one by one on the PR pan, each with its label and a score: dialect 0.0, fidélité 0.2, PII ✗, injection ✓. Sound: a click per weight.
  S6 L6 payoff: the beam tips (back.out), PR pan up = lighter; the PR comment card appears: «## Qistas : ❌ FAIL» + «security: 1 failed case(s): demo-pii-other-customer». Sound: low note.
  S7 L7a fix + claim: the two removed lines turn back green (restored), weights refresh to 1.00, beam returns level, «✅ PASS». Then the claim line and github.com/Chaams/qistas; hold 2.5 s.
BANNED:  dark void, glow, particles, purple/blue gradients, glass cards; everything centred; fade-and-slide-up on every element; three cards in a row; docked logo; a real bank's name or brand (the bank is fictional); invented metrics presented as measured (the scores shown are illustrative and the video says nothing about real performance).
QA:      frame 0 = phone + Gulf message visible (never black); S1 end = red circle around the IBAN; S6 = tipped beam + ❌ comment readable ≥ 2 s; last frame = claim + URL readable.
