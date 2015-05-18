from urlparse import urljoin, urlsplit, parse_qs
import requests
import lxml.html

import scraperwiki

from slugify import slugify_unicode

source_url = 'http://www.parliament.gov.na/index.php?option=com_contact&view=category&id=104&Itemid=1479'
resp = requests.get(source_url)

root = lxml.html.fromstring(resp.text)

terms = [(x.find('span').text.strip(), urljoin(source_url, x.get('href')))
         for x in root.cssselect('.menu-treemenu')[0].cssselect('a')]

data = []

for term_name, term_url in terms:
    while term_url:
        print term_url
        term_resp = requests.get(term_url)
        term_root = lxml.html.fromstring(term_resp.text)

        trs = term_root.cssselect('.jsn-infotable')[0].cssselect('tr')[1:]

        for tr in trs:
            member = {}
            member['term'] = term_name
            member['chamber'] = 'National Assembly'

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
            # import pdb;pdb.set_trace()

            data.append(member)

        next_links = term_root.cssselect('a[title=Next]')
        term_url = urljoin(term_url, next_links[0].get('href')) if next_links else None

scraperwiki.sqlite.save(unique_keys=['name', 'term'], data=data)

