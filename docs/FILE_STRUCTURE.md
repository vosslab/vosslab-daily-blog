# File structure

```text
vosslab-daily-blog/
|-- docs/
|   |-- blog/posts/
|   |   |-- YYYY-MM-DD.md
|   |   `-- YYYY-MM-DD/            images referenced by that post only
|   |-- index.md
|   `-- stylesheets/
|-- generated/
|   |-- releases/                  rendered MkDocs releases
|   `-- staging/                   disposable import/build state
|-- scripts/
|   |-- bundle_snapshot.py         bounded transport reader
|   |-- import_publication_bundle.py
|   |-- publication_staging.py
|   |-- publication_transaction.py
|   `-- site_deployment.py
|-- tests/                         shared vendored hygiene tests only
|-- mkdocs.yml
`-- publish_site.sh
```

`docs/` is MkDocs source, so final post images belong there. Co-locating the selected images beneath
the post's date keeps each publication self-contained without copying the producer's screenshot
catalog.

There is no durable publication JSON tree. Transfer manifests and transaction markers live only in
memory or disposable staging. Editorial evidence and intermediate artifacts remain in the producer
while a run is incomplete and are not display-repository files.
