# Visual Browser Review for Static Sites

A repeatable approach for reviewing marketing pages, landing pages, and docsite output without Lighthouse CLI — using `python3 -m http.server` + browser console inspection.

## Setup

```bash
cd /path/to/repo
python3 -m http.server 8888 --bind 127.0.0.1
```

Then use `browser_navigate` to load `http://127.0.0.1:8888/landing/index.html` (adjust path).

## Landing page checks

### CSS custom properties

```javascript
const s = getComputedStyle(document.documentElement);
JSON.stringify({
  purple: s.getPropertyValue("--purple").trim(),
  purpleDark: s.getPropertyValue("--purple-dark").trim(),
  bg: s.getPropertyValue("--bg").trim(),
  text: s.getPropertyValue("--text").trim(),
});
```

### Computed styles on key elements

```javascript
const navBtn = document.querySelector(".nav-cta");
const heroBtn = document.querySelector(".btn-primary");
JSON.stringify({
  navCtaBg: getComputedStyle(navBtn).backgroundColor, // rgb(138,123,181) = #8a7bb5
  heroBtnBg: getComputedStyle(heroBtn).backgroundColor,
  statColor: getComputedStyle(document.querySelector(".stat-number")).color,
  btnGhostBorder: getComputedStyle(document.querySelector(".btn-ghost")).borderColor,
  logoBg: getComputedStyle(document.querySelector(".logo-mark")).backgroundColor,
});
```

### Link inventory

```javascript
Array.from(document.querySelectorAll("a")).map(
  (a) => a.textContent.trim() + " -> " + a.getAttribute("href"),
);
```

### Nav-specific links

```javascript
Array.from(document.querySelectorAll(".nav-links a")).map(
  (a) => a.textContent.trim() + " -> " + a.getAttribute("href"),
);
```

### Footer links

```javascript
Array.from(document.querySelectorAll(".footer-links a")).map(
  (a) => a.textContent.trim() + " -> " + a.getAttribute("href"),
);
```

### Console errors & metadata

```javascript
document.title;
document.querySelector('meta[name="description"]')?.getAttribute("content");
document.getElementById("terminal-mock") ? "terminal-mock present" : "missing";
```

And clear console first:

```
browser_console(clear=true)
```

then check for errors:

```
browser_console()
```

### Config JSON fetch (runtime validation)

```javascript
fetch("./config.json")
  .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
  .then((d) => console.log(JSON.stringify(d)));
```

### Responsive viewport simulation

Check the inline CSS for expected breakpoints:

```javascript
Array.from(document.querySelectorAll("style"))
  .map((s) => s.textContent)
  .join("\n")
  .match(/@media[^{]+\{[^}]+\}/g);
```

### Copy-to-clipboard interaction

```javascript
(() => {
  const terminal = document.getElementById("terminal-mock");
  const hint = document.getElementById("copy-hint");
  if (!terminal || !hint) return "elements missing";
  terminal.click();
  return new Promise((r) => setTimeout(() => r("after click: " + hint.textContent), 200));
})();
```

## MkDocs rendered docsite checks

After `mkdocs build --site-dir /tmp/check && python3 -m http.server 8889 --directory /tmp/check`:

### Palette data attributes on `<body>`

```javascript
JSON.stringify({
  colorScheme: document.body.getAttribute("data-md-color-scheme"),
  colorPrimary: document.body.getAttribute("data-md-color-primary"),
  colorAccent: document.body.getAttribute("data-md-color-accent"),
});
// Expected: primary="custom" NOT "indigo"
```

This catches the common bug where a palette auto-detect entry is missing `primary: custom`.

### Canonical URL

```javascript
document.querySelector('link[rel="canonical"]')?.getAttribute("href");
// Expected: https://jessinra.github.io/Lorekeeper/docs/
```

### Logo / favicon references

```javascript
JSON.stringify({
  favicon:
    document.querySelector('link[rel="icon"]')?.getAttribute("href") ||
    document.querySelector('link[rel="shortcut icon"]')?.getAttribute("href"),
  logo: document.querySelector(".md-logo img")?.getAttribute("src"),
});
```

### extra_css loading

Check that brand overrides are wired:

```javascript
const links = Array.from(document.querySelectorAll('link[rel="stylesheet"]'));
links.filter((l) => l.href.includes("extra.css")).length > 0 ? "extra.css loaded" : "MISSING";
```

## Deploy URL contract verification

After any deploy-workflow change, verify the build artefact layout:

```bash
cd /path/to/repo
# Simulate what CI does
mkdir -p /tmp/deploy-check/docs
mkdocs build --site-dir /tmp/deploy-check/docs
cp landing/index.html /tmp/deploy-check/index.html
mkdir -p /tmp/deploy-check/landing
cp landing/config.json /tmp/deploy-check/landing/config.json

# Verify tree
find /tmp/deploy-check -maxdepth 2 -type f | sort
```

Expected output:

```
/tmp/deploy-check/index.html              ← landing page at root
/tmp/deploy-check/docs/...                ← MkDocs site under /docs/
/tmp/deploy-check/landing/config.json     ← configurable stats
```

## Pitfalls

- Headless browsers block `navigator.clipboard.writeText()` — test the JS structure, not the actual clipboard write
- `python3 -m http.server` with no `--directory` flag serves from CWD; always use explicit `--directory` when checking MkDocs build output
- CSS custom properties return empty string if the `<style>` block didn't parse (malformed CSS) or the page is served without styles
- MkDocs palette auto-detect entry (`prefers-color-scheme`) often misses `primary: custom` — always check the rendered `<body>` data attributes, not just the mkdocs.yml source
