import re
from urlparse import urljoin, urlsplit, parse_qs

from HTMLParser import HTMLParser
unescape = HTMLParser().unescape

import requests
import lxml.html
import execjs

from slugify import slugify_unicode

sources = (
    ('National Council', 'http://www.parliament.na/index.php?option=com_contact&view=category&id=108&Itemid=1483'),
    ('National Assembly', 'http://www.parliament.gov.na/index.php?option=com_contact&view=category&id=104&Itemid=1479'),
    )


def unjs_email(script):
    """Takes a javascript email mangling script and returns the email address."""

    # Get hold of the lines of javascript which aren't fiddling with the DOM
    jslines = [x.strip() for x in re.search(r'<!--(.*)//-->', script, re.M | re.S).group(1).strip().splitlines() if not x.strip().startswith('document')]

    # The name of the variable containing the variable containing the email address
    # varies, so find it by regex.
    varname = re.search(r'var (addy\d+)', script).group(1)
    jslines.append('return {}'.format(varname))

    js = '(function() {{{}}})()'.format(' '.join(jslines))

    return unescape(execjs.eval(js))


data = {}
term_data = []

def handle_chamber(chamber_name, source_url, data, term_data):
    resp = requests.get(source_url)

    root = lxml.html.fromstring(resp.text)

    terms = [(x.find('span').text.strip(), urljoin(source_url, x.get('href')))
             for x in root.cssselect('.menu-treemenu')[0].cssselect('a')]

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
                name, note = re.match(r'\s+([^\(]+)\s*(?:\((.+)\)+)?', name_link.text).groups()
                member['name'] = name.strip()
                if note:
                    member['note'] = note

                member['id'] = slugify_unicode(member['name'])
                details_url = member['details_url'] = urljoin(source_url, name_link.get('href'))

                try:
                    member['party'] = tr.cssselect('.jsn-table-column-country')[0].text.strip()
                except AttributeError:
                    # Karupu, Sebastiaan, for example, has nothing in this column.
                    # http://www.parliament.gov.na/index.php?option=com_contact&view=category&id=104&Itemid=1479&limitstart=40
                    member['party'] = ''

                try:
                    script = tr.cssselect('.jsn-table-column-email')[0].getchildren()[0].text_content()
                except (AttributeError, IndexError):
                    # No no email for this person.
                    script = None
                else:
                    member['email'] = unjs_email(script)


                # # Get hold of the lines of javascript which aren't fiddling with the DOM
                # jslines = [x.strip() for x in re.search(r'<!--(.*)//-->', mailto_script, re.M | re.S).group(1).strip().splitlines() if not x.strip().startswith('document')]

                # # The name of the variable containing the variable containing the email address
                # # varies, so find it by regex.
                # varname = re.search(r'var (addy\d+)', mailto_script).group(1)
                # jslines.append('return {}'.format(varname))

                # js = '(function() {{{}}})()'.format(' '.join(jslines))
                # member['email'] = unescape(execjs.eval(js))

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


import scraperwiki
scraperwiki.sqlite.save(unique_keys=['id'], data=term_data, table_name='terms')
scraperwiki.sqlite.save(unique_keys=['name', 'term'], data=data.values())

