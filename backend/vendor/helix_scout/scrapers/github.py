"""
Real GitHub Profile Scraper
Adapted from kiryano/Scout (MIT License)
"""
import re
from typing import Dict, Any
import httpx

EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

async def scrape_github_profile(handle: str, client: httpx.AsyncClient) -> Dict[str, Any]:
    """Scrapes real public GitHub profile and commit event email."""
    clean = handle.strip().lstrip("@")
    url = f"https://api.github.com/users/{clean}"
    
    try:
        resp = await client.get(
            url,
            headers={"User-Agent": "Helix-Scout/1.0", "Accept": "application/vnd.github.v3+json"},
            timeout=8.0
        )
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("email")
            email_source = "github_profile" if email else None
            
            # If email is null, check public commit events
            if not email:
                try:
                    events_resp = await client.get(
                        f"https://api.github.com/users/{clean}/events/public",
                        headers={"User-Agent": "Helix-Scout/1.0"},
                        timeout=6.0
                    )
                    if events_resp.status_code == 200:
                        events = events_resp.json()
                        for ev in events[:10]:
                            commits = ev.get("payload", {}).get("commits", [])
                            for c in commits:
                                author_email = c.get("author", {}).get("email")
                                if author_email and "noreply.github.com" not in author_email and EMAIL_REGEX.match(author_email):
                                    email = author_email.lower()
                                    email_source = "github_commit_event"
                                    break
                            if email:
                                break
                except Exception:
                    pass

            blog = data.get("blog")
            if blog and not blog.startswith("http"):
                blog = "https://" + blog

            return {
                "platform": "github",
                "handle": clean,
                "name": data.get("name") or clean,
                "email": email,
                "email_source": email_source,
                "phone": None,
                "phone_source": None,
                "website": blog or data.get("html_url"),
                "bio": data.get("bio"),
                "followers": data.get("followers", 0),
                "is_private": False,
                "captions": [],
                "profile_url": data.get("html_url") or f"https://github.com/{clean}",
                "scrape_status": "ok",
                "error": None,
            }
        elif resp.status_code == 404:
            return {
                "platform": "github",
                "handle": clean,
                "name": clean,
                "email": None,
                "profile_url": f"https://github.com/{clean}",
                "scrape_status": "not_found",
                "error": "user_not_found",
            }
    except Exception as e:
        pass

    return {
        "platform": "github",
        "handle": clean,
        "name": clean,
        "email": None,
        "profile_url": f"https://github.com/{clean}",
        "scrape_status": "needs_manual_review",
        "error": "github_fetch_failed",
    }
