
from openai import OpenAI
from app.config import settings


SYSTEM_PROMPT = """
You are an Industrial Product Intelligence Assistant.

Instructions:
1. Use internal document evidence when it adequately answers the question.
2. If internal evidence is missing or insufficient and web search is
   enabled, search online for reliable information.
3. Prefer official manufacturer websites, product datasheets,
   technical manuals, and authoritative sources.
4. Never invent specifications, model numbers, prices, certifications,
   or source URLs.
5. Clearly distinguish information from internal documents and online
   sources.
6. If reliable evidence cannot be found, state that clearly.
7. For safety-critical decisions, recommend checking the manufacturer's
   original documentation.
"""


def generate_answer(
    question: str,
    evidence: str,
    use_web: bool = False,
) -> str:
    if not settings.openrouter_api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY is missing from the .env file."
        )

    client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"Question:\n{question}\n\n"
                f"Internal document evidence:\n"
                f"{evidence or 'No relevant internal evidence found.'}\n\n"
                "First determine whether the internal evidence is "
                "sufficient to answer the question.\n"
                "If it is insufficient and web search is available, "
                "use online search to find reliable information.\n"
                "Do not claim that you searched online unless a search "
                "was actually performed.\n"
                "Cite sources using the actual URLs or citations "
                "provided by the search tool. Never invent citations."
            ),
        },
    ]

    request = {
        "model": settings.openrouter_model,
        "temperature": 0.1,
        "messages": messages,
    }

    if use_web:
        request["tools"] = [
            {
                "type": "openrouter:web_search",
                "parameters": {
                    "max_results": 5,
                    "search_context_size": "medium",
                },
            }
        ]

    response = client.chat.completions.create(**request)

    message = response.choices[0].message
    answer = message.content or "No answer was returned."

    # Preserve any citations exposed by the OpenRouter response.
    citations = getattr(message, "annotations", None)

    if citations:
        citation_lines = []

        for citation in citations:
            url_citation = (
                citation.get("url_citation")
                if isinstance(citation, dict)
                else getattr(citation, "url_citation", None)
            )

            if url_citation:
                if isinstance(url_citation, dict):
                    title = url_citation.get("title", "Online source")
                    url = url_citation.get("url")
                else:
                    title = getattr(
                        url_citation, "title", "Online source"
                    )
                    url = getattr(url_citation, "url", None)

                if url:
                    citation_lines.append(f"- [{title}]({url})")

        if citation_lines:
            answer += "\n\n### Online sources\n" + "\n".join(
                dict.fromkeys(citation_lines)
            )

    return answer
