---
name: higgsfield-create-agent
description: Deep guide for driving Higgsfield media generation on Helix Intelligence
---

# Higgsfield Media Generation Guide

This skill teaches agents how to properly utilize the `/media/jobs` endpoint in the Helix Intelligence backend to generate images and videos using Higgsfield AI. 

## 1. Provider and Mocking Rules
- **Always** set `provider: "higgsfield"`.
- **Never** use `provider: "mock"`.
- **Never** invent or spoof media URLs.

## 2. API Contract
1. **Submit Job**: `POST {API}/media/jobs` with `Authorization: Bearer <user JWT>`
   ```json
   {
     "prompt": "<full image prompt>",
     "provider": "higgsfield",
     "parameters": { "model": "soul_v2", "kind": "image" }
   }
   ```
2. **Read**: The response will contain `job.id` and `job.status`.
3. **Poll Status**: `GET {API}/media/jobs/{id}` every 2s until `status` is `completed`, `failed`, or `nsfw` (timeout ~5 min).
4. **Success Criteria**: 
   - `status === "completed"` AND `result_url` is a valid `https` URL.
5. **Failure Handling**:
   - On `failed` or `nsfw`, report the `error_message` back to the user and optionally regenerate with a safer prompt.
