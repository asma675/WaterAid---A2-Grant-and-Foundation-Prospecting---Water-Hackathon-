from app.engine import all_opportunities, public_opportunities
from app.ranking import ranking_items
from app.security import scrub_external_payload


def test_expected_regression_opportunities_loaded():
    # No-arg mode intentionally preserves the original challenge regression API.
    ops=all_opportunities()
    assert len(ops)==25
    by={o.opp_id:o for o in ops}
    assert by['O02'].decision=='DECLINE'
    assert by['O03'].decision=='REVIEW'
    assert by['O08'].decision=='PURSUE'
    assert by['O11'].source_count==2


def test_real_public_opportunities_are_separate():
    ops=public_opportunities()
    assert len(ops)>=10
    assert all(x.real_public for x in ops)
    assert any(x.opp_id=='CA-ON-GLLAF-2026' for x in ops)
    # A good engine is allowed to say no early.
    assert all(x.funder_country=='Canada' and x.project_country=='Canada' for x in ops)
    assert any(x.decision=='REVIEW' and x.source_count > 1 for x in ops)


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
