# User Guide

## What This App Does

The Ad Generation Engine helps you turn a campaign brief into a set of ready-to-review ad concepts.

For each campaign, the app can help you:

- create messaging ideas
- generate multiple ad variants
- review the copy and prompts
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
- review the image prompts
- add approval notes
- approve the campaign

## How To Create a Campaign

1. Fill in the campaign form on the left side of the dashboard.
2. Add each pain point on its own line.
3. Add each value proposition on its own line.
4. Choose the channels you want included.
5. Select `Generate campaign`.

The app will create:

- a strategy summary
- messaging angles
- channel-specific ad variants
- image prompts for each variant

If the OpenAI image integration is turned on, the campaign can also include real generated images in the review view.

## How To Review a Campaign

After generation, select the campaign from the campaign list.

Check these areas:

- the strategy summary: does it match the campaign goal?
- the messaging pillars: are they the right selling points?
- the variants: do the headlines and body copy feel usable?
- the image prompts: do they match the brand and audience?

If something feels off, update the campaign brief and generate a new campaign.

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

Not yet. Right now the app is focused on generating, reviewing, and approving campaign output.

## Current Limits

This is still an MVP. Right now:

- campaigns are generated from structured briefs only
- direct in-app copy editing is limited
- image prompts are generated, but image asset creation is still a future step
- approval is simple and does not include multi-person workflow
