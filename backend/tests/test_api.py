from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_health_and_public_corpus():
    r=client.get('/health')
    assert r.status_code==200
    body=r.json()
    assert body['status']=='ok'
    assert body['public_source_count'] >= 20
    assert body['public_opportunity_count'] >= 10
    assert body['gift_signal_count'] >= 10

def test_scan_real_public_default():
    r=client.post('/api/v1/scan',json={'query':'Canadian freshwater watershed funding Ontario','max_results':5})
    assert r.status_code==200
    body=r.json()
    assert len(body['results'])==5
    assert len(body['trace'])==6
    assert body['mode']=='canada-domestic-rag'
    assert all(x['real_public'] for x in body['results'])
    assert all(x['funder_country']=='Canada' and x['project_country']=='Canada' for x in body['results'])
    assert body['rag_hits']

def test_rag_and_gap_closing_endpoints():
    r=client.post('/api/v1/rag/search',json={'query':'Great Lakes watershed Ontario water quality','top_k':5})
    assert r.status_code==200
    assert r.json()['hits']
    assert client.get('/api/v1/funders').json()['funders']
    assert client.get('/api/v1/gift-signals').json()['signals']
    assert len(client.get('/api/v1/public-sources').json()['sources']) >= 20

def test_provider_status_is_honest():
    rows=client.get('/api/v1/providers').json()['providers']
    local=next(x for x in rows if x['id']=='local')
    assert local['configured'] is True
    assert any(x['id']=='microsoft' for x in rows)

def test_pipeline_round_trip():
    created=client.post('/api/v1/pipeline',json={
        'opportunity_id':'TEST-PIPE-1','title':'Test grant','funder':'Test Funder',
        'stage':'Qualified','owner':'Unassigned','next_action':'Verify'
    })
    assert created.status_code==200
    item=created.json()
    patched=client.patch(f"/api/v1/pipeline/{item['id']}",json={'stage':'Cultivating'})
    assert patched.status_code==200
    assert patched.json()['stage']=='Cultivating'
    deleted=client.delete(f"/api/v1/pipeline/{item['id']}")
    assert deleted.status_code==200

def test_decision_log_round_trip():
    r=client.post('/api/v1/decisions',json={
        'opportunity_id':'CA-ON-GLLAF-2026','system_decision':'PURSUE','human_decision':'PURSUE','reason':'Good fit'
    })
    assert r.status_code==200
    assert r.json()['human_decision']=='PURSUE'
    assert client.get('/api/v1/decisions').status_code==200
