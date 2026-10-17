from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)


def test_health_and_public_corpus():
    r=client.get('/health')
    assert r.status_code==200
    body=r.json()
    assert body['status']=='ok'
    assert body['version']=='0.7.0'
    assert body['public_source_count'] >= 25
    assert body['public_opportunity_count'] >= 12
    assert body['gift_signal_count'] >= 15
    assert body['active_target_country_count'] >= 20


def test_target_country_endpoint_and_scope_crud():
    r=client.get('/api/v1/target-countries')
    assert r.status_code==200
    body=r.json()
    assert len(body['countries']) >= 20
    names={x['country'] for x in body['countries']}
    assert {'Malawi','Pakistan','Nigeria','Colombia','India'} <= names
    assert body['profile']['funder_constraint']=='Canadian funders/donors/programs only'
    created=client.post('/api/v1/target-countries',json={'country':'Testland','region':'Test Region','source':'pytest','active':True})
    assert created.status_code==200
    cid=created.json()['id']
    assert client.patch(f'/api/v1/target-countries/{cid}',json={'active':False}).json()['active']==0
    assert client.delete(f'/api/v1/target-countries/{cid}').status_code==200


def test_scan_real_public_default_and_full_brief():
    r=client.post('/api/v1/scan',json={'query':'Canadian funders for WASH climate resilience Malawi','max_results':5})
    assert r.status_code==200
    body=r.json()
    assert len(body['results'])==5
    assert len(body['trace'])==6
    assert body['mode']=='canadian-funders-wateraid-countries'
    assert all(x['real_public'] for x in body['results'])
    allowed={x['country'] for x in client.get('/api/v1/target-countries').json()['countries']}
    assert all(x['funder_country']=='Canada' for x in body['results'])
    assert all(set(x['target_countries']) & allowed for x in body['results'])
    assert body['rag_hits']
    sample=body['results'][0]
    assert len(sample['fit_criteria'])==7
    assert [c['criterion_id'] for c in sample['fit_criteria']]==['C1','C2','C3','C4','C5','C6','C7']
    assert sum(c['weight'] for c in sample['fit_criteria'])==100
    assert all(c['evidence_url'] and c['retrieved'] for c in sample['fit_criteria'])
    assert [g['gate_id'] for g in sample['gates']]==['G1','G2','G3','G4','G5','G6','G7','G8']
    assert all(g['result'] in {'Pass','Fail','Uncertain'} and g['evidence_quote'] and g['source_url'] and g['retrieved'] for g in sample['gates'])
    assert sample['key_dates'] and all(d['status'] in {'Confirmed','Inferred','Unknown'} and d['source_url'] and d['retrieved'] for d in sample['key_dates'])
    assert sample['money_effort']
    assert sample['money_effort']['source_url'] and sample['money_effort']['retrieved']
    assert sample['relationship_path']
    assert sample['risks_unknowns']
    assert sample['next_step']['owner']
    assert sample['briefing_complete'] is True


def test_rag_and_gap_closing_endpoints():
    r=client.post('/api/v1/rag/search',json={'query':'Canadian WASH funder Malawi WaterAid','top_k':5})
    assert r.status_code==200
    assert r.json()['hits']
    assert client.get('/api/v1/funders').json()['funders']
    assert client.get('/api/v1/gift-signals').json()['signals']
    assert len(client.get('/api/v1/public-sources').json()['sources']) >= 25


def test_provider_status_is_honest():
    rows=client.get('/api/v1/providers').json()['providers']
    local=next(x for x in rows if x['id']=='local')
    assert local['configured'] is True
    assert any(x['id']=='microsoft' for x in rows)


def test_planning_settings_and_brief_override():
    p=client.get('/api/v1/planning-settings')
    assert p.status_code==200
    assert p.json()['remaining_fundraising_hours'] >= 0
    assert p.json()['weekly_review_limit'] >= 1
    r=client.patch('/api/v1/brief-overrides/CA-RONCALLI-WASH-2027',json={
        'likely_ask_cad':30000,'fundraising_hours':10,'program_hours':2,'owner':'Test Officer'
    })
    assert r.status_code==200
    body=r.json()
    assert body['money_effort']['likely_ask_cad']==30000
    assert body['money_effort']['fundraising_hours']==10
    assert body['next_step']['owner']=='Test Officer'
    blocked=client.patch('/api/v1/brief-overrides/CA-RONCALLI-WASH-2027',json={
        'relationship_note':'Private board contact should not display','relationship_consent':'No'
    }).json()
    assert blocked['relationship_path']['people_or_channel']!='Private board contact should not display'
    allowed=client.patch('/api/v1/brief-overrides/CA-RONCALLI-WASH-2027',json={
        'relationship_note':'Approved board contact','relationship_consent':'Yes'
    }).json()
    assert allowed['relationship_path']['people_or_channel']=='Approved board contact'


def test_pipeline_round_trip():
    created=client.post('/api/v1/pipeline',json={
        'opportunity_id':'TEST-PIPE-1','title':'Test grant','funder':'Test Funder',
        'stage':'Qualified','owner':'Unassigned','next_action':'Verify'
    })
    assert created.status_code==200
    item=created.json()
    patched=client.patch(f"/api/v1/pipeline/{item['id']}",json={'stage':'Cultivating','notes':'Follow up'})
    assert patched.status_code==200
    assert patched.json()['stage']=='Cultivating'
    assert patched.json()['notes']=='Follow up'
    deleted=client.delete(f"/api/v1/pipeline/{item['id']}")
    assert deleted.status_code==200


def test_decision_log_round_trip():
    r=client.post('/api/v1/decisions',json={
        'opportunity_id':'CA-RONCALLI-WASH-2027','system_decision':'PURSUE-QUEUE','human_decision':'CULTIVATE','reason':'Prepare for next intake'
    })
    assert r.status_code==200
    assert r.json()['human_decision']=='CULTIVATE'
    assert client.get('/api/v1/decisions').status_code==200


def test_data_issue_round_trip():
    r=client.post('/api/v1/data-issues',json={'page':'week','description':'Check test source date'})
    assert r.status_code==200
    item=r.json()
    assert item['status']=='Open'
    patched=client.patch(f"/api/v1/data-issues/{item['id']}",json={'status':'Resolved'})
    assert patched.status_code==200
    assert patched.json()['status']=='Resolved'

def test_removed_seed_country_stays_removed_until_explicitly_readded():
    from app import runtime_store
    from uuid import uuid4
    name='Pytest Seedland '+uuid4().hex[:8]
    seed=[{'country':name,'region':'Test','source':'pytest'}]
    rows=runtime_store.list_countries(seed,include_inactive=True)
    row=next(x for x in rows if x['country']==name)
    assert runtime_store.delete_country(row['id']) is True
    assert all(x['country']!=name for x in runtime_store.list_countries(seed,include_inactive=True))
    restored=runtime_store.add_country(seed,{'country':name,'region':'Test','source':'pytest restore','active':True})
    assert restored['country']==name
    assert runtime_store.delete_country(restored['id']) is True
