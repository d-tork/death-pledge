import os
from bs4 import BeautifulSoup

print(os.getcwd())

fname = 'Matrix.htm'
raw_html = open(fname, 'r', encoding='utf-8')

html = BeautifulSoup(raw_html, 'html.parser')


def get_addresses(soup):
    addresses = set()
    td_container = soup.find_all('td', attrs={'class': 'd192090m16'})

    for span in td_container.find('span', class_='field d192090m14'):
        print(span.text)
        #addresses.add(span.strip())
    return list(addresses)


print(get_addresses(html))

#print(html.get_text())


"""
for li in html.select('li'):
    for name in li.text.split('\n'):
        if len(name) > 0:
            names.add(name.strip())
return list(names)
"""