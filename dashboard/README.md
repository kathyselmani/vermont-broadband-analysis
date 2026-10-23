# Dashboard

`web/index.html` is a self-contained page (data inlined) with a 3D H3 hexagon map of
Vermont built with deck.gl. Open it in any modern browser; it needs an internet
connection only to load deck.gl, h3-js and Google Fonts from public CDNs.

- `web/app.html`: page source (HTML/CSS/JS, no data). Edit this file.
- `web/data.json`: data bundle written by `vermont-broadband-analysis dashboard`.
- `web/index.html`: built page = `app.html` + `data.json`. Rebuilt by the same command.
- `web/preview.png`: screenshot used in the main README.

To publish on GitHub Pages, serve the `dashboard/web/` folder.

`powerbi/` is reserved for an optional Power BI report built on
`data/processed/analysis/*.csv`; `.pbix` files are git-ignored.
