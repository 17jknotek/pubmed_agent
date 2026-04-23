import httpx
from loguru import logger
from app.models.schemas import Article

SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"

async def fetch_pubmed_articles(query: str, max_results: int = 5) -> list[Article]:
    async with httpx.AsyncClient(timeout=15.0) as client:

        # Step 1: Search for PMIDs matching the query
        logger.info(f"Searching PubMed | query={query}")
        search_resp = await client.get(SEARCH_URL, params={
            "db": "pubmed",
            "term": query,
            "retmax": max_results,
            "retmode": "json",
            "sort": "relevance",
        })
        search_resp.raise_for_status()
        pmids = search_resp.json()["esearchresult"]["idlist"]

        if not pmids:
            logger.warning(f"No PubMed results | query={query}")
            return []

        logger.info(f"Found PMIDs: {pmids}")

        # Step 2: Fetch summaries for those PMIDs
        summary_resp = await client.get(SUMMARY_URL, params={
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        })
        summary_resp.raise_for_status()
        summaries = summary_resp.json()["result"]

        # Step 3: Fetch full abstracts via efetch
        fetch_resp = await client.get(FETCH_URL, params={
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "text",
            "rettype": "abstract",
        })
        fetch_resp.raise_for_status()

        # Parse abstracts — efetch returns them as one big text block separated by blank lines
        raw_abstracts = fetch_resp.text.strip().split("\n\n\n")
        abstract_map: dict[str, str] = {}
        for i, pmid in enumerate(pmids):
            abstract_map[pmid] = raw_abstracts[i].strip() if i < len(raw_abstracts) else ""

        # Step 4: Build Article objects
        articles: list[Article] = []
        for pmid in pmids:
            if pmid not in summaries:
                continue
            s = summaries[pmid]
            authors = [a["name"] for a in s.get("authors", [])]
            articles.append(Article(
                pmid=pmid,
                title=s.get("title", "No title"),
                abstract=abstract_map.get(pmid, "No abstract available"),
                authors=authors,
                journal=s.get("source", "Unknown journal"),
                pub_date=s.get("pubdate", "Unknown date"),
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            ))

        logger.info(f"Built {len(articles)} articles | query={query}")
        return articles