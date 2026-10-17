from app.engine import all_opportunities, public_opportunities
from app.ranking import ranking_items
from app.security import scrub_external_payload
from app import data_store


def test_expected_regression_opportunities_loaded():
    ops=all_opportunities()
    assert len(ops)==25
    by={o.opp_id:o for o in ops}
    assert by['O02'].decision=='DECLINE'
    assert by['O03'].decision=='REVIEW'
    assert by['O08'].decision=='PURSUE'
    assert by['O11'].source_count==2


def test_real_public_opportunities_are_canadian_funders_for_wateraid_countries():
    ops=public_opportunities()
    assert len(ops)>=12
    assert all(x.real_public for x in ops)
    assert any(x.opp_id=='CA-RONCALLI-WASH-2027' for x in ops)
    assert any(x.opp_id=='CA-ONEDROP-PARTNER' for x in ops)
    assert all(x.funder_country=='Canada' for x in ops)
    assert all(len(x.gates)==8 for x in ops)
    assert all(x.briefing_complete for x in ops)
    assert any(x.decision=='CULTIVATE' for x in ops)
    assert any(x.decision=='DECLINE' for x in ops)


def test_ranking_reference_order():
    rows=ranking_items()
    assert [r.rank_id for r in rows[:4]]==['K2','K1','K3','K6']
    assert rows[0].fit_score > rows[1].fit_score


def test_privacy_scrubber():
    data={'donor_name':'Private Person','public_fact':'Open call','note':'email a@b.com or 416-555-1212'}
    out=scrub_external_payload(data)
    assert 'donor_name' not in out
    assert 'a@b.com' not in out['note']
    assert '416-555-1212' not in out['note']
