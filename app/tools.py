from app.config import settings


def tavily_search(query: str, max_results: int = 5) -> list[dict]:
    if not settings.tavily_api_key:
        return []
    from tavily import TavilyClient
    client = TavilyClient(api_key=settings.tavily_api_key)
    response = client.search(query=query, search_depth="basic", max_results=max_results)
    return [
        {
            "title": item.get("title", "Web result"),
            "url": item.get("url", ""),
            "content": item.get("content", ""),
            "source_type": "web",
        }
        for item in response.get("results", [])
    ]
