# GLP-1 project website

A project report exploring GLP-1 science, applications, and research.

## Preview locally

Install Python 3.10 or newer, then run these commands from the project folder:

```powershell
python scripts/build.py
python -m http.server 8000 --directory build
```

Open [localhost:8000](http://localhost:8000). Press **Ctrl+C** to stop the server.

After editing content, styling, or JavaScript, rebuild and refresh the browser. Each successful build replaces the previous output and clears obsolete pages and assets.

## Project folders

- `src/` — editable content, templates, and public assets
- `build/` — generated website; ignored by Git and recreated by the build command
- `scripts/` — build commands and checks

## Edit the website

| Change | Where to edit |
| --- | --- |
| Page text | `src/pages/` — Home is `home.html` |
| Menu labels and page order | `src/navigation.json` |
| Site title and description | `src/site.json` |
| References | `src/references.json` |
| Shared page structure | `src/templates/` |
| Colors, typography, and spacing | `src/assets/styles.css` |
| Images | `src/assets/images/` |

Edit files under `src/`. Serve only `build/`, not the project folder. If generation fails, the previous output is kept.

### Add a page

1. Add its title and URL name (slug) to `src/navigation.json`. Use lowercase words separated by hyphens, such as `new-topic`.
2. Create `src/pages/new-topic.html`, using an existing page as a starting point.
3. Rebuild and check that the new page appears in navigation.

The menu order also sets the Previous/Next reading order. Keep Home's slug empty so it continues to use the base URL.

The error page is edited in `src/pages/404.html` and built separately from the menu. Preview it at [localhost:8000/404.html](http://localhost:8000/404.html); GitHub Pages displays it automatically for missing URLs.

### Add citations

Add the source to `src/references.json` using a unique, descriptive key:

```json
{
  "kowalska-glp1-2026": {
    "text": "Full reference details.",
    "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC12941302/"
  }
}
```

Use that key in page text:

```html
<p>Supporting statement.[@kowalska-glp1-2026]</p>
```

Use citation keys rather than manual numbers. The build converts each key into a numbered link to its reference.

Numbers follow the order in `references.json`. To switch to first-appearance numbering, set `citation_numbering` to `first-appearance` in `src/site.json`.

Readers can open a reference preview without leaving the page and dismiss it with **Escape**, the close button, or an outside click.

### Add tables

Copy the table from Current Applications for a timeline, or from GLP-1 Receptor Agonists for a drug comparison, then replace its headings and entries. Use unique caption IDs when adding more than one table to a page.

Check both desktop and mobile previews. Timelines wrap on small screens; drug comparisons become compact labeled entries.

## Check your changes

With Node.js installed, run:

```powershell
python scripts/check.py
```

This rebuilds the website and checks links, citations, shared controls, and existing regression tests. For link and asset validation alone, run `python scripts/validate.py` after building.

Also check the changed pages in a browser. In Chrome or Edge, press **F12**, then **Ctrl+Shift+M** to test phone-sized screens. Try the menu, citation previews, tables, and Previous/Next links.

The Pages workflow publishes only `build/`. In GitHub repository settings, use **Pages → Source → GitHub Actions**. The workflow runs on `main`; adjust its branch setting if needed.
