import sqlite3

import requests
from xml.etree.ElementTree import fromstring
from collections import Counter
from typing import Tuple

URL = 'https://suggestqueries.google.com/complete/search'

conn = sqlite3.connect('keywords.db')
cursor = conn.cursor()


def create_table() -> None:
    cursor.execute('''DROP TABLE IF EXISTS keywords''')
    cursor.execute('''CREATE TABLE keywords
    (source VARCHAR,
    target VARCHAR,
    weight INTEGER
    )
    ''')


def insert(suggestion: Tuple[str, str, int]) -> None:
    cursor.execute('''INSERT INTO keywords
    (source, target, weight) VALUES
    (?, ?, ?)''', suggestion)


def get_suggestions(keyword: str) -> list:
    if not keyword:
        return []
    params = {
        'output': 'toolbar',
        'gl': 'us',
        'hl': 'en',
        'q': f'{keyword} vs '
    }

    r = requests.get(URL, params=params)
    suggestions = []
    if r.ok:
        tree = fromstring(str(r.content, 'latin-1'))
        weight = 5
        accepted_terms = []
        for suggest in tree.findall('CompleteSuggestion'):
            text = suggest.find('suggestion').get('data')
            counter = Counter(text)
            if text == keyword or counter['vs'] > 1:
                continue
            words = text.split()
            if 'vs' in words:
                words.remove('vs')
            if words[0] == keyword:
                text = ' '.join(words[1:])
            else:
                text = ' '.join(words)
            exist_previous_term = any(term in text for term in accepted_terms)
            if not text or keyword in text or exist_previous_term:
                continue

            items = (keyword, text, weight)
            suggestions.append(items)
            accepted_terms.append(text)
            weight -= 1
            if weight == 0:
                break
    return suggestions


def get_sub_suggestions(depth: int, suggestions: list):
    if depth == 0:
        return
    for suggestion in suggestions:
        sub_suggestions = get_suggestions(suggestion[1])
        previous_terms = cursor.execute('''SELECT DISTINCT source
        from keywords
        ''').fetchall()
        previous_keywords = [previous_term[0] for previous_term in previous_terms]
        accepted_terms = []
        for sub_suggestion in sub_suggestions:
            if sub_suggestion[1] not in previous_keywords:
                accepted_terms.append(sub_suggestion)
            insert(sub_suggestion)
        get_sub_suggestions(depth - 1, accepted_terms)


def store_suggestions(keyword: str, depth: int):
    if depth < 1:
        raise ValueError('Invaild depth')
    create_table()
    suggestions = get_suggestions(keyword)
    for suggestion in suggestions:
        insert(suggestion)
    get_sub_suggestions(depth, suggestions)
    conn.commit()


if __name__ == '__main__':
    store_suggestions('google', 4)
