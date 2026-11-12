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
