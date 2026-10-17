from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_history_benchmarks():
    r=client.get('/api/v1/history/benchmarks')
    assert r.status_code==200
    body=r.json()
    assert body['pass'] is True
    assert body['checks']['total_applications']['actual']==104
    assert body['checks']['won_zero_award']['actual']==10


def test_history_metrics_and_denominators():
    r=client.get('/api/v1/history/analytics')
    assert r.status_code==200
    b=r.json()
    assert b['metrics']['total_requested_cad']==22530000
    assert b['metrics']['total_awarded_cad']==7999000
    assert 'Withdrawn' in b['metrics']['denominators']['stage_success_rate']


def test_trl_reference():
    r=client.get('/api/v1/trl')
    assert r.status_code==200
    b=r.json()
    assert len(b['levels'])==9
    assert b['levels'][0]['trl']==1
    assert b['levels'][-1]['trl']==9
    assert 'technology maturity' in b['note'].lower()


def test_role_enforcement_for_scoring_config():
    r=client.patch('/api/v1/scoring-config',headers={'X-GrantCurrent-Role':'Read-only Viewer'},json={'weights':{
        'eligibility_evidence':25,'thematic_alignment':20,'geographic_alignment':15,'donor_relationship':15,'historical_outcomes':10,'application_effort':10,'timing_readiness':5
    }})
    assert r.status_code==403


def test_user_opportunity_unverified_when_evidence_missing():
    countries=client.get('/api/v1/target-countries').json()['countries']
    country=countries[0]['country']
    r=client.post('/api/v1/user-opportunities',json={
        'project_name':'Test rural water project','country':country,'wash_theme':'WASH climate','funding_requirement':100000,
        'expected_application_effort':24,'relationship_status':'Cold','funding_stage':'Prospecting'
    })
    assert r.status_code==200
    b=r.json()
    assert b['eligibility_status']=='Eligibility Unverified'
    assert 0 <= b['score'] <= 100
    client.delete(f"/api/v1/user-opportunities/{b['id']}")


def test_project_crud_and_scenario():
    country=client.get('/api/v1/target-countries').json()['countries'][0]['country']
    p=client.post('/api/v1/projects',json={'title':'Test project','country':country,'total_budget':500000,'existing_funding':100000})
    assert p.status_code==200
    row=p.json()
    assert row['funding_gap']==400000
    assert client.delete(f"/api/v1/projects/{row['id']}").status_code==200

def test_trl_requirement_affects_eligibility():
    country=client.get('/api/v1/target-countries').json()['countries'][0]['country']
    r=client.post('/api/v1/user-opportunities',json={
        'project_name':'TRL water sensor','country':country,'wash_theme':'water quality technology','funding_requirement':250000,
        'expected_application_effort':24,'relationship_status':'Warm','eligibility_requirements':'Applicants must demonstrate TRL 6-8 before submission.',
        'evidence_links':'https://example.org/verified-guideline','trl':4,'funding_stage':'Open call'
    })
    assert r.status_code==200
    b=r.json()
    assert b['eligibility_status']=='Eligibility Conflict'
    assert any('TRL' in x for x in b['risks'])
    client.delete(f"/api/v1/user-opportunities/{b['id']}")


def test_read_only_cannot_change_country_scope():
    r=client.post('/api/v1/target-countries',headers={'X-GrantCurrent-Role':'Read-only Viewer'},json={'country':'Testland','region':'Test'})
    assert r.status_code==403
