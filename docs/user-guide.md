# User Guide

## What This App Does

The Ad Generation Engine helps you turn a campaign brief into a set of ready-to-review ad concepts.

For each campaign, the app can help you:

- create messaging ideas
- generate multiple ad variants
- review the copy and prompts
- edit generated variant copy
- export campaign copy as text
- save notes
- approve a campaign for later use

## What You Need Before You Start

You will get the best results if you already know:

- the brand or product name
- the audience you want to reach
- the main campaign goal
- the offer, if there is one
- the channels you want to use

## Starting the App

Open the project and start the backend:

```powershell
python main.py serve
```

If port `8000` is already in use on your machine, start the backend on another port:

```powershell
python main.py serve 127.0.0.1 8011
```

Start the dashboard in a second terminal:

```powershell
npm run dev
```

If you started the backend on a different port, point the dashboard at it before starting Vite:

```powershell
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8011'
npm run dev -- --host 127.0.0.1 --port 4174
```

Then open the dashboard in your browser at:

```text
http://127.0.0.1:5173
```

If your local port is different, use the address shown in the terminal.

## Main Areas of the Dashboard

The dashboard has three main parts:

### Campaign Form

This is where you describe the campaign you want to generate.

You will fill in:

- brand
- product
- objective
- audience
- pain points
- value props
- offer
- tone
- constraints
- channels

Required fields are marked with a small asterisk next to the label. If you select `Generate campaign` before filling them in, the form blocks the request and surfaces the missing fields inline beneath each input.

The form starts blank on each session so a selected campaign on the right never overwrites what you are typing. Use `Load sample brief` to drop in the demo payload or `Clear` to reset the form to empty. `Load sample brief` asks for confirmation before overwriting if the form already has content.

### Campaign List

This shows the campaigns you have already created.

From here you can:

- open an existing campaign
- check whether it is still a draft
- see whether it has been approved

### Campaign Detail

This is where you review the generated output for one campaign.

You can:

- read the strategy summary
- inspect generated ad variants
- edit headlines, primary text, CTAs, and image prompts
- cancel an in-progress edit without saving
- generate or retry one image at a time
- export the campaign as a text bundle
- review the image prompts
- add approval notes
- approve the campaign
- reuse this campaign's brief as a starting point for a new generation

## How To Create a Campaign

1. Fill in the campaign form on the left side of the dashboard.
2. Add each pain point on its own line.
3. Add each value proposition on its own line.
4. Choose at least one channel. The form blocks generation if no channels are selected.
5. Select `Generate campaign`. Any missing required fields are flagged inline before the request is sent.

The app will create:

- a strategy summary
- messaging angles
- channel-specific ad variants
- image prompts for each variant

Campaign creation stays fast and creates image prompts first. If GPT Image 2 is configured, generate real images from the campaign detail view one variant at a time.

## Turning On GPT Image 2

By default, the app creates image prompts only. To generate real image assets with GPT Image 2, set the OpenAI image provider in your local `.env` file:

```env
AD_ENGINE_IMAGE_PROVIDER=openai_images
OPENAI_API_KEY=your-api-key
OPENAI_IMAGE_MODEL=gpt-image-2
OPENAI_IMAGE_SIZE=1024x1024
OPENAI_IMAGE_QUALITY=medium
OPENAI_IMAGE_BACKGROUND=auto
OPENAI_IMAGE_OUTPUT_FORMAT=png
OPENAI_IMAGE_OUTPUT_DIR=./data/generated_assets
OPENAI_IMAGE_GENERATE_DURING_CREATE=false
```

Restart the backend after changing these settings. New campaigns will still create prompts first. Open a campaign and select `Generate image` on a variant to save a generated file under `data/generated_assets` and show it in the review view.

## How To Review a Campaign

After generation, select the campaign from the campaign list.

Check these areas:

- the strategy summary: does it match the campaign goal?
- the messaging pillars: are they the right selling points?
- the variants: do the headlines and body copy feel usable?
- the image prompts: do they match the brand and audience?

