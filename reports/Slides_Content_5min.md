# 5-Minute Presentation — Slide-by-Slide Content
*(paste into the provided blank deck; ~40 sec/slide, 7 slides)*

---

## Slide 1 — Title
**Team:** [pick: "Suspense Account" / "Chain of Title" / "Motif Diligence"]
**One-liner:** We didn't read 1,149 files. We built a deal team of agents that did.

---

## Slide 2 — Approach (the pipeline)
**Talk track:** We followed your tips literally. Code does the heavy lifting; the LLM only reasons over clean text.

```
1,149 files → EXTRACT (pdftotext, hashing — pure code, no AI)
           → MANIFEST + COVERAGE MATRIX (dupes, corrupt, misfiled, gaps — pure code)
           → SPECIALIST AGENTS (Rights Analyst · Financial Analyst — narrow scope, plain text only)
           → SYNTHESIS (gap analysis, requisition list, this deck)
```
- Hashing alone found 17 duplicate groups — including the "FINAL" term sheet being **byte-identical** to the draft
- The coverage matrix found every missing statement before any LLM read a single document

---

## Slide 3 — What's for sale (and the first crack)
- Hollow Verge publishing: **32 compositions** (3 albums, 1998–2005) + masters interest in 2 albums; sold by Northbridge (ex-Vermillion, 2017)
- Excluded: *Ordinary Weather*, Japanese B-sides EP (reverted to Asahi 2018)
- **But the count doesn't close:** deed says 40 works · sale says 32 · seller's own inventory says 60
- And the 1998 agreement is **administration, not ownership** — title is unproven end-to-end

---

## Slide 4 — What the agents found (screenshot the dashboard here)
- **Revenue overstated 60–74%:** claimed $820k/$785k; seller's own statements sum to ~$470–512k. Gap = distributor's *label gross* counted as publishing income
- **A document from the future:** Capston 2H-FY2026 statement issue-dated 28 Oct 2026
- **Concentration worse than disclosed:** December Rooftops = 39% (claimed 30%) — and its 30% writer share sits in PRS *suspense* (writer deceased, no estate contact)
- A split sheet signed by a man **12 years after his death**; a 4% writer unpaid for 20 years; a 12% writer with lawyers engaged

---

## Slide 5 — Gap analysis
- Fund checklist: **18 document classes → 0 fully met · 8 partial · 10 missing**
- Missing: executed chain of title, masters assignment, writer agreements, copyright registrations, probate ×2, sample clearance, MLC statements (entire society), settlement confirmations, per-song ledger
- Statement coverage: GEMA lost 2021–23 · SACEM 2022 · 20+ statements across PRS/ASCAP/BMI/MCPS/SOCAN/PPL

---

## Slide 6 — Collecting the missing documents
- **Requisition list auto-generated, grouped by counterparty:** Seller/counsel (P0: title docs), PROs (duplicate statements — they reissue on request), estates (probate + verified banking), BMG (sample side letter), Pulse (settlement memo)
- **The pipeline is the tracker:** new docs drop into the room → re-run → coverage matrix and 18-class scorecard re-score automatically → requisition list shrinks to zero

---

## Slide 7 — Verdict + why we built it this way
- **Don't proceed at indicated basis.** Re-price off verified ~$470k; conditions precedent: executed title docs, PRO re-registrations + back-pay quantification, estate paperwork, sample clearance; escrow for unquantified liabilities
- **The kicker:** this isn't just a hackathon exercise. Catalog diligence — chain of title, splits, royalty verification — is the same engine needed to license music catalogs to AI labs. That's what we're building at **Motif**. Today's messy data room is our day job.

---

### Q&A ammo (if asked)
- "How did you avoid hallucination?" → Numbers come from code (hashing, CSV sums, coverage matrices); agents only interpret, and every claim cites a filename
- "Time spent?" → ~80% of findings came from the deterministic layer in the first 30 minutes
- "What would you do with more time?" → OCR the illegible 2001 fax; per-song ledger reconstruction from statement line items; auto-draft the requisition emails
