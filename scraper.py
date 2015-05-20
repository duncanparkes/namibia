import re
from urlparse import urljoin, urlsplit, parse_qs
import requests
import lxml.html

import scraperwiki

from slugify import slugify_unicode

sources = (
    ('National Council', 'http://www.parliament.na/index.php?option=com_contact&view=category&id=108&Itemid=1483'),
    ('National Assembly', 'http://www.parliament.gov.na/index.php?option=com_contact&view=category&id=104&Itemid=1479'),
    )


data = {}
term_data = {}

def handle_chamber(chamber_name, source_url, data, term_data):
    resp = requests.get(source_url)

    root = lxml.html.fromstring(resp.text)

    terms = [(x.find('span').text.strip(), urljoin(source_url, x.get('href')))
             for x in root.cssselect('.menu-treemenu')[0].cssselect('a')]

    term_data = []
    for term_name, term_url in terms:
        term_number, start_date, end_date = re.match(r'(\d*)[^\d]+(\d{4})[ -]+(\d{4})', term_name).groups()
        term = {
            'name': term_name,
            'id': term_name,
            'start_date': int(start_date),
            'end_date': int(end_date),
            'term_number': int(term_number) if term_number else 0,
            }

        term_data.append(term)

        while term_url:
            print term_url
            term_resp = requests.get(term_url)
            term_root = lxml.html.fromstring(term_resp.text)

            trs = term_root.cssselect('.jsn-infotable')[0].cssselect('tr')[1:]

            for tr in trs:
                member = {}
                member['term'] = term_name
                member['term_id'] = term_name
                member['chamber'] = chamber_name

                # There are no constituencies, it's a central party list system
                member['area'] = ''

                name_link = tr.cssselect('.jsn-table-column-name')[0].find('a')
                member['name'] = name_link.text.strip()
                member['id'] = slugify_unicode(member['name'])
                details_url = member['details_url'] = urljoin(source_url, name_link.get('href'))

                try:
                    member['party'] = tr.cssselect('.jsn-table-column-country')[0].text.strip()
                except AttributeError:
                    # Karupu, Sebastiaan, for example, has nothing in this column.
                    # http://www.parliament.gov.na/index.php?option=com_contact&view=category&id=104&Itemid=1479&limitstart=40
                    member['party'] = ''

                # .jsn-table-column-email contains the email address, but only with
                # javascript turned on.

                details_resp = requests.get(details_url)
                details_root = lxml.html.fromstring(details_resp.text)

                key = (member['name'], member['term'])

                try:
                    src = details_root.cssselect('.jsn-contact-image')[0].cssselect('img')[0].get('src')
                    if src:
                        member['image'] = urljoin(source_url, details_root.cssselect('.jsn-contact-image')[0].cssselect('img')[0].get('src'))
                    else:
                        member['image'] = ''
                except:
                    print "No image found for {} in {}".format(*key)
                    member['image'] = ''

                if key in data:
                    print "Duplicate (name, term) pair ignored: ({}, {})".format(*key)
                else:
                    data[key] = member

            next_links = term_root.cssselect('a[title=Next]')
            term_url = urljoin(term_url, next_links[0].get('href')) if next_links else None


for chamber, source_url in sources:
    handle_chamber(chamber, source_url, data, term_data)

print term_data
scraperwiki.sqlite.save(unique_keys=['id'], data=term_data, table_name='terms')
scraperwiki.sqlite.save(unique_keys=['name', 'term'], data=data.values())

