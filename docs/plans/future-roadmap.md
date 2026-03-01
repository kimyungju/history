# Future Roadmap — Post-Hackathon

> Current state: All code complete, 53 tests pass. Production deployment (T11/Cloud Run) is a hackathon requirement — see task tracker.

---

## Monitoring Dashboard

**Priority: Medium — after deployment**

```bash
gcloud monitoring dashboards create --config-from-file=infra/monitoring/dashboard.json
```

Dashboard includes: error rate, query latency by stage, ingestion stage latency, request count.

---

## Batch Ingestion (5.4)

**Priority: Low — needed when corpus grows beyond ~100 docs**

- Replace `BackgroundTasks` with Pub/Sub async ingestion
- Requires: Pub/Sub topic + subscription, Cloud Run subscriber service
- Current approach works fine for ~20 docs

---

## Integration Testing (3.8)

**Priority: Low — nice to have**

- Update `docker-compose.yml` to include frontend service
- Test full flow: question → answer → citation click → PDF viewer
- Test graph: query → nodes render → click node → sidebar
- Test ResizableSplitter drag and mobile tab switching

---

## Potential Enhancements

- **Auth** — add if deploying publicly beyond hackathon (currently no auth by design)
- **Streaming responses** — SSE for real-time answer generation
- **Multi-language UI** — English/Chinese toggle for bilingual archives
- **Export** — download query results and citations as PDF/CSV
- **Annotation** — let researchers flag/correct OCR errors directly
