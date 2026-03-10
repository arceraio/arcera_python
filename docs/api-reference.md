# Arcera API Reference

Base URL: configured via environment (e.g. `http://localhost:5000`)

Auth: most endpoints require a JWT Bearer token in the `Authorization` header.

---

## Health

### `GET /`
Returns server status. — [`app.py:21`](../backend/app.py#L21)

**No auth required.**

**Response**
```json
{ "status": "ok", "message": "Arcera YOLO API is running" }
```

---

### `GET /supabase/health`
Checks Supabase connectivity. — [`app.py:26`](../backend/app.py#L26)

**No auth required.**

**Response**
```json
{ "status": "ok", "message": "Supabase connected" }
```

---

## Authentication

### `GET /member`
Returns the authenticated user's member ID (decoded from JWT). — [`app.py:88`](../backend/app.py#L88)

**Auth required.**

**Response**
```json
{ "member_id": "<uuid>" }
```

---

## Single-Image Flow

### `POST /upload`
Uploads a single image and stages it server-side for detection. — [`app.py:34`](../backend/app.py#L34)

**No auth required.**

**Request** — `multipart/form-data`
| Field   | Type | Description        |
|---------|------|--------------------|
| `image` | file | Image to upload    |

**Response**
```json
{ "message": "Uploaded: photo.jpg", "path": "/abs/path/to/file" }
```

---

### `POST /validate`
Validates the most recently uploaded image (checks file exists and is a supported type). — [`app.py:44`](../backend/app.py#L44)

**No auth required.**

**Response**
```json
{ "valid": true, "message": "File is valid." }
```

---

### `POST /detect`
Runs YOLO detection on the staged image (remote service first, local model fallback). — [`app.py:52`](../backend/app.py#L52) · [`main.py:84`](../backend/main.py#L84)

**No auth required.**

**Response**
```json
{
  "detections": [
    { "class_id": 0, "label": "chair", "confidence": 0.91, "bbox": [x1, y1, x2, y2] }
  ],
  "path": "/abs/path/to/file"
}
```

**Errors**
- `400` — no image staged
- `503` — both remote and local detection unavailable

---

### `POST /store`
Stores confirmed detections for the authenticated user. — [`app.py:67`](../backend/app.py#L67) · [`main.py:125`](../backend/main.py#L125)

**Auth required.**

**Request** — `application/json`
```json
{
  "items": [
    {
      "class_id": 0,
      "label": "chair",
      "confidence": 0.91,
      "bbox": [x1, y1, x2, y2],
      "purchase_year": 2022,
      "cost": 299.99,
      "room_id": 1
    }
  ],
  "path": "/abs/path/to/file",
  "original_storage_path": "originals/user_abc123.jpg"
}
```

`path` and `original_storage_path` are optional if a file was previously uploaded via `/upload`.

**Response**
```json
{ "message": "Stored 1 items." }
```

---

## Multi-Image Flow

### `POST /multi-upload`
Uploads multiple images at once and stages them in `temp_photo`. — [`app.py:190`](../backend/app.py#L190)

**Auth required.**

**Request** — `multipart/form-data`
| Field    | Type   | Description            |
|----------|--------|------------------------|
| `images` | file[] | One or more image files |

**Response**
```json
{ "count": 3, "storage_paths": ["originals/user_abc.jpg", ...] }
```

---

### `POST /multiscan`
Runs YOLO detection on all staged images (from `/multi-upload`). — [`app.py:216`](../backend/app.py#L216) · [`main.py:84`](../backend/main.py#L84)

**Auth required.**

**Response**
```json
{
  "results": [
    {
      "local_path": "/abs/path/file.jpg",
      "storage_path": "originals/user_abc.jpg",
      "detections": [
        { "class_id": 0, "label": "chair", "confidence": 0.91, "bbox": [x1, y1, x2, y2] }
      ]
    }
  ]
}
```

**Errors**
- `404` — no staged images found
- `503` — detection unavailable

---

## Items

### `GET /items`
Returns all items belonging to the authenticated user, with signed image URLs. — [`app.py:110`](../backend/app.py#L110)

**Auth required.**

**Response**
```json
{
  "items": [
    {
      "id": 1,
      "class_id": 0,
      "label": "chair",
      "description": null,
      "purchase_year": 2022,
      "cost": 299.99,
      "count": 1,
      "room": "Living Room",
      "room_id": 1,
      "crop_url": "https://...",
      "original_url": "https://...",
      "bbox": [x1, y1, x2, y2],
      "duplicate_of": null,
      "created_at": "2024-01-01T00:00:00+00:00"
    }
  ]
}
```

---

### `PUT /items/<item_id>`
Edits metadata for a specific item. — [`app.py:169`](../backend/app.py#L169)

**Auth required.**

**Request** — `application/json` (all fields optional)
```json
{
  "name": "My Chair",
  "description": "Ergonomic office chair",
  "purchase_year": 2021,
  "cost": 249.99,
  "count": 2,
  "room_id": 6
}
```

Pass an empty string for `name` or `description` to clear the custom value.

**Response**
```json
{ "message": "Updated." }
```

---

### `DELETE /items/<item_id>`
Deletes a specific item. — [`app.py:163`](../backend/app.py#L163)

**Auth required.**

**Response**
```json
{ "message": "Deleted." }
```

---

## Images

### `GET /photo/<item_id>`
Redirects to a signed URL for the original photo of an item. — [`app.py:152`](../backend/app.py#L152)

**No auth required.**

**Response** — `302 Redirect` to signed Supabase Storage URL.

---

### `GET /crops/<member_id>/<filename>`
Redirects to a signed URL for a cropped detection image. — [`app.py:144`](../backend/app.py#L144)

**No auth required.**

**Response** — `302 Redirect` to signed Supabase Storage URL.

---

## Export

### `GET /export`
Downloads all items for the authenticated user as a CSV file.

**Auth required.**

**Response** — `Content-Disposition: attachment; filename=<member_id>_items.csv`

---

## Rooms Reference

| `room_id` | Room Name    |
|-----------|--------------|
| 1         | Living Room  |
| 2         | Bedroom      |
| 3         | Kitchen      |
| 4         | Bathroom     |
| 5         | Dining Room  |
| 6         | Office       |
| 7         | Garage       |
| 8         | Other        |

---

## Typical User Flows

### Single photo scan
1. `POST /upload` — upload image
2. `POST /detect` — run detection
3. `POST /store` — save confirmed items

### Multi-photo scan
1. `POST /multi-upload` — upload all images
2. `POST /multiscan` — detect across all images
3. `POST /store` (once per image) — save confirmed items per image

### View & manage inventory
- `GET /items` — list everything
- `PUT /items/<id>` — edit name, cost, room, etc.
- `DELETE /items/<id>` — remove an item
- `GET /export` — download CSV
