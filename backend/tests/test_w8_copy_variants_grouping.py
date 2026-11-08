"""W8 A1+A2: keep every copy variant and group same-copy ads instead of dropping them.

Stubs only: no provider or database is touched.
"""
from __future__ import annotations

from app.services.creative_service import provenance_fields
from app.services.discover_service import group_by_concept
from app.services.scraping.metapi_provider import MetapiProvider, metapi_copy_variants
from app.services.scraping.normalizer import normalize_creative


def _metapi_ad(ad_id: int, body: str, image: str, **extra) -> dict:
    item = {
        "provider_id": ad_id,
        "provider_page_id": "15087023444",
        "provider_page_name": "Nike",
        "bodies": [body],
        "creative_link_titles": ["Just Do It"],
        "cta_text": "Shop Now",
        "link_url": "https://www.nike.com/air",
        "snapshot_url": f"https://www.facebook.com/ads/library/?id={ad_id}",
        "original_image_url": [image],
        "delivery_start_time": "2026-10-01T00:00:00Z",
        "countries": ["US"],
        "languages": ["EN"],
    }
    item.update(extra)
    return item


def _parse(items):
    return MetapiProvider.__new__(MetapiProvider)._parse_metapi_ads(items, "nike")


def test_every_copy_variant_is_kept_in_order_without_repeats():
    item = _metapi_ad(
        1, "Run further.", "https://scontent.fbcdn.net/a.jpg",
        bodies=["Run further.", "Run faster.", "Run further.", "Recover better."],
        creative_link_titles=["Air Zoom", "Air Zoom", "Air Zoom", "Pegasus"],
    )
    variants = metapi_copy_variants(item)
    assert [v["body"] for v in variants] == ["Run further.", "Run faster.", "Recover better."]
    assert variants[2]["title"] == "Pegasus"


def test_snapshot_link_landing_url_and_ad_id_use_documented_fields():
    (raw,) = _parse([_metapi_ad(77, "Run further.", "https://scontent.fbcdn.net/a.jpg")])
    assert raw.permalink == "https://www.facebook.com/ads/library/?id=77"
    assert raw.source_ad_id == "77"
    assert raw.landing_url == "https://www.nike.com/air"
    assert raw.landing_domain == "nike.com"
    assert raw.raw["countries"] == ["US"] and raw.raw["page_id"] == "15087023444"


def test_variants_survive_normalization_and_reach_the_api_fields():
    item = _metapi_ad(5, "Run further.", "https://scontent.fbcdn.net/a.jpg", bodies=["Run further.", "Run faster."])
    (raw,) = _parse([item])
    creative, _score = normalize_creative(raw, "job-1", "brand-1", brand_label="Nike")
    fields = provenance_fields(creative)
    assert [v["body"] for v in fields["copy_variants"]] == ["Run further.", "Run faster."]


def test_nike_style_result_keeps_all_ads_and_groups_shared_copy():
    # Mirrors the 2026-11-07 proof: 15 Nike ads, 13 sharing one copy.
    items = [_metapi_ad(i, "Just do it.", f"https://scontent.fbcdn.net/{i}.jpg") for i in range(13)]
    items += [_metapi_ad(100, "New season.", "https://scontent.fbcdn.net/x.jpg")]
    items += [_metapi_ad(101, "Members get more.", "https://scontent.fbcdn.net/y.jpg")]
    records = [normalize_creative(r, "job-1", "brand-1", brand_label="Nike") for r in _parse(items)]

    kept, repeats = group_by_concept(records)

    assert len(kept) == 15 and repeats == 0
    shared = [c for c, _ in kept if c.body == "Just do it."]
    assert len(shared) == 13
    assert {c.variant_count for c in shared} == {13}
    assert len({c.provenance_json["concept_id"] for c in shared}) == 1
    singles = [c for c, _ in kept if c.body != "Just do it."]
    assert {c.variant_count for c in singles} == {1}
    assert len({c.provenance_json["concept_id"] for c in singles}) == 2


def test_true_repeats_of_the_same_ad_are_still_skipped():
    items = [_metapi_ad(9, "Just do it.", "https://scontent.fbcdn.net/9.jpg")] * 3
    records = [normalize_creative(r, "job-1", "brand-1", brand_label="Nike") for r in _parse(items)]
    kept, repeats = group_by_concept(records)
    assert len(kept) == 1 and repeats == 2
    assert kept[0][0].variant_count == 1


def test_ads_without_ids_differ_by_media():
    a = _metapi_ad(1, "Just do it.", "https://scontent.fbcdn.net/a.jpg", provider_id=None)
    b = _metapi_ad(2, "Just do it.", "https://scontent.fbcdn.net/b.jpg", provider_id=None)
    records = [normalize_creative(r, "job-1", "brand-1", brand_label="Nike") for r in _parse([a, b, a])]
    kept, repeats = group_by_concept(records)
    assert len(kept) == 2 and repeats == 1