If a variant is close but needs final polish, use `Edit` on that variant. If the strategy is wrong, update the campaign brief and generate a new campaign.

Variant headlines are clipped to keep cards aligned. Hover a clipped headline to see its full text in a tooltip without opening the editor.

## How To Edit Generated Variants

1. Open a campaign.
2. Select `Edit` on a generated variant.
3. Update the headline, primary text, CTA, or image prompt.
4. Select `Save` to commit, or `Cancel` to discard the in-progress edit and keep the original copy.

The campaign keeps the edited variant and updates the campaign timestamp.

## How To Generate Images

1. Open a campaign.
2. Review or edit the variant's image prompt.
3. Select `Generate image` on that variant.
4. If generation fails, review the message and select `Retry image`.

Generate images only for variants you actually plan to use. This keeps cost and wait time under control. Each image call uses one OpenAI image credit, and the variant card displays a cost hint and a session regeneration counter so you can see how often a given variant has been redone. Regenerating a variant that already has an image asks for confirmation before replacing it.

## How To Reuse A Brief

If you want to iterate on an existing campaign rather than retyping its inputs:

1. Open the campaign you want to start from.
2. Select `Reuse brief` in the detail header.
3. The form on the left fills with the campaign's brief, ready for edits.
4. Adjust the brief and select `Generate campaign` to create a new campaign from it.

The original campaign is untouched. Reusing a brief never overwrites stored data.

## Light And Dark Mode

The dashboard supports a light and a dark theme. Select the theme toggle in the workspace header to switch. Your choice is stored in the browser and applied before the page renders, so reloading does not cause a flash of the wrong theme.

## How To Export a Campaign

Open a campaign and select `Export`.

The app creates a plain-text campaign bundle with:

- campaign summary
- strategy
- messaging pillars
- edited variants
- approval notes, when present

## How To Add Notes

Use the approval notes field in the campaign detail view to capture:

- internal feedback
- revision requests
- launch notes
- client comments

Select `Save notes` to keep them with the campaign.

## How To Approve a Campaign

When a campaign is ready:

1. Open the campaign
2. Review the variants
3. Add any final notes
4. Select `Approve`

The campaign status will change from `draft` to `approved`.

## Saving Your Work

The app can run in two storage modes:

- `memory`: campaigns disappear when the backend stops
- `sqlite`: campaigns stay saved after restart

If you want your campaigns to stay available, use the default SQLite setup in the project `.env` file.

## Tips For Better Results

- Be specific about the audience.
- Use clear, concrete pain points.
- Write value propositions as actual benefits, not vague slogans.
- Include an offer if the campaign has one.
- Keep constraints practical and short.

## Common Questions

### Why did I get weak or generic ad copy?

This usually means the brief is too broad. Add more specific pain points, value props, and audience detail.

### Why don’t I see old campaigns?

The backend may be running in memory mode instead of SQLite mode.

### Why does the dashboard say `Campaign workspace is offline`?

The frontend is usually pointing at the wrong backend URL or port. Make sure:

- the API server is running
- `VITE_API_BASE_URL` matches that API port
- you opened the current Vite URL from the terminal, not an older tab

### Can I edit generated copy directly in the app?

Yes. Open a campaign, select `Edit` on a variant, and save the revised copy. Select `Cancel` to discard the edit and keep the original.

### Can I start a new campaign from an existing one?

Yes. Open the campaign you want to start from and select `Reuse brief`. The form fills with that campaign's brief so you can adjust it and generate a new campaign.

## Current Limits

This is still an MVP. Right now:

- campaigns are generated from structured briefs only
- direct in-app editing currently covers generated variant copy and image prompts
- export is plain text only
- image asset creation is per variant and requires `AD_ENGINE_IMAGE_PROVIDER=openai_images` plus a valid `OPENAI_API_KEY`
- approval is simple and does not include multi-person workflow
- per-channel character limits and channel-native preview sizes are not yet enforced in the generated copy or layout
