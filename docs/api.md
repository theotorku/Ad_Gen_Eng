# API Reference

## Base URL

Local default:

```text
http://127.0.0.1:8000
```

Start the server:

```powershell
python main.py serve
```

## Endpoints

### `GET /health`

Returns service health and the active provider configuration.

Example response:

```json
{
  "status": "ok",
  "db_backend": "memory",
  "providers": {
    "planning_provider": "rule_based",
    "copy_provider": "rule_based",
    "image_provider": "prompt_template"
  }
}
```

### `POST /bundles`

Creates a new campaign and returns the stored campaign record plus the generated bundle.

Required request body fields:

- `brand_name`
- `product_name`
- `objective`
- `target_audience`
- `value_props`
- `channels`

Example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/bundles -ContentType 'application/json' -InFile 'sample_brief.json'
```

### `GET /bundles/{id}`

Returns only the generated `AdBundle` payload for a campaign ID.

Use this when the caller only needs the creative output and not campaign lifecycle fields.

### `GET /generated-assets/{filename}`

Returns a generated image file saved by the `openai_images` provider.

Use this route when a campaign variant includes a `generated_asset.path` value and the dashboard or another client needs to display the actual image.

### `GET /campaigns`

Lists every campaign in the in-memory store.

Example response shape:

```json
{
  "campaigns": [],
  "count": 0
}
```

### `GET /campaigns/{id}`

Returns one campaign record, including:

- status
- timestamps
- approval notes
- metadata
- generated bundle

### `PATCH /campaigns/{id}`

Updates mutable campaign fields.

Supported payload fields:

- `status`
- `approval_notes`
- `metadata`

Example:

```powershell
Invoke-RestMethod -Method Patch -Uri http://127.0.0.1:8000/campaigns/<campaign-id> -ContentType 'application/json' -Body '{"approval_notes":"Needs final stakeholder review","metadata":{"owner":"Theo"}}'
```

Supported statuses:

- `draft`
- `approved`

### `POST /campaigns/{id}/approve`

Approves a campaign and optionally attaches approval notes.

Example:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/campaigns/<campaign-id>/approve -ContentType 'application/json' -Body '{"approval_notes":"Approved for launch"}'
```

## Validation Errors

The API returns `400 Bad Request` when:

- the JSON body is invalid
- a required brief field is missing
- an unsupported channel is requested
- a patch field has the wrong type
- an unsupported campaign status is supplied

The API returns `404 Not Found` when a campaign ID or route does not exist.

## Notes

- Campaign persistence depends on the configured store backend.
- `POST /bundles` is currently the campaign creation endpoint.
- `GET /bundles/{id}` and `GET /campaigns/{id}` use the same underlying campaign ID.
- Generated image files are saved on disk and exposed through `GET /generated-assets/{filename}`.
