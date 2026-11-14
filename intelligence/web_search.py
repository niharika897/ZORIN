import json
import re
import urllib.parse
from html import unescape
from typing import List, Dict, Any
import requests


def search_duckduckgo(query: str, max_results: int = 4) -> List[Dict[str, str]]:
    """Searches DuckDuckGo HTML endpoint for live web results."""
    results = []
    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        }
        resp = requests.post(url, data={"q": query}, headers=headers, timeout=6)
        if resp.status_code in (200, 202):
            raw_html = resp.text

            # Extract snippets and titles
            # Result title and URL
            title_pattern = re.compile(r'<a class="result__url"[^>]*>(.*?)</a>', re.DOTALL)
            snippet_pattern = re.compile(r'<a class="result__snippet[^>]*>(.*?)</a>', re.DOTALL)

            titles = title_pattern.findall(raw_html)
            snippets = snippet_pattern.findall(raw_html)

            for i in range(min(len(snippets), max_results)):
                clean_snippet = unescape(re.sub(r'<[^>]+>', '', snippets[i])).strip()
                clean_title = unescape(re.sub(r'<[^>]+>', '', titles[i])).strip() if i < len(titles) else "Web Result"
                if clean_snippet:
                    results.append({
                        "title": clean_title,
                        "snippet": clean_snippet
                    })
    except Exception as e:
        print(f"DuckDuckGo search warning: {e}")

    return results


def search_wikipedia(query: str, max_results: int = 2) -> List[Dict[str, str]]:
    """Searches Wikipedia API for factual summaries."""
    results = []
    try:
        headers = {"User-Agent": "ZorinAssistant/2.0 (niharika@zorin.ai)"}
        endpoint = (
            f"https://en.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote(query)}&format=json&utf8=1"
        )
        resp = requests.get(endpoint, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("query", {}).get("search", [])
            for item in items[:max_results]:
                snippet = unescape(re.sub(r'<[^>]+>', '', item.get("snippet", ""))).strip()
                title = item.get("title", "")
                if snippet:
                    results.append({
                        "title": f"Wikipedia: {title}",
                        "snippet": snippet
                    })
    except Exception as e:
        print(f"Wikipedia search warning: {e}")

    return results


def search_web(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Unified real-time web search for ZORIN.
    Aggregates DuckDuckGo live results with encyclopedic lookups.
    """
    clean_query = str(query).strip()
    if not clean_query:
        return {"success": False, "message": "Search query cannot be empty.", "results": []}

    print(f"\n🔍 [ZORIN WEB SEARCH] Query: '{clean_query}'")

    combined_results = []

    # 1. Try DuckDuckGo live web search
    ddg_results = search_duckduckgo(clean_query, max_results=max_results)
    combined_results.extend(ddg_results)

    # 2. Augment with Wikipedia factual lookup if few results
    if len(combined_results) < 2:
        wiki_results = search_wikipedia(clean_query, max_results=2)
        combined_results.extend(wiki_results)

    if not combined_results:
        # Fallback summary
        return {
            "success": True,
            "query": clean_query,
            "message": f"No immediate live web search results found for '{clean_query}'.",
            "results": []
        }

    formatted_summary = "\n".join(
        [f"- {r['title']}: {r['snippet']}" for r in combined_results]
    )

    return {
        "success": True,
        "query": clean_query,
        "count": len(combined_results),
        "summary": formatted_summary,
        "results": combined_results
    }


if __name__ == "__main__":
    test_res = search_web("2026 calendar events")
    print(json.dumps(test_res, indent=2))
