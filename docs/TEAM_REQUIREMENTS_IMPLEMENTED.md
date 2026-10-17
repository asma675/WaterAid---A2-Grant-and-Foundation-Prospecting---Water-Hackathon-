# Team Requirements — v0.6 Implementation Map

This document maps the teammate specification into the working application.

| Requirement | v0.6 implementation |
|---|---|
| Executive Intelligence Dashboard | Overview page with all requested KPIs, global filters and seven analytical views |
| Historical Pipeline Explorer | Full L1 CSV import, detail view, search/sort/filter, export, duplicate prevention, validation |
| AI Funder Intelligence | Funder profiles and grounded deterministic insight panel |
| Opportunity Matching | Verified public brief + user-entered 0–100 scoring engine |
| Fundraising Efficiency | Dedicated analytics page, samples/outlier warning, largest-award toggle |
| FundScope Advisor | Deterministic grounded assistant with suggested questions and limitations |
| Project Funding Planner | Persistent projects, gaps, linked opportunities and scenario planning |
| Reports & Pitch Mode | Executive report, CSV, browser PDF and presentation mode |
| Data safeguards | Separate stage/cash conversion, explicit denominators, no ML probability claim |
| Database entities | Funders, HistoricalApplications, FundingOpportunities, WASHProjects, ProjectFundingLinks, FundraisingTasks, ScoringConfigurations, UserProfiles, AuditLogs |
| Role-based access | Server-side demo permissions for 5 requested roles |
| Navigation | 9 requested functional sidebar modules |
| Demo benchmarks | Dynamically reconciled and test-covered |
| Persistence | SQLite volume-backed hackathon persistence |
| Accessibility | Larger default type, high contrast, responsive layout, light/dark theme |
| Requested funding filters | Recommendation, Hard gates, Relationship, Application type, Source freshness, Staff decision |
| Target-country management | Add/edit/activate/deactivate/remove/re-add |
| TRL | ISED TRL 1–9 guide, NASA origin note, optional project/opportunity field, explicit eligibility check when TRL appears in requirements |

## Not misrepresented as complete enterprise infrastructure

The build does not claim that demo role selection is organizational authentication, nor that SQLite is a managed enterprise database. Those are deployment-stage integrations, documented in README under Production boundary.
