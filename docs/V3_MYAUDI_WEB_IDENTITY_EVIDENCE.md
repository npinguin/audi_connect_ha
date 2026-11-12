# myAudi web inventory evidence — development investigation

A user-supplied browser HAR from November 2026 contains four identical successful
POST requests to the same-origin Belgian myAudi web proxy:
`/userinfo-emea/v2/myaudi/proxy/vgql/v1/graphql`. All four returned HTTP 200,
one vehicle, non-null OEM long/short model, year, drivetrain, model coding,
colors and seven render entries, without GraphQL errors.

The web request uses operationName GET_USER_VEHICLES_ORDERED_BY and variables
orderBy=FAVORITE_AND_REGISTRATION. The browser capture includes an x-csrf-token
header and no Authorization header. It does not establish how the server-side
proxy authenticates to vgql; cookies may have been stripped from the export.

The b13 native baseline and current branch use the same vehicleList query and
the same shared Auth0 implementation (identical audi_services.py blob).
The legacy/modern token roles are distinct in concept but Auth0 currently sets
all three token slots to the same result. The HAR proves web metadata is
available, not that the native bearer can access it or that token exchange
caused the regression.

## Controlled comparison

Workbench > Vehicle Identity > Configure & test > graphql.inventory.webOrdered
sends the HAR-derived document and exact fixed variables to the existing native
Audi GraphQL host, using the existing authorized bearer. It does not call the
web proxy, import any captured secret, change auth scopes, or activate mappings.
Compare with graphql.inventory.vehicleList and capture HTTP status, field
presence, sanitized errors and auth-context evidence. The original document's
formatting is normalized, not its selected fields or parameters.

If the ordered query returns metadata, investigate adoption as a reviewed
runtime source. If it fails similarly, the remaining hypothesis is a difference
in API/session authorization or upstream resolver context. Any web-session
integration requires a separately reviewed, supported authorization lifecycle.

Other observed read-only web-proxy routes include usercapabilities, measurements,
oil-norm, service-record-overview and follow-up-warranty. These are research
candidates, not verified native bearer routes or active capabilities.

No raw capture, identity values, URLs containing identifiers, tokens, cookies,
CSRF values or personal data are included in this repository.

## Current development — reviewed identity adoption

The existing Workbench identity test endpoint now has an explicit adoption path for fresh, same-VIN, same-market OEM model evidence from a reviewed fixed query or garage operation. Edited experimental queries remain non-activating. Adoption uses existing context reconciliation and the private identity cache, not a new authentication or fallback mechanism. It is not proof that any alternative returns valid model data on a new real installation. Validate the fixed webOrdered and garage results with fresh target diagnostics before promoting a source to automatic discovery. No browser token or cookie reuse. Identity remains a release blocker.

## Live b18 result — native authorization boundary confirmed (2026-11-12)

The maintainer executed the exact reviewed `graphql.inventory.webOrdered` request against the existing native app API. HTTP 401 returned the selected VIN inventory but null core/media/classification/renderPictures, with sanitized `token_exchange_denied` for `userVehicles.vehicle` and `userVehicles.vehicle.classification`. The Auth0 GraphQL role uses the same bearer as CARIAD (audience cariad; scopes offline_access, openid, profile). This establishes an upstream token-exchange rejection, not a query/mapping failure. The precise missing entitlement or backend cause is not established.

Independent corroboration: [vwgroup-connect-ha Audi EU client](https://github.com/its-me-prash/vwgroup-connect-ha/blob/main/custom_components/vag_connect/cariad/api/audi.py) reports live EU Auth0 token-exchange rejection on 2026-11-08 and distinguishes the historical IDK-to-AZS flow from Auth0. Do not copy its implementation or retry a denied exchange. The successful Belgian myAudi web HAR establishes a different session context, not permission to reuse browser credentials. Keep the shared token owner and existing native controls unchanged; investigate legitimate OEM-supported authorization or upstream recovery, no more speculative query variants. Identity remains open. No new live identity source has been proven.
