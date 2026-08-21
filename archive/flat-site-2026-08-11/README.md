# Vosslab Daily Blog

A standalone, private-LAN static blog for Vosslab work notes. It is intentionally independent of
`vosslab-podcast` and contains no local-model runtime, project-local API credential, or dependency
on that repository.

## Live address

- `http://aella.local:8016`
- `http://192.168.2.13:8016`

The service binds only to `192.168.2.13:8016`. It is not designed for public internet exposure.

## Source and generated files

- `content/site.json`: site identity and displayed collection status.
- `content/posts/*.json`: date-stamped post records with optional source links.
- `site-assets/`: local CSS and favicon assets.
- `scripts/build_site.py`: standard-library static-site builder.
- `public/`: generated, served output. Do not hand-edit it.

## Build

```bash
python3 scripts/build_site.py
```

## Verify

```bash
python3 scripts/build_site.py --check
curl --fail http://192.168.2.13:8016/status.json
systemctl --user status vosslab-daily-blog.service
```

## Operations

```bash
systemctl --user restart vosslab-daily-blog.service
journalctl --user -u vosslab-daily-blog.service --since today
```

## GitHub-report boundary

The initial post contains a clearly labeled public-activity snapshot. It is not presented as a
complete personal commit report. A future collector must write a validated post record from an
explicit date, confirmed `vosslab` commit attribution, complete pagination, and source permalinks.
