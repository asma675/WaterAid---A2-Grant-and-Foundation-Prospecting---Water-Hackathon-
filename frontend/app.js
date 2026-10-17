const BASE = "";
const API_URL = "";

const mockOpportunities = [
  {
    opp_id: "GC-001",
    funder_name: "Canada Water Agency",
    title: "Freshwater Ecosystem Initiative",
    fit_score: 4.8,
    province: "Ontario / Quebec",
    location: "Great Lakes Basin",
    decision: "PURSUE",
    deadline: "2026-12-01",
    status: "Open",
    amount: "$50,000 - $250,000",
    themes: ["Freshwater", "Restoration", "Watershed"],
    funder_type: "Federal Government",
    rationale: "High strategic fit for community-led watershed restoration inside Ontario.",
    geography: "Projects must be located within Canadian eco-zones.",
    applicant_types: ["Non-profit", "Indigenous Communities"],
    confidence: "high",
    source_count: 3,
    readiness_index: 85,
    evidence: [{ retrieved: "2026-10-17" }]
  },
  {
    opp_id: "GC-002",
    funder_name: "TD Friends of the Environment Foundation",
    title: "Community Water Quality Grants",
    fit_score: 4.2,
    province: "Ontario",
    location: "Toronto / Hamilton",
    decision: "REVIEW",
    deadline: "2026-11-15",
    status: "Upcoming",
    amount: "$5,000 - $25,000",
    themes: ["Stormwater", "Community Environment"],
    funder_type: "Corporate Foundation",
    rationale: "Strong local match for grassroots stormwater education campaigns.",
    geography: "Canadian municipalities only.",
    applicant_types: ["Registered Charities", "Schools"],
    confidence: "high",
    source_count: 2,
    readiness_index: 90,
    evidence: [{ retrieved: "2026-10-17" }]
  }
];

const state = {
  tab:'week', ops: mockOpportunities, selected: mockOpportunities[0], sources:[], funders:[], gifts:[], contacts:[], alerts:[], providers:[], agents:[], pipeline:[], decisions:[],
  query:'freshwater grants for community water projects in Ontario', rag:[], research:[], loading:false, researchLoading:false, error:'',
  weekFilter:'ALL', province:'ALL', issue:'ALL', funderType:'ALL', giftQuery:'', giftFilters:{funder:'ALL',focus:'ALL',location:'ALL',year:'ALL'},
  savedSearches: JSON.parse(localStorage.getItem('gc_saved_searches')||'[]')
};
