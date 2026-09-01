from app.search.parser import parse_lens_results
from app.search.ranking import rank_candidates


def test_parse_lens_results_basic():
    data = {
        "visual_matches": [
            {"title": "Instagram post", "link": "https://www.instagram.com/p/abc/", "source": "Instagram", "thumbnail": "https://example.com/t.jpg"},
            {"title": "Blog", "link": "https://example.com/blog", "source": "example.com", "thumbnail": ""},
        ]
    }
    cands = parse_lens_results(data)
    assert len(cands) == 2
    assert cands[0]["url"] == "https://www.instagram.com/p/abc/"
    assert cands[0]["title"] == "Instagram post"


def test_parse_dedup():
    data = {
        "visual_matches": [
            {"title": "A", "link": "https://example.com/a", "source": "example.com"},
            {"title": "A dup", "link": "https://example.com/a", "source": "example.com"},
        ]
    }
    assert len(parse_lens_results(data)) == 1


def test_rank_social_first():
    cands = [
        {"title": "Blog", "url": "https://example.com/blog", "source": "example.com", "thumbnail": "", "position": 1},
        {"title": "Insta", "url": "https://www.instagram.com/p/xyz/", "source": "instagram.com", "thumbnail": "", "position": 2},
    ]
    ranked = rank_candidates(cands)
    assert "instagram.com" in ranked[0]["url"]
