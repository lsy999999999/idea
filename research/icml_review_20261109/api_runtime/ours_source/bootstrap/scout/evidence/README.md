# Scout Evidence

`fetch_log.json` records the refetch time, request and final response URLs, HTTP status, response headers, body size, and SHA-256 for every saved response. The timestamp is UTC. This refetch was made on 2026-11-03 because the initial response bodies had not been persisted.

The `.json` files are exact response bodies from the corresponding USGS and OpenAlex requests. `usgs_sample_audit.json` records the temporal coverage, interval, duplicate check, and cache-header review for the USGS sample. The USGS sample query returned three complete 15-minute series over the requested three-day window (288 observations per station); the earlier report's “five-minute” label was incorrect and has been corrected.

OpenAlex search results are metadata-search evidence, not a systematic literature review or a novelty certificate. USGS water values can be provisional and subject to revision; the response itself carries the USGS provisional-data disclaimer.
