import re, string, calendar, requests, time
from wikipedia import WikipediaPage
import wikipedia
from bs4 import BeautifulSoup
from match import match
from typing import List, Callable, Tuple, Any, Match


def get_page_html(title: str) -> str:
    search_response = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": title, "format": "json"},
        headers={"User-Agent": "Wikipedia-Let-Me-Through/1.0"},
        timeout=10
    )
    results = search_response.json().get("query", {}).get("search", [])
    if results:
        title = results[0]["title"]  # use the top search result title
        print(f"Searching Wikipedia for: {title}")
    
    for attempt in range(5):
        response = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json",
                "redirects": True,
            },
            headers={"User-Agent": "intro-ai-class/1.0"}
        )
        if response.status_code == 429:
            wait = int(response.headers.get("Retry-After", 5))
            print(f"Rate limited — waiting {wait}s before retrying '{title}'...")
            time.sleep(wait)
            continue
        if response.status_code == 200 and response.text.strip():
            data = response.json()
            if "error" not in data:
                time.sleep(2)  # polite delay after every successful call
                return data["parse"]["text"]["*"]
    raise ConnectionError(f"Could not retrieve Wikipedia page for '{title}' after 5 attempts")


def get_first_infobox_text(html: str) -> str:
    """Gets first infobox html from a Wikipedia page (summary box)

    Args:
        html - the full html of the page

    Returns:
        html of just the first infobox
    """
    soup = BeautifulSoup(html, "html.parser")
    results = soup.find_all(class_="infobox")

    if not results:
        raise LookupError("Page has no infobox")
    return results[0].text


def clean_text(text: str) -> str:
    """Cleans given text removing non-ASCII characters and duplicate spaces & newlines

    Args:
        text - text to clean

    Returns:
        cleaned text
    """
    only_ascii = "".join([char if char in string.printable else " " for char in text])
    no_dup_spaces = re.sub(" +", " ", only_ascii)
    no_dup_newlines = re.sub("\n+", "\n", no_dup_spaces)
    return no_dup_newlines


def get_match(
    text: str,
    pattern: str,
    error_text: str = "Page doesn't appear to have the property you're expecting",
) -> Match:
    """Finds regex matches for a pattern

    Args:
        text - text to search within
        pattern - pattern to attempt to find within text
        error_text - text to display if pattern fails to match

    Returns:
        text that matches
    """
    p = re.compile(pattern, re.DOTALL | re.IGNORECASE)
    match = p.search(text)

    if not match:
        raise AttributeError(error_text)
    return match


def get_population(country_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(country_name)))
    pattern = r"Population.*?(?:Increase|Decrease|Neutral decrease|Neutral increase)?\s*(?P<population>[\d,]{6,})"
    error_text = "Page infobox has no population information"
    match = get_match(infobox_text, pattern, error_text)

    return match.group("population").strip()

def get_capital(country_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(country_name)))
    pattern = r"Capital(?:\s*and\s*largest\s*city\s*)?(?P<capital>[A-Z][A-Za-z\s,\.]+?)(?:\d|Largest|Official|Government)"
    error_text = "Page infobox has no capital information"
    match = get_match(infobox_text, pattern, error_text)

    return match.group("capital").strip()

def get_currency(country_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(country_name)))
    pattern = r"Currency(?:\s+)?(?P<currency>[A-Z\.\s][A-Za-z\.\s]+(?:\([^)]+\))?)"
    error_text = "Page infobox has no currency information"
    match = get_match(infobox_text, pattern, error_text)
    return match.group("currency").strip()


def get_language(country_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(country_name)))
    pattern = pattern_language = r"Official\s+language(?:s)?(?:and\s+national\s+language)?\s*(?P<language>[A-Z][A-Za-z\s,]+?)(?:\(|\[|\d|National|Regional|Ethnic|Religion)"
    error_text = "Page infobox has no official language information"
    match = get_match(infobox_text, pattern, error_text)
    return match.group("language").strip()

def get_area(country_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(country_name)))
    pattern = r"Area\s+Total\s*(?:area)?\s*(?P<area>[\d,]+(?:\.\d+)?)(?:\[\d+\])*\s*(?:km2|sq\s+mi|sq|km)?"
    error_text = "Page infobox has no area information"
    match = get_match(infobox_text, pattern, error_text)
    return match.group("area").strip()


