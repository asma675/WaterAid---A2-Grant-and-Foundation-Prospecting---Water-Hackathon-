# RAG and external research

## Local RAG

GrantCurrent builds a searchable local corpus from:

- Canadian public funding sources
- domestic water opportunities
- Canadian funder profiles
- public award/gift history
- verified public program contacts

Local retrieval requires no API key and sends no information outside the application.

## External research workers

OpenAI, Gemini and Microsoft/Copilot are optional **discovery workers**, not decision makers.

The research instruction requires:

- Canadian funder/program only
- project takes place in Canada
- first-party source preferred
- confirmed values only
- unknown remains unknown

OpenAI uses an approved-domain list. Gemini and Microsoft receive the same Canada-only instruction. Because external search can still surface mistakes, provider output remains in an unverified discovery queue until the app's own verification rules are satisfied.
