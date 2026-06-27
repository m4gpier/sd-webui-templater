# Templater — SD WebUI Extension

Create and reuse prompt templates made of named sections. Templates appear as cards in the Extra Networks panel (alongside LoRA, Textual Inversion, etc). Click a card to insert its tags into the prompt. Edit templates directly from the card's gear popup.

---

## Installation

**Via WebUI (recommended)**
1. Go to **Extensions → Install from URL**
2. Paste this repo's URL and click **Install**
3. Restart the WebUI

**Manual**
```bash
cd stable-diffusion-webui/extensions
git clone https://github.com/m4gpier/sd-webui-templater.git
```

---

## How it works

Templates live in `extensions/sd-webui-templater/templates/` as plain JSON files. Each template has a name and any number of named sections, each containing a list of tags.

When you click a template card, all enabled section tags are assembled and appended to whatever is in the main prompt box, skipping any tags already present to avoid duplicates. The assembled tags are also passed through at generation time as a backup.

---

## Usage

### Using templates

1. Open the **Templates** tab in the Extra Networks panel below the prompt
2. Click a card to insert its tags into the prompt
3. Hit **Generate** as normal

### Creating templates

Click the **gear icon** on any template card (or any card placeholder) to open the editor popup:

- Set a **template name**
- Add sections with **➕ Add section** — each section has a name and a tag list
- Remove sections with the **✕** button on each row
- Click **Save** to write the template to disk
- Use **Replace preview** to set a card thumbnail image

### Editing templates

Open the gear popup on an existing card — it loads the current sections into the editor. Make changes and hit **Save**.

---

## Template format

Templates are stored as JSON and can be edited manually:

```json
{
  "name": "Anime Portrait",
  "sections": [
    { "name": "Subject",    "tags": "1girl, solo, looking at viewer" },
    { "name": "Style",      "tags": "anime, illustration, highly detailed, best quality" },
    { "name": "Lighting",   "tags": "soft light, rim lighting, volumetric light" },
    { "name": "Background", "tags": "simple background, gradient background" }
  ]
}
```

Files go in `extensions/sd-webui-templater/templates/`. The filename (minus `.json`) becomes the card name. Preview images are stored as `<template name>.preview.png` in the same folder.

---

## Compatibility

- Tested on **reForge** and **AUTOMATIC1111**
- Works with any model
- No additional dependencies required

---

## License

MIT
