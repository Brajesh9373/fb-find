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


def test_rank_social_platforms_equal():
    # No platform is preferred: discovery order decides among socials.
    cands = [
        {"title": "Insta", "url": "https://www.instagram.com/p/xyz/", "source": "instagram.com", "thumbnail": "", "position": 2},
        {"title": "Tok", "url": "https://www.tiktok.com/@u/video/1", "source": "tiktok.com", "thumbnail": "", "position": 1},
        {"title": "Tube", "url": "https://www.youtube.com/watch?v=1", "source": "youtube.com", "thumbnail": "", "position": 3},
        {"title": "Blog", "url": "https://example.com/blog", "source": "example.com", "thumbnail": "", "position": 0},
    ]
    ranked = rank_candidates(cands)
    assert [c["source"] for c in ranked] == ["tiktok.com", "instagram.com", "youtube.com", "example.com"]


def test_parse_marks_exact_matches():
    data = {
        "visual_matches": [
            {"title": "Similar", "link": "https://example.com/similar", "source": "example.com", "thumbnail": ""},
        ],
        "exact_matches": [
            {"title": "Exact", "link": "https://www.youtube.com/watch?v=9", "source": "youtube.com", "thumbnail": ""},
        ],
    }
    cands = parse_lens_results(data)
    by_url = {c["url"]: c for c in cands}
    assert by_url["https://www.youtube.com/watch?v=9"]["is_exact"] is True
    assert by_url["https://example.com/similar"]["is_exact"] is False


def test_rank_exact_first():
    # An exact image match outranks socials and earlier positions.
    cands = [
        {"title": "Insta", "url": "https://www.instagram.com/p/xyz/", "source": "instagram.com", "thumbnail": "", "position": 1},
        {"title": "Blog", "url": "https://example.com/blog", "source": "example.com", "thumbnail": "", "position": 2},
        {"title": "Exact", "url": "https://www.youtube.com/watch?v=9", "source": "youtube.com", "thumbnail": "", "position": 7, "is_exact": True},
    ]
    ranked = rank_candidates(cands)
    assert ranked[0]["url"] == "https://www.youtube.com/watch?v=9"
    assert [c["source"] for c in ranked[1:]] == ["instagram.com", "example.com"]
