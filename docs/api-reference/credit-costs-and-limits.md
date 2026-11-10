# Access and usage controls

The API enforces organization scope and administrator-granted access. Client-side navigation and feature flags do not grant permission.

## Access state

- `GET /api/account/access` returns the authenticated workspace's access state.
- `POST /api/account/access-requests` submits an access request.
- Administrator grant and revocation routes require the relevant platform-admin permissions.

Pending, rejected, expired, and revoked access must not be presented as a purchase requirement. Billing-provider routes remain unavailable; there is no checkout integration.

## Usage accounting

The server may reserve internal usage credits before provider work and compensate terminal failures under its transaction rules. Credits are usage controls, not a price or payment balance. Do not infer a public plan or fee from internal cost constants.

Use the current API response for status, limits, and remaining availability. Static examples in older versions of the documentation are not authoritative entitlement data.

## Job outcomes

Discover status and cancellation endpoints enforce the same tenant checks as search creation. A client timeout is not permission to abandon server work silently. Observe the server's terminal status and machine-readable reason before offering a retry.

All retries must preserve session and organization identity. Do not replay a request with another account's token after switching users.
