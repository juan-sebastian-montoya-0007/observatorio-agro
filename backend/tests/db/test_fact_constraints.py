import pytest
from sqlalchemy.exc import IntegrityError


def test_fact_key_allows_variants_but_rejects_exact_duplicate(session, fact_factory):
    session.add(fact_factory(crop_variant_id=1, source_row=10))
    session.commit()

    session.add(fact_factory(crop_variant_id=2, source_row=11))
    session.commit()

    session.add(fact_factory(crop_variant_id=1, source_row=12))
    with pytest.raises(IntegrityError):
        session.commit()