def get_calling_code(country_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(country_name)))
    pattern = r"Calling\s+code\s*(?P<code>\+?[\d\s\-]+)"
    error_text = "Page infobox has no calling code information"
    match = get_match(infobox_text, pattern, error_text)
    return match.group("code").strip()


def get_tld(country_name: str) -> str:
    infobox_text = clean_text(get_first_infobox_text(get_page_html(country_name)))
    pattern = r"Internet\s+TLD\s*(?P<tld>\.[a-z]{2,3})"
    error_text = "Page infobox has no internet TLD information"
    match = get_match(infobox_text, pattern, error_text)
    return match.group("tld").strip()


# below are a set of actions. Each takes a list argument and returns a list of answers
# according to the action and the argument. It is important that each function returns a
# list of the answer(s) and not just the answer itself.

def capital(matches: List[str]) -> List[str]:
    try:
        return [get_capital(" ".join(matches))]
    except Exception as e:
        return [f"Sorry, I couldn't process the capital: {str(e)}"]

def population(matches: List[str]) -> List[str]:
    try:
        return [get_population(" ".join(matches))]
    except Exception as e:
        return [f"Sorry, I couldn't process the population: {str(e)}"]

def currency(matches: List[str]) -> List[str]:
    try:
        return [get_currency(" ".join(matches))]
    except Exception as e:
        return [f"Sorry, I couldn't process the currency: {str(e)}"]

def language(matches: List[str]) -> List[str]:
    try:
        return [get_language(" ".join(matches))]
    except Exception as e:
        return [f"Sorry, I couldn't process the language: {str(e)}"]

def area(matches: List[str]) -> List[str]:
    try:
        return [get_area(" ".join(matches))]
    except Exception as e:
        return [f"Sorry, I couldn't process the area: {str(e)}"]

def calling_code(matches: List[str]) -> List[str]:
    try:
        return [get_calling_code(" ".join(matches))]
    except Exception as e:
        return [f"Sorry, I couldn't process the calling code: {str(e)}"]

def tld(matches: List[str]) -> List[str]:
    try:
        return [get_tld(" ".join(matches))]
    except Exception as e:
        return [f"Sorry, I couldn't process the internet domain TLD: {str(e)}"]

# dummy argument is ignored and doesn't matter
def bye_action(dummy: List[str]) -> None:
    raise KeyboardInterrupt


# type aliases to make pa_list type more readable, could also have written:
# pa_list: List[Tuple[List[str], Callable[[List[str]], List[Any]]]] = [...]
Pattern = List[str]
Action = Callable[[List[str]], List[Any]]

# The pattern-action list for the natural language query system. It must be declared
# here, after all of the function definitions
pa_list: List[Tuple[Pattern, Action]] = [
    ("what is the capital of %".split(), capital),
    ("what is the population of %".split(), population),
    ("what is the currency of %".split(), currency),
    ("what is the official language of %".split(), language),
    ("what is the total area of %".split(), area),
    ("what is the calling code for %".split(), calling_code),
    ("what is the internet tld for %".split(), tld),
    (["bye"], bye_action),
]


def search_pa_list(src: List[str]) -> List[str]:
    """Takes source, finds matching pattern and calls corresponding action. If it finds
    a match but has no answers it returns ["No answers"]. If it finds no match it
    returns ["I don't understand"].

    Args:
        source - a phrase represented as a list of words (strings)

    Returns:
        a list of answers. Will be ["I don't understand"] if it finds no matches and
        ["No answers"] if it finds a match but no answers
    """
    for pat, act in pa_list:
        mat = match(pat, src)
        if mat is not None:
            answer = act(mat)
            return answer if answer else ["No answers"]

    return ["I don't understand"]


def query_loop() -> None:
    """The simple query loop. The try/except structure is to catch Ctrl-C or Ctrl-D
    characters and exit gracefully"""
    print("Welcome to the wikipedia chatbot!\n")
    while True:
        try:
            print()
            query = input("Your query? ").replace("?", "").lower().split()
            answers = search_pa_list(query)
            for ans in answers:
                print(ans)

        except (KeyboardInterrupt, EOFError):
            break

    print("\nSo long!\n")


# uncomment the next line once you've implemented everything are ready to try it out
query_loop()