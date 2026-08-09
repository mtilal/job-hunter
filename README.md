# Job Hunter

Upload a CV, search Indeed, LinkedIn and remote job boards, and get every result
scored 0–100 on how well it matches your background.

## Features

- **CV-driven scoring** — PDF, Word, Markdown or text. Skills are extracted and
  each job is ranked against them. No API key, no cost.
- **Multiple sources** — Indeed, LinkedIn, Remotive, Arbeitnow, Jobicy, and
  optionally Adzuna.
- **74 countries** plus job type, workplace (remote / on-site / hybrid) and
  visa-sponsorship filters.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Requires **Python 3.11** — `python-jobspy` pins an older numpy that will not
build on 3.13.

## Deploy to Streamlit Community Cloud

1. Push this folder to a **public** GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. **New app** → pick the repo → main file `app.py`.
4. Under **Advanced settings**, set **Python version to 3.11**.
5. Deploy. You get a permanent `*.streamlit.app` URL that runs whether or not
   your own machine is on.

### Optional: Adzuna keys as secrets

Rather than typing them into the UI each visit, add them under
**App settings → Secrets**:

```toml
ADZUNA_APP_ID = "your-id"
ADZUNA_APP_KEY = "your-key"
```

## Known limitation

Indeed and LinkedIn block traffic from datacenter IP addresses. Running on a
cloud host, those two sources will frequently return nothing while the other
boards keep working. Errors are surfaced in the UI rather than hidden. If you
need them to work reliably from the cloud, route jobspy through a residential
proxy.
