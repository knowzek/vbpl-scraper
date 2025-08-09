from helpers import wJson, rJson
import re
from constants import TITLE_KEYWORD_TO_CATEGORY_RAW

def check_keyword(word, text):
    pattern = rf'\b{re.escape(word)}\b'
    if re.search(pattern, text, re.IGNORECASE):
        return True
    return False


if __name__ == "__main__":
    full_data = rJson('events.json')

    loc_cat = "Event Location - Hampton"
    free_cat = "Audience - Free Event"
    age_cats = [
        "Audience - School Age",
        "Audience - Teens",
        "Audience - Family Event"
    ]

    full_data_new = []

    for i, event in enumerate(full_data):
        categories = set()
        tags = event['Tags']
        tags = [t['tag'] for t in tags]
        if not "Things to Do with Kids" in tags:
            continue

        for keyword, categorie in TITLE_KEYWORD_TO_CATEGORY_RAW.items():
            if check_keyword(keyword.lower(), event['Event Name'].lower()) or check_keyword(keyword, event['Event Description'].lower()):
                categories.add(categorie)

        categories = list(categories)

        full_data[i]['Categories'] = [loc_cat, free_cat]

        if free_cat in categories:
            categories.remove(free_cat)

        full_data[i]['Categories'].extend(age_cats)
        
        if categories:
            # print(event['Event Link'])
            categories = ", ".join(categories)
            categories = categories.split(', ')
            categories = list(set(categories))
            full_data[i]['Categories'].extend(categories)

        full_data[i]['Categories'] = ", ".join(full_data[i]['Categories'])
        



        full_data_new.append(full_data[i])

    wJson(full_data_new, 'full_data.json')
        
    pass